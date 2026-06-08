"""[B-1] 자료 4+5 수집 — Mobot (Missouri Botanical Garden visual guides) 2페이지 HTML 스크래핑.

입력 URL:
  Indoor: .../visual-guides/problems-common-to-many-indoor-plants
  Herb  : .../visual-guides/herb-problems-indoors
출력 (data/raw/b_dataset/mobot/):
  problems-common-to-many-indoor-plants.html / .json   (카드 21: Env 8 / Insects 7 / Diseases 4 / Nutrient 2)
  herb-problems-indoors.html / .json                   (카드 12)

확정 셀렉터 (사용자 승인): td > strong
  - 첫 <strong> = 카드 제목, <td> 본문(제목 strong 위치부터) = body.
  - 제목 strong 앞 텍스트(이미지 크레딧 등)는 제거 — 예: Nitrogen deficiency td의
    "John Ruter, University of Georgia, Bugwood.org" prefix.
  - Indoor 섹션 = 선행 <h2>. Herb는 'Insects and insectlike pests' 카드를 분기점으로 섹션 전환.
  - lookalikes: 'may...or' 정규식이 honeydew 외형 묘사를 오탐하고 의도한 감별진단 문구는
    안정 추출 불가 → 5자료 모두 null (스키마 필드는 유지). 본문(body)에 원문 보존됨.

스크래핑 매너: User-Agent 박기, robots Crawl-delay 30초 준수, timeout 30s, 재시도 1회.
raw HTML이 이미 있으면 재사용(재fetch 안 함).

실행 (프로젝트 루트에서)::

    python scripts/collect_mobot.py [--refetch] [--dump]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

OUTDIR = Path("data/raw/b_dataset/mobot")
USER_AGENT = "plant-diagnosis-research/0.1 (educational; rangedayo@naver.com; +https://github.com/rangedayo)"
CRAWL_DELAY_S = 30  # robots.txt: User-agent:* Crawl-delay 30
TIMEOUT_S = 30

PAGES: list[dict] = [
    {
        "source_id": "mobot_indoor",
        "html": "problems-common-to-many-indoor-plants.html",
        "json": "problems-common-to-many-indoor-plants.json",
        "url": "https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/problems-common-to-many-indoor-plants",
        "page": "Problems Common to Many Indoor Plants (Missouri Botanical Garden visual guide)",
    },
    {
        "source_id": "mobot_herb",
        "html": "herb-problems-indoors.html",
        "json": "herb-problems-indoors.json",
        "url": "https://www.missouribotanicalgarden.org/gardens-gardening/your-garden/help-for-the-home-gardener/advice-tips-resources/visual-guides/herb-problems-indoors",
        "page": "Herb Problems Indoors (Missouri Botanical Garden visual guide)",
    },
]

INDOOR_CATEGORIES = {"Environmental Conditions", "Insects", "Diseases", "Nutrient Deficiencies"}
HERB_INSECT_MARKER = "Insects and insectlike pests"
NOISE_TITLES = {"Menu", ""}


def fetch_all(refetch: bool) -> list[str]:
    """raw HTML 확보 — 파일 있으면 재사용, 없거나 --refetch면 매너 지켜 fetch."""
    notes: list[str] = []
    headers = {"User-Agent": USER_AGENT}
    fetched = 0
    for page in PAGES:
        path = OUTDIR / page["html"]
        if path.exists() and not refetch:
            notes.append(f"{page['html']}: reuse cached ({path.stat().st_size} B)")
            continue
        if fetched > 0:
            time.sleep(CRAWL_DELAY_S)  # 페이지 간 Crawl-delay
        last_exc: Exception | None = None
        for attempt in (1, 2):  # 최초 + 재시도 1회
            try:
                r = httpx.get(page["url"], headers=headers, timeout=TIMEOUT_S, follow_redirects=True)
                r.raise_for_status()
                path.write_text(r.text, encoding="utf-8")
                notes.append(f"{page['html']}: HTTP {r.status_code}, {len(r.text)} B (attempt {attempt})")
                break
            except Exception as exc:  # noqa: BLE001 - 매너상 중단·보고
                last_exc = exc
                time.sleep(CRAWL_DELAY_S)
        else:
            raise RuntimeError(f"fetch 실패(2회): {page['url']} -> {last_exc}")
        fetched += 1
    return notes


def text_from(strong: Tag, td: Tag) -> str:
    """td 본문을 제목 strong 위치부터 수집(앞쪽 이미지 크레딧 등 prefix 제거) + 공백 정리."""
    parts: list[str] = []
    started = False
    for el in td.descendants:
        if el is strong:
            started = True
        if started and isinstance(el, NavigableString):
            parts.append(str(el))
    return " ".join(" ".join(parts).split())


def is_card_td(td: Tag, title: str, body: str) -> bool:
    if title in NOISE_TITLES or len(body) <= len(title) + 10:
        return False
    return td.find("td") is None  # 최내곽 td만(중첩 셀 제외)


def parse_cards(html: str, source_id: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[dict] = []
    current_section: str | None = None

    for el in soup.descendants:
        name = getattr(el, "name", None)
        if name == "h2":
            t = el.get_text(strip=True)
            if t in INDOOR_CATEGORIES:
                current_section = t
            continue
        if name != "td":
            continue
        strong = el.find("strong")
        if strong is None:
            continue
        title = strong.get_text(" ", strip=True)
        body = text_from(strong, el)
        if not is_card_td(el, title, body):
            continue

        if source_id == "mobot_indoor":
            section = current_section or "Indoor problems"
        else:  # mobot_herb — h2 카테고리 없음, 곤충 마커로 섹션 전환
            if title == HERB_INSECT_MARKER:
                current_section = HERB_INSECT_MARKER
            section = current_section or "Growing herbs — cultural & environmental"

        cards.append({"section": section, "title": title, "body": body})
    return cards


def build_json(cards: list[dict], page: dict, fetched_at: str) -> dict:
    out_cards = [
        {
            "id": f"{page['source_id']}_{i:03d}",
            "section": c["section"],
            "title": c["title"],
            "body": c["body"],
            "lookalikes": None,
            "external_link": None,
        }
        for i, c in enumerate(cards, 1)
    ]
    return {
        "source": page["source_id"],
        "page": page["page"],
        "license": "fair_use_personal_educational",
        "fetched_at": fetched_at,
        "card_count": len(out_cards),
        "cards": out_cards,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    notes = fetch_all(refetch="--refetch" in sys.argv)
    for n in notes:
        print("  fetch:", n)

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for page in PAGES:
        html = (OUTDIR / page["html"]).read_text(encoding="utf-8")
        cards = parse_cards(html, page["source_id"])
        data = build_json(cards, page, fetched_at)
        (OUTDIR / page["json"]).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        by_sec: dict[str, int] = {}
        for c in data["cards"]:
            by_sec[c["section"]] = by_sec.get(c["section"], 0) + 1
        print(f"[{page['source_id']}] {data['card_count']} cards -> {OUTDIR / page['json']}")
        for s, n in by_sec.items():
            print(f"   {s}: {n}")
        if "--dump" in sys.argv:
            for c in data["cards"]:
                print(f"   {c['id']} [{c['section'][:20]}] {c['title']!r}: {c['body'][len(c['title']):][:55].strip()}")


if __name__ == "__main__":
    main()
