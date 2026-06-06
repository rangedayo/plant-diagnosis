"""
b_dataset raw JSON 5자료(영문)를 청크화·임베딩하여 Chroma `b_dataset_rag` 컬렉션을 구축한다.

- 입력: data/raw/b_dataset/*/*.json (psu_ucanr / psu_indoor / mu_trinklein / mobot_indoor / mobot_herb)
- 출력: data/vector_db/ 의 Chroma `b_dataset_rag` 컬렉션 (82 청크 예상)
- 부수: 적재·검증 통과 후 `ncpms_rag` 컬렉션 폐기 (atomic — NCPMS 도메인 미스매치 본질, v14 가설)

설계 ([B-2] 작업 프롬프트 영역 결정):
- 카드 = 청크 1:1 (영역 1 A). 청크 본문 = `title + ": " + body` (build_main_rag.flatten_document 일관성)
- 청크 ID = 카드의 id 그대로 (source prefix가 자료 간 충돌 방지)
- 메타 6 필드: source/source_id/section/title/problem_type/card_id (영역 3 B)
- 임베딩 OpenAIEmbeddings(model="text-embedding-ada-002") 명시 (검색·a_dataset_rag와 동일, 영역 5 A)

실행 (프로젝트 루트에서):

  .venv\\Scripts\\python.exe scripts\\build_b_dataset_rag.py

`.env`에 OPENAI_API_KEY 필요. 임베딩 비용 ~$0.01 (82 카드).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

COLLECTION_NAME = "b_dataset_rag"
NCPMS_COLLECTION = "ncpms_rag"
# 임베딩 모델: 검색(app.graph)·다른 적재 스크립트와 동일해야 cosine이 유효.
# langchain_openai 기본값을 명시 고정(기본값 변경 사고 방지).
EMBEDDING_MODEL = "text-embedding-ada-002"

# (논리 source 키, 프로젝트 루트 기준 상대 경로)
JSON_FILES: list[tuple[str, str]] = [
    ("psu_ucanr", "data/raw/b_dataset/psu_ucanr/psu_ucanr.json"),
    ("psu_indoor", "data/raw/b_dataset/psu_indoor/psu_indoor.json"),
    ("mu_trinklein", "data/raw/b_dataset/mu_trinklein/mu_trinklein.json"),
    ("mobot_indoor", "data/raw/b_dataset/mobot/problems-common-to-many-indoor-plants.json"),
    ("mobot_herb", "data/raw/b_dataset/mobot/herb-problems-indoors.json"),
]

EXPECTED_TOTAL = 82


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    load_dotenv(_project_root() / ".env")


def _require_openai_key() -> str:
    import os

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 OPENAI_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


def classify_problem_type(source: str, section: str, card_id: str) -> str:
    """§3.1 C 매핑 룰. 매칭 실패 시 'general' 디폴트.

    MU Trinklein 첫 2 카드(frame 정의)는 id로 직접 박음 — section 파싱 의존 안 함.
    """
    sl = (section or "").lower()
    if source == "psu_ucanr":
        if "pest" in sl:
            return "pest"
        if "disease" in sl:
            return "disease"
        if "abiotic" in sl:
            return "abiotic"
        return "general"
    if source == "psu_indoor":
        if "pest" in sl:
            return "pest"
        if "disease" in sl:
            return "disease"
        return "general"
    if source == "mu_trinklein":
        if card_id in ("mu_trinklein_001", "mu_trinklein_002"):
            return "frame"
        return "general"
    if source == "mobot_indoor":
        if "environmental" in sl:
            return "env"
        if "insect" in sl:
            return "pest"
        if "disease" in sl:
            return "disease"
        if "nutrient" in sl:
            return "nutrient"
        return "general"
    if source == "mobot_herb":
        if "insect" in sl:
            return "pest"
        if "disease" in sl:
            return "disease"
        return "general"
    return "general"


def build_chunk_text(title: str, body: str) -> str:
    """청크 본문 = title + ': ' + body (build_main_rag.flatten_document 일관성)."""
    t = (title or "").strip()
    b = (body or "").strip()
    if t and b:
        return f"{t}: {b}"
    return t or b


def load_cards(root: Path) -> tuple[list[str], list[str], list[dict[str, str]]]:
    """5 JSON 로드 → (ids, documents, metadatas). 카드=청크 1:1."""
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    per_source: dict[str, int] = {}

    for source, rel in JSON_FILES:
        path = root / rel
        if not path.is_file():
            print(f"오류: 입력 JSON 없음: {path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
        source_id = str(data.get("source") or source)
        cards = data.get("cards") or []
        per_source[source] = len(cards)
        for card in cards:
            card_id = str(card.get("id") or "")
            section = str(card.get("section") or "")
            title = str(card.get("title") or "")
            body = str(card.get("body") or "")
            doc = build_chunk_text(title, body)
            problem_type = classify_problem_type(source, section, card_id)
            ids.append(card_id)
            documents.append(doc)
            metadatas.append(
                {
                    "source": source,
                    "source_id": source_id,
                    "section": section,
                    "title": title,
                    "problem_type": problem_type,
                    "card_id": card_id,
                }
            )

    print("[1] 5 JSON 로드…")
    for source, _ in JSON_FILES:
        print(f"    {source}: {per_source.get(source, 0)} cards")
    print(f"    total: {len(ids)}")
    return ids, documents, metadatas


def persist_b_dataset_rag(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, str]],
    vector_db: Path,
    openai_key: str,
) -> int:
    """OpenAI 임베딩 + Chroma 적재. persist_main_rag 패턴 그대로. 반환: 적재 후 count."""
    print(f"[3] OpenAI 임베딩 ({len(documents)} documents)…")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key, model=EMBEDDING_MODEL)
    vectors = embeddings.embed_documents(documents)

    print(f"[4] Chroma 저장 ({COLLECTION_NAME})…")
    vector_db.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(vector_db))
    try:
        client.delete_collection(COLLECTION_NAME)  # 멱등성
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,
    )
    return collection.count()


def verify_b_dataset_query(vector_db: Path) -> None:
    """[ACC-fix2 재발방지#3] 빌드 후 신규 클라이언트로 1쿼리 성공까지 검증.

    count는 sqlite 메타만 읽으므로 HNSW 세그먼트 불완전 영속(R11 "Nothing found on
    disk")을 잡지 못한다. 신규 PersistentClient로 재오픈해 더미 임베딩 쿼리(무과금)가
    실제 문서를 반환하는지 확인한다. 실패 시 atomic 보호(retire_ncpms 전 중단).
    """
    print(f"[5b] 쿼리 검증 (신규 클라이언트, {COLLECTION_NAME})…")
    client = chromadb.PersistentClient(path=str(vector_db))
    collection = client.get_collection(COLLECTION_NAME)
    got = collection.get(limit=1, include=["embeddings"])
    embs = got.get("embeddings")
    if embs is None or len(embs) == 0:
        print("오류: 검증 실패 — 저장된 임베딩을 읽지 못했습니다.", file=sys.stderr)
        sys.exit(1)
    dim = len(embs[0])
    try:
        res = collection.query(
            query_embeddings=[[0.0] * dim], n_results=3, include=["documents"]
        )
    except Exception as e:
        print(
            f"오류: 검증 쿼리 실패 (HNSW 세그먼트 읽기 불가): {e}", file=sys.stderr
        )
        sys.exit(1)
    docs = (res.get("documents") or [[]])[0]
    if len(docs) == 0:
        print(
            "오류: 검증 쿼리가 0건 반환 — HNSW 인덱스 불완전. 재적재 필요.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"[5b] 쿼리 검증 통과: {len(docs)} docs 반환")


def retire_ncpms(vector_db: Path) -> None:
    """ncpms_rag 폐기 (atomic — b_dataset_rag 적재·검증 통과 후에만 호출)."""
    client = chromadb.PersistentClient(path=str(vector_db))
    try:
        client.delete_collection(NCPMS_COLLECTION)
        print("[6] ncpms_rag 컬렉션 폐기 완료")
    except Exception as e:
        print(f"[6] ncpms_rag 폐기 스킵 (이미 없음 또는 에러): {e}")


def main() -> None:
    _load_env()
    openai_key = _require_openai_key()
    root = _project_root()
    vector_db = root / "data" / "vector_db"

    ids, documents, metadatas = load_cards(root)

    if not documents:
        print("오류: 적재할 청크가 없습니다.", file=sys.stderr)
        sys.exit(1)

    dist = Counter(m["problem_type"] for m in metadatas)
    print(f"[2] problem_type 분포: {dict(sorted(dist.items()))}")

    count = persist_b_dataset_rag(ids, documents, metadatas, vector_db, openai_key)
    match = "일치" if count == EXPECTED_TOTAL else f"불일치(예상 {EXPECTED_TOTAL})"
    print(f"[5] count: {count} ({match})")

    if count != EXPECTED_TOTAL:
        print(
            f"오류: 적재 count {count} != 예상 {EXPECTED_TOTAL}. "
            "NCPMS 폐기 중단 (atomic 보호).",
            file=sys.stderr,
        )
        sys.exit(1)

    # [ACC-fix2 재발방지#3] count 통과 후 신규 클라이언트 쿼리까지 검증 (HNSW 영속 확인)
    verify_b_dataset_query(vector_db)

    # 적재·count·쿼리 검증 통과 후에만 NCPMS 폐기 (atomic)
    retire_ncpms(vector_db)


if __name__ == "__main__":
    main()
