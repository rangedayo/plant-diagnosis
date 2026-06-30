"""
LangGraph: analyze → keyword → retrieve → generate ([1-5] Gemini 경로)
RAG: SVC05 기반 Chroma, cosine 유사도 필터 후 생성
"""

from __future__ import annotations

import asyncio
import logging
import threading
from itertools import zip_longest
from pathlib import Path
from typing import Any, TypedDict

import chromadb
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import END, StateGraph

from app import care_guide as care_guide_mod
from app import model_utils
from app.nodes.analyze import make_analyze_node
from app.vision.base import VisionProvider

logger = logging.getLogger("plant_api")

DEBUG = True

# multi-RAG ([B-2]): b_dataset 메인(top_k=7) + a_dataset_rag 보조(top_k=3) — 합 10 기준
MAIN_TOP_K = 3              # 비중 재조정: a_dataset_rag 보조
B_DATASET_TOP_K = 7         # 비중 재조정: b_dataset 메인
# 검색 후 필터: cosine similarity(임베딩) 기준
RAG_MIN_COSINE_SIMILARITY = 0.65
# 임베딩 모델: 적재(build_*_rag.py)와 검색이 같아야 cosine이 유효하다.
# langchain_openai 기본값을 코드에 명시 고정 — 기본값 변경 사고 방지(적재 벡터와 동일).
EMBEDDING_MODEL = "text-embedding-ada-002"
# 필터 통과 문서만 있을 때, 최고 유사도가 이 값 미만이면 '약한 근거' 안내 (raw cosine)
RAG_WEAK_MAX_SIMILARITY = 0.72
# 랭킹 가중치
UC_IPM_SOLUTION_SIM_PENALTY = 0.85
B_DATASET_SIM_WEIGHT = 1.0  # 페널티 제거 (가설 직격). 상수 유지로 명명 일관성 + 향후 조정 여지
PLANT_NAME_MATCH_BOOST = 0.1
GENERIC_DOC_PENALTY = 0.9
# [1-6] keyword_node가 RAG 쿼리에 쓰는 observed_symptoms 명사구 최대 개수.
RAG_SYMPTOM_KEYWORD_MAX = 5

HEALTHY_KEYWORDS = ["건강", "이상 없음", "문제 없음", "정상", "깨끗", "갈변 없음"]

# ── [status guard] generate over-escalate 후처리 교정 ────────────────────────
# generate 설득 3회(B-4b 프롬프트 / B-4c tie·cosmetic 룰 / B' 종 사실 RAG)가 모두
# 커버-종 FP 순효과 0. 입력 신호로는 안 풀린다가 측정으로 확정 → generate 출력 뒤에서
# 코드가 status enum 값만 교정(설득이 아니라 우회). JSON 구조·enum 집합·한국어 설명 불변.
GUARD_HEALTHY_STATUS = "건강"
# 병변(비건강 사수) 토큰 — 1개라도 있으면 건강 교정 금지(FN 0 안전판).
# 도출: eval/after_phase_b_prime{,_run1,_run2} TP 전수가 동반한 단어
# (고사·마름·황화·반점·처짐·줄기 고사·손상). TP를 깎지 않으려면 이 분리선이 핵심.
STATUS_GUARD_LESION_TOKENS: tuple[str, ...] = (
    "고사", "마름", "마른", "시들", "시듦", "위조",
    "황화", "반점", "괴사", "부패", "썩", "무름",
    "처짐", "주름", "손상", "절단", "찢", "구멍", "뚫",
    "확산", "번짐", "줄기", "부착", "물질",
    "백색", "흰", "검은", "흑색", "곰팡",
)
# cosmetic(건강쪽 신호) — 끝·가장자리·소수 잎 국한 + 변색. B-4c §5 분리선 재현.
STATUS_GUARD_COSMETIC_LOCATION: tuple[str, ...] = (
    "잎끝", "잎 끝", "끝부분", "끝 부분", "가장자리",
    "일부", "자루", "엽초", "잎집", "불염포", "꽃",
)
STATUS_GUARD_COSMETIC_DISCOLOR: tuple[str, ...] = ("갈변", "변색", "갈색")
STATUS_GUARD_DISEASE_TOP1: tuple[str, ...] = ("disease", "pest")
# [R12a] 하부 위치 신호 토큰 — "아래쪽 잎 갈변"은 말단(잎끝·가장자리) cosmetic이 아니라
# 건조 등 진행성 신호일 수 있다. cosmetic 건강 교정을 차단(veto)해 over-correct로 인한
# FN을 막는다. lesion veto(규칙 2)와 동형의 보수적 FN-0 안전판. 부분 일치(substring).
STATUS_GUARD_PROGRESSIVE_LOCATION: tuple[str, ...] = ("아래쪽", "하엽", "하부", "하단")


