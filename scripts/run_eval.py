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

import argparse
import asyncio
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SCRIPTS))  # eval_retrieval 재사용 ([B-4a] 경우 2)

from app import prompts  # noqa: E402
from app.care_guide import normalize_species_key  # noqa: E402
from app.graph import (  # noqa: E402
    _vector_db_path,
    build_diagnosis_graph,
)
from app.vision.gemini import GeminiProvider  # noqa: E402
from test_data.labeling_vocab import (  # noqa: E402
    PLANT_NAME_KO_MAP,
    STATUS_AMBIGUOUS,
    STATUS_VOCAB,
)

# [B-prime→status guard] gt_plant → 종 키 매핑. B' 종 주입 revert 후 graph가
# _normalize_species를 더는 export 안 하므로 run_eval 자립용 로컬 사본
# (FP를 종별로 분해하는 진단 목적, 주입 로직과 무관한 순수 매퍼).
_SPECIES_KEYWORD_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("행운목", ("행운목", "fragrans", "corn plant")),
    ("스파티필룸", ("스파티필", "스파트", "spathiphyllum", "peace lil")),
    ("산세베리아", ("산세베리아", "산세비에리아", "sansevieria", "snake plant", "trifasciata")),
    ("드라세나", ("드라세나", "dracaena")),
)


def _normalize_species(
    plant_name_korean: str | None, plant_name: str | None = None
) -> str | None:
    """식별/gt 식물명 → 종 키 (없으면 None). 구체 종 우선(행운목 먼저)."""
    hay = f"{plant_name_korean or ''} {plant_name or ''}".lower()
    if not hay.strip():
        return None
    for key, tokens in _SPECIES_KEYWORD_MAP:
        if any(tok.lower() in hay for tok in tokens):
            return key
    return None

# [B-4a] FP 본질 진단 측정 — graph.py 무변경 원칙(경우 2):
# state엔 rag_docs(텍스트)만 박히고 메타(card_id·problem_type)는 누락되므로
# [B-3] eval_retrieval._retrieve_top_n 을 동일 쿼리로 재호출해 top_3 메타를 얻는다.
from eval_retrieval import _retrieve_top_n  # noqa: E402

