"""[L0-D] run_eval 결과 N개를 평균내 일관된 `_avg` 요약을 산출.

배경: 기존 `eval/*_avg.json`은 스크립트 없이 수동 작성돼 스키마가 파일마다
다르고(`{note,run1,run2,avg}` / `{_doc,runs,...}` / `{meta,average_2runs,...}`)
인코딩도 깨져 있었다(PowerShell Set-Content CP949 혼선). 또 status guard·FP 진단
블록이 빠져 run1/run2 원본을 봐야만 가드 효과가 보였다.

이 스크립트는 run_eval.py 신스키마(가드 전/후 confusion·guard_caught_fp·
status_guard_diagnosis·fp_analysis 포함) run 파일 2개 이상을 읽어 핵심 지표를
평균/합산하고, BOM 없는 UTF-8 JSON으로 저장한다. 전수 dump(per_case·samples)는
평균이 무의미하므로 제외하고 원본 run 경로만 남긴다.

실행 (프로젝트 루트, eval/ 접두 없이 파일명만):

  .venv\\Scripts\\python.exe scripts\\eval_avg.py run1.json run2.json --out avg.json

모델콜 없음(저장된 JSON만 읽음) — Gemini 불필요.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_EVAL_DIR = _ROOT / "eval"

# 평균낼 confusion 필드 (positive_class 같은 라벨은 대표값으로 그대로 보존)
_CONFUSION_NUM_KEYS = ("tp", "tn", "fp", "fn", "precision", "recall", "accuracy")


def _resolve(name: str) -> Path:
    """파일명(또는 상대/절대 경로) → eval/ 기준 경로. eval/ 접두 중복 방지."""
    p = Path(name)
    if p.is_absolute():
        return p
    if p.parts[:1] == ("eval",):
        return _ROOT / p
    return _EVAL_DIR / name


def _load(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8-sig"))


def _mean(values: list[float | None]) -> float | None:
    """None을 제외한 평균. 전부 None이면 None."""
    nums = [v for v in values if v is not None]
    return (sum(nums) / len(nums)) if nums else None


def _round(v: float | None, nd: int = 4) -> float | None:
    return round(v, nd) if isinstance(v, (int, float)) else None


def _avg_confusion(blocks: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    """confusion dict 리스트 → 필드별 평균. 누락 run은 건너뜀."""
    present = [b for b in blocks if isinstance(b, dict)]
    if not present:
        return None
    out: dict[str, Any] = {"positive_class": present[0].get("positive_class", "unhealthy")}
    for k in _CONFUSION_NUM_KEYS:
        out[k] = _round(_mean([b.get(k) for b in present]))
    return out


def _merge_count_dict(dicts: list[dict[str, Any] | None]) -> dict[str, int]:
    """{라벨: 수} dict들을 라벨별로 합산 (분포 누적)."""
    out: dict[str, int] = {}
    for d in dicts:
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if isinstance(v, (int, float)):
                out[k] = out.get(k, 0) + int(v)
    return out


def build_avg(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """run_eval 결과 N개 → 평균 요약 (전수 dump 제외)."""
    totals = {r.get("total") for r in runs}

    def col(path: tuple[str, ...]) -> list[Any]:
        """각 run에서 중첩 키 경로 값을 뽑아 리스트로."""
        vals: list[Any] = []
        for r in runs:
            cur: Any = r
            for key in path:
                cur = cur.get(key) if isinstance(cur, dict) else None
            vals.append(cur)
        return vals

    guard_blocks = col(("status_guard_diagnosis",))
    fp_blocks = col(("fp_analysis",))

    return {
        "total": totals.pop() if len(totals) == 1 else sorted(t for t in totals if t),
        "plant_name_accuracy": _round(_mean(col(("plant_name", "accuracy")))),
        "is_healthy_post_guard": _avg_confusion(col(("is_healthy_post_guard",))),
        "is_healthy_pre_guard": _avg_confusion(col(("is_healthy_pre_guard",))),
        "guard_caught_fp": _round(_mean(col(("guard_caught_fp",))), 2),
        "status_guard": {
            "fired": _round(_mean([(b or {}).get("fired_count") for b in guard_blocks]), 2),
            "correct_fp": _round(
                _mean([(b or {}).get("guard_correct_fp") for b in guard_blocks]), 2
            ),
            "induced_fn": _round(
                _mean([(b or {}).get("guard_induced_fn") for b in guard_blocks]), 2
            ),
            "by_reason_total": _merge_count_dict(
                [(b or {}).get("by_reason") for b in guard_blocks]
            ),
        },
        "fp_analysis": {
            "fp_count": _round(_mean([(b or {}).get("fp_count") for b in fp_blocks]), 2),
            "status_distribution_total": _merge_count_dict(
                [(b or {}).get("fp_status_distribution") for b in fp_blocks]
            ),
            "top3_problem_type_majority_total": _merge_count_dict(
                [(b or {}).get("fp_top3_problem_type_majority") for b in fp_blocks]
            ),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="run_eval 결과 평균 요약 산출")
    ap.add_argument("runs", nargs="+", help="run_eval 출력 파일명(eval/ 기준) 2개 이상")
    ap.add_argument("--out", default="after_avg.json", help="출력 파일명(eval/ 기준)")
    ap.add_argument("--note", default="", help="요약에 남길 메모(선택)")
    args = ap.parse_args()

    run_paths = [_resolve(n) for n in args.runs]
    missing = [str(p) for p in run_paths if not p.is_file()]
    if missing:
        raise SystemExit(f"run 파일 없음: {missing}")

    runs = [_load(p) for p in run_paths]
    result = {
        "_doc": "run_eval N-run 평균 요약 (scripts/eval_avg.py 산출). 전수 dump 제외.",
        "note": args.note,
        "n_runs": len(runs),
        "runs": [str(p.relative_to(_ROOT)).replace("\\", "/") for p in run_paths],
        "avg": build_avg(runs),
    }

    out_path = _resolve(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    avg = result["avg"]
    print(f"[eval_avg] {len(runs)} runs → {out_path}")
    print(f"  plant_acc={avg['plant_name_accuracy']}")
    post, pre = avg["is_healthy_post_guard"], avg["is_healthy_pre_guard"]
    if post and pre:
        print(
            f"  FP 가드전={pre['fp']} → 가드후={post['fp']} "
            f"(잡은 FP={avg['guard_caught_fp']})  FN={post['fn']}"
        )
    print(f"  status_guard={avg['status_guard']}")
    print(f"  fp_analysis={avg['fp_analysis']}")


if __name__ == "__main__":
    main()
