"""GeminiProvider 단위 테스트(5건) + 통합 테스트(1건).

단위 테스트는 genai.Client를 통째 패치하므로 실제 GEMINI_API_KEY 없이도 동작한다.
통합 테스트는 GEMINI_API_KEY가 있을 때만 실행되며, Pydantic default 값 거부 여부를 실증한다.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.vision.base import AnalyzeResult, VisionInput
from app.vision.errors import VisionPermanentError, VisionRetryableError

try:
    from google.genai import errors as genai_errors
except ImportError:  # pragma: no cover - google-genai 미설치 환경 방어
    genai_errors = None  # type: ignore[assignment]

FAKE_KEY = "test-key"


def _sample_input() -> VisionInput:
    return VisionInput(image_bytes=b"\xff\xd8\xff", mime_type="image/jpeg")


def _sample_result() -> AnalyzeResult:
    return AnalyzeResult(
        plant_name="Dracaena reflexa",
        plant_name_korean="드라세나 리플렉사",
        plant_confidence="high",
        alt_candidates=["Dracaena fragrans"],
        visual_description="가늘고 긴 녹색 잎.",
        observed_symptoms=["잎끝 갈변"],
    )


def _client_error(code: int):
    return genai_errors.ClientError(
        code, {"error": {"code": code, "message": "err", "status": "S"}}
    )


def _server_error(code: int):
    return genai_errors.ServerError(
        code, {"error": {"code": code, "message": "err", "status": "S"}}
    )


def _make_provider_with_mocked_client(generate_content: AsyncMock):
    """genai.Client를 패치한 상태로 GeminiProvider 생성. generate_content만 교체해 반환."""
    from app.vision.gemini import GeminiProvider

    provider = GeminiProvider(system_prompt="placeholder", api_key=FAKE_KEY)
    # __init__에서 만든 client는 patch된 MagicMock이므로 generate_content만 교체
    provider._client.aio.models.generate_content = generate_content
    return provider


@pytest.mark.asyncio
async def test_analyze_returns_parsed_result_on_success() -> None:
    expected = _sample_result()
    response = MagicMock()
    response.parsed = expected
    gen = AsyncMock(return_value=response)

    with patch("app.vision.gemini.genai.Client", return_value=MagicMock()):
        provider = _make_provider_with_mocked_client(gen)
        out = await provider.analyze(_sample_input())

    assert out is expected
    gen.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_raises_retryable_on_429() -> None:
    gen = AsyncMock(side_effect=_client_error(429))

    with patch("app.vision.gemini.genai.Client", return_value=MagicMock()):
        provider = _make_provider_with_mocked_client(gen)
        with pytest.raises(VisionRetryableError) as ei:
            await provider.analyze(_sample_input())

    assert ei.value.retry_hint.kind == "rate_limit"
    assert ei.value.retry_hint.backoff_seconds >= 60
    assert ei.value.status_code == 429


@pytest.mark.asyncio
async def test_analyze_raises_retryable_on_5xx() -> None:
    gen = AsyncMock(side_effect=_server_error(503))

    with patch("app.vision.gemini.genai.Client", return_value=MagicMock()):
        provider = _make_provider_with_mocked_client(gen)
        with pytest.raises(VisionRetryableError) as ei:
            await provider.analyze(_sample_input())

    assert ei.value.retry_hint.kind == "server_error"
    assert ei.value.retry_hint.backoff_seconds == 2.0
    assert ei.value.status_code == 503


@pytest.mark.asyncio
async def test_analyze_raises_permanent_on_4xx_non_429() -> None:
    gen = AsyncMock(side_effect=_client_error(400))

    with patch("app.vision.gemini.genai.Client", return_value=MagicMock()):
        provider = _make_provider_with_mocked_client(gen)
        with pytest.raises(VisionPermanentError) as ei:
            await provider.analyze(_sample_input())

    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_analyze_raises_permanent_on_invalid_parsed() -> None:
    response = MagicMock()
    response.parsed = None  # 스키마 검증 실패 케이스
    gen = AsyncMock(return_value=response)

    with patch("app.vision.gemini.genai.Client", return_value=MagicMock()):
        provider = _make_provider_with_mocked_client(gen)
        with pytest.raises(VisionPermanentError):
            await provider.analyze(_sample_input())


_INTEGRATION_IMAGE = (
    Path(__file__).resolve().parents[2]
    / "test_data"
    / "main_eval"
    / "images"
    / "self_haengun_001.jpg"
)


@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GEMINI_API_KEY")),
    reason="GOOGLE_CLOUD_PROJECT(Vertex) 또는 GEMINI_API_KEY(AI Studio) 중 하나 필요",
)
@pytest.mark.asyncio
async def test_integration_real_gemini_call() -> None:
    """실제 Gemini 1회 호출 — Pydantic default(default_factory=list) 거부 여부 실증."""
    from app.vision.gemini import GeminiProvider

    assert _INTEGRATION_IMAGE.exists(), f"통합 테스트 이미지 없음: {_INTEGRATION_IMAGE}"
    image_bytes = _INTEGRATION_IMAGE.read_bytes()

    provider = GeminiProvider(
        system_prompt=(
            "이 이미지를 한국어로 분석해서 6필드 JSON으로 반환하라. "
            "plant_name(영문 학명), plant_name_korean(한국어명), "
            "plant_confidence(low/med/high), alt_candidates(학명 리스트), "
            "visual_description(시각 묘사), observed_symptoms(증상 키워드 리스트)."
        ),
    )

    t0 = time.perf_counter()
    out = await provider.analyze(
        VisionInput(image_bytes=image_bytes, mime_type="image/jpeg")
    )
    latency = time.perf_counter() - t0

    assert isinstance(out, AnalyzeResult)
    # 6필드 존재 (빈 문자열·빈 리스트 허용)
    assert isinstance(out.plant_name, str)
    assert isinstance(out.plant_name_korean, str)
    assert out.plant_confidence in ("low", "med", "high")
    assert isinstance(out.alt_candidates, list)
    assert isinstance(out.visual_description, str)
    assert isinstance(out.observed_symptoms, list)

    print(
        "\n[통합] latency=%.2fs\n  plant_name=%r\n  plant_name_korean=%r\n"
        "  plant_confidence=%r\n  alt_candidates=%r\n  visual_description=%r\n"
        "  observed_symptoms=%r"
        % (
            latency,
            out.plant_name,
            out.plant_name_korean,
            out.plant_confidence,
            out.alt_candidates,
            out.visual_description[:80],
            out.observed_symptoms,
        )
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GOOGLE_CLOUD_PROJECT"),
    reason="GOOGLE_CLOUD_PROJECT 미설정 — Vertex 모드 테스트 스킵",
)
@pytest.mark.asyncio
async def test_vertex_mode_authenticates_and_analyzes() -> None:
    """Vertex 모드로 self_haengun_001.jpg 1회 호출. ADC 자동 인증 + SDK Vertex 모드 실증."""
    from app.vision.gemini import GeminiProvider

    assert _INTEGRATION_IMAGE.exists(), f"통합 테스트 이미지 없음: {_INTEGRATION_IMAGE}"

    provider = GeminiProvider(
        system_prompt="이 이미지를 한국어로 분석해서 6필드 JSON으로 반환하라.",
    )
    assert provider._auth_mode == "vertex"

    image_bytes = _INTEGRATION_IMAGE.read_bytes()
    out = await provider.analyze(
        VisionInput(image_bytes=image_bytes, mime_type="image/jpeg")
    )

    assert isinstance(out, AnalyzeResult)
    assert out.plant_name  # 6필드 채워졌는지
    assert isinstance(out.observed_symptoms, list)