def _symptom_has_lesion(symptom: str) -> bool:
    """병변(비건강) 단어 포함 여부 — FN 0 안전판의 핵심 판정."""
    return any(tok in symptom for tok in STATUS_GUARD_LESION_TOKENS)


def _symptom_is_cosmetic(symptom: str) -> bool:
    """끝·가장자리·소수 잎 국한 변색만인 cosmetic 증상인지 (병변 단어 없을 때만)."""
    if _symptom_has_lesion(symptom):
        return False
    has_loc = any(tok in symptom for tok in STATUS_GUARD_COSMETIC_LOCATION)
    has_disc = any(tok in symptom for tok in STATUS_GUARD_COSMETIC_DISCOLOR)
    return has_loc and has_disc


def _symptom_has_progressive_location(symptom: str) -> bool:
    """하부 위치(아래쪽·하엽 등) 진행성 신호 포함 여부 — cosmetic 건강 교정 veto용 (R12a)."""
    return any(tok in symptom for tok in STATUS_GUARD_PROGRESSIVE_LOCATION)


def apply_status_guard(
    status: str | None,
    observed_symptoms: list[str] | None,
    top_1_problem_type: str | None,
) -> tuple[str, str | None]:
    """generate over-escalate 교정. ``(교정된 status, 발동 사유 | None)`` 반환.

    이진 게이트(건강↔비건강)만 교정 — enum 값만 바꾸고 JSON 구조·설명문은 손대지 않는다.
    보수적: 병변 단어 1개라도 있으면 비건강 유지(FN 0 사수 우선). 애매하면 LLM status 유지.
    """
    cur = str(status or "").strip()
    if cur == GUARD_HEALTHY_STATUS:
        return cur, None  # 이미 건강 — guard는 over-escalate만 교정
    syms = [str(s) for s in (observed_symptoms or []) if str(s).strip()]
    # 규칙 1: 증상 empty → 건강
    if not syms:
        return GUARD_HEALTHY_STATUS, "empty_symptoms"
    # 규칙 2: 병변 단어 1개라도 → 유지(비건강) — FN 0 안전판
    if any(_symptom_has_lesion(s) for s in syms):
        return cur, None
    # 규칙 3: 전 증상 cosmetic + 비-disease/pest top_1 → 건강 교정 (핵심)
    if all(_symptom_is_cosmetic(s) for s in syms):
        # [R12a] 하부 위치 veto — 증상에 "아래쪽·하엽" 등 진행성 위치 신호가 있으면
        # 말단 cosmetic으로 보지 않고 건강 교정을 차단(비건강 유지). lesion veto와 동형.
        # status 미변경이므로 (cur, None) 반환 — guard_fired=False·cause 재생성 미발동.
        if any(_symptom_has_progressive_location(s) for s in syms):
            return cur, None
        top1 = str(top_1_problem_type or "").strip().lower()
        if top1 not in STATUS_GUARD_DISEASE_TOP1:
            return GUARD_HEALTHY_STATUS, "all_cosmetic_nondisease_top1"
        return cur, None  # disease/pest top_1 → 보수적 유지
    # 규칙 4: 애매(cosmetic도 병변도 아닌 증상 혼재) → 유지
    return cur, None


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
    # [B-4b] generate가 RAG problem_type 분포를 활용하도록 메타 노출
    rag_metas: list[dict[str, Any]]  # 필터 통과 문서의 메타(problem_type 포함)
    rag_sims: list[float]  # 필터 통과 문서의 raw cosine (rag_metas와 정렬 일치)
    top_3_problem_type_weighted: dict[str, Any]  # top_3 sim 가중 다수결
    structured_result: dict[str, Any]
    # [status guard] over-escalate 교정 발동 내역 (측정 진단용)
    status_guard: dict[str, Any]
    # [기능 (b)] 종명 키 케어 가이드 (진단과 무관, 항상 첨부 시도; 미커버 시 None)
    care_guide: dict[str, Any] | None
    # [챗봇 2차 보정] 객관식 답변 — 1차엔 없음(None), 2차 /diagnose/refine에서만 채워짐.
    # generate에 참고 맥락으로만 합류(context_summary), observed_symptoms 불변(게이트 보존).
    followup_answers: list[dict[str, str]] | None


