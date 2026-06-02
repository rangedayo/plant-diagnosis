"""
[단계 B'] 종별 (a) 정상화 카드를 임베딩하여 Chroma `species_normal_rag` 컬렉션을 구축한다.

- 입력: data/raw/species_normal/species_normal_cards.json (4 카드, 드라세나속 위주)
- 출력: data/vector_db/ 의 Chroma `species_normal_rag` 컬렉션 (격리 — b_dataset_rag/main_rag 불변)
- 메타: species(정규화 종명) / src_cntntsNo / card_id

설계 ([B-prime] 작업 프롬프트 §3):
- 카드 = 청크 1:1. 청크 본문 = card.text (이미 "[종명] 이 종의 정상 생육 특성: ..." 형태)
- 임베딩 OpenAIEmbeddings() 기본값 (b_dataset_rag와 동일)
- 격리 원칙: 기존 컬렉션 건드리지 않음. species_normal_rag만 생성/멱등 재생성.

실행 (프로젝트 루트에서):

  .venv\\Scripts\\python.exe scripts\\build_species_normal_rag.py

`.env`에 OPENAI_API_KEY 필요. 임베딩 비용 ~$0.001 (4 카드).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

COLLECTION_NAME = "species_normal_rag"
CARDS_REL = "data/raw/species_normal/species_normal_cards.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _require_openai_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 OPENAI_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


def load_cards(root: Path) -> tuple[list[str], list[str], list[dict[str, str]]]:
    path = root / CARDS_REL
    if not path.is_file():
        print(f"오류: 입력 JSON 없음: {path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data.get("cards") or []
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    for card in cards:
        card_id = str(card.get("id") or "")
        species = str(card.get("species") or "")
        text = str(card.get("text") or "").strip()
        if not card_id or not species or not text:
            print(f"오류: 카드 필드 누락: {card}", file=sys.stderr)
            sys.exit(1)
        ids.append(card_id)
        documents.append(text)
        metadatas.append(
            {
                "species": species,
                "src_cntntsNo": str(card.get("src_cntntsNo") or ""),
                "card_id": card_id,
            }
        )
    print(f"[1] 카드 로드: {len(ids)}개")
    for m in metadatas:
        print(f"    {m['card_id']} (species={m['species']}, src={m['src_cntntsNo']})")
    return ids, documents, metadatas


def persist(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, str]],
    vector_db: Path,
    openai_key: str,
) -> int:
    print(f"[2] OpenAI 임베딩 ({len(documents)} documents)…")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
    vectors = embeddings.embed_documents(documents)

    print(f"[3] Chroma 저장 ({COLLECTION_NAME}) - 격리, 기존 컬렉션 불변")
    vector_db.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(vector_db))
    try:
        client.delete_collection(COLLECTION_NAME)  # 멱등성 (이 컬렉션만)
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


def main() -> None:
    root = _project_root()
    load_dotenv(root / ".env")
    openai_key = _require_openai_key()
    vector_db = root / "data" / "vector_db"

    ids, documents, metadatas = load_cards(root)
    if not documents:
        print("오류: 적재할 카드가 없습니다.", file=sys.stderr)
        sys.exit(1)

    count = persist(ids, documents, metadatas, vector_db, openai_key)
    print(f"[4] count: {count} (예상 {len(ids)})")
    if count != len(ids):
        print(f"오류: 적재 count {count} != 예상 {len(ids)}.", file=sys.stderr)
        sys.exit(1)
    print("[5] 완료. 기존 b_dataset_rag/main_rag 컬렉션은 건드리지 않음.")


if __name__ == "__main__":
    main()
