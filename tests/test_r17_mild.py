"""[R17] generate 경미 출력 — 매핑 단위 테스트 (모델 호출 0).

- run_eval._status_to_is_healthy: 경미 → True (GT 컨벤션 정합, 이진 건강 쪽).
- model_utils.normalize_structured_result: status="경미"를 enum 밖으로 강등시키지 않고 보존.
- ALLOWED_STRUCT_STATUS에 경미 포함, 미지원 status는 여전히 "병해 의심"으로 강등(회귀 가드).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SCRIPTS))

from run_eval import _status_to_is_healthy  # noqa: E402
from app.model_utils import ALLOWED_STRUCT_STATUS, normalize_structured_result  # noqa: E402


# ───────────────────────── _status_to_is_healthy ─────────────────────────

def test_is_healthy_geon():
    assert _status_to_is_healthy("건강") is True


def test_is_healthy_mild_is_true():
    # 경미는 GT 컨벤션(is_healthy=True)과 정합 → 이진에서 건강 쪽.
    assert _status_to_is_healthy("경미") is True


def test_is_healthy_unhealthy_statuses_false():
    for s in ("과습", "건조", "병해 의심", "영양 부족"):
        assert _status_to_is_healthy(s) is False, s


def test_is_healthy_none_false():
    assert _status_to_is_healthy(None) is False


# ───────────────────────── normalize_structured_result ─────────────────────

def _payload(status: str) -> dict:
    return {
        "summary": "요약",
        "current_state": "상태",
        "cause": "원인",
        "action_plan": ["조치1", "조치2"],
        "status": status,
    }


def test_allowed_struct_status_contains_mild():
    assert "경미" in ALLOWED_STRUCT_STATUS


def test_normalize_preserves_mild():
    # 경미가 enum에 있으므로 "병해 의심"으로 강등되지 않고 살아남아야 한다.
    out = normalize_structured_result(_payload("경미"))
    assert out["status"] == "경미"


def test_normalize_preserves_healthy():
    out = normalize_structured_result(_payload("건강"))
    assert out["status"] == "건강"


def test_normalize_downgrades_unknown_to_disease_suspect():
    # 회귀 가드: enum 밖 status는 여전히 안전 측 "병해 의심"으로 강등.
    out = normalize_structured_result(_payload("외계상태"))
    assert out["status"] == "병해 의심"
