"""
baseline 측정 스크립트 — test_data/main_eval/labels.json (33장) 기준.

측정 범위 (이것만):
  1. 식물 이름 정확도 (학명 → PLANT_NAME_KO_MAP 한국어 변환 후 비교)
  2. 건강 여부 정확도 (structured_result.status → bool, ground_truth.is_healthy 비교)
  3. status 분포 + is_healthy 교차표
  4. 보조 지표: JSON 파싱 성공률, 케이스별 latency

진단 호출은 HTTP(/diagnose)가 아니라 app.graph.build_diagnosis_graph 를 직접 구동.
(scripts/eval_rag.py 의 _initial_state / app/main.py:183-199 초기 state 패턴을 그대로 따름)

app/ 코드는 수정하지 않는다. 결과는 eval/baseline.json (BOM 없는 UTF-8).

TODO(baseline 제외, 추후 정밀 채점기 별도 작업):
  - symptoms 코드 채점 (ground_truth.symptoms vs 모델 증상 추출)
  - diagnosis 텍스트 채점 (ground_truth.diagnosis vs structured_result 텍스트)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app import prompts  # noqa: E402
from app.graph import build_diagnosis_graph  # noqa: E402
from app.vision.gemini import GeminiProvider  # noqa: E402
from test_data.labeling_vocab import PLANT_NAME_KO_MAP  # noqa: E402

LABELS_PATH = _ROOT / "test_data" / "main_eval" / "labels.json"
# 기본은 baseline.json. RUN_EVAL_OUT로 출력 파일명을 바꿔 baseline 덮어쓰기 방지
# (예: [1-5] 회귀 측정은 RUN_EVAL_OUT=after_phase1_wiring.json).
OUTPUT_PATH = _ROOT / "eval" / os.environ.get("RUN_EVAL_OUT", "baseline.json")

STRUCT_REQUIRED_KEYS = ("summary", "current_state", "cause", "action_plan", "status")
HEALTHY_STATUS = "건강"


def _load_labels(path: Path) -> list[dict[str, Any]]:
    with open(path, "rb") as f:
        data = json.loads(f.read().decode("utf-8-sig"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"labels.json 형식 오류 또는 빈 배열: {path}")
    return data


def _initial_state(image_bytes: bytes) -> dict[str, Any]:
    """app/main.py:183-199 / eval_rag._initial_state 와 동일한 초기 state."""
    return {
        "image_bytes": image_bytes,
        "plant_filter_mode": "strict",
        "plant_name": None,
        "plant_name_korean": None,
        "plant_confidence": None,
        "alt_candidates": [],
        "visual_description": "",
        "observed_symptoms": [],
        "disease_name": None,
        "confidence": None,
        "is_healthy_prob": None,
        "top_candidates": [],
        "description": "",
        "keywords": [],
        "rag_query": "",
        "fallback_plant_name": None,
        "rag_docs": [],
        "sick_keys": [],
        "rag_doc_sick_pairs": [],
        "structured_result": {},
    }


def _scientific_to_korean(plant_name_scientific: str | None) -> str | None:
    """학명 → 한국어. 정확히 키가 일치할 때만 변환, 아니면 None(=unmappable)."""
    if not plant_name_scientific:
        return None
    return PLANT_NAME_KO_MAP.get(str(plant_name_scientific).strip())


def _status_to_is_healthy(status: str | None) -> bool:
    """status "건강" → True, 나머지 → False."""
    return str(status or "").strip() == HEALTHY_STATUS


def _struct_json_ok(structured_result: Any) -> bool:
    """structured_result가 5키를 모두 갖춘 dict인지."""
    if not isinstance(structured_result, dict):
        return False
    return all(k in structured_result for k in STRUCT_REQUIRED_KEYS)


async def _run_one_case(graph, image_bytes: bytes) -> tuple[dict[str, Any], float]:
    """그래프 1회 구동. (최종 state, latency_sec) 반환."""
    start = time.perf_counter()
    out = await graph.ainvoke(_initial_state(image_bytes))
    latency = time.perf_counter() - start
    return out, latency


def _safe_div(num: float, den: float) -> float | None:
    return (num / den) if den else None


async def async_main() -> None:
    load_dotenv(_ROOT / ".env")
    labels = _load_labels(LABELS_PATH)
    total = len(labels)
    print(f"[run_eval] 평가셋 {total}장 로드: {LABELS_PATH}")

    per_case: list[dict[str, Any]] = []

    vision_provider = GeminiProvider(system_prompt=prompts.ANALYZE_SYSTEM)
    async with httpx.AsyncClient() as client:
        graph = build_diagnosis_graph(client, vision_provider)

        for i, row in enumerate(labels, start=1):
            image_id = row.get("image_id", "")
            gt = row.get("ground_truth", {}) or {}
            gt_plant = gt.get("plant_name_korean")
            gt_is_healthy = bool(gt.get("is_healthy"))
            rel = row.get("image_path", "")
            img_path = _ROOT / rel

            if not img_path.is_file():
                print(f"[{i}/{total}] {image_id}: [skip] 이미지 없음 {rel}")
                per_case.append(
                    {
                        "image_id": image_id,
                        "gt_plant": gt_plant,
                        "pred_plant_scientific": None,
                        "pred_plant_ko": None,
                        "plant_match": None,
                        "gt_is_healthy": gt_is_healthy,
                        "pred_status": None,
                        "pred_is_healthy": None,
                        "healthy_match": None,
                        "latency_sec": None,
                        "json_ok": False,
                        "error": "image_not_found",
                    }
                )
                continue

            image_bytes = img_path.read_bytes()
            try:
                out, latency = await _run_one_case(graph, image_bytes)
            except Exception as e:  # noqa: BLE001 — baseline은 케이스 실패를 기록만
                print(f"[{i}/{total}] {image_id}: [error] {type(e).__name__}: {e}")
                per_case.append(
                    {
                        "image_id": image_id,
                        "gt_plant": gt_plant,
                        "pred_plant_scientific": None,
                        "pred_plant_ko": None,
                        "plant_match": None,
                        "gt_is_healthy": gt_is_healthy,
                        "pred_status": None,
                        "pred_is_healthy": None,
                        "healthy_match": None,
                        "latency_sec": None,
                        "json_ok": False,
                        "error": f"{type(e).__name__}: {e}",
                    }
                )
                continue

            pred_sci = out.get("plant_name")
            pred_ko = _scientific_to_korean(pred_sci)
            sr = out.get("structured_result")
            json_ok = _struct_json_ok(sr)
            pred_status = sr.get("status") if isinstance(sr, dict) else None
            pred_is_healthy = _status_to_is_healthy(pred_status)

            # 식물명: 변환 불가(unmappable) / 일치(correct) / 불일치(wrong)
            if pred_ko is None:
                plant_match: bool | None = None  # unmappable
            else:
                plant_match = pred_ko == gt_plant

            healthy_match = pred_is_healthy == gt_is_healthy

            per_case.append(
                {
                    "image_id": image_id,
                    "gt_plant": gt_plant,
                    "pred_plant_scientific": pred_sci,
                    "pred_plant_ko": pred_ko,
                    "plant_match": plant_match,
                    "gt_is_healthy": gt_is_healthy,
                    "pred_status": pred_status,
                    "pred_is_healthy": pred_is_healthy,
                    "healthy_match": healthy_match,
                    "latency_sec": round(latency, 3),
                    "json_ok": json_ok,
                }
            )
            print(
                f"[{i}/{total}] {image_id}: plant={pred_sci!r}->{pred_ko!r} "
                f"(gt={gt_plant!r}) status={pred_status!r} "
                f"gt_healthy={gt_is_healthy} json_ok={json_ok} {latency:.1f}s"
            )

    _aggregate_and_report(total, per_case)


def _aggregate_and_report(total: int, per_case: list[dict[str, Any]]) -> None:
    # --- 식물 이름 ---
    correct = sum(1 for c in per_case if c["plant_match"] is True)
    wrong = sum(1 for c in per_case if c["plant_match"] is False)
    unmappable = sum(1 for c in per_case if c["plant_match"] is None)
    plant_acc = _safe_div(correct, correct + wrong)  # 매칭가능한 것 중 비율

    # --- 건강 여부 (unhealthy = positive) ---
    scored = [c for c in per_case if c["pred_is_healthy"] is not None]
    tp = sum(1 for c in scored if not c["gt_is_healthy"] and not c["pred_is_healthy"])
    tn = sum(1 for c in scored if c["gt_is_healthy"] and c["pred_is_healthy"])
    fp = sum(1 for c in scored if c["gt_is_healthy"] and not c["pred_is_healthy"])
    fn = sum(1 for c in scored if not c["gt_is_healthy"] and c["pred_is_healthy"])
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    healthy_acc = _safe_div(tp + tn, len(scored))

    # --- status 분포 + is_healthy 교차표 ---
    status_dist: dict[str, int] = {}
    status_by_health: dict[str, dict[str, int]] = {}
    for c in per_case:
        st = c["pred_status"]
        if st is None:
            st = "(none)"
        status_dist[st] = status_dist.get(st, 0) + 1
        bucket = status_by_health.setdefault(st, {"gt_healthy": 0, "gt_unhealthy": 0})
        if c["gt_is_healthy"]:
            bucket["gt_healthy"] += 1
        else:
            bucket["gt_unhealthy"] += 1

    # --- 보조 지표 ---
    json_ok_count = sum(1 for c in per_case if c["json_ok"])
    json_rate = _safe_div(json_ok_count, total)
    latencies = [c["latency_sec"] for c in per_case if c["latency_sec"] is not None]
    if latencies:
        lat = {
            "mean": round(sum(latencies) / len(latencies), 3),
            "min": round(min(latencies), 3),
            "max": round(max(latencies), 3),
        }
    else:
        lat = {"mean": None, "min": None, "max": None}

    json_fail_ids = [c["image_id"] for c in per_case if not c["json_ok"]]

    result = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "total": total,
        "plant_name": {
            "correct": correct,
            "wrong": wrong,
            "unmappable": unmappable,
            "accuracy": plant_acc,
        },
        "is_healthy": {
            "positive_class": "unhealthy",
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "accuracy": healthy_acc,
        },
        "status_distribution": status_dist,
        "status_by_is_healthy": status_by_health,
        "json_parse_success_rate": json_rate,
        "json_parse_failed_ids": json_fail_ids,
        "latency_sec": lat,
        "per_case": per_case,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # --- 콘솔 요약표 ---
    def pct(v: float | None) -> str:
        return f"{v:.1%}" if v is not None else "N/A"

    print("\n" + "=" * 56)
    print("BASELINE 요약")
    print("=" * 56)
    print(f"총 케이스: {total}")
    print("\n[식물 이름]")
    print(f"  correct={correct}  wrong={wrong}  unmappable={unmappable}")
    print(f"  정확도(매칭가능 중): {pct(plant_acc)}")
    print("\n[건강 여부] (positive=unhealthy)")
    print(f"  TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(f"  precision={pct(precision)}  recall={pct(recall)}  accuracy={pct(healthy_acc)}")
    print("\n[status 분포]")
    for st, cnt in sorted(status_dist.items(), key=lambda x: -x[1]):
        h = status_by_health.get(st, {})
        print(
            f"  {st:10} {cnt:3}  (gt건강={h.get('gt_healthy',0)}, "
            f"gt비건강={h.get('gt_unhealthy',0)})"
        )
    print("\n[보조 지표]")
    print(f"  JSON 파싱 성공률: {pct(json_rate)} ({json_ok_count}/{total})")
    if json_fail_ids:
        print(f"  JSON 실패 케이스: {json_fail_ids}")
    print(f"  latency(s): mean={lat['mean']} min={lat['min']} max={lat['max']}")
    print("\n저장:", OUTPUT_PATH)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