def _vector_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "vector_db"


# Chroma PersistentClient 싱글톤 (db_path별 1개) — 쿼리마다 신규 생성 방지(재발방지 #2).
# chromadb는 같은 path에 다중 PersistentClient 생성을 권장하지 않으며, 반복 생성은
# 트랜지언트 HNSW 읽기 실패 정황과 연결됐었다(ACC-fix2). 검색은 읽기 전용이라 안전.
_chroma_clients: dict[str, Any] = {}
_chroma_client_lock = threading.Lock()


def _get_chroma_client(db_path: str) -> Any:
    """db_path별 PersistentClient를 캐시해 재사용(double-checked locking, 스레드 안전)."""
    client = _chroma_clients.get(db_path)
    if client is None:
        with _chroma_client_lock:
            client = _chroma_clients.get(db_path)
            if client is None:
                client = chromadb.PersistentClient(path=db_path)
                _chroma_clients[db_path] = client
    return client


def _embed_query_sync(query: str) -> tuple[list[float] | None, str | None]:
    """쿼리를 1회 임베딩. (embedding, error) — 실패 시 (None, 메시지).

    두 컬렉션(b_dataset·a_dataset)이 같은 쿼리를 쓰므로 임베딩을 1번만 만들어
    재사용한다(쿼리당 OpenAI 임베딩 호출 2회 → 1회).
    """
    key = model_utils.get_openai_api_key()
    if not key:
        logger.warning("Chroma 검색 생략: OPENAI_API_KEY 없음")
        return None, "OPENAI_API_KEY 미설정"
    try:
        emb = OpenAIEmbeddings(openai_api_key=key, model=EMBEDDING_MODEL)
        return emb.embed_query(query), None
    except Exception as e:
        logger.exception("쿼리 임베딩 중 예외")
        return None, f"쿼리 임베딩 예외: {e}"


def _chroma_query_sync(
    query_embedding: list[float],
    db_path: str,
    top_k: int,
    collection_name: str,
) -> tuple[list[str], list[dict[str, Any] | None], list[float], str | None]:
    """미리 임베딩한 쿼리로 Chroma cosine 검색. 마지막 값은 시스템 오류(성공 시 None)."""
    try:
        qe = query_embedding
        client = _get_chroma_client(db_path)
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
    """merge·정렬용: b_dataset 가중·UC_IPM solution 구간 페널티."""
    s = float(raw_cosine)
    if rag_source == "b_dataset":
        s *= B_DATASET_SIM_WEIGHT
        logger.debug(
            "rank: b_dataset sim weight raw=%.4f -> %.4f",
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
    b_dataset_triples: list[tuple[str, dict[str, Any], float]],
    main_triples: list[tuple[str, dict[str, Any], float]],
    *,
    b_dataset_top_k: int,
    main_top_k: int,
) -> tuple[list[str], list[dict[str, Any]], list[float], list[float]]:
    """
    소스별 raw cosine 정렬 → merge_sim(가중) 재정렬 후
    b_dataset 상위 b_dataset_top_k + main 상위 main_top_k를 먼저 넣고 나머지 풀을 합친 뒤
    merge_sim 기준으로 정렬, 문서 기준 중복 제거.
    반환: docs, metas, raw_cosine 리스트, merge_sim 리스트(동일 순서).
    """
    b_enriched: list[tuple[str, dict[str, Any], float, float]] = []
    for doc, meta, raw in b_dataset_triples:
        rs = str(meta.get("_rag_source") or "b_dataset")
        ms = _merge_similarity_for_ranking(raw, meta, rag_source=rs)
        b_enriched.append((doc, meta, raw, ms))
    m_enriched: list[tuple[str, dict[str, Any], float, float]] = []
    for doc, meta, raw in main_triples:
        rs = str(meta.get("_rag_source") or "main")
        ms = _merge_similarity_for_ranking(raw, meta, rag_source=rs)
        m_enriched.append((doc, meta, raw, ms))

    b_sorted = sorted(b_enriched, key=lambda t: -t[3])
    m_sorted = sorted(m_enriched, key=lambda t: -t[3])
    take_b = min(b_dataset_top_k, len(b_sorted))
    take_m = min(main_top_k, len(m_sorted))
    b_selected = b_sorted[:take_b]
    main_selected = m_sorted[:take_m]
    remaining_pool = b_sorted[take_b:] + m_sorted[take_m:]
    pool = list(b_selected) + list(main_selected) + list(remaining_pool)
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
        "retrieve: merge_rag b_dataset_top_k=%d main_top_k=%d merged=%d (가중 후 정렬)",
        take_b,
        take_m,
        len(merged_docs),
    )
    return merged_docs, merged_metas, merged_raw, merged_merge_sims


