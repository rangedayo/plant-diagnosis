"""일회성: 기존 baseline per_case 학명 예측에 갱신된 PLANT_NAME_KO_MAP만 재적용.

모델을 재호출하지 않으므로 is_healthy/status/latency 등은 그대로 유지되고,
식물명 한국어 열·집계만 새 맵 기준으로 재산출된다. (맵 변경 효과 격리용)
run_eval.py 의 _scientific_to_korean / _aggregate_and_report 를 그대로 재사용.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_eval import (
    LABELS_PATH,
    OUTPUT_PATH,
    _aggregate_and_report,
    _scientific_to_korean,
)

_ROOT = Path(__file__).resolve().parent.parent


def _gt_plant_by_id() -> dict[str, str]:
    """정정된 labels.json 의 image_id -> plant_name_korean (현재 정답)."""
    with open(LABELS_PATH, "rb") as f:
        labels = json.loads(f.read().decode("utf-8-sig"))
    return {
        r["image_id"]: r["ground_truth"]["plant_name_korean"] for r in labels
    }


def main() -> None:
    with open(OUTPUT_PATH, "rb") as f:
        data = json.loads(f.read().decode("utf-8-sig"))
    per_case = data["per_case"]
    total = data["total"]
    gt_map = _gt_plant_by_id()

    for c in per_case:
        # 정정된 정답지(labels.json) gt 로 동기화 — frozen baseline 의 stale gt 교정.
        if c.get("image_id") in gt_map:
            c["gt_plant"] = gt_map[c["image_id"]]
        pred_ko = _scientific_to_korean(c.get("pred_plant_scientific"))
        c["pred_plant_ko"] = pred_ko
        if pred_ko is None:
            c["plant_match"] = None
        else:
            c["plant_match"] = pred_ko == c.get("gt_plant")

    _aggregate_and_report(total, per_case)


if __name__ == "__main__":
    main()
