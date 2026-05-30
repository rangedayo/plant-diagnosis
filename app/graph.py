"""
LangGraph: analyze → keyword → retrieve → generate ([1-5] Gemini 경로)
RAG: SVC05 기반 Chroma, cosine 유사도 필터 후 생성
"""

from __future__ import annotations

import asyncio
import logging
from itertools import zip_longest
from pathlib import Path
from typing import Any, TypedDict

import chromadb
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import END, StateGraph

from app import model_utils
from app.nodes.analyze import make_analyze_node
from app.vision.base import VisionProvider

logger = logging.getLogger("plant_api")

DEBUG = True

# multi-RAG: main_rag 중심(70%), ncpms 보조(30%) — 합 10 기준 (main 6~7, ncpms 3)
MAIN_TOP_K = 7
NCPMS_TOP_K = 3
# 검색 후 필터: cosine similarity(임베딩) 기준
RAG_MIN_COSINE_SIMILARITY = 0.65
# 필터 통과 문서만 있을 때, 최고 유사도가 이 값 미만이면 '약한 근거' 안내 (raw cosine)
RAG_WEAK_MAX_SIMILARITY = 0.72
# 랭킹 가중치
UC_IPM_SOLUTION_SIM_PENALTY = 0.85
NCPMS_SIM_WEIGHT = 0.8
PLANT_NAME_MATCH_BOOST = 0.1
GENERIC_DOC_PENALTY = 0.9
# [1-6] keyword_node가 RAG 쿼리에 쓰는 observed_symptoms 명사구 최대 개수.
RAG_SYMPTOM_KEYWORD_MAX = 5

HEALTHY_KEYWORDS = ["건강", "이상 없음", "문제 없음", "정상", "깨끗", "갈변 없음"]


class DiagnosisState(TypedDict, total=False):
    image_bytes: bytes
    plant_name: str | None
    # [1-5] analyze 6필드 (decision #1). plant_name은 기존 키와 공유.
    plant_name_korean: str | None
    plant_confidence: str | None  # 'low' | 'med' | 'high'
    alt_candidates: list[str]
    visual_description: str
    observed_symptoms: list[str]
    keywords: list[str]
    keywords_en: list[str]
    rag_query: str
    rag_docs: list[str]
    sick_keys: list[str]
    rag_doc_sick_pairs: list[dict[str, str]]
    rag_failed: bool  # True = 벡터 DB/API/예외 등 시스템 실패만
    rag_no_docs: bool  # True = 검색은 했으나 통과 문서 0건 (또는 검색 미수행)
    rag_weak_evidence: bool
    structured_result: dict[str, Any]


def _vector_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "vector_db"


