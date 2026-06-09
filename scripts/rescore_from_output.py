"""재측정 없이 기존 측정 출력 + (정정된) labels.json으로 점수만 재계산.

Gemini·gpt-4o-mini·임베딩 등 모델 호출 일절 없음. run_eval._build_result(순수 집계
함수)를 그대로 재사용해, 기존 per_case의 pred_* 는 보존하고 ground_truth(gt_is_healthy,
gt_true_status)만 현행 labels.json으로 재병합한 뒤 모든 지표를 다시 계산한다.

라벨 정정(FP 재검 등) 후 baseline을 재측정 없이 갱신하는 용도.

사용 (프로젝트 루트에서):

    .venv\\Scripts\\python.exe scripts\\rescore_from_output.py <input_eval.json> <output_eval.json>

- input: 기존 run_eval 출력 JSON (per_case 포함).
- 정답: test_data/main_eval/labels.json (현행, 즉 정정 반영본).
- output: 재채점 결과 JSON (baseline.json 덮어쓰기 금지 — 명시 경로로만 출력).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SCRIPTS))

from run_eval import _build_result, _load_labels, _status_to_tier, LABELS_PATH  # noqa: E402


def rescore(input_path: Path, output_path: Path) -> dict:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    per_case = data.get("per_case")
    if not isinstance(per_case, list) or not per_case:
        raise SystemExit(f"입력에 per_case가 없습니다: {input_path}")

    labels = _load_labels(LABELS_PATH)
    gt_by_id = {r["image_id"]: (r.get("ground_truth") or {}) for r in labels}

    remerged = 0
    for c in per_case:
        g = gt_by_id.get(c["image_id"])
        if g is None:
            continue
        new_h = bool(g.get("is_healthy"))
        new_ts = g.get("true_status")
        if c.get("gt_is_healthy") != new_h or c.get("gt_true_status") != new_ts:
            remerged += 1
        c["gt_is_healthy"] = new_h
        c["gt_true_status"] = new_ts
        # [R16] 3단 tier 재병합: gt_tier는 labels.json에서, pred_tier는 보존된 pred_status에서.
        c["gt_tier"] = g.get("tier")
        c["pred_tier"] = _status_to_tier(c.get("pred_status"))
        if c.get("pred_is_healthy") is not None:
            c["healthy_match"] = c["pred_is_healthy"] == new_h

    result = _build_result(len(per_case), per_case)
    result["rescored_from"] = str(input_path)
    result["rescore_note"] = (
        "no model calls; gt re-merged from labels.json; pred_* unchanged"
    )
    result["rescore_remerged_cases"] = remerged

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return result


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "사용: python scripts/rescore_from_output.py <input_eval.json> <output_eval.json>"
        )
    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    if outp.name == "baseline.json":
        raise SystemExit("baseline.json 덮어쓰기 금지 — 다른 출력 경로를 지정하세요.")
    result = rescore(inp, outp)
    ih = result["is_healthy_post_guard"]
    print(f"re-merged gt for {result['rescore_remerged_cases']} case(s)")
    print(
        f"is_healthy(post-guard): tp={ih['tp']} tn={ih['tn']} fp={ih['fp']} "
        f"fn={ih['fn']} acc={ih['accuracy']:.4f}"
    )
    td = result["tier_diagnosis"]
    oc = td["over_call"]
    print(
        f"tier(3단): exact={td['exact_match']}/{td['scored']} "
        f"cardinal_miss={td['cardinal_miss']} soft_miss={td['soft_miss']} "
        f"minor_undercall={td['minor_undercall']} "
        f"over_call={oc['total']}(→경미{oc['to_mild']}/→비건강{oc['to_unhealthy']})"
    )
    print(f"저장: {outp}")


if __name__ == "__main__":
    main()
