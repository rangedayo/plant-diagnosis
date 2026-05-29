"""analyze_node ([1-4]) 단위 테스트 5건.

- make_analyze_node factory + _with_retry helper 검증.
- MockVisionProvider(성공/영구오류 단일 응답) + AsyncMock side_effect(분기형) 혼용.
- asyncio.sleep을 patch해 실제 대기 없이 재시도 흐름만 검증.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.analyze import _with_retry, make_analyze_node
from app.vision.base import AnalyzeResult
from app.vision.errors import (
    RetryHint,
    VisionPermanentError,
    VisionRetryableError,
)
from app.vision.mock import MockVisionProvider

SLEEP_PATCH_TARGET = "app.nodes.analyze.asyncio.sleep"


def _sample_result() -> AnalyzeResult:
    return AnalyzeResult(
        plant_name="Dracaena fragrans",
        plant_name_korean="드라세나 프라그란스 (행운목)",
        plant_confidence="high",
        alt_candidates=["Dracaena reflexa"],
        visual_description="평행한 잎맥의 긴 피침형 잎.",
        observed_symptoms=["잎끝 갈변"],
    )


def _state() -> dict[str, Any]:
    return {"image_bytes": b"\xff\xd8\xff\xe0JFIF"}


def _retryable(backoff: float = 2.0) -> VisionRetryableError:
    return VisionRetryableError(
        "일시적 오류",
        RetryHint(kind="server_error", backoff_seconds=backoff),
        status_code=503,
    )


class _FakeProvider:
    """analyze가 AsyncMock인 분기형 provider — side_effect로 시도별 결과를 정한다."""

    def __init__(self, *side_effect: Any) -> None:
        self.analyze = AsyncMock(side_effect=list(side_effect))


@pytest.mark.asyncio
async def test_analyze_node_returns_6_fields_on_success() -> None:
    expected = _sample_result()
    provider = MockVisionProvider(result=expected)
    analyze_node = make_analyze_node(provider)

    out = await analyze_node(_state())

    assert set(out.keys()) == {
        "plant_name",
        "plant_name_korean",
        "plant_confidence",
        "alt_candidates",
        "visual_description",
        "observed_symptoms",
    }
    assert out["plant_name"] == expected.plant_name
    assert out["plant_name_korean"] == expected.plant_name_korean
    assert out["plant_confidence"] == expected.plant_confidence
    assert out["alt_candidates"] == expected.alt_candidates
    assert out["visual_description"] == expected.visual_description
    assert out["observed_symptoms"] == expected.observed_symptoms


@pytest.mark.asyncio
async def test_analyze_node_propagates_permanent_error() -> None:
    provider = MockVisionProvider(raise_error=VisionPermanentError("400", status_code=400))
    analyze_node = make_analyze_node(provider)

    with patch(SLEEP_PATCH_TARGET, new_callable=AsyncMock) as sleep_mock:
        with pytest.raises(VisionPermanentError):
            await analyze_node(_state())

    assert sleep_mock.await_count == 0  # 재시도 없음


@pytest.mark.asyncio
async def test_analyze_node_retries_on_retryable_error_then_succeeds() -> None:
    expected = _sample_result()
    provider = _FakeProvider(_retryable(backoff=2.0), expected)
    analyze_node = make_analyze_node(provider)

    with patch(SLEEP_PATCH_TARGET, new_callable=AsyncMock) as sleep_mock:
        out = await analyze_node(_state())

    assert out["plant_name"] == expected.plant_name
    assert provider.analyze.await_count == 2
    assert sleep_mock.await_count == 1
    sleep_mock.assert_awaited_once_with(2.0)


@pytest.mark.asyncio
async def test_analyze_node_raises_after_max_attempts() -> None:
    provider = _FakeProvider(_retryable(), _retryable())
    analyze_node = make_analyze_node(provider)

    with patch(SLEEP_PATCH_TARGET, new_callable=AsyncMock) as sleep_mock:
        with pytest.raises(VisionRetryableError):
            await analyze_node(_state())

    assert provider.analyze.await_count == 2  # 최초 + 재시도 1회
    assert sleep_mock.await_count == 1  # max_attempts - 1


@pytest.mark.asyncio
async def test_with_retry_uses_backoff_seconds_from_retry_hint() -> None:
    expected = _sample_result()

    for backoff in (60.0, 2.0):
        err = VisionRetryableError(
            "retry",
            RetryHint(
                kind="rate_limit" if backoff >= 60 else "server_error",
                backoff_seconds=backoff,
            ),
        )
        fn = AsyncMock(side_effect=[err, expected])
        with patch(SLEEP_PATCH_TARGET, new_callable=AsyncMock) as sleep_mock:
            out = await _with_retry(fn, "ignored-arg")

        assert out is expected
        sleep_mock.assert_awaited_once_with(backoff)
