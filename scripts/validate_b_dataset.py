"""[B-1] 검증 게이트 — b_dataset raw 수집 결과 카드 수 + 필수 키워드 체크.

자료별 (카드 수 최소, 필수 키워드)를 검사해 PASS/FAIL 출력. 하나라도 FAIL이면 exit 1.
키워드는 섹션명 또는 본문(body)에서 1회 이상 등장하면 통과(대소문자 무시).

실행 (프로젝트 루트에서)::

    python scripts/validate_b_dataset.py [--dump-bodies]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path("data/raw/b_dataset")

# (라벨, json 경로, 최소 카드 수, 필수 키워드)
GATES: list[tuple[str, str, int, str]] = [
    ("psu_ucanr", "psu_ucanr/psu_ucanr.json", 18, "Abiotic"),
    ("psu_indoor", "psu_indoor/psu_indoor.json", 10, "honeydew"),
    ("mu_trinklein", "mu_trinklein/mu_trinklein.json", 3, "disorder"),
    ("mobot_indoor", "mobot/problems-common-to-many-indoor-plants.json", 19, "Environmental Conditions"),
    ("mobot_herb", "mobot/herb-problems-indoors.json", 10, "winter"),  # 또는 overwintering
]
HERB_ALT_KEYWORD = "overwintering"


def keyword_present(data: dict, keyword: str, alt: str | None = None) -> bool:
    needles = [keyword.lower()] + ([alt.lower()] if alt else [])
    for c in data["cards"]:
        hay = f"{c.get('section', '')} {c.get('title', '')} {c.get('body', '')}".lower()
        if any(n in hay for n in needles):
            return True
    return False


def main() -> None:
    dump = "--dump-bodies" in sys.argv
    all_pass = True
    total = 0

    for label, rel, min_cards, keyword in GATES:
        path = BASE / rel
        if not path.exists():
            print(f"[FAIL] {label:13}: file missing ({rel})")
            all_pass = False
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        n = data.get("card_count", len(data.get("cards", [])))
        total += n
        alt = HERB_ALT_KEYWORD if label == "mobot_herb" else None
        kw_ok = keyword_present(data, keyword, alt)
        count_ok = n >= min_cards
        status = "PASS" if (count_ok and kw_ok) else "FAIL"
        all_pass = all_pass and (count_ok and kw_ok)
        kw_label = keyword + (f"'/'{alt}" if alt else "")
        print(
            f"[{status}] {label:13}: {n:2d} cards (>={min_cards}) "
            f"{'OK' if count_ok else 'TOO FEW'}, "
            f"'{kw_label}' {'found' if kw_ok else 'NOT FOUND'}"
        )
        if dump:
            for c in data["cards"]:
                print(f"        {c['id']}: {c['body'][:80]}")

    print(f"[{'PASS' if all_pass else 'FAIL'}] total: {total} cards")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
