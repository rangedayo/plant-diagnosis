"""
baseline 측정 스크립트 — test_data/main_eval/labels.json (33장) 기준.

측정 범위 (이것만):
  1. 식물 이름 정확도 (학명 → PLANT_NAME_KO_MAP 한국어 변환 후 비교)
  2. 건강 여부 정확도 (structured_result.status → bool, ground_truth.is_healthy 비교)
  3. status 분포 + is_healthy 교차표
  4. 보조 지표: JSON 파싱 성공률, 케이스별 latency

진단 호출은 HTTP(/diagnose)가 아니라 app.graph.build_diagnosis_graph 를 직접 구동.
(scripts/eval_rag.py 의 _initial_state / app/main.py 초기 state 패턴을 그대로 따름)

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

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SCRIPTS))  # eval_retrieval 재사용 ([B-4a] 경우 2)

from app import prompts  # noqa: E402
from app.graph import _vector_db_path, build_diagnosis_graph  # noqa: E402
from app.vision.gemini import GeminiProvider  # noqa: E402
from test_data.labeling_vocab import PLANT_NAME_KO_MAP  # noqa: E402

# [B-4a] FP 본질 진단 측정 — graph.py 무변경 원칙(경우 2):
# state엔 rag_docs(텍스트)만 박히고 메타(card_id·problem_type)는 누락되므로
# [B-3] eval_retrieval._retrieve_top_n 을 동일 쿼리로 재호출해 top_3 메타를 얻는다.
from eval_retrieval import _retrieve_top_n  # noqa: E402

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
    """app/main.py / eval_rag._initial_state 와 동일한 초기 state."""
    return {
        "image_bytes": image_bytes,
        "plant_name": None,
        "plant_name_korean": None,
        "plant_confidence": None,
        "alt_candidates": [],
        "visual_description": "",
        "observed_symptoms": [],
        "keywords": [],
        "rag_query": "",
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


# ───────────────────────────── [B-4a] FP 진단 측정 ─────────────────────────────
# read-only 추가. 본 라벨링 계산 무변경. graph.py 무변경(경우 2: 동일 쿼리 재검색).

def _query_for_retrieval(out: dict[str, Any]) -> str:
    """graph retrieve_node와 동일한 검색 쿼리 재구성: ``(query_en or query_ko)``.

    graph.py:407 ``mq = (query_en or query_ko).strip()`` 거울.
    query_en = keyword_node가 state에 박은 keywords_en, query_ko = rag_query.
    """
    query_en = " ".join(out.get("keywords_en") or []).strip()
    query_ko = (out.get("rag_query") or "").strip()
    return query_en or query_ko


def _build_top_3_rag(out: dict[str, Any], db_path: str) -> list[dict[str, Any]]:
    """RAG retrieve 상위 3개 카드 메타 (eval_retrieval._retrieve_top_n 재사용)."""
    query = _query_for_retrieval(out)
    if not query:
        return []
    top_10 = _retrieve_top_n(query, db_path)
    return [
        {
            "card_id": item.get("card_id") or "",
            "problem_type": item.get("problem_type") or "",
            "source": item.get("source") or "",
            "title": item.get("title") or "",
            "sim": item.get("sim", 0.0),
            # eval_retrieval은 b_dataset/main 구분을 source 키로 통합 (프롬프트 §2 허용)
            "rag_source": item.get("source") or "",
        }
        for item in top_10[:3]
    ]


def _count_by_key(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    """FP 케이스를 특정 키 값으로 집계 (None → "(none)")."""
    out: dict[str, int] = {}
    for c in cases:
        v = c.get(key)
        label = str(v) if v not in (None, "") else "(none)"
        out[label] = out.get(label, 0) + 1
    return out


def _majority_problem_type(top_3_rag: list[dict[str, Any]] | None) -> str:
    """top_3 카드의 problem_type 다수결. 동률→"tie", 비어있음→"(empty)"."""
    types = [str(t.get("problem_type") or "") for t in (top_3_rag or [])]
    types = [t for t in types if t]
    if not types:
        return "(empty)"
    counts: dict[str, int] = {}
    for t in types:
        counts[t] = counts.get(t, 0) + 1
    top = max(counts.values())
    leaders = [t for t, n in counts.items() if n == top]
    return "tie" if len(leaders) > 1 else leaders[0]


def _count_top3_majority(fp_cases: list[dict[str, Any]]) -> dict[str, int]:
    """각 FP 케이스의 top_3 problem_type 다수결 분포 집계."""
    out: dict[str, int] = {}
    for c in fp_cases:
        maj = _majority_problem_type(c.get("top_3_rag"))
        out[maj] = out.get(maj, 0) + 1
    return out


def _build_fp_analysis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """FP 17건 분포 분석 — [B-4a] 핵심 산출물. FP 정의는 본 e2e와 동일.

    gt_is_healthy=True AND pred_is_healthy is False (None=skip/error 제외).
    """
    fp_cases = [
        c
        for c in per_case
        if c.get("gt_is_healthy") and c.get("pred_is_healthy") is False
    ]
    return {
        "fp_count": len(fp_cases),
        "fp_status_distribution": _count_by_key(fp_cases, "pred_status"),
        "fp_observed_symptoms_buckets": {
            "empty": sum(1 for c in fp_cases if not c.get("observed_symptoms")),
            "non_empty": sum(1 for c in fp_cases if c.get("observed_symptoms")),
        },
        "fp_top3_problem_type_majority": _count_top3_majority(fp_cases),
        "fp_observed_symptoms_samples": [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "pred_status": c["pred_status"],
                "observed_symptoms": c.get("observed_symptoms") or [],
                "top_3_problem_types": [
                    str(t.get("problem_type") or "") for t in (c.get("top_3_rag") or [])
                ],
            }
            for c in fp_cases
        ],
    }


def _build_tp_analysis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """TP(진짜 아픈데 맞춤) + FN(진짜 아픈데 놓침) 분포 — [B-4c] recall 안전장치.

    TP: gt_is_healthy=False AND pred_is_healthy is False
    FN: gt_is_healthy=False AND pred_is_healthy is True  ← recall 직격, 0이어야 정상
    """
    sick_cases = [
        c
        for c in per_case
        if c.get("gt_is_healthy") is False and c.get("pred_is_healthy") is not None
    ]
    tp_cases = [c for c in sick_cases if c.get("pred_is_healthy") is False]
    fn_cases = [c for c in sick_cases if c.get("pred_is_healthy") is True]

    def _dump(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "pred_status": c["pred_status"],
                "observed_symptoms": c.get("observed_symptoms") or [],
                "top_3_problem_types": [
                    str(t.get("problem_type") or "") for t in (c.get("top_3_rag") or [])
                ],
                "top_3_majority": _majority_problem_type(c.get("top_3_rag")),
            }
            for c in cases
        ]

    return {
        "tp_count": len(tp_cases),
        "fn_count": len(fn_cases),
        "tp_status_distribution": _count_by_key(tp_cases, "pred_status"),
        "tp_top3_majority": _count_top3_majority(tp_cases),
        "fn_top3_majority": _count_top3_majority(fn_cases),
        # 전수 dump (TP+FN 합쳐 ~5건)
        "tp_samples": _dump(tp_cases),
        "fn_samples": _dump(fn_cases),  # ← 비어 있어야 recall 100%
    }


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
    graph = build_diagnosis_graph(vision_provider)
    db_path = str(_vector_db_path())  # [B-4a] top_3_rag 재검색용

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
                    "observed_symptoms": [],
                    "top_3_rag": [],
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
                    "observed_symptoms": [],
                    "top_3_rag": [],
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
                # [B-4a] FP 진단 측정 신규 키 (read-only)
                "observed_symptoms": list(out.get("observed_symptoms") or []),
                "top_3_rag": _build_top_3_rag(out, db_path),
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
        "fp_analysis": _build_fp_analysis(per_case),  # [B-4a] FP 17건 본질 진단
        "tp_analysis": _build_tp_analysis(per_case),  # [B-4c] recall 안전장치
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

    fpa = result["fp_analysis"]
    print("\n[FP 분석] ([B-4a])")
    print(f"  FP={fpa['fp_count']}")
    print(f"  status 분포: {fpa['fp_status_distribution']}")
    print(f"  observed_symptoms: {fpa['fp_observed_symptoms_buckets']}")
    print(f"  top_3 problem_type 다수결: {fpa['fp_top3_problem_type_majority']}")

    tpa = result["tp_analysis"]
    print("\n[TP/FN 분석] ([B-4c] recall 안전장치)")
    print(f"  TP={tpa['tp_count']}  FN={tpa['fn_count']} (FN>0이면 recall 깎임)")
    print(f"  TP status: {tpa['tp_status_distribution']}")
    print(f"  TP top_3 majority: {tpa['tp_top3_majority']}")
    print(f"  FN top_3 majority: {tpa['fn_top3_majority']}")

    print("\n[관찰 증상 문장 - TP 케이스 (진짜 아픈 식물)]")
    for s in tpa["tp_samples"]:
        print(f"  - {s['image_id']} [{s['pred_status']}] majority={s['top_3_majority']}")
        print(f"    증상: {s['observed_symptoms']}")
    if tpa["fn_samples"]:
        print("\n[(주의) 관찰 증상 문장 - FN 케이스 (놓친 아픈 식물)]")
        for s in tpa["fn_samples"]:
            print(f"  - {s['image_id']} [{s['pred_status']}] majority={s['top_3_majority']}")
            print(f"    증상: {s['observed_symptoms']}")

    print("\n[관찰 증상 문장 - FP 케이스 일부 (오진 유지분, 최대 8건)]")
    for s in fpa.get("fp_observed_symptoms_samples", [])[:8]:
        print(f"  - {s['image_id']} [{s['pred_status']}]")
        print(
            f"    증상: {s.get('observed_symptoms', [])}  "
            f"타입: {s.get('top_3_problem_types', [])}"
        )
    print("\n저장:", OUTPUT_PATH)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
