"""
b_dataset_rag 적재 sanity check ([B-2] §3.4) — 읽기 전용.

2계층:
  (1) 자동 게이트 — count(82/21)·빈 청크 0·중복 청크 0·problem_type 누락 0
  (2) 정성 inspect — 길이 분포 + 무작위 N=20 dump + problem_type 분포
  (3) 임베딩 nearest neighbor sanity — 한국어 5 쿼리 top-5

실행 (프로젝트 루트에서):

  .venv\\Scripts\\python.exe scripts\\validate_b_chunks.py

자동 게이트 FAIL이면 exit 1. `.env`에 OPENAI_API_KEY 필요 (sanity 쿼리 임베딩).
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

B_COLLECTION = "b_dataset_rag"
MAIN_COLLECTION = "a_dataset_rag"
# 임베딩 모델: 검색·적재와 동일해야 nearest-neighbor sanity가 유효(기본값 명시 고정).
EMBEDDING_MODEL = "text-embedding-ada-002"

EXPECTED_B = 82
EXPECTED_MAIN = 21
MIN_CHUNK_CHARS = 10

SANITY_QUERIES = [
    "잎끝이 갈색으로 변해요",
    "끈적한 액체가 잎에 묻어있어요",
    "흙이 항상 축축해요",
    "잎이 노랗게 변하고 떨어져요",
    "갈색 반점이 있어요",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _vector_db(root: Path) -> Path:
    return root / "data" / "vector_db"


def _require_openai_key() -> str:
    import os

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 OPENAI_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


def run_auto_gate(
    client: chromadb.ClientAPI,
) -> tuple[list[str], list[dict], list[str]]:
    """자동 게이트. 통과 시 (ids, metadatas, documents) 반환. 실패 시 AssertionError."""
    print("=== (1) 자동 게이트 ===")

    b = client.get_collection(B_COLLECTION)
    b_count = b.count()
    assert b_count == EXPECTED_B, f"b_dataset_rag count {b_count} != {EXPECTED_B}"
    print(f"[OK] b_dataset_rag count == {EXPECTED_B}")

    main = client.get_collection(MAIN_COLLECTION)
    main_count = main.count()
    assert main_count == EXPECTED_MAIN, (
        f"a_dataset_rag count {main_count} != {EXPECTED_MAIN} (변수 격리 위반)"
    )
    print(f"[OK] a_dataset_rag count == {EXPECTED_MAIN} (변수 격리)")

    got = b.get(include=["documents", "metadatas"])
    ids = list(got.get("ids") or [])
    docs = list(got.get("documents") or [])
    metas = list(got.get("metadatas") or [])

    # 빈 청크 (title+body 합산 < 10자)
    empties = [i for i, d in zip(ids, docs) if len((d or "").strip()) < MIN_CHUNK_CHARS]
    assert not empties, f"빈 청크 {len(empties)}건: {empties[:5]}"
    print(f"[OK] 빈 청크 (<{MIN_CHUNK_CHARS}자) 0")

    # 중복 청크 (documents 완전 동일)
    doc_counts = Counter(docs)
    dups = [d for d, c in doc_counts.items() if c > 1]
    assert not dups, f"중복 청크 {len(dups)}종"
    print("[OK] 중복 청크 0")

    # problem_type 누락
    missing_pt = [
        m.get("card_id") for m in metas if not (m.get("problem_type") or "").strip()
    ]
    assert not missing_pt, f"problem_type 누락 {len(missing_pt)}건: {missing_pt[:5]}"
    print("[OK] 모든 카드에 problem_type 메타 박힘")

    print("=== 자동 게이트 전체 통과 ===\n")
    return ids, metas, docs


def run_inspect(ids: list[str], metas: list[dict], docs: list[str]) -> None:
    print("=== (2) 정성 inspect ===")

    lengths = [len(d or "") for d in docs]
    lengths_sorted = sorted(lengths)
    p95 = lengths_sorted[min(int(len(lengths_sorted) * 0.95), len(lengths_sorted) - 1)]
    print(
        f"청크 길이 (title+': '+body): "
        f"mean={statistics.mean(lengths):.1f} median={statistics.median(lengths):.0f} "
        f"p95={p95} max={max(lengths)} min={min(lengths)}"
    )

    pt_dist = Counter(m.get("problem_type") for m in metas)
    src_dist = Counter(m.get("source") for m in metas)
    print(f"problem_type 분포: {dict(sorted(pt_dist.items()))}  (합 {sum(pt_dist.values())})")
    print(f"source 분포: {dict(sorted(src_dist.items()))}")

    print("\n무작위 N=20 청크 dump (id · source · problem_type · title · body 첫 100자):")
    rng = random.Random(42)
    idxs = sorted(rng.sample(range(len(ids)), min(20, len(ids))))
    for i in idxs:
        m = metas[i]
        body_preview = (docs[i] or "")[:100].replace("\n", " ")
        print(
            f"  {ids[i]:<20} {str(m.get('source')):<14} "
            f"{str(m.get('problem_type')):<9} {str(m.get('title'))[:30]:<30} | {body_preview}"
        )
    print()


def run_sanity_queries(client: chromadb.ClientAPI, openai_key: str) -> None:
    print("=== (3) 임베딩 nearest neighbor sanity (top-5) ===")
    emb = OpenAIEmbeddings(openai_api_key=openai_key, model=EMBEDDING_MODEL)
    b = client.get_collection(B_COLLECTION)
    for q in SANITY_QUERIES:
        qe = emb.embed_query(q)
        res = b.query(
            query_embeddings=[qe],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        print(f"\n쿼리: {q!r}")
        for rank, (d, m, dist) in enumerate(zip(docs, metas, dists), start=1):
            sim = 1.0 - float(dist)
            body_preview = (d or "")[:60].replace("\n", " ")
            print(
                f"  {rank}. {str(m.get('card_id')):<20} "
                f"{str(m.get('source')):<14} {str(m.get('problem_type')):<9} "
                f"sim={sim:.4f} | {body_preview}"
            )
    print()


def main() -> None:
    load_dotenv(_project_root() / ".env")
    openai_key = _require_openai_key()
    client = chromadb.PersistentClient(path=str(_vector_db(_project_root())))

    try:
        ids, metas, docs = run_auto_gate(client)
    except AssertionError as e:
        print(f"[FAIL] 자동 게이트 실패: {e}", file=sys.stderr)
        sys.exit(1)

    run_inspect(ids, metas, docs)
    run_sanity_queries(client, openai_key)
    print("validate_b_chunks: 완료 (자동 게이트 통과, 정성·sanity는 사람 검토)")


if __name__ == "__main__":
    main()
