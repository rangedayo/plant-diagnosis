"""[B-1] 자료 1 수집 — PSU UCANR (Penn State, Preventing/Diagnosing Common Houseplant Problems).

입력 : data/source/PSU.pdf  (4 pages, 2-column layout + 무선 테두리 테이블 3종)
출력 : data/raw/b_dataset/psu_ucanr/PSU.pdf        (원본 무변형 카피)
       data/raw/b_dataset/psu_ucanr/psu_ucanr.json (파싱 카드)

파싱 전략 (좌표 기반 행 재구성):
  - 테이블 3종(Pest / Disease / Abiotic)은 테두리가 없어 extract_tables 실패.
  - extract_words 좌표로 줄(line)을 클러스터링 후, 좌측 마진(x0≈54)에 단어가 있고
    불릿(§)을 포함하는 줄 = 새 카드. 좌측 마진이 비면 = 직전 카드의 연속 행.
  - 테이블 헤더(Pest/Description, Name/Organism, Symptom/Common Cause)로 섹션 판별.
  - 좌측 마진 + 불릿 없음 = 테이블 종료(꼬리 산문). boilerplate(footer)는 스킵.

본질(변경 금지): Abiotic Problems 테이블이 1단계 FP 직격 — 황화·잎끝 갈변을 환경 원인에 매핑.

실행 (프로젝트 루트에서)::

    python scripts/collect_psu_ucanr.py [--dump]
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

SRC = Path("data/source/PSU.pdf")
OUTDIR = Path("data/raw/b_dataset/psu_ucanr")
SOURCE_ID = "psu_ucanr"
BULLET = "§"  # PDF에서 리스트 불릿이 § 글리프로 추출됨
LEFT_TOL = 14  # 좌측 마진 허용 오차(pt)
LINE_TOL = 4  # 같은 줄로 묶을 top 좌표 허용 오차(pt)

# 테이블 헤더 시그니처 -> (섹션명, 1열 헤더 단어, 2열 헤더 단어)
TABLE_HEADERS: list[tuple[str, str, str]] = [
    ("Pest Problems", "Pest", "Description"),
    ("Disease Problems", "Name", "Organism"),
    ("Abiotic Problems", "Symptom", "Common"),
]
# footer/boilerplate — 좌측 마진에 나타나도 테이블을 끝내지 않고 스킵
BOILERPLATE: tuple[str, ...] = (
    "Cooperative Extension", "College of Agricultural", "PENN STATE",
    "Fact Sheet series", "Suggested", "Prepared by", "www.", "Issued in furtherance",
)


def cluster_lines(words: list[dict]) -> list[dict]:
    """단어들을 top 좌표로 줄 단위 클러스터링 후, 각 줄 내부는 x0 오름차순."""
    lines: list[dict] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(w["top"] - lines[-1]["top"]) <= LINE_TOL:
            lines[-1]["words"].append(w)
            lines[-1]["top"] = (lines[-1]["top"] + w["top"]) / 2
        else:
            lines.append({"top": w["top"], "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
        ln["text"] = " ".join(w["text"] for w in ln["words"])
        ln["min_x0"] = min(w["x0"] for w in ln["words"])
    return lines


def block_text(words: list[dict]) -> str:
    """카드 블록 단어들을 reading order(top, x0)로 합치고 불릿 정규화·공백 정리."""
    ordered = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    txt = " ".join(w["text"] for w in ordered)
    txt = txt.replace(BULLET + " ", "• ").replace(BULLET, "• ")
    return " ".join(txt.split())  # 다중 공백 -> 단일 공백 (의미 단어 삭제 없음)


def is_boilerplate(text: str) -> bool:
    return any(b in text for b in BOILERPLATE)


def detect_header(text: str) -> tuple[str, str, str] | None:
    for section, c1, c2 in TABLE_HEADERS:
        if c1 in text and c2 in text:
            return section, c1, c2
    return None


def collect() -> list[dict]:
    with pdfplumber.open(str(SRC)) as pdf:
        all_lines: list[dict] = []
        for page in pdf.pages:
            all_lines.extend(cluster_lines(page.extract_words()))

    cards: list[dict] = []
    section: str | None = None
    in_table = False
    left_margin = 54.0
    col2_x = 162.0
    cur: dict | None = None  # 현재 카드 누적 버퍼

    def flush() -> None:
        nonlocal cur
        if cur and cur["words"]:
            # 제목 = 카드 첫 줄(최소 top)에서 1열(x0 < col2_x)에 있는 단어만
            first_top = min(w["top"] for w in cur["words"])
            title_words = [
                w for w in cur["words"]
                if w["x0"] < col2_x and abs(w["top"] - first_top) <= LINE_TOL
            ]
            title = block_text(title_words) if title_words else ""
            cards.append({"section": cur["section"], "title": title, "words": cur["words"]})
        cur = None

    for ln in all_lines:
        text = ln["text"]
        hdr = detect_header(text)
        if hdr:
            flush()
            section, c1, c2 = hdr
            in_table = True
            hdr_words = {w["text"]: w["x0"] for w in ln["words"]}
            left_margin = hdr_words.get(c1, 54.0)
            col2_x = hdr_words.get(c2, 162.0)
            continue
        if not in_table:
            continue

        has_left = ln["min_x0"] <= left_margin + LEFT_TOL
        has_bullet = BULLET in text

        if has_left and not has_bullet:
            if is_boilerplate(text):
                continue  # footer -> 무시, 테이블 계속
            flush()  # 꼬리 산문 -> 테이블 종료
            in_table = False
            continue
        if has_left and has_bullet:
            flush()
            cur = {"section": section, "words": list(ln["words"])}
        elif cur is not None:
            cur["words"].extend(ln["words"])  # 연속 행
    flush()

    return cards


def build_json(cards: list[dict]) -> dict:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_cards = [
        {
            "id": f"{SOURCE_ID}_{i:03d}",
            "section": c["section"],
            "title": c["title"],
            "body": block_text(c["words"]),
            "lookalikes": None,
            "external_link": None,
        }
        for i, c in enumerate(cards, 1)
    ]
    return {
        "source": SOURCE_ID,
        "page": "PSU.pdf (Penn State — Preventing, Diagnosing, and Correcting Common Houseplant Problems)",
        "license": "fair_use_personal_educational",
        "fetched_at": fetched_at,
        "card_count": len(out_cards),
        "cards": out_cards,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, OUTDIR / "PSU.pdf")  # 원본 무변형 카피

    data = build_json(collect())
    (OUTDIR / "psu_ucanr.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_sec: dict[str, int] = {}
    for c in data["cards"]:
        by_sec[c["section"]] = by_sec.get(c["section"], 0) + 1
    print(f"[psu_ucanr] {data['card_count']} cards -> {OUTDIR / 'psu_ucanr.json'}")
    for s, n in by_sec.items():
        print(f"   {s}: {n}")

    if "--dump" in sys.argv:
        for c in data["cards"]:
            print(f"  {c['id']} [{c['section']}] {c['title']!r}: {c['body'][:90]}")


if __name__ == "__main__":
    main()
