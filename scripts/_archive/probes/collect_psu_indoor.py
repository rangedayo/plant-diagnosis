"""[B-1] 자료 2 수집 — PSU Indoor (Pest and Disease Problems of Indoor Plants).

입력 : data/source/Pest_and_Disease_Problems_of_Indo.txt  (markdown 평문)
출력 : data/raw/b_dataset/psu_indoor/pest_and_disease_problems.txt  (원본 무변형 카피)
       data/raw/b_dataset/psu_indoor/psu_indoor.json             (파싱 카드)

파싱 전략:
  - 빈 줄 기준 문단 분리. 섹션 헤더 2종으로 Pests / Diseases 구분.
  - "<Name> — <설명>" (em-dash) 패턴 문단 = problem 카드 (title = em-dash 앞).
  - em-dash 없는 연속 산문(honeydew·control·prevention) = 섹션 notes 카드로 보존.

본질(변경 금지): honeydew → sooty mold 매핑이 본문에 명시 — 1단계 "병해 의심" FP 직격.

실행 (프로젝트 루트에서)::

    python scripts/collect_psu_indoor.py [--dump]
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("data/source/Pest_and_Disease_Problems_of_Indo.txt")
OUTDIR = Path("data/raw/b_dataset/psu_indoor")
SOURCE_ID = "psu_indoor"

# 섹션 헤더 substring -> 정규 섹션명
SECTION_MARKERS: list[tuple[str, str]] = [
    ("Pests Commonly Found", "Pests Commonly Found on Houseplants"),
    ("Diseases That Can Afflict", "Diseases That Can Afflict Houseplants"),
]
EM_DASH = "—"  # —
ENTRY_RE = re.compile(rf"^(?P<name>.+?)\s+{EM_DASH}\s+(?P<rest>.+)$", re.DOTALL)


def detect_section(line: str) -> str | None:
    for marker, name in SECTION_MARKERS:
        if marker in line:
            return name
    return None


def collect() -> list[dict]:
    raw = SRC.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]

    cards: list[dict] = []
    section: str | None = None
    notes_buf: list[str] = []

    def flush_notes() -> None:
        nonlocal notes_buf
        if notes_buf and section is not None:
            body = " ".join(" ".join(p.split()) for p in notes_buf)
            cards.append({
                "section": section,
                "title": f"{section} — overview/notes",
                "body": body,
            })
        notes_buf = []

    def process(block: str) -> None:
        """entry/notes 블록 처리 (헤더 줄은 이미 제거된 상태)."""
        if not block.strip() or section is None:
            return
        m = ENTRY_RE.match(block)
        if m:
            flush_notes()  # 직전 산문 블록을 먼저 카드화
            cards.append({
                "section": section,
                "title": m.group("name").strip(),
                "body": " ".join(block.split()),  # 줄바꿈·다중 공백 정리 (의미 단어 보존)
            })
        else:
            notes_buf.append(block)  # 연속 산문 누적

    for para in paragraphs:
        first_line = para.splitlines()[0].strip()

        if first_line.startswith("#"):
            continue  # 문서 제목(#, ##) 스킵

        sec = detect_section(first_line)
        if sec is not None:
            flush_notes()
            section = sec
            # 헤더와 같은 문단에 붙은 잔여(예: "Aphids — ...")를 이어서 처리
            remainder = "\n".join(para.splitlines()[1:]).strip()
            process(remainder)
            continue
        if section is None:
            continue  # 첫 섹션 이전 인트로 산문 스킵

        process(para)
    flush_notes()

    return cards


def build_json(cards: list[dict]) -> dict:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_cards = [
        {
            "id": f"{SOURCE_ID}_{i:03d}",
            "section": c["section"],
            "title": c["title"],
            "body": c["body"],
            "lookalikes": None,
            "external_link": None,
        }
        for i, c in enumerate(cards, 1)
    ]
    return {
        "source": SOURCE_ID,
        "page": "Pest and Disease Problems of Indoor Plants (Penn State Extension)",
        "license": "fair_use_personal_educational",
        "fetched_at": fetched_at,
        "card_count": len(out_cards),
        "cards": out_cards,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, OUTDIR / "pest_and_disease_problems.txt")  # 원본 무변형 카피

    data = build_json(collect())
    (OUTDIR / "psu_indoor.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_sec: dict[str, int] = {}
    for c in data["cards"]:
        by_sec[c["section"]] = by_sec.get(c["section"], 0) + 1
    print(f"[psu_indoor] {data['card_count']} cards -> {OUTDIR / 'psu_indoor.json'}")
    for s, n in by_sec.items():
        print(f"   {s}: {n}")

    if "--dump" in sys.argv:
        for c in data["cards"]:
            print(f"  {c['id']} [{c['section']}] {c['title']!r}: {c['body'][:80]}")


if __name__ == "__main__":
    main()
