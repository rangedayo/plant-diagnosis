"""
UC IPM PDF(pnhouseplantproblems.pdf) + 수동 정제 HOUSEPLANT(data/houseplant.txt)로 a_dataset_rag를 구축한다.

- pnhouseplantproblems.pdf: UC IPM Pest Notes (Table 1 + MANAGEMENT)
- data/houseplant.txt: issue_type / symptoms / cause / solution 블록(불릿)

실행 (프로젝트 루트에서):

  .venv\\\\Scripts\\\\python.exe scripts\\\\build_main_rag.py

`.env`에 OPENAI_API_KEY 필요. `data/vector_db`에 Chroma `a_dataset_rag` 컬렉션 생성.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, TypedDict

import chromadb
import pdfplumber
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

COLLECTION_NAME = "a_dataset_rag"
# 임베딩 모델: 검색(app.graph)·다른 적재 스크립트와 동일해야 cosine이 유효.
# langchain_openai 기본값을 명시 고정(기본값 변경 사고 방지).
EMBEDDING_MODEL = "text-embedding-ada-002"

PDF_UC_IPM = "data/raw_sources/pnhouseplantproblems.pdf"
HOUSEPLANT_TXT = "data/houseplant.txt"

# PDF 기반 하우스플랜트 파싱은 비활성화(data/houseplant.txt 사용)
PDF_HOUSEPLANT = "FSA-6116.pdf"


class MainDoc(TypedDict):
    source: str
    plant_name: str
    issue_type: str
    symptoms: str
    cause: str
    solution: str


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


def extract_pdf_text_pages(path: Path) -> str:
    """페이지별 텍스트 추출 후 전체 결합."""
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    return "\n".join(parts)


def _column_words_to_text(words: list[dict[str, Any]]) -> str:
    if not words:
        return ""
    words.sort(key=lambda w: (round(w["top"] / 2), w["x0"]))
    lines: list[str] = []
    cur_top: float | None = None
    line_words: list[str] = []
    for w in words:
        t = round(w["top"] / 2)
        if cur_top is None:
            cur_top = t
        if t != cur_top:
            lines.append(" ".join(line_words))
            line_words = [w["text"]]
            cur_top = t
        else:
            line_words.append(w["text"])
    if line_words:
        lines.append(" ".join(line_words))
    return "\n".join(lines)


def two_column_left_then_right_page(page: Any) -> str:
    """
    2단 PDF: 열 단위로 위→아래 읽은 뒤 왼쪽 열 전체 + 오른쪽 열 전체.
    (행 우선 병합은 'Leaves Small and Off-Color' 등 제목이 열 사이에 끼어 깨짐)
    """
    words = page.extract_words()
    if not words:
        return ""
    mid = page.width / 2
    left = [w for w in words if (w["x0"] + w["x1"]) / 2 < mid]
    right = [w for w in words if (w["x0"] + w["x1"]) / 2 >= mid]
    return _column_words_to_text(left) + "\n" + _column_words_to_text(right)


def extract_houseplant_pdf_ordered(path: Path) -> str:
    """FSA-6116: 열 단위(좌→우) 텍스트."""
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(two_column_left_then_right_page(page))
    text = "\n\n".join(chunks)
    return text.replace("\u2019", "'").replace("\u2018", "'")


# (정규식, 표시용 issue_type)
FSA_SECTION_PATTERNS: list[tuple[str, str]] = [
    (r"Marginal or Tip Leaf Burn", "Marginal or Tip Leaf Burn"),
    (r"Sudden Leaf Drop", "Sudden Leaf Drop"),
    (r"Leaves Small and\s+Off-Color", "Leaves Small and Off-Color"),
    (r"Slow Loss of\s+(?:Our Campus\s+)?Lower Leaves", "Slow Loss of Lower Leaves"),
    (r"Leaves Mottled on the Upper Surface", "Leaves Mottled on the Upper Surface"),
    (r"Plants Don't Grow", "Plants Don't Grow"),
    (r"Plants Don't Flower", "Plants Don't Flower"),
    (r"Leaves Distorted With\s+the\s+Edges\s+Curled\s+Down", "Leaves Distorted With the Edges Curled Down"),
    (r"Tips of Fig Tree Dying", "Tips of Fig Tree Dying"),
    (r"Plants Have\s+White\s+Globs\s+on\s+the\s+Stems", "Plants Have White Globs on the Stems"),
    (r"Floor Is Sticky", "Floor Is Sticky"),
    (r"Small Gnats Buzzing Around Plant", "Small Gnats Buzzing Around Plant"),
]


def _strip_fsa_boilerplate(body: str) -> str:
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if re.search(
            r"^(Visit our web site|University of Arkansas|https?://|Our Campus|Arkansas Is|Cooperating)",
            s,
            re.I,
        ):
            continue
        if "Department of Agriculture" in s and "County" in s:
            continue
        lines.append(line)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


_CAUSE_RE = re.compile(
    r"\b(cause|caused|due to|associated with|indicates|usually|result from|often|infested)\b",
    re.I,
)
_SOLUTION_RE = re.compile(
    r"\b(repot|spray|control|prune|apply|wash |remove |isolate|fertiliz|discard|destroy|"
    r"mist|insecticidal|horticultural oil|bleach|drench|systemic)\b",
    re.I,
)


def split_houseplant_fields(body: str) -> tuple[str, str, str]:
    """규칙 기반: 증상/원인/대처 문장 분리."""
    body = _strip_fsa_boilerplate(body)
    if not body:
        return "", "", ""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    if not sentences:
        return body, "", ""

    symptoms: list[str] = []
    cause: list[str] = []
    solution: list[str] = []
    for i, sent in enumerate(sentences):
        if _SOLUTION_RE.search(sent) and (symptoms or cause):
            solution.append(sent)
        elif _CAUSE_RE.search(sent) and symptoms:
            cause.append(sent)
        elif len(symptoms) < 3:
            symptoms.append(sent)
        elif _CAUSE_RE.search(sent):
            cause.append(sent)
        else:
            solution.append(sent)

    sym_s = " ".join(symptoms).strip()
    c_s = " ".join(cause).strip()
    sol_s = " ".join(solution).strip()
    if not c_s and not sol_s:
        # 폴백: 앞부분 증상, 나머지 본문
        mid = max(len(body) // 2, 120)
        sym_s = body[:mid].strip()
        sol_s = body[mid:].strip()
    return sym_s, c_s, sol_s


def _strip_bullet_line(line: str) -> str:
    s = line.strip()
    if s.startswith("•"):
        return s[1:].strip()
    if s.startswith("*"):
        return s[1:].strip()
    if s.startswith("-"):
        return s[1:].strip()
    return s


def _join_field_lines(lines: list[str]) -> str:
    """불릿/항목을 하나의 문자열로 (쉼표 구분)."""
    parts = [x.strip() for x in lines if x.strip()]
    return ", ".join(parts)


def parse_houseplant_txt(path: Path) -> list[MainDoc]:
    """
    data/houseplant.txt — issue_type / symptoms / cause / solution 블록.
    각 블록은 줄 시작(선행 공백 허용)의 issue_type: 마커로 구분. 대소문자 무시. 불릿은 *, -, • 허용.
    빈 필드가 있으면 해당 블록은 건너뜀(경고 로그).
    """
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        print("경고: houseplant.txt가 비어 있습니다.", file=sys.stderr)
        return []

    # 줄 시작(공백 허용)의 issue_type: 마커 개수 — 분리 전 검사
    issue_marker_re = re.compile(r"^\s*issue_type\s*:", re.I | re.MULTILINE)
    marker_count = len(issue_marker_re.findall(raw))
    if marker_count <= 1:
        print(
            f"경고: houseplant.txt에서 issue_type 마커가 {marker_count}개입니다. "
            "여러 블록을 기대했다면 형식을 확인하세요.",
            file=sys.stderr,
        )

    # 블록 분리: 줄 시작의 (선행 공백 허용) issue_type: 앞에서 자름
    blocks = [
        b.strip()
        for b in re.split(r"(?im)(?=^\s*issue_type\s*:)", raw)
        if b.strip()
    ]
    print(f"HOUSEPLANT 블록 수: {len(blocks)}")
    if len(blocks) <= 1:
        print(
            "경고: HOUSEPLANT 블록이 1개 이하입니다. 파싱 실패 가능성이 있습니다 "
            "(issue_type: 줄 앞 공백/줄바꿈, 또는 마커 누락을 확인하세요).",
            file=sys.stderr,
        )

    out: list[MainDoc] = []
    for bi, block in enumerate(blocks):
        issue_lines: list[str] = []
        sym: list[str] = []
        cause: list[str] = []
        sol: list[str] = []
        section: str | None = None

        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            hm = re.match(r"^(issue_type|symptoms|cause|solution)\s*:\s*(.*)$", stripped, re.I)
            if hm:
                key = hm.group(1).lower()
                rest = hm.group(2).strip()
                if key == "issue_type":
                    section = "issue_type"
                    if rest:
                        issue_lines.append(rest)
                elif key == "symptoms":
                    section = "symptoms"
                    if rest and rest[0] in "*-•":
                        sym.append(_strip_bullet_line(rest))
                elif key == "cause":
                    section = "cause"
                    if rest and rest[0] in "*-•":
                        cause.append(_strip_bullet_line(rest))
                elif key == "solution":
                    section = "solution"
                    if rest and rest[0] in "*-•":
                        sol.append(_strip_bullet_line(rest))
                continue

            if stripped[0] in "*-•":
                bullet = _strip_bullet_line(stripped)
                if section == "symptoms":
                    sym.append(bullet)
                elif section == "cause":
                    cause.append(bullet)
                elif section == "solution":
                    sol.append(bullet)
            elif section == "issue_type":
                issue_lines.append(stripped)

        issue_type = " ".join(issue_lines).strip()
        symptoms_s = _join_field_lines(sym)
        cause_s = _join_field_lines(cause)
        solution_s = _join_field_lines(sol)

        if not (issue_type and symptoms_s and cause_s and solution_s):
            print(
                f"경고: houseplant 블록 {bi + 1} 건너뜀 (빈 필드: "
                f"issue_type={bool(issue_type)}, symptoms={bool(symptoms_s)}, "
                f"cause={bool(cause_s)}, solution={bool(solution_s)})",
                file=sys.stderr,
            )
            continue

        out.append(
            {
                "source": "HOUSEPLANT",
                "plant_name": "generic",
                "issue_type": issue_type,
                "symptoms": symptoms_s,
                "cause": cause_s,
                "solution": solution_s,
            }
        )
    return out


def parse_houseplant_pdf(path: Path) -> list[MainDoc]:
    """
    [비활성화] FSA-6116 PDF에서 하우스플랜트 섹션 파싱.
    현재 파이프라인은 parse_houseplant_txt(data/houseplant.txt)만 사용한다.
    """
    text = extract_houseplant_pdf_ordered(path)
    spans: list[tuple[int, int, str]] = []
    # 제목은 원문 대소문자와 일치 (본문의 "Sudden leaf drop" 등 오탐 방지)
    for pat, label in FSA_SECTION_PATTERNS:
        for m in re.finditer(pat, text, re.DOTALL):
            spans.append((m.start(), m.end(), label))
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    # 동일 시작 위치는 가장 긴 매치만
    by_start: dict[int, tuple[int, int, str]] = {}
    for s, e, name in spans:
        if s not in by_start or (e - s) > (by_start[s][1] - by_start[s][0]):
            by_start[s] = (s, e, name)
    ordered = sorted(by_start.values(), key=lambda x: x[0])

    out: list[MainDoc] = []
    for i, (_s, e, issue_type) in enumerate(ordered):
        next_start = ordered[i + 1][0] if i + 1 < len(ordered) else len(text)
        body = text[e:next_start].strip()
        sym, cau, sol = split_houseplant_fields(body)
        out.append(
            {
                "source": "HOUSEPLANT",
                "plant_name": "generic",
                "issue_type": issue_type,
                "symptoms": sym,
                "cause": cau,
                "solution": sol,
            }
        )
    return out


def extract_uc_ipm_management(full_text: str) -> str:
    """MANAGEMENT 섹션(일반 문화적 관리) ~ CONTROLLING INSECT 직전."""
    end = full_text.find("CONTROLLING INSECT")
    if end < 0:
        end = len(full_text)
    block = full_text[:end]
    # 열 혼합이 적은 본문 앵커 우선
    best = block.find("The best approach to long term")
    if best >= 0:
        return re.sub(r"\s+", " ", block[best:]).strip()
    idx = block.find("MANAGEMENT rotating indoor plants")
    if idx < 0:
        m = re.search(r"\nMANAGEMENT\s+", block, re.IGNORECASE)
        idx = m.start() if m else -1
    if idx < 0:
        return ""
    return re.sub(r"\s+", " ", block[idx:]).strip()


def parse_uc_ipm_pdf(path: Path) -> list[MainDoc]:
    """Table 1 + MANAGEMENT 블록."""
    full = extract_pdf_text_pages(path)
    management = extract_uc_ipm_management(full)

    with pdfplumber.open(path) as pdf:
        page3 = pdf.pages[2]
        tables = page3.extract_tables() or []

    rows: list[tuple[str, str]] = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [((c or "").strip().lower()) for c in table[0]]
        if "symptom" in " ".join(header) and "possible" in " ".join(header):
            for row in table[1:]:
                if not row or len(row) < 2:
                    continue
                sym = re.sub(r"\s+", " ", (row[0] or "").strip())
                cause = re.sub(r"\s+", " ", (row[1] or "").strip())
                if sym.lower() in ("symptom", "") or cause.lower() in ("possible causes", ""):
                    continue
                if sym.lower() == "symptom":
                    continue
                rows.append((sym, cause))
            break

    out: list[MainDoc] = []
    for sym, cause in rows:
        issue = sym[:120] + ("…" if len(sym) > 120 else "")
        out.append(
            {
                "source": "UC_IPM",
                "plant_name": "generic",
                "issue_type": issue,
                "symptoms": sym,
                "cause": cause,
                "solution": management,
            }
        )
    return out


def flatten_document(doc: MainDoc) -> str:
    it = doc["issue_type"] or "general"
    return (
        f"[{it}]\n"
        f"symptoms: {doc['symptoms']}\n"
        f"cause: {doc['cause']}\n"
        f"solution: {doc['solution']}"
    )


def normalize_for_index(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s가-힣]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dedupe_exact(strings: list[str]) -> tuple[list[str], list[int]]:
    """완전 동일 문자열만 제거. 첫 인덱스 유지."""
    seen: set[str] = set()
    keep_idx: list[int] = []
    for i, s in enumerate(strings):
        if s in seen:
            continue
        seen.add(s)
        keep_idx.append(i)
    return [strings[i] for i in keep_idx], keep_idx


def persist_main_rag(
    documents: list[str],
    metadatas: list[dict[str, str]],
    vector_db: Path,
    openai_key: str,
) -> None:
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key, model=EMBEDDING_MODEL)
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
    ids = [f"a_dataset_{i}" for i in range(len(documents))]
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,
    )


def main() -> None:
    _load_env()
    openai_key = _require_openai_key()
    root = _project_root()
    vector_db = root / "data" / "vector_db"

    uc_path = root / PDF_UC_IPM
    hs_txt = root / HOUSEPLANT_TXT
    if not uc_path.is_file():
        print(f"오류: PDF 없음: {uc_path}", file=sys.stderr)
        sys.exit(1)
    if not hs_txt.is_file():
        print(f"오류: 파일 없음: {hs_txt}", file=sys.stderr)
        sys.exit(1)

    print("[1] UC IPM PDF + houseplant.txt 로드…")
    uc_docs = parse_uc_ipm_pdf(uc_path)
    hs_docs = parse_houseplant_txt(hs_txt)
    all_docs: list[MainDoc] = uc_docs + hs_docs

    print(f"    UC_IPM 문서: {len(uc_docs)}, HOUSEPLANT 문서: {len(hs_docs)}")

    flat_raw = [flatten_document(d) for d in all_docs]
    flat_norm = [normalize_for_index(t) for t in flat_raw]

    unique_norm, keep_idx = dedupe_exact(flat_norm)
    flat_out = [flat_raw[i] for i in keep_idx]
    meta_out: list[dict[str, str]] = []
    for i in keep_idx:
        d = all_docs[i]
        meta_out.append(
            {
                "source": d["source"],
                "issue_type": (d["issue_type"] or "")[:2000],
                "plant_name": (d.get("plant_name") or "generic")[:500],
            }
        )

    print(f"[2] 전처리 후 문서 수: {len(flat_out)} (중복 제거 {len(flat_raw) - len(flat_out)})")

    if not flat_out:
        print("경고: 저장할 문서가 없습니다.")
        return

    print("[3] OpenAI 임베딩 + Chroma 저장…")
    persist_main_rag(flat_out, meta_out, vector_db, openai_key)


if __name__ == "__main__":
    main()