def _doc_plant_for_ranking(doc: str, meta: dict[str, Any]) -> str:
    """a_dataset_rag는 메타 plant_name, 그 외(b_dataset 등)는 plant_name 메타 없음 → generic."""
    m = meta or {}
    pn = (m.get("plant_name") or "").strip()
    if pn:
        return pn
    return "generic"


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


def _weighted_problem_type_majority(
    metas: list[dict[str, Any]], sims: list[float]
) -> dict[str, Any]:
    """top_N의 problem_type을 raw cosine으로 가중합 다수결.

    a_dataset_rag 문서는 problem_type 메타가 없어(빈 문자열) 가중에서 제외된다
    (eval_retrieval 일관성). 1위·2위 가중합 차이가 전체의 5% 미만이면 'tie'.

    Returns:
        {
            "majority": "abiotic"|"disease"|"nutrient"|"env"|"pest"
                        |"general"|"frame"|"tie",
            "distribution": {"abiotic": 0.42, ...},  # 가중합 정규화
            "top_problem_type": "abiotic"|"" (top_1 카드의 problem_type),
        }
    """
    weights: dict[str, float] = {}
    for meta, sim in zip(metas or [], sims or []):
        pt = str((meta or {}).get("problem_type") or "").strip()
        if not pt:
            continue
        weights[pt] = weights.get(pt, 0.0) + max(float(sim), 0.0)

    if not weights:
        return {"majority": "tie", "distribution": {}, "top_problem_type": ""}

    total = sum(weights.values()) or 1.0
    distribution = {k: round(v / total, 4) for k, v in weights.items()}

    sorted_weights = sorted(weights.items(), key=lambda x: -x[1])
    if len(sorted_weights) == 1:
        majority = sorted_weights[0][0]
    elif sorted_weights[0][1] - sorted_weights[1][1] < 0.05 * total:
        majority = "tie"
    else:
        majority = sorted_weights[0][0]

    top_pt = str((metas[0] or {}).get("problem_type") or "") if metas else ""
    return {
        "majority": majority,
        "distribution": distribution,
        "top_problem_type": top_pt,
    }


def _tag_doc_with_problem_type(doc: str, meta: dict[str, Any] | None) -> str:
    """카드 본문 앞에 [problem_type] prefix를 박아 generate에 타입 노출 (결정 1C)."""
    pt = str((meta or {}).get("problem_type") or "").strip()
    if not pt:
        return doc
    if doc.startswith(f"[{pt}]"):
        return doc  # 중복 방지
    return f"[{pt}] {doc}"


