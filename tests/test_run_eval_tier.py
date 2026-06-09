"""[R16] run_eval 3단 tier 채점 단위 테스트 (모델 호출 0, 합성 per_case).

_status_to_tier 매핑 + build_tier_diagnosis 비대칭 게이트 지표를 검증한다.
회귀 안전: 기존 이진/5-status 지표는 건드리지 않으므로 여기선 tier만 본다.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SCRIPTS))

from run_eval import _status_to_tier, build_tier_diagnosis  # noqa: E402


# ───────────────────────────── _status_to_tier ─────────────────────────────

def test_status_to_tier_healthy():
    assert _status_to_tier("건강") == "건강"


def test_status_to_tier_mild():
    # 현 모델은 미출력하지만 미래 대비 통과해야 한다.
    assert _status_to_tier("경미") == "경미"


def test_status_to_tier_unhealthy_five_status():
    for s in ("과습", "건조", "병해 의심", "영양 부족"):
        assert _status_to_tier(s) == "비건강", s


def test_status_to_tier_unknown_cause_is_unhealthy():
    assert _status_to_tier("비건강-원인미상") == "비건강"


def test_status_to_tier_none_is_none():
    # skip/error(pred 없음)는 tier 채점에서 제외 → None.
    assert _status_to_tier(None) is None


def test_status_to_tier_unsupported_maps_to_unhealthy_safe_side():
    # 미지원 status는 안전 측(과대)=비건강으로 매핑(로그는 stderr).
    assert _status_to_tier("외계상태") == "비건강"


# ───────────────────────────── build_tier_diagnosis ─────────────────────────

def _case(iid: str, gt_tier, pred_tier) -> dict:
    return {"image_id": iid, "gt_tier": gt_tier, "pred_tier": pred_tier}


def _corner_per_case() -> list[dict]:
    """각 코너 1건씩 + skip 2건 (scored 9, skipped 2)."""
    return [
        _case("exact_h", "건강", "건강"),        # 대각
        _case("exact_m", "경미", "경미"),        # 대각
        _case("exact_u", "비건강", "비건강"),    # 대각
        _case("cardinal", "비건강", "건강"),     # cardinal_miss
        _case("soft", "비건강", "경미"),         # soft_miss
        _case("minor", "경미", "건강"),          # minor_undercall
        _case("over_mild", "건강", "경미"),      # over_call to_mild
        _case("over_unh_h", "건강", "비건강"),   # over_call to_unhealthy (건강→비건강)
        _case("over_unh_m", "경미", "비건강"),   # over_call to_unhealthy (경미→비건강)
        _case("skip_pred", "비건강", None),      # pred None → skipped
        _case("skip_gt", None, "비건강"),        # gt 미지원 → skipped
    ]


def test_tier_diagnosis_scored_and_skipped_counts():
    td = build_tier_diagnosis(_corner_per_case())
    assert td["scored"] == 9
    assert td["skipped"] == 2
    assert set(td["skipped_ids"]) == {"skip_pred", "skip_gt"}


def test_tier_diagnosis_confusion_matrix():
    td = build_tier_diagnosis(_corner_per_case())
    # 행=gt [건강,경미,비건강], 열=pred [건강,경미,비건강]. 각 코너 1건씩 → 전부 1.
    assert td["tiers"] == ["건강", "경미", "비건강"]
    assert td["counts"] == [[1, 1, 1], [1, 1, 1], [1, 1, 1]]


def test_tier_diagnosis_asymmetric_metrics():
    td = build_tier_diagnosis(_corner_per_case())
    assert td["exact_match"] == 3
    assert td["exact_match_rate"] == 3 / 9
    assert td["cardinal_miss"] == 1       # gt비건강 & pred건강
    assert td["soft_miss"] == 1           # gt비건강 & pred경미
    assert td["minor_undercall"] == 1     # gt경미 & pred건강
    assert td["over_call"]["to_mild"] == 1        # 건강→경미
    assert td["over_call"]["to_unhealthy"] == 2   # 건강→비건강 + 경미→비건강
    assert td["over_call"]["total"] == 3


def test_tier_diagnosis_current_model_no_mild_output():
    """현 모델은 경미를 못 내므로 pred=경미 열은 전부 0, soft_miss=0 (R16 출발선)."""
    per_case = [
        _case("a", "건강", "건강"),
        _case("b", "비건강", "비건강"),
        _case("c", "비건강", "건강"),    # cardinal_miss (모델이 비건강을 건강이라 함)
        _case("d", "경미", "건강"),      # minor_undercall (경미 GT를 건강이라 함)
    ]
    td = build_tier_diagnosis(per_case)
    pred_mild_col = sum(row[1] for row in td["counts"])  # 열 index 1 = 경미
    assert pred_mild_col == 0
    assert td["soft_miss"] == 0
    assert td["cardinal_miss"] == 1
    assert td["minor_undercall"] == 1


def test_tier_diagnosis_empty_is_safe():
    td = build_tier_diagnosis([])
    assert td["scored"] == 0
    assert td["exact_match"] == 0
    assert td["exact_match_rate"] is None  # _safe_div(0, 0)
    assert td["cardinal_miss"] == 0