LABELS_PATH = _ROOT / "test_data" / "main_eval" / "labels.json"
# [ACC-R4] --aux 보조 측정용 PlantVillage 50장 평가셋.
PLANTVILLAGE_LABELS_PATH = _ROOT / "test_data" / "plantvillage_50" / "labels.json"
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
    # [ACC-R4] §137 — ambiguous는 이진 TP/FN 분모에서도 제외.
    sick_cases = [
        c
        for c in per_case
        if c.get("gt_is_healthy") is False
        and c.get("pred_is_healthy") is not None
        and not _is_ambiguous(c)
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


def _build_species_normal_diagnosis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """[B-prime] 종 메타 (a) 정상화 효과 진단 — (i)/(ii)/(iii) 판정 근거.

    gt_plant이 이번 라운드 커버 종(드라세나/행운목/스파티필룸/산세베리아)인 케이스만 대상.
    - card_injected: generate 컨텍스트에 정상화 카드가 실제로 올라간 케이스 수.
    - covered_fp_with_card_present: 카드가 올라갔는데도 FP(오진) 유지 → (ii) generate 무시.
    - covered_fp_without_card: 커버 종인데 카드 미주입(analyze 종 오식별) → (i) 연결 문제.
    """
    rows: list[tuple[str, dict[str, Any]]] = []
    for c in per_case:
        gt_key = _normalize_species(c.get("gt_plant"), None)
        if gt_key:
            rows.append((gt_key, c))

    by_species: dict[str, dict[str, int]] = {}
    for gt_key, c in rows:
        b = by_species.setdefault(
            gt_key,
            {
                "images": 0,
                "card_injected": 0,
                "healthy": 0,
                "fp": 0,
                "sick": 0,
                "tp": 0,
                "fn": 0,
                "inject_mismatch": 0,
            },
        )
        b["images"] += 1
        injected = int(c.get("species_normal_card_count") or 0) > 0
        if injected:
            b["card_injected"] += 1
        sn_sp = c.get("species_normal_species") or ""
        if sn_sp and sn_sp != gt_key:
            b["inject_mismatch"] += 1
        gt_h = c.get("gt_is_healthy")
        pred_h = c.get("pred_is_healthy")
        if gt_h:
            b["healthy"] += 1
            if pred_h is False:
                b["fp"] += 1
        elif gt_h is False:
            b["sick"] += 1
            if pred_h is False:
                b["tp"] += 1
            elif pred_h is True:
                b["fn"] += 1

    fp_with_card = sum(
        1
        for _k, c in rows
        if c.get("gt_is_healthy")
        and c.get("pred_is_healthy") is False
        and int(c.get("species_normal_card_count") or 0) > 0
    )
    tot_fp = sum(b["fp"] for b in by_species.values())
    return {
        "covered_gt_species": sorted(by_species.keys()),
        "covered_gt_images": sum(b["images"] for b in by_species.values()),
        "covered_gt_healthy_images": sum(b["healthy"] for b in by_species.values()),
        "card_injected_images": sum(b["card_injected"] for b in by_species.values()),
        "covered_fp": tot_fp,
        "covered_fp_with_card_present": fp_with_card,  # (ii) generate 무시
        "covered_fp_without_card": tot_fp - fp_with_card,  # (i) analyze 오식별
        "covered_fn": sum(b["fn"] for b in by_species.values()),  # recall 안전장치
        "by_species": by_species,
    }


def _build_status_guard_diagnosis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """[status guard] over-escalate 교정 발동 진단 — PART C 핵심 산출물.

    - fired_count: guard가 비건강→건강으로 내린 건수.
    - by_reason: 발동 사유 분포(empty_symptoms / all_cosmetic_nondisease_top1).
    - guard_correct_fp: 발동분 중 gt_is_healthy=True (진짜 FP를 올바로 교정).
    - guard_induced_fn: 발동분 중 gt_is_healthy=False (아픈 식물을 깎음) ← 0이어야 정상.
    - fired_samples: 전수 dump (교정 정확도·FN 수동 검증용).
    """
    fired = [c for c in per_case if c.get("guard_fired")]
    correct_fp = [c for c in fired if c.get("gt_is_healthy") is True]
    induced_fn = [c for c in fired if c.get("gt_is_healthy") is False]

    by_reason: dict[str, int] = {}
    for c in fired:
        r = str(c.get("guard_reason") or "(none)")
        by_reason[r] = by_reason.get(r, 0) + 1

    def _dump(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "gt_is_healthy": c.get("gt_is_healthy"),
                "guard_reason": c.get("guard_reason"),
                "pre_status": c.get("guard_pre_status"),
                "post_status": c.get("pred_status"),
                # [정합] cause 재생성 전(generate "병해 의심")/후(건강 전제) 대조
                "cause_regenerated": c.get("guard_cause_regenerated"),
                "pre_cause": c.get("guard_pre_cause"),
                "post_cause": c.get("pred_cause"),
                "observed_symptoms": c.get("observed_symptoms") or [],
                "top_3_problem_types": [
                    str(t.get("problem_type") or "") for t in (c.get("top_3_rag") or [])
                ],
            }
            for c in cases
        ]

    return {
        "fired_count": len(fired),
        "by_reason": by_reason,
        "guard_correct_fp": len(correct_fp),  # 진짜 FP 교정
        "guard_induced_fn": len(induced_fn),  # ← 0이어야 recall 안전
        "fired_samples": _dump(fired),
        "induced_fn_samples": _dump(induced_fn),  # 비어 있어야 정상
    }


def _build_care_guide_diagnosis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """[기능 (b)] 케어 가이드 커버리지·종 연결 정확도 — PART C 산출물.

    - coverage: 진단 성공 케이스 중 care_guide가 첨부된 비율(평가셋 9종 전체 커버 기대).
    - link_correct/link_wrong: 첨부분 중 gt 기대 종 키와 일치/오연결(엉뚱한 케어 카드).
    - by_species: gt 기대 종별 첨부·오연결 분해.
    - mislink_samples: 오연결 케이스 전수(analyze 종 오식별 → 엉뚱 케어).
    """
    scored = [c for c in per_case if c.get("pred_is_healthy") is not None]
    attached = [c for c in scored if c.get("care_attached")]
    link_correct = [c for c in attached if c.get("care_link_correct") is True]
    link_wrong = [c for c in attached if c.get("care_link_correct") is False]

    by_species: dict[str, dict[str, int]] = {}
    for c in scored:
        exp = str(c.get("expected_care_key") or "(none)")
        b = by_species.setdefault(exp, {"images": 0, "attached": 0, "link_correct": 0, "link_wrong": 0})
        b["images"] += 1
        if c.get("care_attached"):
            b["attached"] += 1
            if c.get("care_link_correct") is True:
                b["link_correct"] += 1
            elif c.get("care_link_correct") is False:
                b["link_wrong"] += 1

    return {
        "scored_images": len(scored),
        "care_attached": len(attached),
        "coverage": _safe_div(len(attached), len(scored)),
        "link_correct": len(link_correct),
        "link_wrong": len(link_wrong),
        "link_accuracy": _safe_div(len(link_correct), len(link_correct) + len(link_wrong)),
        "by_species": by_species,
        "mislink_samples": [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "pred_plant_scientific": c.get("pred_plant_scientific"),
                "expected_care_key": c.get("expected_care_key"),
                "care_species_key": c.get("care_species_key"),
            }
            for c in link_wrong
        ],
        "uncovered_samples": [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "pred_plant_scientific": c.get("pred_plant_scientific"),
                "expected_care_key": c.get("expected_care_key"),
            }
            for c in scored
            if not c.get("care_attached")
        ],
    }


