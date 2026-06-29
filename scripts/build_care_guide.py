"""[기능 (b)] 농사로 garden API에서 평가셋 9종의 케어 필드를 받아 종명 키 케어 카드
(data/care_guide.json)를 만든다.

설계 ([기능b] 작업 프롬프트 PART A):
- (a) species_normal_rag(자유서술 RAG)와 **별개**. (b)는 **구조화 케어 필드**라
  RAG/cosine이 아니라 **종명 키 lookup** 딕셔너리.
- gardenDtl에서 케어 필드(토양·계절별 물주기·광량·온습도·비료·배치·관리난이도 등)만
  보수적 추출. 코드값(Code) 말고 한글명(CodeNm) 위주.
- 품종 레벨이 아닌 **종 레벨 대표 카드** (같은 종은 케어 유사).
- 진단 로직과 무관 — 진단 응답에 첨부만 한다.

실행 (프로젝트 루트):

  .venv\\Scripts\\python.exe -X utf8 scripts\\build_care_guide.py

`.env`에 RDA_API_KEY 필요. 호출 9회(gardenDtl), 무료.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DTL_URL = "http://api.nongsaro.go.kr/service/garden/gardenDtl"
OUT_REL = "data/care_guide.json"

# 평가셋 9종 → 농사로 garden cntntsNo (종 레벨 대표).
# 4종은 [단계 B'] 종 매핑(→ docs/species_normalization_mapping.md)에서 확인됨, 5종은 [기능b] gardenList 검색으로 확보.
# (species_key, display_name, cntntsNo, note)
SPECIES: tuple[tuple[str, str, str, str], ...] = (
    ("드라세나", "드라세나", "14676", "송오브자마이카 — 드라세나속 대표"),
    ("행운목", "행운목", "12983", "Dracaena fragrans"),
    ("스파티필룸", "스파티필룸", "19717", "Spathiphyllum wallisii (평가셋 표기 '스파티필름')"),
    ("산세베리아", "산세베리아", "19448", "Sansevieria trifasciata"),
    ("아글라오네마", "아글라오네마", "19469", "gardenList 정확 매칭"),
    ("접란", "접란", "16447", "gardenList 정확 매칭"),
    ("스킨답서스", "스킨답서스", "19716", "gardenList 정확 매칭"),
    ("고무나무", "데코라고무나무", "13337", "Ficus elastica 대표 (속 공통 케어)"),
    ("몬스테라", "몬스테라", "16449", "gardenList 정확 매칭"),
)

# garden gardenDtl 응답 키 → 케어 카드 필드. 한글명(CodeNm)/Info 위주.
FIELD_MAP: dict[str, str] = {
    "soilInfo": "soil",
    "lighttdemanddoCodeNm": "light",
    "grwhTpCodeNm": "temperature",
    "hdCodeNm": "humidity",
    "frtlzrInfo": "fertilizer",
    "postngplaceCodeNm": "placement",
    "managelevelCodeNm": "manage_level",
    "winterLwetTpCodeNm": "winter_min_temp",
    "growthHgInfo": "growth_height_cm",
    "growthAraInfo": "growth_area_cm",
    "plntbneNm": "scientific_name",
    "cntntsSj": "src_cntntsSj",
}
WATER_MAP: dict[str, str] = {
    "watercycleSprngCodeNm": "spring",
    "watercycleSummerCodeNm": "summer",
    "watercycleAutumnCodeNm": "autumn",
    "watercycleWinterCodeNm": "winter",
}


def _t(tag: str | None) -> str:
    if not tag:
        return ""
    return tag.split("}", 1)[1] if "}" in tag else tag


def _require_key() -> str:
    key = (os.getenv("RDA_API_KEY") or "").strip()
    if not key:
        print("오류: .env에 RDA_API_KEY가 필요합니다.", file=sys.stderr)
        sys.exit(1)
    return key


async def fetch_detail(client: httpx.AsyncClient, key: str, no: str) -> dict[str, str]:
    r = await client.get(DTL_URL, params={"apiKey": key, "cntntsNo": no}, timeout=60.0)
    r.raise_for_status()
    fields: dict[str, str] = {}
    root = ET.fromstring(r.text)
    for item in root.iter("item"):
        for ch in item:
            fields[_t(ch.tag)] = (ch.text or "").strip()
    return fields


def build_card(
    species_key: str, display_name: str, cntntsNo: str, note: str, raw: dict[str, str]
) -> dict[str, object]:
    card: dict[str, object] = {
        "species_key": species_key,
        "display_name": display_name,
        "src_cntntsNo": cntntsNo,
        "note": note,
    }
    for src, dst in FIELD_MAP.items():
        val = raw.get(src, "").strip()
        if val:
            card[dst] = val
    water = {dst: raw.get(src, "").strip() for src, dst in WATER_MAP.items()}
    water = {k: v for k, v in water.items() if v}
    if water:
        card["water"] = water
    return card


async def main() -> None:
    load_dotenv(ROOT / ".env")
    key = _require_key()
    species_cards: dict[str, dict[str, object]] = {}
    report: list[str] = []

    async with httpx.AsyncClient() as client:
        for species_key, display_name, no, note in SPECIES:
            raw = await fetch_detail(client, key, no)
            card = build_card(species_key, display_name, no, note, raw)
            species_cards[species_key] = card
            present = [k for k in (*FIELD_MAP.values(), "water") if k in card]
            sci = card.get("scientific_name", "")
            report.append(
                f"  {species_key:10} no={no} 학명={sci!r} 필드={len(present)} "
                f"(물주기={'O' if 'water' in card else 'X'})"
            )

    out = {
        "_doc": (
            "[기능 (b)] 농사로 garden API 종명 키 케어 카드. RAG 아님 — 종명 lookup용. "
            "(a) species_normal_rag(자유서술 정상화 RAG)와 별개. 진단 로직 무관, 응답 첨부 전용."
        ),
        "source": "nongsaro_garden_dtl",
        "version": "care_guide_v1",
        "fetched_at": datetime.date.today().isoformat(),
        "species_count": len(species_cards),
        "species": species_cards,
    }
    out_path = ROOT / OUT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[care_guide] {len(species_cards)}종 적재 → {out_path}")
    for line in report:
        print(line)


if __name__ == "__main__":
    asyncio.run(main())
