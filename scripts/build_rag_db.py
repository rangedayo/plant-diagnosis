"""
NCPMS: SVC01로 sickKey 수집 → SVC05 상세(XML) → 전처리·1문단·Chroma(data/vector_db)
문서당 sickKey 1건, metadata에 sickKey 저장.

실행 방법 (프로젝트 루트에서, `python -c` 사용하지 말 것):

  Windows PowerShell::

    $env:BUILD_RAG_MAX_KEYS = "3"   # 테스트: sickKey 상한 (미설정=상한 없음)
    .venv\\Scripts\\python.exe scripts\\build_rag_db.py

  bash::

    export BUILD_RAG_MAX_KEYS=3
    python scripts/build_rag_db.py

`.env`의 OPENAI_API_KEY, RDA_API_KEY는 기존과 같음. `BUILD_RAG_MAX_KEYS`는 쉘에서만 설정.
"""

from __future__ import annotations

import asyncio
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import chromadb
import httpx
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

NCPMS_SERVICE_URL = "http://ncpms.rda.go.kr/npmsAPI/service"

SVC01_PARAMS = {
    "serviceCode": "SVC01",
    "serviceType": "AA001",
}

SVC05_PARAMS = {
    "serviceCode": "SVC05",
    "serviceType": "AA001",
}

# SVC01 sickNameKor 검색 키워드 (sickKey 목록 확보용)
SICK_NAME_KOR_KEYWORDS = [
    "갈색",
    "검은색",
    "황색",
    "흰색",
    "반점",
    "병반",
    "시듦",
    "고사",
    "부패",
    "곰팡이",
    "무늬",
    "변색",
    "잎마름",
    "병",
    "썩음",
]

# 조건부 최소 길이: `should_keep_document` 참고
LONG_DOC_MIN_CHARS = 100
ABSOLUTE_MIN_CHARS = 30
SYMPTOMS_MEANINGFUL_MIN = 20

COLLECTION_NAME = "ncpms_rag"

# para에서 필드 제거 후 남는 짧은 잔여가 이 패턴만이면 노이즈로 간주 (Step 3)
_VAGUE_BOILERPLATE_MARKERS = (
    "잎에 반점",
    "병 발생",
    "병이 발생",
    "발생할 수 있다",
    "발생한다",
    "나타난다",
    "의심된다",
    "병원균",
)


def _parse_max_sick_keys_from_env() -> int:
    """BUILD_RAG_MAX_KEYS: 숫자만 허용. 빈 값=상한 없음(0). 테스트 시 쉘에서 3 등으로 설정."""
    raw = (os.getenv("BUILD_RAG_MAX_KEYS") or "").strip()
    if not raw:
        return 0
    if raw.isdigit():
        return int(raw)
    return 0


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _local_tag(tag: str | None) -> str:
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _load_env() -> None:
    load_dotenv(_project_root() / ".env")


def _require_openai_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 OPENAI_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


