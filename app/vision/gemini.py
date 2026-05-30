"""
GeminiProvider — google-genai 기반 VisionProvider 구현.

[1-1]의 VisionProvider Protocol / AnalyzeResult / VisionInput / 에러 계층 위에 얹는다.
graph 와이어링은 [1-5] 작업이라 여기서는 graph.py/main.py를 건드리지 않는다.

에러 매핑 (catch 순서 중요 — ClientError가 ServerError보다 먼저, 둘 다 APIError 서브클래스):
- ClientError 429       → VisionRetryableError(rate_limit, Retry-After 또는 60.0초)
- ClientError 그 외 4xx → VisionPermanentError
- ServerError 5xx       → VisionRetryableError(server_error, 2.0초)  (phase2_decisions #9)
"""

from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app import model_utils
from app.vision.base import AnalyzeResult, VisionInput
from app.vision.errors import (
    RetryHint,
    VisionPermanentError,
    VisionRetryableError,
)

DEFAULT_RATE_LIMIT_BACKOFF_SECONDS = 60.0
SERVER_ERROR_BACKOFF_SECONDS = 2.0


def _parse_retry_after_value(raw: Any) -> float | None:
    """Retry-After 값 파싱: 정수/실수 초 또는 '57s' 같은 문자열. HTTP-date는 미지원(None)."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if raw > 0 else None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("s") and s[:-1].replace(".", "", 1).isdigit():
        s = s[:-1]
    try:
        val = float(s)
    except ValueError:
        return None
    return val if val > 0 else None


def _retry_after_from_details(details: Any) -> float | None:
    """error.details(response_json) 안에서 'retryDelay'/'Retry-After' 류 값을 재귀 탐색."""
    if isinstance(details, dict):
        for key in ("retryDelay", "retry_delay", "Retry-After", "retry-after"):
            if key in details:
                val = _parse_retry_after_value(details[key])
                if val is not None:
                    return val
        for v in details.values():
            val = _retry_after_from_details(v)
            if val is not None:
                return val
    elif isinstance(details, (list, tuple)):
        for item in details:
            val = _retry_after_from_details(item)
            if val is not None:
                return val
    return None


def _extract_retry_after(error: genai_errors.ClientError) -> float | None:
    """
    429 응답에서 backoff 초를 추출한다. 실패 시 None(호출부가 기본 60.0초 사용).

    탐색 우선순위 (SDK 실증 기준):
    1. error.response.headers 의 Retry-After 헤더 (표준 위치)
    2. error.details (response_json) 안의 retryDelay 등 구조화 필드 (Google RetryInfo)
    """
    resp = getattr(error, "response", None)
    headers = getattr(resp, "headers", None)
    if headers is not None:
        try:
            raw = headers.get("Retry-After") or headers.get("retry-after")
        except (AttributeError, TypeError):
            raw = None
        val = _parse_retry_after_value(raw)
        if val is not None:
            return val
    return _retry_after_from_details(getattr(error, "details", None))


class GeminiProvider:
    """VisionProvider Protocol을 만족하는 Gemini 비전 분석 provider."""

    def __init__(
        self,
        *,
        system_prompt: str,
        api_key: str | None = None,
        project: str | None = None,
        location: str | None = None,
        model: str = "gemini-2.5-pro",
        temperature: float | None = None,
    ) -> None:
        # 인증 모드 자동 분기 (옵션 A, [1-2.5]):
        #   GOOGLE_CLOUD_PROJECT 있으면 Vertex(ADC), 없으면 GEMINI_API_KEY로 AI Studio.
        project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = location or os.getenv("GOOGLE_CLOUD_LOCATION") or "asia-northeast1"
        if project:
            self._client = genai.Client(
                vertexai=True, project=project, location=location
            )
            self._auth_mode = "vertex"
            self._project = project
            self._location = location
        else:
            resolved_key = api_key or model_utils.get_gemini_api_key()
            if not resolved_key:
                raise RuntimeError(
                    "GOOGLE_CLOUD_PROJECT(Vertex 모드) 또는 "
                    "GEMINI_API_KEY(AI Studio 모드) 중 하나 필요."
                )
            self._client = genai.Client(api_key=resolved_key)
            self._auth_mode = "ai_studio"
        self._model = model
        self._system_prompt = system_prompt
        self._temperature = temperature

    async def analyze(self, vision_input: VisionInput) -> AnalyzeResult:
        contents = [
            types.Part.from_text(text=self._system_prompt),
            types.Part.from_bytes(
                data=vision_input.image_bytes,
                mime_type=vision_input.mime_type,
            ),
        ]
        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": AnalyzeResult,
        }
        if self._temperature is not None:
            config["temperature"] = self._temperature

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except genai_errors.ClientError as e:
            if e.code == 429:
                backoff = _extract_retry_after(e) or DEFAULT_RATE_LIMIT_BACKOFF_SECONDS
                raise VisionRetryableError(
                    str(e),
                    RetryHint(kind="rate_limit", backoff_seconds=backoff),
                    status_code=e.code,
                ) from e
            raise VisionPermanentError(str(e), status_code=e.code) from e
        except genai_errors.ServerError as e:
            raise VisionRetryableError(
                str(e),
                RetryHint(
                    kind="server_error",
                    backoff_seconds=SERVER_ERROR_BACKOFF_SECONDS,
                ),
                status_code=e.code,
            ) from e

        parsed = response.parsed
        if not isinstance(parsed, AnalyzeResult):
            raise VisionPermanentError(
                f"응답 스키마 검증 실패: parsed={type(parsed).__name__}"
            )
        return parsed