def _chroma_query_sync(
    query: str,
    db_path: str,
    top_k: int,
    collection_name: str,
) -> tuple[list[str], list[dict[str, Any] | None], list[float], str | None]:
    """Chroma cosine 검색. 마지막 값은 시스템 오류 메시지(성공 시 None)."""
    key = model_utils.get_openai_api_key()
    if not key:
        logger.warning("Chroma 검색 생략: OPENAI_API_KEY 없음 (%s)", collection_name)
        return [], [], [], "OPENAI_API_KEY 미설정"
    try:
        emb = OpenAIEmbeddings(openai_api_key=key)
        qe = emb.embed_query(query)
        client = chromadb.PersistentClient(path=db_path)
        try:
            coll = client.get_collection(collection_name)
        except Exception as e:
            logger.warning("Chroma 컬렉션 로드 실패 (%s): %s", collection_name, e)
            return [], [], [], f"Chroma 컬렉션 로드 실패 ({collection_name}): {e}"
        res = coll.query(
            query_embeddings=[qe],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        docs = list((res.get("documents") or [[]])[0])
        metas = list((res.get("metadatas") or [[]])[0])
        dists = list((res.get("distances") or [[]])[0])
        similarities = [1.0 - float(d) for d in dists]
        return docs, metas, similarities, None
    except Exception as e:
        logger.exception("Chroma 검색 중 예외 (%s)", collection_name)
        return [], [], [], f"Chroma 검색 예외 ({collection_name}): {e}"


def _triples_from_chroma(
    docs: list[str],
    metas: list[dict[str, Any] | None],
    sims: list[float],
) -> list[tuple[str, dict[str, Any], float]]:
    out: list[tuple[str, dict[str, Any], float]] = []
    for doc, meta, sim in zip_longest(docs, metas, sims):
        if doc is None or sim is None:
            continue
        out.append((doc, meta if isinstance(meta, dict) else {}, float(sim)))
    return out


def _tag_triples_rag_source(
    triples: list[tuple[str, dict[str, Any], float]],
    rag_source: str,
) -> list[tuple[str, dict[str, Any], float]]:
    out: list[tuple[str, dict[str, Any], float]] = []
    for doc, meta, sim in triples:
        m = dict(meta)
        m["_rag_source"] = rag_source
        out.append((doc, m, sim))
    return out


def _merge_similarity_for_ranking(
    raw_cosine: float,
    meta: dict[str, Any],
    *,
    rag_source: str,
) -> float:
    """merge·정렬용: NCPMS 가중·UC_IPM solution 구간 페널티."""
    s = float(raw_cosine)
    if rag_source == "ncpms":
        s *= NCPMS_SIM_WEIGHT
        logger.debug(
            "rank: ncpms sim weight raw=%.4f -> %.4f",
            raw_cosine,
            s,
        )
    elif rag_source == "main":
        if meta.get("source") == "UC_IPM":
            s *= UC_IPM_SOLUTION_SIM_PENALTY
            logger.debug(
                "rank: UC_IPM solution penalty raw=%.4f -> %.4f",
                raw_cosine,
                s,
            )
    return s


def _merge_rag_triples(
    ncpms_triples: list[tuple[str, dict[str, Any], float]],
    main_triples: list[tuple[str, dict[str, Any], float]],
    *,
    ncpms_top_k: int,
    main_top_k: int,
) -> tuple[list[str], list[dict[str, Any]], list[float], list[float]]:
    """
    소스별 raw cosine 정렬 → merge_sim(가중) 재정렬 후
    ncpms 상위 ncpms_top_k + main 상위 main_top_k를 먼저 넣고 나머지 풀을 합친 뒤
    merge_sim 기준으로 정렬, 문서 기준 중복 제거.
    반환: docs, metas, raw_cosine 리스트, merge_sim 리스트(동일 순서).
    """
    n_enriched: list[tuple[str, dict[str, Any], float, float]] = []
    for doc, meta, raw in ncpms_triples:
        rs = str(meta.get("_rag_source") or "ncpms")
        ms = _merge_similarity_for_ranking(raw, meta, rag_source=rs)
        n_enriched.append((doc, meta, raw, ms))
    m_enriched: list[tuple[str, dict[str, Any], float, float]] = []
    for doc, meta, raw in main_triples:
        rs = str(meta.get("_rag_source") or "main")
        ms = _merge_similarity_for_ranking(raw, meta, rag_source=rs)
        m_enriched.append((doc, meta, raw, ms))

    n_sorted = sorted(n_enriched, key=lambda t: -t[3])
    m_sorted = sorted(m_enriched, key=lambda t: -t[3])
    take_n = min(ncpms_top_k, len(n_sorted))
    take_m = min(main_top_k, len(m_sorted))
    ncpms_selected = n_sorted[:take_n]
    main_selected = m_sorted[:take_m]
    remaining_pool = n_sorted[take_n:] + m_sorted[take_m:]
    pool = list(ncpms_selected) + list(main_selected) + list(remaining_pool)
    pool.sort(key=lambda t: -t[3])
    seen: set[str] = set()
    merged_docs: list[str] = []
    merged_metas: list[dict[str, Any]] = []
    merged_raw: list[float] = []
    merged_merge_sims: list[float] = []
    for doc, meta, raw, ms in pool:
        if doc in seen:
            continue
        seen.add(doc)
        merged_docs.append(doc)
        merged_metas.append(meta)
        merged_raw.append(raw)
        merged_merge_sims.append(ms)
    logger.info(
        "retrieve: merge_rag ncpms_top_k=%d main_top_k=%d merged=%d (가중 후 정렬)",
        take_n,
        take_m,
        len(merged_docs),
    )
    return merged_docs, merged_metas, merged_raw, merged_merge_sims


def _doc_first_token_as_crop(doc: str) -> str:
    """SVC05 문단은 보통 작물명(cropName)이 첫 토큰."""
    t = (doc or "").strip()
    if not t:
        return ""
    return t.split()[0]


def _doc_plant_for_ranking(doc: str, meta: dict[str, Any]) -> str:
    """main_rag는 메타 plant_name, NCPMS는 작물명(첫 토큰), 없으면 generic."""
    m = meta or {}
    pn = (m.get("plant_name") or "").strip()
    if pn:
        return pn
    if m.get("_rag_source") == "ncpms" or (m.get("sickKey") or "").strip():
        return _doc_first_token_as_crop(doc) or "generic"
    if m.get("source") in ("UC_IPM", "HOUSEPLANT"):
        return "generic"
    return _doc_first_token_as_crop(doc) or "generic"


def _final_rank_score(
    merge_sim: float,
    doc: str,
    meta: dict[str, Any],
    *,
    identified_plant: str | None,
) -> tuple[float, dict[str, Any]]:
    """merge 단계 가중 유사도 + generic·식물명 매칭(문서 제거 없음)."""
    score = float(merge_sim)
    dp = _doc_plant_for_ranking(doc, meta)
    detail: dict[str, Any] = {
        "doc_plant": dp,
        "merge_sim": merge_sim,
    }
    if dp == "generic":
        score *= GENERIC_DOC_PENALTY
        detail["generic_penalty"] = GENERIC_DOC_PENALTY
    ident = (identified_plant or "").strip()
    if ident and dp == ident:
        score += PLANT_NAME_MATCH_BOOST
        detail["plant_match_boost"] = PLANT_NAME_MATCH_BOOST
    detail["final_rank_score"] = score
    return score, detail


def _apply_plant_filter_after_similarity(
    docs: list[str],
    metas: list[dict[str, Any]],
    raw_sims: list[float],
    merge_sims: list[float],
    *,
    state: DiagnosisState,
) -> tuple[list[str], list[dict[str, Any]], list[float], bool]:
    """
    유사도 필터 통과 후: 문서 제거 없이 가중 랭킹만 적용.
    반환 raw_sims는 재정렬된 순서(약한 근거 판정용), similarity_only_rollback은 항상 False.
    """
    if not docs:
        return docs, metas, raw_sims, False

    identified = state.get("plant_name")
    ident_s = str(identified).strip() if identified is not None else ""

    triples = list(zip(docs, metas, raw_sims, merge_sims))
    scored: list[
        tuple[float, str, dict[str, Any], float, float, dict[str, Any]]
    ] = []
    for doc, meta, raw, ms in triples:
        fs, det = _final_rank_score(
            ms,
            doc,
            meta,
            identified_plant=ident_s or None,
        )
        scored.append((fs, doc, meta, raw, ms, det))

    scored.sort(key=lambda t: -t[0])
    rd = [t[1] for t in scored]
    rm = [t[2] for t in scored]
    rr = [t[3] for t in scored]
    for rank, (fs, doc, _meta, raw, ms, det) in enumerate(scored, start=1):
        logger.info(
            "retrieve: rank_adjust rank=%d final_score=%.4f raw_cos=%.4f merge_sim=%.4f "
            "doc_plant=%r ident_plant=%r detail=%s",
            rank,
            fs,
            raw,
            ms,
            det.get("doc_plant"),
            ident_s or None,
            det,
        )
    return rd, rm, rr, False


_compiled_graph = None


def build_diagnosis_graph(
    vision_provider: VisionProvider,
):
    # [1-5] analyze 경로. make_analyze_node는 6필드 dict만 반환(analyze.py, [1-4]).
    _analyze = make_analyze_node(vision_provider)

    async def analyze_node(state: DiagnosisState) -> dict:
        out = await _analyze(state)
        if DEBUG:
            print(
                "[DEBUG] analyze:",
                out.get("plant_name"),
                out.get("plant_name_korean"),
                out.get("plant_confidence"),
            )
        return out

    async def keyword_node(state: DiagnosisState) -> dict:
        # [1-6] decision #2: keyword_node는 영문 번역 전용으로 축소.
        # analyze가 만든 observed_symptoms(한국어 명사구)를 RAG 키워드로 그대로
        # 채택하고 영문 번역 1콜만 수행한다. build_rag_search_query_with_gpt /
        # estimate_fallback_plant_with_gpt 호출은 제거(중복 LLM 분석 제거).
        symptoms = [
            s.strip()
            for s in (state.get("observed_symptoms") or [])
            if s and str(s).strip()
        ]
        keywords_ko = list(dict.fromkeys(symptoms))[:RAG_SYMPTOM_KEYWORD_MAX]
        keywords_en = (
            await model_utils.generate_english_keywords(keywords_ko)
            if keywords_ko
            else []
        )
        plant_name = (state.get("plant_name") or "").strip()
        parts: list[str] = []
        if plant_name:
            parts.append(plant_name)
        parts.extend(keywords_ko)
        query_ko = " ".join(parts)
        out = {
            "rag_query": query_ko,
            "keywords": keywords_ko,
            "keywords_en": keywords_en,
        }
        if DEBUG:
            print("[DEBUG] observed_symptoms:", state.get("observed_symptoms"))
            print("[DEBUG] keywords:", out.get("keywords"))
            print("[DEBUG] keywords_en:", out.get("keywords_en"))
        return out

    async def retrieve_node(state: DiagnosisState) -> dict:
        query_ko = (state.get("rag_query") or "").strip()
        query_en = " ".join(state.get("keywords_en") or []).strip()
        pn = state.get("plant_name")
        fn = str(pn).strip() if pn is not None and str(pn).strip() else None
        if DEBUG:
            print("[DEBUG] query_ko:", query_ko)
        print("[DEBUG] query_en:", query_en)
        if not query_en:
            print(
                "[INFO] query_en empty → main_rag uses query_ko (영어 코퍼스 폴백)",
                flush=True,
            )
        logger.info(
            "retrieve: plant_name=%r final_plant_name=%r query_ko=%r query_en=%r",
            pn,
            fn,
            query_ko,
            query_en,
        )

        if not query_ko:
            logger.info("retrieve: query 비어 있음 → 검색 미수행 (rag_no_docs만 설정)")
            ret = {
                "rag_docs": [],
                "sick_keys": [],
                "rag_doc_sick_pairs": [],
                "rag_failed": False,
                "rag_no_docs": True,
                "rag_weak_evidence": False,
            }
            if DEBUG:
                print("[DEBUG] rag_docs count:", len(ret.get("rag_docs", [])))
            return ret

        is_healthy_hint_in_query = any(k in query_ko for k in HEALTHY_KEYWORDS)
        if is_healthy_hint_in_query:
            logger.info(
                "retrieve: 건강 관련 표현이 검색어에 포함됨 (참고용, RAG는 계속 수행)"
            )
            if DEBUG:
                print(
                    "[INFO] 건강 상태 감지 (참고용) — RAG 차단 없음",
                    flush=True,
                )

        db_path = str(_vector_db_path())
        loop = asyncio.get_running_loop()

        def _run() -> tuple[
            list[str],
            list[dict[str, Any] | None],
            list[float],
            list[str],
            list[dict[str, Any] | None],
            list[float],
            str | None,
            str | None,
        ]:
            docs_ncpms, metas_ncpms, sims_ncpms, err_ncpms = _chroma_query_sync(
                query_ko, db_path, NCPMS_TOP_K, "ncpms_rag"
            )
            mq = (query_en or query_ko).strip()
            docs_main, metas_main, sims_main, err_main = _chroma_query_sync(
                mq, db_path, MAIN_TOP_K, "main_rag"
            )
            return (
                docs_ncpms,
                metas_ncpms,
                sims_ncpms,
                docs_main,
                metas_main,
                sims_main,
                err_ncpms,
                err_main,
            )

        try:
            (
                docs_ncpms,
                metas_ncpms,
                sims_ncpms,
                docs_main,
                metas_main,
                sims_main,
                err_ncpms,
                err_main,
            ) = await loop.run_in_executor(None, _run)
        except Exception:
            logger.exception("retrieve: RAG 실행 중 예외 (시스템 실패)")
            return {
                "rag_docs": [],
                "sick_keys": [],
                "rag_doc_sick_pairs": [],
                "rag_failed": True,
                "rag_no_docs": True,
                "rag_weak_evidence": False,
            }

        if err_ncpms:
            logger.warning("retrieve: ncpms_rag 시스템 오류: %s", err_ncpms)
        if err_main:
            logger.warning("retrieve: main_rag 시스템 오류: %s", err_main)
        rag_system_failed = bool(err_ncpms and err_main)
        if rag_system_failed:
            logger.error(
                "retrieve: 두 컬렉션 모두 검색 실패 → rag_failed=True (시스템 오류)",
            )
            return {
                "rag_docs": [],
                "sick_keys": [],
                "rag_doc_sick_pairs": [],
                "rag_failed": True,
                "rag_no_docs": True,
                "rag_weak_evidence": False,
            }

        if DEBUG:
            print("[DEBUG] ncpms_docs:", len(docs_ncpms))
            print("[DEBUG] main_docs:", len(docs_main))

        t_ncpms = _tag_triples_rag_source(
            _triples_from_chroma(docs_ncpms, metas_ncpms, sims_ncpms),
            "ncpms",
        )
        t_main = _tag_triples_rag_source(
            _triples_from_chroma(docs_main, metas_main, sims_main),
            "main",
        )
        docs, metas, raw_sims, merge_sims = _merge_rag_triples(
            t_ncpms,
            t_main,
            ncpms_top_k=NCPMS_TOP_K,
            main_top_k=MAIN_TOP_K,
        )

        if DEBUG:
            print("[DEBUG] merged_docs:", len(docs))

        logger.info("retrieve: query_ko=%r query_en=%r", query_ko, query_en)
        for i, (doc, raw, ms) in enumerate(
            zip_longest(docs, raw_sims, merge_sims, fillvalue=None)
        ):
            if doc is None:
                continue
            logger.info(
                "retrieve: pre_filter rank=%d raw_cosine=%.4f merge_sim=%.4f",
                i + 1,
                float(raw) if raw is not None else float("nan"),
                float(ms) if ms is not None else float("nan"),
            )

        filtered_docs: list[str] = []
        filtered_metas: list[dict[str, Any]] = []
        filtered_raw: list[float] = []
        filtered_merge: list[float] = []
        for doc, meta, raw, ms in zip_longest(docs, metas, raw_sims, merge_sims):
            if doc is None or raw is None:
                continue
            if raw < RAG_MIN_COSINE_SIMILARITY:
                logger.debug(
                    "retrieve: skip doc below raw cosine threshold raw=%.4f < %.2f",
                    float(raw),
                    RAG_MIN_COSINE_SIMILARITY,
                )
                continue
            filtered_docs.append(doc)
            filtered_metas.append(meta if isinstance(meta, dict) else {})
            filtered_raw.append(float(raw))
            filtered_merge.append(float(ms) if ms is not None else float(raw))

        logger.info(
            "retrieve: 유사도 필터 raw_cosine (≥%.2f) 후 남은 문서 수=%d",
            RAG_MIN_COSINE_SIMILARITY,
            len(filtered_docs),
        )

        filtered_docs, filtered_metas, filtered_sims, _sim_rollback = (
            _apply_plant_filter_after_similarity(
                filtered_docs,
                filtered_metas,
                filtered_raw,
                filtered_merge,
                state=state,
            )
        )
        logger.info(
            "retrieve: 식물 필터 후 문서 수=%d (유사도만 롤백=%s)",
            len(filtered_docs),
            _sim_rollback,
        )

        rag_no_docs = len(filtered_docs) == 0
        rag_failed = False
        no_plant_id = pn is None or not str(pn).strip()
        rag_weak = no_plant_id or (
            not rag_no_docs
            and bool(filtered_sims)
            and max(filtered_sims) < RAG_WEAK_MAX_SIMILARITY
        )

        pairs: list[dict[str, str]] = []
        for doc, meta in zip_longest(filtered_docs, filtered_metas, fillvalue=None):
            m = meta if isinstance(meta, dict) else {}
            key = str(m.get("sickKey", "") or "")
            pairs.append({"doc": doc or "", "sickKey": key})

        raw_keys = [p["sickKey"] for p in pairs]
        clean_keys: list[str] = []
        seen: set[str] = set()
        for k in raw_keys:
            if not k or not k.startswith("D"):
                continue
            if k in seen:
                continue
            seen.add(k)
            clean_keys.append(k)

        logger.info(
            "retrieve 완료: sick_keys(정제)=%d pairs=%d rag_failed=%s rag_no_docs=%s rag_weak=%s",
            len(clean_keys),
            len(pairs),
            rag_failed,
            rag_no_docs,
            rag_weak,
        )
        ret = {
            "rag_docs": filtered_docs,
            "sick_keys": clean_keys,
            "rag_doc_sick_pairs": pairs,
            "rag_failed": rag_failed,
            "rag_no_docs": rag_no_docs,
            "rag_weak_evidence": rag_weak,
        }
        if DEBUG:
            print("[DEBUG] rag_docs count:", len(ret.get("rag_docs", [])))
        return ret

    async def generate_node(state: DiagnosisState) -> dict:
        if DEBUG:
            _rd = state.get("rag_docs") or []
            print("[DEBUG] final rag_context doc_count:", len(_rd))
        # [1-7] analyze 6필드 직접 사용 (decision #1 옵션 A). Plant.id 팩트 섹션 폐기.
        visual_description = state.get("visual_description") or ""
        plant_name = state.get("plant_name")
        plant_name_korean = state.get("plant_name_korean")
        plant_confidence = state.get("plant_confidence")
        alt = state.get("alt_candidates") or []
        symptoms = state.get("observed_symptoms") or []
        alt_str = ", ".join(alt) if alt else "없음"
        symptoms_str = ", ".join(symptoms) if symptoms else "관찰된 이상 없음"
        context_summary = (
            f"묘사:\n{visual_description}\n\n"
            f"[관찰 정보]\n"
            f"- 식물명(학명 1위): {plant_name}\n"
            f"- 식물명(통명): {plant_name_korean}\n"
            f"- 식별 신뢰도: {plant_confidence}\n"
            f"- 대안 후보: {alt_str}\n"
            f"- 관찰된 증상: {symptoms_str}\n"
        )
        rag_chunks = "\n\n".join(state.get("rag_docs") or [])
        structured = await model_utils.generate_structured_diagnosis_with_gpt(
            context_summary,
            rag_chunks,
            rag_failed=bool(state.get("rag_failed")),
            rag_no_docs=bool(state.get("rag_no_docs")),
            rag_weak_evidence=bool(state.get("rag_weak_evidence")),
        )
        return {"structured_result": structured}

    g = StateGraph(DiagnosisState)
    g.add_node("analyze", analyze_node)
    g.add_node("keyword", keyword_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("analyze")
    g.add_edge("analyze", "keyword")
    g.add_edge("keyword", "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


def init_graph(
    vision_provider: VisionProvider,
) -> None:
    global _compiled_graph
    _compiled_graph = build_diagnosis_graph(vision_provider)


def get_compiled_graph():
    if _compiled_graph is None:
        raise RuntimeError("LangGraph이 초기화되지 않았습니다.")
    return _compiled_graph
