"""AnalyzeResult / VisionInput 스키마 단위 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.vision.base import AnalyzeResult, VisionInput


def test_analyze_result_full_instance() -> None:
    # Arrange / Act
    result = AnalyzeResult(
        plant_name="Dracaena reflexa",
        plant_name_korean="드라세나 리플렉사",
        plant_confidence="high",
        alt_candidates=["Dracaena fragrans"],
        visual_description="가늘고 긴 녹색 잎이 방사형으로 자란다.",
        observed_symptoms=["잎끝 갈변"],
    )

    # Assert
    assert result.plant_name == "Dracaena reflexa"
    assert result.plant_name_korean == "드라세나 리플렉사"
    assert result.plant_confidence == "high"
    assert result.alt_candidates == ["Dracaena fragrans"]
    assert result.visual_description.startswith("가늘고")
    assert result.observed_symptoms == ["잎끝 갈변"]


def test_analyze_result_list_fields_default_empty() -> None:
    # Arrange / Act
    result = AnalyzeResult(
        plant_name="Unknown",
        plant_name_korean="알 수 없음",
        plant_confidence="low",
        visual_description="설명",
    )

    # Assert
    assert result.alt_candidates == []
    assert result.observed_symptoms == []


def test_analyze_result_invalid_confidence_raises() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        AnalyzeResult(
            plant_name="Unknown",
            plant_name_korean="알 수 없음",
            plant_confidence="medium",  # Literal 외 값
            visual_description="설명",
        )


def test_vision_input_default_mime_type() -> None:
    # Arrange / Act
    vi = VisionInput(image_bytes=b"\xff\xd8\xff")

    # Assert
    assert vi.mime_type == "image/jpeg"


def test_vision_input_invalid_mime_type_raises() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        VisionInput(image_bytes=b"\x89PNG", mime_type="image/gif")