async def run_generate(
    *,
    visual_description: str,
    plant_name: str | None,
    plant_name_korean: str | None,
    plant_confidence: str | None,
    alt_candidates: list[str],
    observed_symptoms: list[str],
    top_3_problem_type_weighted: dict[str, Any] | None,
    rag_docs: list[str],
    rag_failed: bool,
    rag_no_docs: bool,
    rag_weak_evidence: bool,
    followup_answers: list[dict[str, str]] | None = None,
) -> dict:
    """generate 본문 공유 callable — 1차 그래프 노드와 2차 보정(/diagnose/refine) 공용.

    1차/2차 동일 경로: context_summary 조립 → generate(gpt-4o-mini) → status guard →
    (교정 시) cause 재생성 → care_guide lookup. **1차 동작 불변**이 핵심: followup_answers가
    None/빈 값이면 기존 generate_node와 바이트 동일하게 작동한다.

    [2차 게이트 보존] observed_symptoms는 1차 값을 그대로 받아 guard 키로 사용 — 답변은
    context_summary [사용자 추가 입력] 블록으로만 합류하고 증상 배열엔 일절 미접촉.
    """
    if DEBUG:
        print("[DEBUG] final rag_context doc_count:", len(rag_docs or []))
    # [1-7] analyze 6필드 직접 사용 (decision #1 옵션 A). Plant.id 팩트 섹션 폐기.
    visual_description = visual_description or ""
    alt = alt_candidates or []
    symptoms = observed_symptoms or []
    alt_str = ", ".join(alt) if alt else "없음"
    symptoms_str = ", ".join(symptoms) if symptoms else "관찰된 이상 없음"
    # [B-4b] RAG problem_type 가중 다수결 분포를 generate에 노출 (결정 1C)
    top_3_pt = top_3_problem_type_weighted or {}
    majority = str(top_3_pt.get("majority") or "tie")
    dist = top_3_pt.get("distribution") or {}
    top_pt = str(top_3_pt.get("top_problem_type") or "")
    dist_str = (
        ", ".join(
            f"{k} {v:.2f}"
            for k, v in sorted(dist.items(), key=lambda x: -x[1])
        )
        or "없음"
    )
    context_summary = (
        f"묘사:\n{visual_description}\n\n"
        f"[관찰 정보]\n"
        f"- 식물명(학명 1위): {plant_name}\n"
        f"- 식물명(통명): {plant_name_korean}\n"
        f"- 식별 신뢰도: {plant_confidence}\n"
        f"- 대안 후보: {alt_str}\n"
        f"- 관찰된 증상: {symptoms_str}\n\n"
        f"[검색된 자료의 타입 분포 (top_3 sim 가중)]\n"
        f"- 우세 타입: {majority}\n"
        f"- 1위 카드 타입: {top_pt}\n"
        f"- 분포: {dist_str}\n"
    )
    # [2차 보정] 객관식 답변 가산 — 답변이 있을 때만 [사용자 추가 입력] 블록 추가.
    # generate는 이를 참고 맥락으로만 사용(프롬프트 판정 규칙 무변경). 1차는 None → 미추가.
    answers = [
        a
        for a in (followup_answers or [])
        if str((a or {}).get("answer") or "").strip()
    ]
    if answers:
        answer_lines = "\n".join(
            f"- {str(a.get('question') or '').strip()}: {str(a.get('answer') or '').strip()}"
            for a in answers
        )
        context_summary += f"\n[사용자 추가 입력]\n{answer_lines}\n"
    rag_chunks = "\n\n".join(rag_docs or [])
    structured = await model_utils.generate_structured_diagnosis_with_gpt(
        context_summary,
        rag_chunks,
        rag_failed=bool(rag_failed),
        rag_no_docs=bool(rag_no_docs),
        rag_weak_evidence=bool(rag_weak_evidence),
        has_followup_answers=bool(answers),
    )
    # [status guard] generate over-escalate 교정 — 입력 설득 3회 실패(B-4b/c/B') 후
    # 출력 뒤에서 status enum 값만 교정. FN 0 사수(병변 단어 veto).
    pre_status = structured.get("status") if isinstance(structured, dict) else None
    new_status, guard_reason = apply_status_guard(pre_status, symptoms, top_pt)
    guard_fired = guard_reason is not None
    pre_cause = structured.get("cause") if isinstance(structured, dict) else None
    cause_regenerated = False
    if guard_fired and isinstance(structured, dict):
        # status 교정과 cause 텍스트 정합: generate의 "병해 의심" cause가
        # 교정된 status="건강"과 모순되므로 cause만 건강 전제로 재생성한다.
        # ⚠ status는 guard 확정값(new_status)으로 고정 — 재생성은 cause만 건드린다.
        new_cause = await model_utils.regenerate_healthy_cause(
            plant_name_korean or plant_name, symptoms
        )
        structured = {**structured, "status": new_status, "cause": new_cause}
        cause_regenerated = True
        logger.info(
            "status_guard 발동: %r→%r 사유=%s 증상=%s top_1=%r (cause 재생성)",
            pre_status, new_status, guard_reason, symptoms, top_pt,
        )
    # [기능 (b)] 케어 가이드 첨부 — 진단(structured/guard) 확정 뒤 별도 lookup.
    # status 무관 항상 시도(건강도 지속 관리법). 진단 필드는 일절 건드리지 않는다.
    care_guide = care_guide_mod.lookup_care_guide(plant_name_korean, plant_name)
    if DEBUG:
        _ck = (care_guide or {}).get("species_key") if care_guide else None
        print("[DEBUG] care_guide species_key:", _ck)
    return {
        "structured_result": structured,
        "status_guard": {
            "fired": bool(guard_fired),
            "reason": guard_reason,
            "pre_status": pre_status,
            "post_status": new_status,
            "top_1_problem_type": top_pt,
            "cause_regenerated": cause_regenerated,
            "pre_cause": pre_cause,
        },
        "care_guide": care_guide,
    }


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
                "[INFO] query_en empty → a_dataset_rag uses query_ko (영어 코퍼스 폴백)",
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
            # b_dataset·main 모두 영문 코퍼스 → 영문 쿼리 우선(query_ko 폴백)
            mq = (query_en or query_ko).strip()
            # 두 컬렉션이 같은 쿼리를 쓰므로 임베딩은 1회만(쿼리당 OpenAI 임베딩 2회 → 1회)
            qe, emb_err = _embed_query_sync(mq)
            if qe is None:
                return ([], [], [], [], [], [], emb_err, emb_err)
            docs_b, metas_b, sims_b, err_b = _chroma_query_sync(
                qe, db_path, B_DATASET_TOP_K, "b_dataset_rag"
            )
            docs_main, metas_main, sims_main, err_main = _chroma_query_sync(
                qe, db_path, MAIN_TOP_K, "a_dataset_rag"
            )
            return (
                docs_b,
                metas_b,
                sims_b,
                docs_main,
                metas_main,
                sims_main,
                err_b,
                err_main,
            )

        try:
            (
                docs_b,
                metas_b,
                sims_b,
                docs_main,
                metas_main,
                sims_main,
                err_b,
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

        if err_b:
            logger.warning("retrieve: b_dataset_rag 시스템 오류: %s", err_b)
        if err_main:
            logger.warning("retrieve: a_dataset_rag 시스템 오류: %s", err_main)
        rag_system_failed = bool(err_b and err_main)
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
            print("[DEBUG] b_docs:", len(docs_b))
            print("[DEBUG] main_docs:", len(docs_main))

        t_b = _tag_triples_rag_source(
            _triples_from_chroma(docs_b, metas_b, sims_b),
            "b_dataset",
        )
        t_main = _tag_triples_rag_source(
            _triples_from_chroma(docs_main, metas_main, sims_main),
            "main",
        )
        docs, metas, raw_sims, merge_sims = _merge_rag_triples(
            t_b,
            t_main,
            b_dataset_top_k=B_DATASET_TOP_K,
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
        # [B-4b] problem_type 가중 다수결 (top_3, raw cosine 가중) + 카드 prefix
        top_3_pt_weighted = _weighted_problem_type_majority(
            filtered_metas[:3], filtered_sims[:3]
        )
        docs_tagged = [
            _tag_doc_with_problem_type(doc, meta)
            for doc, meta in zip_longest(filtered_docs, filtered_metas, fillvalue=None)
            if doc is not None
        ]
        logger.info(
            "retrieve: top_3 problem_type 가중 다수결=%s",
            top_3_pt_weighted,
        )
        ret = {
            "rag_docs": docs_tagged,
            "rag_metas": list(filtered_metas or []),
            "rag_sims": list(filtered_sims or []),
            "top_3_problem_type_weighted": top_3_pt_weighted,
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
        # 본문은 모듈 레벨 run_generate로 추출 — 1차 노드와 2차 보정(/diagnose/refine)이
        # 같은 callable을 호출한다. 1차는 followup_answers 없음(None) → 기존과 동일 동작.
        return await run_generate(
            visual_description=state.get("visual_description") or "",
            plant_name=state.get("plant_name"),
            plant_name_korean=state.get("plant_name_korean"),
            plant_confidence=state.get("plant_confidence"),
            alt_candidates=state.get("alt_candidates") or [],
            observed_symptoms=state.get("observed_symptoms") or [],
            top_3_problem_type_weighted=state.get("top_3_problem_type_weighted") or {},
            rag_docs=state.get("rag_docs") or [],
            rag_failed=bool(state.get("rag_failed")),
            rag_no_docs=bool(state.get("rag_no_docs")),
            rag_weak_evidence=bool(state.get("rag_weak_evidence")),
            followup_answers=state.get("followup_answers"),
        )

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
