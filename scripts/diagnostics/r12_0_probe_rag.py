"""R12-0 read-only Chroma probe (NO write, NO Gemini).

영역 C 진단용. 기본 모드는 임베딩/OpenAI 호출 0건:
  - b_dataset_rag 컬렉션 통계(총 카드 수, problem_type 분포, source 분포)
  - 건조 관련 키워드(영/한) 카드 검색 (documents + metadata 텍스트 매칭)
  - R11 결과 JSON(eval/after_acc_r10_v2_rag_ok.json)의 건조 6건 stored top_3_rag 인용

선택 모드(R12_PROBE_EMBED=1 일 때만): observed_symptoms를 그대로 임베딩 쿼리로
던져 top_10을 본다. OpenAI 임베딩(ada-002) 과금 발생 — 기본 OFF.

읽기 전용 보장: chromadb.PersistentClient(get_collection/get/query)만 사용.
add/upsert/update/delete/modify 호출 없음.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VECTOR_DB = ROOT / "data" / "vector_db"
EVAL_JSON = ROOT / "eval" / "after_acc_r10_v2_rag_ok.json"
B_COLL = "b_dataset_rag"

DRY_IDS = [
    "self_haengun_002",
    "self_haengun_003",
    "self_haengun_005",
    "self_haengun_006",
    "self_haengun_008",
    "inat_epipremnum_aureum_004",
]

DRY_KEYWORDS_EN = [
    "underwatering", "drought", "dry soil", "dehydration", "water stress",
    "low humidity", "wilting", "crispy", "leaf scorch", "scorch", "dry ",
    "underwater", "drying", "wilt",
]
DRY_KEYWORDS_KO = ["건조", "수분 부족", "물 부족", "시듦", "시들"]


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def probe_collection_stats(coll):
    _section(f"C.1  {B_COLL} 컬렉션 통계 (read-only)")
    got = coll.get(include=["documents", "metadatas"])
    ids = got.get("ids") or []
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    print(f"총 카드 수: {len(ids)}")

    pt = Counter(str((m or {}).get("problem_type") or "<none>") for m in metas)
    print("\nproblem_type 분포:")
    for k, v in pt.most_common():
        print(f"  {k:<14} {v}")

    src = Counter(str((m or {}).get("source") or "<none>") for m in metas)
    print("\nsource 분포:")
    for k, v in src.most_common():
        print(f"  {k:<22} {v}")

    keyset: Counter = Counter()
    for m in metas:
        for k in (m or {}).keys():
            keyset[k] += 1
    print("\n메타데이터 키 인벤토리 (key: 등장 카드 수):")
    for k, v in keyset.most_common():
        print(f"  {k:<16} {v}")
    return ids, docs, metas


def probe_dry_keyword_cards(ids, docs, metas) -> None:
    _section("C.1  건조 관련 카드 검색 (documents + metadata 텍스트 매칭)")
    for label, kws in (("EN", DRY_KEYWORDS_EN), ("KO", DRY_KEYWORDS_KO)):
        print(f"\n[{label}] 키워드별 매칭 카드 수:")
        for kw in kws:
            hits = []
            for cid, doc, meta in zip(ids, docs, metas):
                blob = (str(doc or "") + " " + json.dumps(meta or {}, ensure_ascii=False)).lower()
                if kw.lower() in blob:
                    hits.append(cid)
            mark = "" if hits else "  (없음)"
            print(f"  {kw:<16} {len(hits):>2}{mark}")
            if hits:
                for h in hits[:8]:
                    print(f"       - {h}")


def probe_stored_top3(eval_json: Path) -> None:
    _section("C.2  건조 6건 stored top_3_rag (R11 JSON, OpenAI 호출 0건)")
    if not eval_json.exists():
        print(f"  [missing] {eval_json}")
        return
    d = json.loads(eval_json.read_text(encoding="utf-8"))
    pc = d.get("per_case") or []
    by_id = {c.get("image_id"): c for c in pc}
    for did in DRY_IDS:
        c = by_id.get(did)
        if not c:
            cand = [c for c in pc if did.split("_")[-1] in str(c.get("image_id"))]
            c = cand[0] if cand else None
        if not c:
            print(f"\n== {did}: per_case에 없음")
            continue
        print(f"\n== {c.get('image_id')}")
        print(f"   gt_true_status={c.get('gt_true_status')} pred_status={c.get('pred_status')} "
              f"gt_is_healthy={c.get('gt_is_healthy')} pred_is_healthy={c.get('pred_is_healthy')}")
        print(f"   guard_fired={c.get('guard_fired')} reason={c.get('guard_reason')} "
              f"pre_status={c.get('guard_pre_status')}")
        print(f"   observed_symptoms={c.get('observed_symptoms')}")
        print(f"   pred_cause={c.get('pred_cause')!r}")
        print(f"   guard_pre_cause={c.get('guard_pre_cause')!r}")
        t3 = c.get("top_3_rag") or []
        for i, r in enumerate(t3, 1):
            print(f"   top_3[{i}]: {r}")


def probe_embed_top10(coll) -> None:
    """선택 모드: 프로덕션 재현(EN) top_10. OpenAI 과금(gpt-4o-mini 번역 + ada-002 임베딩).

    retrieve_node와 동일한 쿼리 경로를 재현:
      observed_symptoms → dedup[:RAG_SYMPTOM_KEYWORD_MAX] → generate_english_keywords
      (gpt-4o-mini) → query_en = " ".join(keywords_en) → ada-002 embed → b_dataset top_10.
    plant_name은 query_en에 포함되지 않으므로(retrieve의 mq=query_en) analyze 불필요.
    """
    import asyncio  # noqa: PLC0415

    from langchain_openai import OpenAIEmbeddings  # noqa: PLC0415
    from app import graph as graph_mod  # noqa: PLC0415
    from app import model_utils  # noqa: PLC0415

    _section("C.2(opt)  프로덕션 재현 EN top_10  [R12_PROBE_EMBED=1]")
    key = model_utils.get_openai_api_key()
    if not key:
        print("  OPENAI_API_KEY 없음 — skip")
        return
    emb = OpenAIEmbeddings(openai_api_key=key, model="text-embedding-ada-002")
    kmax = graph_mod.RAG_SYMPTOM_KEYWORD_MAX
    d = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    by_id = {c.get("image_id"): c for c in (d.get("per_case") or [])}

    # 모든 번역을 단일 이벤트 루프에서 처리 (asyncio.run 반복 시 httpx 정리 경고 방지)
    async def _translate_all() -> dict[str, tuple[list[str], list[str]]]:
        out: dict[str, tuple[list[str], list[str]]] = {}
        for did in DRY_IDS:
            c = by_id.get(did)
            if not c:
                continue
            syms = [s.strip() for s in (c.get("observed_symptoms") or []) if s and str(s).strip()]
            keywords_ko = list(dict.fromkeys(syms))[:kmax]
            keywords_en = await model_utils.generate_english_keywords(keywords_ko)
            out[did] = (keywords_ko, keywords_en)
        return out

    translations = asyncio.run(_translate_all())
    for did in DRY_IDS:
        if did not in translations:
            continue
        keywords_ko, keywords_en = translations[did]
        query_en = " ".join(keywords_en).strip()
        qe = emb.embed_query(query_en)
        res = coll.query(query_embeddings=[qe], n_results=10,
                         include=["documents", "metadatas", "distances"])
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        ids = (res.get("ids") or [[]])[0]
        print(f"\n== {did}")
        print(f"   keywords_ko={keywords_ko}")
        print(f"   query_en={query_en!r}")
        for i, (cid, m, dist) in enumerate(zip(ids, metas, dists), 1):
            sim = 1.0 - float(dist)
            pt = (m or {}).get("problem_type")
            title = (m or {}).get("title") or (m or {}).get("card_id")
            print(f"   {i:>2}. sim={sim:.4f} pt={pt!r:<12} {cid}  {title}")


def main() -> None:
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    print("컬렉션 목록:", [c.name for c in client.list_collections()])
    coll = client.get_collection(B_COLL)
    ids, docs, metas = probe_collection_stats(coll)
    probe_dry_keyword_cards(ids, docs, metas)
    probe_stored_top3(EVAL_JSON)
    if os.environ.get("R12_PROBE_EMBED") == "1":
        probe_embed_top10(coll)
    else:
        print("\n[note] 임베딩 top_10 probe 생략 (R12_PROBE_EMBED=1 로 활성화, OpenAI 과금)")


if __name__ == "__main__":
    main()