def _require_rda_key() -> str:
    key = (os.getenv("RDA_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 RDA_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


def _strip_html_and_ws(text: str) -> str:
    """HTML 태그 제거, 엔티티 디코드, 공백 정리."""
    if not text:
        return ""
    t = html.unescape(text)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _element_plain_text(el: ET.Element) -> str:
    return _strip_html_and_ws("".join(el.itertext()))


def _svc05_error_message(xml_text: str) -> str | None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "XML 파싱 실패"
    for e in root.iter():
        if _local_tag(e.tag) == "errorCode" and (e.text or "").strip():
            msg = ""
            for s in root.iter():
                if _local_tag(s.tag) == "errorMsg":
                    msg = (s.text or "").strip()
            return (e.text or "").strip() + (f": {msg}" if msg else "")
    return None


def parse_svc05_detail(xml_text: str) -> dict[str, str] | None:
    """
    SVC05 응답에서 필드 추출. 오류 XML이면 None.
    virusList/item 다건이면 virusName·sfeNm 각각 공백으로 연결.
    """
    err = _svc05_error_message(xml_text)
    if err:
        return None
    root = ET.fromstring(xml_text)
    if _local_tag(root.tag) != "service":
        return None

    out: dict[str, str] = {}
    virus_names: list[str] = []
    sfe_parts: list[str] = []

    for child in root:
        tag = _local_tag(child.tag)
        if tag == "virusList":
            for item in child:
                if _local_tag(item.tag) != "item":
                    continue
                vn = ""
                sf = ""
                for sub in item:
                    st = _local_tag(sub.tag)
                    if st == "virusName":
                        vn = _element_plain_text(sub)
                    elif st == "sfeNm":
                        sf = _element_plain_text(sub)
                if vn:
                    virus_names.append(vn)
                if sf:
                    sfe_parts.append(sf)
            continue
        if tag in (
            "cropName",
            "sickNameKor",
            "sickNameEng",
            "symptoms",
            "developmentCondition",
            "preventionMethod",
        ):
            out[tag] = _element_plain_text(child)

    if virus_names:
        out["virusName"] = " ".join(virus_names)
    if sfe_parts:
        out["sfeNm"] = " ".join(sfe_parts)

    return out


FIELD_ORDER = (
    "cropName",
    "sickNameKor",
    "sickNameEng",
    "symptoms",
    "developmentCondition",
    "preventionMethod",
    "virusName",
    "sfeNm",
)


def build_paragraph_from_fields(fields: dict[str, str]) -> str:
    """빈 필드 제외, 순서대로 한 문단으로 합침."""
    parts: list[str] = []
    for key in FIELD_ORDER:
        v = (fields.get(key) or "").strip()
        if v:
            parts.append(v)
    return " ".join(parts) if parts else ""


def _is_only_vague_generic_boilerplate(para: str, fields: dict[str, str]) -> bool:
    """
    필드 값을 제외한 잔여 텍스트가 짧고, 일반적·모호한 문장(반점·병 발생 등) 위주면 True.
    (필드 기반으로 이미 crop/sick 등이 있어도 본문이 그 외에 실질 정보가 거의 없으면 제외)
    """
    remainder = para
    for key in FIELD_ORDER:
        v = (fields.get(key) or "").strip()
        if len(v) >= 2:
            remainder = remainder.replace(v, " ")
    remainder = re.sub(r"\s+", " ", remainder).strip()
    if len(remainder) >= 20:
        return False
    if not remainder:
        return False
    return any(m in remainder for m in _VAGUE_BOILERPLATE_MARKERS)


def should_keep_document(fields: dict[str, str], para: str) -> bool:
    """
    조건부 최소 길이: 100자 이상은 항상 허용.
    100자 미만은 필드 구조(작물+병명, 증상 길이, 예방·발병)로 허용 여부 판단.
    """
    if len(para) >= LONG_DOC_MIN_CHARS:
        return True
    if len(para) < ABSOLUTE_MIN_CHARS:
        return False

    crop = (fields.get("cropName") or "").strip()
    sick_kor = (fields.get("sickNameKor") or "").strip()
    if not crop and not sick_kor:
        return False

    if _is_only_vague_generic_boilerplate(para, fields):
        return False

    if crop and sick_kor:
        return True
    if len((fields.get("symptoms") or "").strip()) >= SYMPTOMS_MEANINGFUL_MIN:
        return True
    if (fields.get("preventionMethod") or "").strip() or (
        fields.get("developmentCondition") or ""
    ).strip():
        return True
    return False


async def fetch_svc01_list(client: httpx.AsyncClient, sick_keyword: str) -> str:
    params = {
        **SVC01_PARAMS,
        "apiKey": os.getenv("RDA_API_KEY"),
        "sickNameKor": sick_keyword,
    }
    r = await client.get(NCPMS_SERVICE_URL, params=params, timeout=120.0)
    r.raise_for_status()
    return r.text


async def fetch_svc05_detail(client: httpx.AsyncClient, sick_key: str) -> str:
    params = {
        **SVC05_PARAMS,
        "apiKey": os.getenv("RDA_API_KEY"),
        "sickKey": sick_key,
    }
    r = await client.get(NCPMS_SERVICE_URL, params=params, timeout=120.0)
    r.raise_for_status()
    return r.text


def parse_svc01_sick_keys(xml_text: str) -> list[str]:
    """SVC01 item에서 sickKey 목록 (중복 허용 — 호출부에서 set 처리)."""
    root = ET.fromstring(xml_text)
    keys: list[str] = []
    for parent in root.iter():
        if _local_tag(parent.tag) != "item":
            continue
        for ch in parent:
            if _local_tag(ch.tag) == "sickKey" and (ch.text or "").strip():
                keys.append((ch.text or "").strip())
    return keys


def persist_chroma(
    documents: list[str],
    metadatas: list[dict[str, str]],
    vector_db: Path,
    openai_key: str,
) -> None:
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
    vectors = embeddings.embed_documents(documents)

    vector_db.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(vector_db))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    ids = [f"doc_{i}" for i in range(len(documents))]
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,
    )


