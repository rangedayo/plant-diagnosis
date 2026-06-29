"""[B-3] retrieval 골든셋 측정 — Hit Rate@10 · MRR (외부 10 케이스, 자가검증화 방지).

eval/golden_set.json(외부 10 케이스 + acceptable_card_ids)을 읽어
각 케이스 symptom_en을 쿼리로 b_dataset_rag(top 7) + a_dataset_rag(top 3)를 검색하고
app.graph._merge_rag_triples 로직 그대로 가중 정렬·중복제거한 top 10 기준으로
Hit@10 / Reciprocal Rank를 계산한다.

- 쿼리: symptom_en (query_en 우선, [B-2] 결정 — b_dataset 영문 코퍼스)
- 매핑 실패 케이스(acceptable_card_ids 빈 리스트)는 메트릭 분모에서 제외
- 출력: eval/after_phase_b3_retrieval.json (BOM 없는 UTF-8)

graph.py 미변경(변수 격리) — 검색 상수·함수는 app.graph에서 import.

실행 (프로젝트 루트에서):

  .venv\\Scripts\\python.exe scripts\\eval_retrieval.py

`.env`에 OPENAI_API_KEY 필요 (검색 임베딩).
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app.graph import (  # noqa: E402
    B_DATASET_TOP_K,
    MAIN_TOP_K,
    _chroma_query_sync,
    _embed_query_sync,
    _merge_rag_triples,
    _tag_triples_rag_source,
    _triples_from_chroma,
    _vector_db_path,
)

GOLDEN_PATH = _ROOT / "eval" / "golden_set.json"
# 출력 파일명: EVAL_RETRIEVAL_OUT로 오버라이드(run_eval RUN_EVAL_OUT 패턴) — 기존 앵커 덮어쓰기 방지.
OUTPUT_PATH = _ROOT / "eval" / os.environ.get(
    "EVAL_RETRIEVAL_OUT", "after_phase_b3_retrieval.json"
)
TOP_N = 10


def _load_golden() -> list[dict[str, Any]]:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    cases = data.get("external_cases") or []
    if not cases:
        raise SystemExit(f"golden_set.json external_cases 비어 있음: {GOLDEN_PATH}")
    return cases


def _retrieve_top_n(query: str, db_path: str) -> list[dict[str, Any]]:
    """graph.retrieve_node와 동일한 검색·merge 로직으로 상위 TOP_N 반환.

    retrieve_node와 동일하게 쿼리를 1회 임베딩(_embed_query_sync) 후 두 컬렉션에
    벡터를 재사용한다. (_chroma_query_sync는 문자열이 아니라 임베딩 벡터를 받는다.)
    """
    qe, emb_err = _embed_query_sync(query)
    if qe is None:
        print(f"[WARN] 쿼리 임베딩 실패: {emb_err}", file=sys.stderr)
        return []
    docs_b, metas_b, sims_b, err_b = _chroma_query_sync(
        qe, db_path, B_DATASET_TOP_K, "b_dataset_rag"
    )
    docs_main, metas_main, sims_main, err_main = _chroma_query_sync(
        qe, db_path, MAIN_TOP_K, "a_dataset_rag"
    )
    if err_b:
        print(f"[WARN] b_dataset_rag 검색 오류: {err_b}", file=sys.stderr)
    if err_main:
        print(f"[WARN] a_dataset_rag 검색 오류: {err_main}", file=sys.stderr)

    t_b = _tag_triples_rag_source(
        _triples_from_chroma(docs_b, metas_b, sims_b), "b_dataset"
    )
    t_main = _tag_triples_rag_source(
        _triples_from_chroma(docs_main, metas_main, sims_main), "main"
    )
    docs, metas, raw_sims, _merge_sims = _merge_rag_triples(
        t_b, t_main, b_dataset_top_k=B_DATASET_TOP_K, main_top_k=MAIN_TOP_K
    )

    out: list[dict[str, Any]] = []
    for rank, (doc, meta, raw) in enumerate(zip(docs, metas, raw_sims), start=1):
        if rank > TOP_N:
            break
        m = meta or {}
        cid = str(m.get("card_id") or "")  # a_dataset_rag 문서는 card_id 없음 → ""
        out.append(
            {
                "rank": rank,
                "card_id": cid,
                "source": str(m.get("source") or m.get("_rag_source") or ""),
                "problem_type": str(m.get("problem_type") or ""),
                "sim": round(float(raw), 4),
                "title": str(m.get("title") or "")[:80],
            }
        )
    return out


def _score_case(case: dict[str, Any], top_n: list[dict[str, Any]]) -> dict[str, Any]:
    acceptable = list(case.get("acceptable_card_ids") or [])
    excluded = len(acceptable) == 0

    hit = 0
    rr = 0.0
    first_rank: int | None = None
    if not excluded:
        acc_set = set(acceptable)
        for item in top_n:
            if item["card_id"] and item["card_id"] in acc_set:
                first_rank = item["rank"]
                break
        if first_rank is not None:
            hit = 1
            rr = 1.0 / first_rank

    return {
        "case_id": case.get("case_id"),
        "symptom_en": case.get("symptom_en"),
        "primary_problem_type": case.get("primary_problem_type"),
        "acceptable_card_ids": acceptable,
        "top_10": top_n,
        "hit_at_10": hit,
        "reciprocal_rank": round(rr, 4),
        "first_acceptable_rank": first_rank,
        "excluded_from_metrics": excluded,
    }


def main() -> None:
    load_dotenv(_ROOT / ".env")
    cases = _load_golden()
    db_path = str(_vector_db_path())
    print(f"[eval_retrieval] 골든셋 {len(cases)} 케이스 로드: {GOLDEN_PATH}")

    per_case: list[dict[str, Any]] = []
    for i, case in enumerate(cases, start=1):
        query = str(case.get("symptom_en") or "").strip()
        top_n = _retrieve_top_n(query, db_path) if query else []
        scored = _score_case(case, top_n)
        per_case.append(scored)
        tag = "EXCLUDED" if scored["excluded_from_metrics"] else (
            f"hit={scored['hit_at_10']} rr={scored['reciprocal_rank']} "
            f"first={scored['first_acceptable_rank']}"
        )
        print(
            f"[{i}/{len(cases)}] {scored['case_id']} "
            f"[{scored['primary_problem_type']:8}] {tag}"
        )

    evaluated = [c for c in per_case if not c["excluded_from_metrics"]]
    n_eval = len(evaluated)
    n_excl = len(per_case) - n_eval
    hit_rate = (
        sum(c["hit_at_10"] for c in evaluated) / n_eval if n_eval else None
    )
    mrr = (
        sum(c["reciprocal_rank"] for c in evaluated) / n_eval if n_eval else None
    )

    result = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "metrics": {
            "hit_rate_at_10": round(hit_rate, 4) if hit_rate is not None else None,
            "mrr": round(mrr, 4) if mrr is not None else None,
            "cases_evaluated": n_eval,
            "cases_excluded": n_excl,
        },
        "per_case": per_case,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("\n" + "=" * 56)
    print("RETRIEVAL 측정 요약")
    print("=" * 56)
    hr = result["metrics"]["hit_rate_at_10"]
    mr = result["metrics"]["mrr"]
    print(f"Hit Rate@10: {hr}  (평가 {n_eval}, 제외 {n_excl})")
    print(f"MRR        : {mr}")
    print("저장:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
