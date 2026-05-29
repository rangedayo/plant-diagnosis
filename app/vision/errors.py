"""
VisionProvider 에러 계층.

분류:
- VisionRetryableError: 일시적 오류(429 rate limit / 5xx server error). RetryHint 첨부.
- VisionPermanentError: 재시도 불가 오류(4xx 잘못된 요청, 인증 실패 등).

phase2_decisions #9: 429는 분 단위 회복(rate_limit), 5xx는 초 단위 회복(server_error)으로
backoff를 분리하기 위해 RetryHint(kind, backoff_seconds)를 retryable 에러에 첨부한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RetryHint:
    """재시도 힌트 — analyze_node helper가 이 값을 보고 sleep 시간을 결정한다."""

    kind: Literal["rate_limit", "server_error"]
    backoff_seconds: float


class VisionProviderError(Exception):
    """VisionProvider 모든 에러의 베이스."""


class VisionRetryableError(VisionProviderError):
    """재시도하면 성공할 수 있는 일시적 오류(rate limit / server error)."""

    def __init__(
        self,
        message: str,
        retry_hint: RetryHint,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_hint = retry_hint
        self.status_code = status_code


class VisionPermanentError(VisionProviderError):
    """재시도해도 동일하게 실패하는 영구 오류(잘못된 요청, 인증 실패 등)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