async def async_main() -> None:
    _load_env()
    _require_rda_key()
    openai_key = _require_openai_key()
    vector_db = _project_root() / "data" / "vector_db"

    max_keys = _parse_max_sick_keys_from_env()

    print("[1] SVC01 sickNameKor로 sickKey 수집…", SICK_NAME_KOR_KEYWORDS)
    sick_keys_ordered: list[str] = []
    seen: set[str] = set()
    async with httpx.AsyncClient() as client:
        for kw in SICK_NAME_KOR_KEYWORDS:
            xml_text = await fetch_svc01_list(client, kw)
            print(f"    sickNameKor={kw!r} XML {len(xml_text)} bytes")
            for sk in parse_svc01_sick_keys(xml_text):
                if sk not in seen:
                    seen.add(sk)
                    sick_keys_ordered.append(sk)
                    if max_keys and len(sick_keys_ordered) >= max_keys:
                        break
            if max_keys and len(sick_keys_ordered) >= max_keys:
                break

    print(f"[1] 고유 sickKey 수: {len(sick_keys_ordered)}" + (f" (상한 {max_keys})" if max_keys else ""))

    documents: list[str] = []
    doc_metas: list[dict[str, str]] = []
    skipped_filter = 0
    skipped_err = 0

    print("[2] SVC05 상세 조회·문단 구성…")
    async with httpx.AsyncClient() as client:
        for i, sk in enumerate(sick_keys_ordered):
            xml_text = await fetch_svc05_detail(client, sk)
            fields = parse_svc05_detail(xml_text)
            if not fields:
                skipped_err += 1
                print(f"    skip (오류/빈응답) sickKey={sk}")
                continue
            para = build_paragraph_from_fields(fields)
            if not should_keep_document(fields, para):
                skipped_filter += 1
                print(f"    skip (조건부 품질 필터 {len(para)}자) sickKey={sk}")
                continue
            documents.append(para)
            doc_metas.append({"sickKey": sk})
            if (i + 1) % 50 == 0:
                print(f"    … 처리 {i + 1}/{len(sick_keys_ordered)}")
            await asyncio.sleep(0.05)

    print(
        f"[2] 저장 대상 문서: {len(documents)} "
        f"(제외: 오류 {skipped_err}, 조건부 필터 {skipped_filter})"
    )

    if not documents:
        print("경고: 저장할 문서가 없어 Chroma에 쓰지 않습니다.")
        return

    print("[3] OpenAI 임베딩 + Chroma 저장…")
    persist_chroma(documents, doc_metas, vector_db, openai_key)

    print("--- 샘플 chunk 3개 (로그) ---")
    for idx in range(min(3, len(documents))):
        d = documents[idx]
        meta = doc_metas[idx]
        preview = d if len(d) <= 500 else d[:500] + "…"
        print(f"[sample {idx + 1}] sickKey={meta.get('sickKey')} len={len(d)}")
        print(preview)
        print()

    print("---")
    print(f"총 문서 수: {len(documents)}")
    print(f"저장 경로: {vector_db.resolve()}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
