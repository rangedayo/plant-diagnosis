"""MockVisionProvider 단위 테스트."""

from __future__ import annotations

import pytest

from app.vision.base import AnalyzeResult, VisionInput
from app.vision.errors import RetryHint, VisionRetryableError
from app.vision.mock import MockVisionProvider


def _sample_input() -> VisionInput:
    return VisionInput(image_bytes=b"\xff\xd8\xff", mime_type="image/jpeg")


@pytest.mark.asyncio
async def test_mock_returns_injected_result() -> None:
    # Arrange
    injected = AnalyzeResult(
        plant_name="Ficus elastica",
        plant_name_korean="고무나무",
        plant_confidence="med",
        visual_description="두껍고 윤기 있는 잎.",
    )
    provider = MockVisionProvider(result=injected)

    # Act
    out = await provider.analyze(_sample_input())

    # Assert
    assert out is injected
    assert out.plant_name == "Ficus elastica"


@pytest.mark.asyncio
async def test_mock_raises_injected_error() -> None:
    # Arrange
    err = VisionRetryableError(
        "rate limit", RetryHint(kind="rate_limit", backoff_seconds=60.0)
    )
    provider = MockVisionProvider(raise_error=err)

    # Act / Assert
    with pytest.raises(VisionRetryableError):
        await provider.analyze(_sample_input())


@pytest.mark.asyncio
async def test_mock_default_result_when_nothing_injected() -> None:
    # Arrange
    provider = MockVisionProvider()

    # Act
    out = await provider.analyze(_sample_input())

    # Assert
    assert out.plant_name == "Unknown"
    assert out.plant_name_korean == "알 수 없음"
    assert out.plant_confidence == "low"
    assert out.alt_candidates == []
    assert out.observed_symptoms == []