async def _run_one_case(graph, image_bytes: bytes) -> tuple[dict[str, Any], float]:
    """그래프 1회 구동. (최종 state, latency_sec) 반환."""
    start = time.perf_counter()
    out = await graph.ainvoke(_initial_state(image_bytes))
    latency = time.perf_counter() - start
    return out, latency


def _safe_div(num: float, den: float) -> float | None:
    return (num / den) if den else None


# ───────────────────────────── [L0-C] 가드 전/후 confusion ─────────────────────
# status guard는 비건강→"건강" 단방향 교정(graph.apply_status_guard). pre_status는
# generate 원본 status로 항상 기록되고, 가드 미발동이면 pre==post. 같은 confusion을
# pre/post 두 벌로 내고 그 FP 차이(guard_caught_fp)로 "가드가 잡은 FP"를 한눈에 본다.

def _post_guard_is_healthy(c: dict[str, Any]) -> bool:
    """최종(가드 후) status 기준 건강 여부 — 기존 is_healthy와 동일 축."""
    return bool(c["pred_is_healthy"])


def _pre_guard_is_healthy(c: dict[str, Any]) -> bool:
    """가드 전(generate 원본) status 기준 건강 여부. pre_status 없으면 pre=post."""
    pre = c.get("guard_pre_status")
    if pre is None:
        return bool(c["pred_is_healthy"])
    return _status_to_is_healthy(pre)


