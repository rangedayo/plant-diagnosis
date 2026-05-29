"""[1-3] analyze 프롬프트 v2 통합 검증 (일회성 스크립트).

검증 계획 8장에 대해 v2 ANALYZE_SYSTEM으로 GeminiProvider.analyze()를 1회씩 호출하고
6필드 출력 + 정답 라벨(labels.json) 비교를 stdout으로 출력한다.

실행: PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe _validate_analyze_prompt_v2.py
(GEMINI_API_KEY 필요 — app.model_utils가 import 시 load_dotenv())

확정 후 ANALYZE_SYSTEM은 app/prompts.py로 옮기고 이 스크립트는 삭제 예정.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from app.vision.base import VisionInput
from app.vision.gemini import GeminiProvider

# v2 프롬프트 (1-3_analyze_프롬프트_초안_v1.md 의 ANALYZE_SYSTEM, 검토포인트 1~4 확정 반영)
ANALYZE_SYSTEM = """당신은 식물 이미지를 분석해 구조화된 JSON으로 답하는 조력자입니다.
출력은 유효한 JSON 객체 하나뿐이어야 합니다. 마크다운, 코드 블록, 설명 문장은 절대 금지입니다.

반드시 다음 6개 키를 모두 사용하세요 (이름·순서 변경 금지):

- "plant_name": 문자열. 식물 학명(영문). 가장 가능성 높은 1위만.
- "plant_name_korean": 문자열. 식물의 한국어 명칭. 한국 원예·화훼 시장에서 통용되는 유통명이 있으면 그 이름을 우선 사용하세요 (예: "스파티필름", "몬스테라", "산세베리아"). 학명 음역만 알려진 경우 음역을 쓰되, 통용명이 있으면 음역 옆 괄호로 함께 표기할 수 있습니다 (예: "드라세나 프라그란스 (행운목)").
- "plant_confidence": 문자열. 정확히 다음 중 하나만: "low", "med", "high".
  - "high": 잎·줄기·전체 형태가 명확해 단일 종으로 확신할 때.
  - "med": 같은 속(genus) 안에서 1~2개 후보로 좁혔으나 종(species) 확신은 약할 때.
  - "low": 속 단위에서도 후보가 분산되거나 이미지 품질이 불충분할 때.
- "alt_candidates": 문자열 배열. 대안 학명 후보(영문 학명만). 최대 3개.
  같은 속(genus) 안에서 잎 형태가 유사해 헷갈리는 종이 있으면 우선 포함하세요 (예: Dracaena 속이나 Aglaonema 속).
- "visual_description": 문자열. 이미지에 보이는 식물의 시각적 묘사를 한국어로 작성.
  잎의 모양·색·무늬·잎맥, 줄기 형태, 화분 환경 등을 사실 그대로 기술하세요.
  가능하면 식물학적 용어를 활용하면 좋습니다 (예: "평행한 잎맥", "긴 피침형 잎").
- "observed_symptoms": 문자열 배열. 이미지에서 명확히 보이는 이상 징후만 간결한 명사구로 기록(한국어).
  예: "잎끝 갈변", "잎 표면 노란 반점", "잎 처짐".
  개수를 채우려 없는 증상을 만들지 마세요. 종 고유의 무늬·형태, 물리적 흠집·벌레 먹은 자국, 물방울·먼지 같은 환경 요인은 증상이 아닙니다.
  이상이 보이지 않으면 빈 배열 [].

규칙:
- 값은 모두 한국어로 작성하되, plant_name과 alt_candidates의 학명만은 영문 그대로.
- 당신의 역할은 **관찰**입니다. 진단(병명 단정)·처방(조치 권고)·건강 여부 판단은 다른 단계의 책임이므로 이 출력에는 포함하지 마세요.
  "~로 보입니다", "~가 관찰됩니다" 같은 관찰형 표현을 쓰고, "이 식물은 ~병에 걸렸습니다", "이 식물은 건강합니다" 같은 단정 표현은 피하세요.
- 식별 신뢰도는 자기보고(self-report)입니다. 분명히 모르겠으면 "low"를 솔직히 선택하세요. 거짓 확신은 금지입니다.
- JSON 키는 반드시 큰따옴표로 감싼 표준 JSON 형식.
- 출력 외 어떤 텍스트도 추가하지 마세요."""

ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "test_data" / "main_eval" / "images"
LABELS_PATH = ROOT / "test_data" / "main_eval" / "labels.json"

VALIDATION_IDS = [
    "self_dracaena_001",
    "self_haengun_001",
    "self_haengun_004",
    "inat_monstera_deliciosa_001",
    "inat_sansevieria_trifasciata_001",
    "inat_spathiphyllum_001",
    "inat_chlorophytum_comosum_002",
    "self_haengun_002",
]


def _load_ground_truth() -> dict[str, dict]:
    rows = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return {r["image_id"]: r["ground_truth"] for r in rows}


async def _run() -> None:
    gt = _load_ground_truth()
    provider = GeminiProvider(system_prompt=ANALYZE_SYSTEM)

    for image_id in VALIDATION_IDS:
        image_path = IMAGES_DIR / f"{image_id}.jpg"
        if not image_path.exists():
            print(f"[SKIP] {image_id}: 이미지 없음")
            continue

        t0 = time.perf_counter()
        out = await provider.analyze(
            VisionInput(image_bytes=image_path.read_bytes(), mime_type="image/jpeg")
        )
        latency = time.perf_counter() - t0

        truth = gt.get(image_id, {})
        print("=" * 78)
        print(f"[{image_id}]  latency={latency:.1f}s")
        print(
            f"  GT  : plant={truth.get('plant_name_korean')!r} "
            f"symptoms={truth.get('symptoms')}"
        )
        print(f"  --- v2 analyze ---")
        print(f"  plant_name        : {out.plant_name!r}")
        print(f"  plant_name_korean : {out.plant_name_korean!r}")
        print(f"  plant_confidence  : {out.plant_confidence!r}")
        print(f"  alt_candidates    : {out.alt_candidates}")
        print(f"  observed_symptoms : {out.observed_symptoms}")
        print(f"  visual_description: {out.visual_description}")

    print("=" * 78)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    asyncio.run(_run())
