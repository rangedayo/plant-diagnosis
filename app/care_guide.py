"""[기능 (b)] 종명 키 케어 가이드 lookup.

(a) species_normal_rag(자유서술 정상화 RAG, cosine 검색)와 **별개**. (b)는 농사로 garden의
**구조화 케어 필드**라 RAG가 아니라 **종명 키 딕셔너리 조회**(data/care_guide.json)다.

⚠ 진단 로직과 무관 — analyze 식물명을 종 키로 정규화해 케어 카드를 반환만 한다.
status 무관 항상 첨부(건강일 때도 지속 관리법). 매핑 실패(미등록·미커버) 시 None.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("plant_api")

_CARE_GUIDE_REL = "data/care_guide.json"

# 식별 식물명(통명/학명) → 케어 카드 종 키.
# 구체 종 우선: 행운목·산세베리아는 학명에 'dracaena'/'trifasciata'가 들어가 드라세나속
# catch-all과 충돌하므로 드라세나를 맨 뒤에 둔다 (run_eval._SPECIES_KEYWORD_MAP와 동일 원칙).
SPECIES_KEYWORD_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("행운목", ("행운목", "fragrans", "corn plant")),
    ("산세베리아", ("산세베리아", "산세비에리아", "sansevieria", "snake plant", "trifasciata")),
    ("스파티필룸", ("스파티필", "스파트", "spathiphyllum", "peace lily", "peace lil")),
    ("아글라오네마", ("아글라오네마", "aglaonema", "chinese evergreen")),
    ("접란", ("접란", "chlorophytum", "spider plant", "comosum")),
    ("스킨답서스", ("스킨답서스", "epipremnum", "pothos", "aureum")),
    ("고무나무", ("고무나무", "ficus elastica", "rubber plant", "rubber fig", "elastica")),
    ("몬스테라", ("몬스테라", "monstera", "deliciosa", "swiss cheese")),
    ("드라세나", ("드라세나", "dracaena")),  # 속 catch-all — 맨 뒤
)


def _care_guide_path() -> Path:
    return Path(__file__).resolve().parent.parent / _CARE_GUIDE_REL


@lru_cache(maxsize=1)
def _load_care_guide() -> dict[str, dict[str, Any]]:
    """data/care_guide.json의 species 딕셔너리를 1회 로드·캐시. 실패 시 빈 dict(진단 무영향)."""
    path = _care_guide_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("care_guide.json 없음: %s (케어 가이드 비활성)", path)
        return {}
    except Exception as e:  # noqa: BLE001 — 케어는 부가 기능, 진단을 막지 않는다
        logger.warning("care_guide.json 로드 실패: %s", e)
        return {}
    species = data.get("species")
    if not isinstance(species, dict):
        logger.warning("care_guide.json에 'species' dict 없음")
        return {}
    return species


def normalize_species_key(
    plant_name_korean: str | None, plant_name: str | None = None
) -> str | None:
    """식별 식물명(통명/학명) → 케어 카드 종 키 (없으면 None). 구체 종 우선."""
    hay = f"{plant_name_korean or ''} {plant_name or ''}".lower()
    if not hay.strip():
        return None
    for key, tokens in SPECIES_KEYWORD_MAP:
        if any(tok.lower() in hay for tok in tokens):
            return key
    return None


def lookup_care_guide(
    plant_name_korean: str | None, plant_name: str | None = None
) -> dict[str, Any] | None:
    """식별 식물명 → 케어 카드 dict (없으면 None). 진단 status와 무관, 항상 시도."""
    key = normalize_species_key(plant_name_korean, plant_name)
    if not key:
        return None
    return _load_care_guide().get(key)