def _confusion(
    scored: list[dict[str, Any]],
    pred_healthy: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    """건강여부 confusion (positive=비건강). pred_healthy(case)->건강 bool."""
    tp = sum(1 for c in scored if not c["gt_is_healthy"] and not pred_healthy(c))
    tn = sum(1 for c in scored if c["gt_is_healthy"] and pred_healthy(c))
    fp = sum(1 for c in scored if c["gt_is_healthy"] and not pred_healthy(c))
    fn = sum(1 for c in scored if not c["gt_is_healthy"] and pred_healthy(c))
    return {
        "positive_class": "unhealthy",
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": _safe_div(tp, tp + fp),
        "recall": _safe_div(tp, tp + fn),
        "accuracy": _safe_div(tp + tn, len(scored)),
    }


# ───────────────────────────── [ACC-R4] 5-status 혼동표 ─────────────────────────
# true_status(정답 5-status) × pred_status(모델 status) 혼동표. ambiguous는 행으로
# 보여주되 정확도 계산에서 제외(excluded_rows). 표본 0인 status는 unmeasured_rows로
# 명시(현 39건 기준 과습·영양 부족은 미측정). pred가 5-status 밖이거나 None(skip/error)
# 인 케이스는 어느 열에도 들어가지 않아 행 합이 sample_size보다 작을 수 있다.

def _is_ambiguous(case: dict[str, Any]) -> bool:
    """gt true_status가 ambiguous인가 (정확도 분모에서 완전 제외 대상)."""
    return case.get("gt_true_status") == STATUS_AMBIGUOUS


def build_status_confusion_matrix(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """5-status 혼동표 산출 (read-only 집계, 진단 로직 무관).

    rows = STATUS_VOCAB + [ambiguous] (true), cols = STATUS_VOCAB (predicted).
    counts[i][j] = true=rows[i] & pred=cols[j] 인 케이스 수.
    """
    rows = list(STATUS_VOCAB) + [STATUS_AMBIGUOUS]
    cols = list(STATUS_VOCAB)
    row_idx = {r: i for i, r in enumerate(rows)}
    col_idx = {c: j for j, c in enumerate(cols)}
    counts = [[0 for _ in cols] for _ in rows]
    sample_sizes = {r: 0 for r in rows}

    for c in per_case:
        gt = c.get("gt_true_status")
        if gt not in row_idx:  # gt 미기입/미지원 status → 표 제외
            continue
        sample_sizes[gt] += 1
        pred = c.get("pred_status")
        if pred in col_idx:  # pred None(skip/error)·off-enum은 어느 열에도 안 들어감
            counts[row_idx[gt]][col_idx[pred]] += 1

    unmeasured_rows = [r for r in STATUS_VOCAB if sample_sizes[r] == 0]
    return {
        "rows": rows,
        "cols": cols,
        "counts": counts,
        "unmeasured_rows": unmeasured_rows,  # 표본 0 (예: 과습·영양 부족)
        "excluded_rows": [STATUS_AMBIGUOUS],  # 정확도 분모 제외
        "sample_sizes": sample_sizes,
    }


async def _measure_labels(
    graph, db_path: str, labels: list[dict[str, Any]], tag: str
) -> list[dict[str, Any]]:
    """평가셋 1개를 그래프로 측정해 per_case 리스트 반환 (집계/출력은 분리).

    tag는 콘솔 로그 접두(main/aux 구분). 진단 로직 무변경.
    """
    total = len(labels)
    per_case: list[dict[str, Any]] = []

    for i, row in enumerate(labels, start=1):
        image_id = row.get("image_id", "")
        gt = row.get("ground_truth", {}) or {}
        gt_plant = gt.get("plant_name_korean")
        gt_is_healthy = bool(gt.get("is_healthy"))
        gt_true_status = gt.get("true_status")  # [ACC-R4] 5-status 혼동표용
        rel = row.get("image_path", "")
        img_path = _ROOT / rel

        if not img_path.is_file():
            print(f"[{tag} {i}/{total}] {image_id}: [skip] 이미지 없음 {rel}")
            per_case.append(
                {
                    "image_id": image_id,
                    "gt_plant": gt_plant,
                    "pred_plant_scientific": None,
                    "pred_plant_ko": None,
                    "plant_match": None,
                    "gt_is_healthy": gt_is_healthy,
                    "gt_true_status": gt_true_status,
                    "pred_status": None,
                    "pred_is_healthy": None,
                    "healthy_match": None,
                    "latency_sec": None,
                    "json_ok": False,
                    "observed_symptoms": [],
                    "top_3_rag": [],
                    "species_normal_species": "",
                    "species_normal_card_count": 0,
                    "error": "image_not_found",
                }
            )
            continue

        image_bytes = img_path.read_bytes()
        try:
            out, latency = await _run_one_case(graph, image_bytes)
        except Exception as e:  # noqa: BLE001 — baseline은 케이스 실패를 기록만
            print(f"[{tag} {i}/{total}] {image_id}: [error] {type(e).__name__}: {e}")
            per_case.append(
                {
                    "image_id": image_id,
                    "gt_plant": gt_plant,
                    "pred_plant_scientific": None,
                    "pred_plant_ko": None,
                    "plant_match": None,
                    "gt_is_healthy": gt_is_healthy,
                    "gt_true_status": gt_true_status,
                    "pred_status": None,
                    "pred_is_healthy": None,
                    "healthy_match": None,
                    "latency_sec": None,
                    "json_ok": False,
                    "observed_symptoms": [],
                    "top_3_rag": [],
                    "species_normal_species": "",
                    "species_normal_card_count": 0,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
            continue

        pred_sci = out.get("plant_name")
        pred_ko = _scientific_to_korean(pred_sci)
        sr = out.get("structured_result")
        json_ok = _struct_json_ok(sr)
        pred_status = sr.get("status") if isinstance(sr, dict) else None
        pred_cause = sr.get("cause") if isinstance(sr, dict) else None
        pred_is_healthy = _status_to_is_healthy(pred_status)

        # 식물명: 변환 불가(unmappable) / 일치(correct) / 불일치(wrong)
        if pred_ko is None:
            plant_match: bool | None = None  # unmappable
        else:
            plant_match = pred_ko == gt_plant

        healthy_match = pred_is_healthy == gt_is_healthy

        # [기능 (b)] 케어 가이드 첨부·종 연결 정확도 (진단 무관, 측정만)
        care = out.get("care_guide")
        care_species_key = (care or {}).get("species_key") if isinstance(care, dict) else None
        care_attached = bool(care_species_key)
        # gt 기반 기대 종 키 (평가셋 9종 전체 커버 → 정상이면 항상 매핑)
        expected_care_key = normalize_species_key(gt_plant, pred_sci)
        if not care_attached:
            care_link_correct: bool | None = None  # 미첨부 → 연결 정확도 분모 제외
        else:
            care_link_correct = care_species_key == expected_care_key

        per_case.append(
            {
                "image_id": image_id,
                "gt_plant": gt_plant,
                "pred_plant_scientific": pred_sci,
                "pred_plant_ko": pred_ko,
                "plant_match": plant_match,
                "gt_is_healthy": gt_is_healthy,
                "gt_true_status": gt_true_status,  # [ACC-R4] 5-status 정답
                "pred_status": pred_status,
                "pred_is_healthy": pred_is_healthy,
                "healthy_match": healthy_match,
                "latency_sec": round(latency, 3),
                "json_ok": json_ok,
                # [기능 (b)] 케어 가이드 측정 (read-only)
                "care_attached": care_attached,
                "care_species_key": care_species_key,
                "expected_care_key": expected_care_key,
                "care_link_correct": care_link_correct,
                # [B-4a] FP 진단 측정 신규 키 (read-only)
                "observed_symptoms": list(out.get("observed_symptoms") or []),
                "top_3_rag": _build_top_3_rag(out, db_path),
                # [B-prime] 종 메타 정상화 카드 주입 여부 (i/ii/iii 진단용)
                "species_normal_species": out.get("species_normal_species") or "",
                "species_normal_card_count": len(
                    out.get("species_normal_docs") or []
                ),
                # [status guard] over-escalate 교정 발동 내역
                "guard_fired": bool((out.get("status_guard") or {}).get("fired")),
                "guard_reason": (out.get("status_guard") or {}).get("reason"),
                "guard_pre_status": (out.get("status_guard") or {}).get("pre_status"),
                # [status guard 정합] cause 재생성 전(generate 원본)/후(최종) 대조용
                "pred_cause": pred_cause,
                "guard_pre_cause": (out.get("status_guard") or {}).get("pre_cause"),
                "guard_cause_regenerated": bool(
                    (out.get("status_guard") or {}).get("cause_regenerated")
                ),
            }
        )
        print(
            f"[{tag} {i}/{total}] {image_id}: plant={pred_sci!r}->{pred_ko!r} "
            f"(gt={gt_plant!r}) status={pred_status!r} "
            f"gt_healthy={gt_is_healthy} json_ok={json_ok} {latency:.1f}s"
        )

    return per_case


def _probe_rag_collections(db_path: str, names: tuple[str, ...]) -> None:
    """[ACC-fix2 재발방지#4] 측정 전 RAG 자가점검.

    Gemini(과금) 호출 전에 각 컬렉션을 1쿼리 프로브하고, count==0/로드 에러/0건
    반환이면 즉시 중단한다. chromadb 1.x HNSW 일시 읽기 실패(R11 "Nothing found on
    disk") 상태로 측정해 과금만 태우는 사고를 차단한다.
    """
    import chromadb

    client = chromadb.PersistentClient(path=db_path)
    for name in names:
        try:
            coll = client.get_collection(name)
            cnt = coll.count()
        except Exception as e:
            print(
                f"[run_eval] RAG 자가점검 실패 — 컬렉션 로드 불가 ({name}): {e}",
                file=sys.stderr,
            )
            sys.exit(2)
        if cnt == 0:
            print(
                f"[run_eval] RAG 자가점검 실패 — {name} count=0 (빈 컬렉션). 측정 중단.",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            got = coll.get(limit=1, include=["embeddings"])
            embs = got.get("embeddings")
            dim = len(embs[0])
            res = coll.query(
                query_embeddings=[[0.0] * dim], n_results=1, include=["documents"]
            )
            docs = (res.get("documents") or [[]])[0]
        except Exception as e:
            print(
                f"[run_eval] RAG 자가점검 실패 — {name} 쿼리 에러 (HNSW 세그먼트?): {e}",
                file=sys.stderr,
            )
            sys.exit(2)
        if len(docs) == 0:
            print(
                f"[run_eval] RAG 자가점검 실패 — {name} 쿼리 0건. HNSW 불완전. 측정 중단.",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"[run_eval] RAG 자가점검 OK: {name} count={cnt}, 쿼리 {len(docs)} docs")


async def async_main(run_aux: bool = False) -> None:
    load_dotenv(_ROOT / ".env")
    labels = _load_labels(LABELS_PATH)
    total = len(labels)
    print(f"[run_eval] 평가셋 {total}장 로드: {LABELS_PATH}")

    # [ACC-fix2 재발방지#4] Gemini 과금 전 RAG 자가점검 (죽은 채 측정 차단)
    _probe_rag_collections(str(_vector_db_path()), ("b_dataset_rag", "a_dataset_rag"))

    vision_provider = GeminiProvider(system_prompt=prompts.ANALYZE_SYSTEM)
    graph = build_diagnosis_graph(vision_provider)
    db_path = str(_vector_db_path())  # [B-4a] top_3_rag 재검색용

    per_case = await _measure_labels(graph, db_path, labels, "main")
    result = _build_result(total, per_case)

    if run_aux:
        # [ACC-R4] PlantVillage 50장 보조 sanity check (게이트 제외, 메인과 분리).
        aux_labels = _load_labels(PLANTVILLAGE_LABELS_PATH)
        aux_total = len(aux_labels)
        print(
            f"\n[run_eval --aux] 보조 평가셋 {aux_total}장 로드: "
            f"{PLANTVILLAGE_LABELS_PATH}"
        )
        aux_per_case = await _measure_labels(graph, db_path, aux_labels, "aux")
        result["aux_plantvillage_results"] = _build_result(aux_total, aux_per_case)

    _write_result(result)
    _report_console(result)
    if run_aux:
        _report_aux_console(result["aux_plantvillage_results"])
    print("\n저장:", OUTPUT_PATH)


def _build_result(total: int, per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """per_case → 집계 result dict (파일 쓰기·콘솔 출력과 분리, aux에서도 재사용)."""
    # --- 식물 이름 ---
    correct = sum(1 for c in per_case if c["plant_match"] is True)
    wrong = sum(1 for c in per_case if c["plant_match"] is False)
    unmappable = sum(1 for c in per_case if c["plant_match"] is None)
    plant_acc = _safe_div(correct, correct + wrong)  # 매칭가능한 것 중 비율

    # --- 건강 여부 (unhealthy = positive) ---
    # [L0-C] 가드 전(generate 원본)/후(최종) confusion을 나란히. post_guard는 기존
    # is_healthy와 동일(호환 유지), pre_guard는 guard_pre_status 기준.
    # [ACC-R4] §137 — true_status=ambiguous는 정확도 분모에서 완전 제외(이진·5-status 공통).
    scored = [
        c
        for c in per_case
        if c["pred_is_healthy"] is not None and not _is_ambiguous(c)
    ]
    post_guard = _confusion(scored, _post_guard_is_healthy)
    pre_guard = _confusion(scored, _pre_guard_is_healthy)
    guard_caught_fp = pre_guard["fp"] - post_guard["fp"]
    # 콘솔/기존 키 호환용 (post_guard 기준)
    tp, tn, fp, fn = post_guard["tp"], post_guard["tn"], post_guard["fp"], post_guard["fn"]
    precision, recall, healthy_acc = (
        post_guard["precision"],
        post_guard["recall"],
        post_guard["accuracy"],
    )

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
        "is_healthy": post_guard,  # [L0-C] 기존 키 유지(= post_guard, 호환)
        "is_healthy_post_guard": post_guard,  # 최종 status 기준
        "is_healthy_pre_guard": pre_guard,  # generate 원본 status 기준
        # 가드가 건강 복원해 잡은 FP 수 (pre.fp - post.fp). 0이면 가드 무발동/무효.
        "guard_caught_fp": guard_caught_fp,
        # [ACC-R4] 5-status 혼동표 (ambiguous 행 제외표시, 표본 0 행 미측정표시).
        "status_confusion_matrix": build_status_confusion_matrix(per_case),
        "status_distribution": status_dist,
        "status_by_is_healthy": status_by_health,
        "json_parse_success_rate": json_rate,
        "json_parse_failed_ids": json_fail_ids,
        "latency_sec": lat,
        "fp_analysis": _build_fp_analysis(per_case),  # [B-4a] FP 17건 본질 진단
        "tp_analysis": _build_tp_analysis(per_case),  # [B-4c] recall 안전장치
        "species_normal_diagnosis": _build_species_normal_diagnosis(
            per_case
        ),  # [B-prime] (a) 정상화 카드 효과 (i/ii/iii)
        "status_guard_diagnosis": _build_status_guard_diagnosis(
            per_case
        ),  # [status guard] over-escalate 교정 발동·FN 점검
        "care_guide_diagnosis": _build_care_guide_diagnosis(
            per_case
        ),  # [기능 (b)] 케어 가이드 커버리지·종 연결 정확도
        "per_case": per_case,
    }
    return result


def _write_result(result: dict[str, Any]) -> None:
    """result dict를 OUTPUT_PATH(BOM 없는 UTF-8)로 기록."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _pct(v: float | None) -> str:
    return f"{v:.1%}" if v is not None else "N/A"


def _print_status_confusion_matrix(scm: dict[str, Any]) -> None:
    """[ACC-R4] 5-status 혼동표 콘솔 출력. 미측정 행·제외 행 명시."""
    rows = scm["rows"]
    cols = scm["cols"]
    counts = scm["counts"]
    sizes = scm["sample_sizes"]
    unmeasured = set(scm["unmeasured_rows"])
    excluded = set(scm["excluded_rows"])

    print("\n[5-status 혼동표] (행=정답 true_status, 열=예측 pred_status)")
    print(f"  표본 수: {sizes}")
    print(f"  미측정 행(표본 0): {scm['unmeasured_rows'] or '없음'}")
    print(f"  제외 행(정확도 분모 제외): {scm['excluded_rows']}")
    header = "  " + " " * 12 + "".join(f"{c:>10}" for c in cols)
    print(header)
    for i, r in enumerate(rows):
        if r in excluded:
            tag = " (제외)"
        elif r in unmeasured:
            tag = " (미측정)"
        else:
            tag = ""
        cells = "".join(f"{counts[i][j]:>10}" for j in range(len(cols)))
        print(f"  {r:<12}{cells}{tag}")


def _report_console(result: dict[str, Any]) -> None:
    """메인 측정 result 콘솔 요약 (기존 출력 + 5-status 혼동표)."""
    total = result["total"]
    pn = result["plant_name"]
    correct, wrong, unmappable = pn["correct"], pn["wrong"], pn["unmappable"]
    post_guard = result["is_healthy_post_guard"]
    pre_guard = result["is_healthy_pre_guard"]
    guard_caught_fp = result["guard_caught_fp"]
    tp, tn, fp, fn = post_guard["tp"], post_guard["tn"], post_guard["fp"], post_guard["fn"]
    status_dist = result["status_distribution"]
    status_by_health = result["status_by_is_healthy"]
    json_rate = result["json_parse_success_rate"]
    json_fail_ids = result["json_parse_failed_ids"]
    json_ok_count = total - len(json_fail_ids)
    lat = result["latency_sec"]

    print("\n" + "=" * 56)
    print("BASELINE 요약")
    print("=" * 56)
    print(f"총 케이스: {total}")
    print("\n[식물 이름]")
    print(f"  correct={correct}  wrong={wrong}  unmappable={unmappable}")
    print(f"  정확도(매칭가능 중): {_pct(pn['accuracy'])}")
    print("\n[건강 여부] (positive=unhealthy, 최종=가드 후)")
    print(f"  TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(
        f"  precision={_pct(post_guard['precision'])}  "
        f"recall={_pct(post_guard['recall'])}  accuracy={_pct(post_guard['accuracy'])}"
    )
    print(
        f"  [가드 전] FP={pre_guard['fp']} → [가드 후] FP={post_guard['fp']}  "
        f"(가드가 잡은 FP={guard_caught_fp})"
    )
    _print_status_confusion_matrix(result["status_confusion_matrix"])
    print("\n[status 분포]")
    for st, cnt in sorted(status_dist.items(), key=lambda x: -x[1]):
        h = status_by_health.get(st, {})
        print(
            f"  {st:10} {cnt:3}  (gt건강={h.get('gt_healthy',0)}, "
            f"gt비건강={h.get('gt_unhealthy',0)})"
        )
    print("\n[보조 지표]")
    print(f"  JSON 파싱 성공률: {_pct(json_rate)} ({json_ok_count}/{total})")
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
    snd = result["species_normal_diagnosis"]
    print("\n[종 메타 정상화 진단] ([B-prime] (a) 카드 효과)")
    print(f"  커버 종(gt 기준): {snd['covered_gt_species']}")
    print(
        f"  커버 종 이미지={snd['covered_gt_images']} "
        f"(healthy={snd['covered_gt_healthy_images']}), "
        f"카드 주입={snd['card_injected_images']}"
    )
    print(
        f"  커버 종 FP={snd['covered_fp']} "
        f"(카드 올라갔는데 FP={snd['covered_fp_with_card_present']} → (ii) 무시, "
        f"카드 미주입 FP={snd['covered_fp_without_card']} → (i) 오식별)"
    )
    print(f"  커버 종 FN={snd['covered_fn']} (recall 안전장치, 0이어야 정상)")
    for sp, b in sorted(snd["by_species"].items()):
        print(
            f"    {sp:8} img={b['images']} 카드={b['card_injected']} "
            f"healthy={b['healthy']} FP={b['fp']} sick={b['sick']} "
            f"TP={b['tp']} FN={b['fn']} 오매칭={b['inject_mismatch']}"
        )
    sgd = result["status_guard_diagnosis"]
    print("\n[status guard 진단] (over-escalate 교정)")
    print(
        f"  발동={sgd['fired_count']} (사유: {sgd['by_reason']})  "
        f"올바른 FP 교정={sgd['guard_correct_fp']}  "
        f"유발 FN={sgd['guard_induced_fn']} (0이어야 정상)"
    )
    for s in sgd["fired_samples"]:
        flag = "" if s["gt_is_healthy"] else "  ⚠FN!"
        print(
            f"    - {s['image_id']} gt_healthy={s['gt_is_healthy']} "
            f"{s['pre_status']}→{s['post_status']} [{s['guard_reason']}]{flag}"
        )
        print(f"      증상: {s['observed_symptoms']}")

    cgd = result["care_guide_diagnosis"]
    print("\n[케어 가이드 진단] ([기능 b])")
    print(
        f"  커버리지={_pct(cgd['coverage'])} ({cgd['care_attached']}/{cgd['scored_images']})  "
        f"연결정확도={_pct(cgd['link_accuracy'])} "
        f"(정상={cgd['link_correct']} 오연결={cgd['link_wrong']})"
    )
    for sp, b in sorted(cgd["by_species"].items()):
        print(
            f"    {sp:12} img={b['images']} 첨부={b['attached']} "
            f"정상연결={b['link_correct']} 오연결={b['link_wrong']}"
        )
    if cgd["mislink_samples"]:
        print("  [오연결 케이스 (엉뚱한 케어 카드)]")
        for s in cgd["mislink_samples"]:
            print(
                f"    - {s['image_id']} gt={s['gt_plant']!r} "
                f"기대={s['expected_care_key']!r} 첨부={s['care_species_key']!r}"
            )
    if cgd["uncovered_samples"]:
        print("  [미첨부 케이스]")
        for s in cgd["uncovered_samples"]:
            print(
                f"    - {s['image_id']} gt={s['gt_plant']!r} "
                f"pred_sci={s['pred_plant_scientific']!r} 기대={s['expected_care_key']!r}"
            )


def _report_aux_console(aux: dict[str, Any]) -> None:
    """[ACC-R4] --aux PlantVillage 보조 측정 요약 (게이트 제외, sanity 한정)."""
    post_guard = aux["is_healthy_post_guard"]
    print("\n" + "=" * 56)
    print("AUX (PlantVillage 50) 보조 sanity — 게이트 제외")
    print("=" * 56)
    print(f"총 케이스: {aux['total']}")
    print("\n[건강 여부] (positive=unhealthy)")
    print(
        f"  TP={post_guard['tp']}  TN={post_guard['tn']}  "
        f"FP={post_guard['fp']}  FN={post_guard['fn']}"
    )
    print(
        f"  precision={_pct(post_guard['precision'])}  "
        f"recall={_pct(post_guard['recall'])}  accuracy={_pct(post_guard['accuracy'])}"
    )
    _print_status_confusion_matrix(aux["status_confusion_matrix"])
    print(f"\n  JSON 파싱 성공률: {_pct(aux['json_parse_success_rate'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="main_eval 평가셋 측정 (+ --aux PlantVillage 보조 sanity)"
    )
    parser.add_argument(
        "--aux",
        action="store_true",
        help="PlantVillage 50장 보조 측정 추가 (게이트 제외, sanity 한정)",
    )
    args = parser.parse_args()
    asyncio.run(async_main(run_aux=args.aux))


if __name__ == "__main__":
    main()
