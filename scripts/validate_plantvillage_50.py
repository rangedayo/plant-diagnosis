"""plantvillage_50 보조 평가셋 라벨 검증 진입점.

설계: docs/work_history/ACC-R4_run_eval확장+plantvillage사전매핑.md
성격: 보조 평가셋 라벨 검증 (진단/프론트 무관, LLM/Vision 호출 없음).

동작:
    - test_data/plantvillage_50/labels.json 을 utf-8-sig 로 로드.
    - labeling_vocab.validate_dataset 로 전체 순회 → 분포 리포트 출력.
    - 종료 코드 = 위반(violation) 수 (0 = 전부 통과).

검증 항목 (validate_label에 위임):
    - ground_truth 필수 필드 누락 (true_status 포함)
    - symptoms enum 위반 / unhealthy인데 symptoms 없음
    - true_status enum 위반
    - is_healthy ↔ true_status 정합성 위반

실행 (프로젝트 루트에서)::

    python scripts/validate_plantvillage_50.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from test_data.labeling_vocab import validate_dataset, validate_label  # noqa: E402

LABELS_PATH = _ROOT / "test_data" / "plantvillage_50" / "labels.json"


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"labels.json 형식 오류 또는 빈 배열: {path}")
    return data


def main() -> int:
    labels = _load(LABELS_PATH)

    # 종료 코드용 위반 수 집계 (validate_dataset은 실패 시 ValueError를 던지므로
    # 카운트를 따로 노출하지 않는다 → 공개 API validate_label로 직접 센다).
    violations = 0
    for label in labels:
        try:
            validate_label(label)
        except ValueError:
            violations += 1

    # 분포 리포트는 validate_dataset에 위임(실패 시 리포트 출력 후 raise → 삼킴).
    try:
        validate_dataset(labels)
    except ValueError:
        pass

    return violations


if __name__ == "__main__":
    sys.exit(main())
