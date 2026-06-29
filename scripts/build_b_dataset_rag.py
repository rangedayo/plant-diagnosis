"""
b_dataset raw JSON 5자료(영문)를 청크화·임베딩하여 Chroma `b_dataset_rag` 컬렉션을 구축한다.

- 입력: data/raw/b_dataset/*/*.json (psu_ucanr / psu_indoor / mu_trinklein / mobot_indoor / mobot_herb)
- 출력: data/vector_db/ 의 Chroma `b_dataset_rag` 컬렉션 (82 청크 예상)

설계 ([B-2] 작업 프롬프트 영역 결정):
- 카드 = 청크 1:1 (영역 1 A). 청크 본문 = `title + ": " + body` (build_main_rag.flatten_document 일관성)
- 청크 ID = 카드의 id 그대로 (source prefix가 자료 간 충돌 방지)
- 메타 8 필드: source/source_id/section/title/problem_type/card_id (영역 3 B)
  + license/source_url (R12c-1). [R12d-1] status_hint 제거(graph.py 미소비 dead metadata)
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
    # [R12c-1] 건조 전용 보충 카드 (CC 작성, abiotic-water)
    ("dry_supplement", "data/raw/b_dataset/dry_supplement/dry_supplement.json"),
]

# [R12c-1] problem_type 택소노미에 abiotic-water 신설(건조·과습 등 수분 abiotic).
PROBLEM_TYPE_ABIOTIC_WATER = "abiotic-water"

# [R12c-1] 기존 dry-adjacent 카드 재분류 (본문 확인 후 판정, R12c1 §2.4).
# card_id → problem_type. 본문이 명확한 수분 카드만 — over-claim 금지.
# [R12d-1] status_hint 제거 (graph.py 미소비 dead metadata) — problem_type만 유지.
RECLASSIFY: dict[str, str] = {
    "mobot_indoor_001": PROBLEM_TYPE_ABIOTIC_WATER,  # "Too dry" — 순수 underwatering
    "mobot_indoor_002": PROBLEM_TYPE_ABIOTIC_WATER,  # "Overwatering" — 순수 과습
    "psu_ucanr_019": PROBLEM_TYPE_ABIOTIC_WATER,     # "Wilting • too wet/dry" — 수분 양방향
}

# EXPECTED_TOTAL은 동적: 각 JSON의 선언 card_count 합으로 산출(silent load 실패 탐지 유지).
# R12c-1 기준 82 + dry_supplement 6 = 88.


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


def resolve_problem_type(source: str, section: str, card_id: str, card: dict) -> str:
    """problem_type 결정 우선순위: 카드 명시값 > RECLASSIFY > section 기반 classify."""
    explicit = str(card.get("problem_type") or "").strip()
    if explicit:
        return explicit
    if card_id in RECLASSIFY:
        return RECLASSIFY[card_id]
    return classify_problem_type(source, section, card_id)


def load_cards(
    root: Path,
) -> tuple[list[str], list[str], list[dict[str, str]], int]:
    """JSON 로드 → (ids, documents, metadatas, declared_total). 카드=청크 1:1.

    declared_total = 각 파일의 선언 card_count 합(없으면 실제 카드 수). silent load 실패 탐지용.
    """
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    per_source: dict[str, int] = {}
    declared_total = 0

    for source, rel in JSON_FILES:
        path = root / rel
        if not path.is_file():
            print(f"오류: 입력 JSON 없음: {path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
        source_id = str(data.get("source") or source)
        license_str = str(data.get("license") or "")
        cards = data.get("cards") or []
        per_source[source] = len(cards)
        declared_total += int(data.get("card_count") or len(cards))
        for card in cards:
            card_id = str(card.get("id") or "")
            section = str(card.get("section") or "")
            title = str(card.get("title") or "")
            body = str(card.get("body") or "")
            doc = build_chunk_text(title, body)
            problem_type = resolve_problem_type(source, section, card_id, card)
            source_url = str(card.get("source_url") or "")
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
                    # [R12c-1] 라이선스 + 원문 URL ([R12d-1] status_hint 제거: dead metadata)
                    "license": license_str,
                    "source_url": source_url,
                }
            )

    print(f"[1] {len(JSON_FILES)} JSON 로드…")
    for source, _ in JSON_FILES:
        print(f"    {source}: {per_source.get(source, 0)} cards")
    print(f"    total: {len(ids)} (선언 합 {declared_total})")
    return ids, documents, metadatas, declared_total


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
    실제 문서를 반환하는지 확인한다. 실패 시 중단(atomic 보호).
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


# [R12c-1] 건조 6건 case의 영문 쿼리(R12-0 probe·R11 analyze에서 채취, 결정적 고정).
# 재적재 후 이 쿼리들로 top_10에 abiotic-water 카드가 1장 이상 잡히는지 검증 → 콘텐츠 실효 확인.
DRY_VERIFY_QUERIES: dict[str, str] = {
    "haengun_002": (
        "overall yellowing and drying of lower leaves tip burn on some leaves "
        "leaf surface wrinkling and yellowish spots on some leaves"
    ),
    "haengun_003": "crispy wilting and dieback of lower leaves tip burn of new shoots",
    "haengun_005": (
        "brown leaf tip and crispy desiccation irregular small yellow spots on leaf surface"
    ),
    "haengun_006": "brown tip and edge of lower leaves",
    "haengun_008": (
        "brown leaf tips of multiple leaves lower leaf dieback overall leaf drooping and curling"
    ),
    "epipremnum_004": "brown necrosis on leaf margins and centers parchment-like brown areas",
}


def verify_dry_top10_entry(vector_db: Path, openai_key: str) -> None:
    """[R12c-1 §2.5] 건조 6건 영문 쿼리 각각 top_10에 abiotic-water 카드 ≥1장 진입 검증.

    실측(run_eval) 전에 카드 추가/재분류가 검색에 실효 있는지 build 단계에서 강제한다.
    실패(어느 한 case라도 미진입) 시 exit 2 → 적재 중단. 임베딩 과금(소액).
    """
    print(f"[5c] 건조 top_10 진입 검증 ({len(DRY_VERIFY_QUERIES)} case)…")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key, model=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(vector_db))
    collection = client.get_collection(COLLECTION_NAME)
    failures: list[str] = []
    for case, query in DRY_VERIFY_QUERIES.items():
        qe = embeddings.embed_query(query)
        res = collection.query(
            query_embeddings=[qe], n_results=10, include=["metadatas"]
        )
        metas = (res.get("metadatas") or [[]])[0]
        hits = [
            str((m or {}).get("card_id") or "")
            for m in metas
            if str((m or {}).get("problem_type") or "") == PROBLEM_TYPE_ABIOTIC_WATER
        ]
        mark = "OK" if hits else "FAIL"
        print(f"    {case}: {mark} (abiotic-water {len(hits)}장: {hits[:3]})")
        if not hits:
            failures.append(case)
    if failures:
        print(
            "오류: 건조 top_10 진입 검증 실패 — 다음 case에 abiotic-water 카드 미진입: "
            f"{failures}. 카드 본문/어휘 재검토 필요(R12c-1-α). 적재 중단.",
            file=sys.stderr,
        )
        sys.exit(2)
    print("[5c] 건조 top_10 진입 검증 통과 (6/6 case)")


def dry_run(root: Path) -> None:
    """[R12c-1 §4.1] Chroma 쓰기·임베딩 없이 카드 로드·메타 무결성만 검증 (무과금)."""
    ids, documents, metadatas, declared_total = load_cards(root)
    print(f"[dry-run] declared_total={declared_total} loaded={len(ids)}")
    assert len(ids) == declared_total, "선언 합과 로드 수 불일치"
    assert len(set(ids)) == len(ids), "card_id 중복 존재"
    required = {"source", "source_id", "section", "title", "problem_type",
                "card_id", "license", "source_url"}
    for m in metadatas:
        missing = required - set(m.keys())
        assert not missing, f"메타 키 누락 {missing} @ {m.get('card_id')}"
        for k, v in m.items():
            assert isinstance(v, str), f"메타 값 비문자열 {k}={v!r} @ {m.get('card_id')}"
    dist = Counter(m["problem_type"] for m in metadatas)
    print(f"[dry-run] problem_type 분포: {dict(sorted(dist.items()))}")
    aw = [m["card_id"] for m in metadatas if m["problem_type"] == PROBLEM_TYPE_ABIOTIC_WATER]
    print(f"[dry-run] abiotic-water 카드 {len(aw)}장: {aw}")
    print("[dry-run] 메타 무결성 검증 통과 (Chroma 무변경)")


def main() -> None:
    if "--dry-run" in sys.argv:
        dry_run(_project_root())
        return
    _load_env()
    openai_key = _require_openai_key()
    root = _project_root()
    vector_db = root / "data" / "vector_db"

    ids, documents, metadatas, declared_total = load_cards(root)

    if not documents:
        print("오류: 적재할 청크가 없습니다.", file=sys.stderr)
        sys.exit(1)

    dist = Counter(m["problem_type"] for m in metadatas)
    print(f"[2] problem_type 분포: {dict(sorted(dist.items()))}")

    count = persist_b_dataset_rag(ids, documents, metadatas, vector_db, openai_key)
    match = "일치" if count == declared_total else f"불일치(선언 합 {declared_total})"
    print(f"[5] count: {count} ({match})")

    if count != declared_total:
        print(
            f"오류: 적재 count {count} != 선언 합 {declared_total}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # [ACC-fix2 재발방지#3] count 통과 후 신규 클라이언트 쿼리까지 검증 (HNSW 영속 확인)
    verify_b_dataset_query(vector_db)

    # [R12c-1 §2.5] 건조 6건 top_10에 abiotic-water 진입 검증 (콘텐츠 실효 강제)
    verify_dry_top10_entry(vector_db, openai_key)


if __name__ == "__main__":
    main()
