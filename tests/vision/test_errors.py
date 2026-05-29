"""VisionProvider 에러 계층 단위 테스트."""

from __future__ import annotations

import dataclasses

import pytest

from app.vision.errors import (
    RetryHint,
    VisionPermanentError,
    VisionProviderError,
    VisionRetryableError,
)


def test_retry_hint_is_frozen() -> None:
    # Arrange
    hint = RetryHint(kind="rate_limit", backoff_seconds=60.0)

    # Act / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        hint.backoff_seconds = 1.0  # type: ignore[misc]


def test_retryable_error_exposes_hint_and_status() -> None:
    # Arrange
    hint = RetryHint(kind="server_error", backoff_seconds=2.0)

    # Act
    err = VisionRetryableError("일시 오류", hint, status_code=503)

    # Assert
    assert err.retry_hint is hint
    assert err.retry_hint.kind == "server_error"
    assert err.retry_hint.backoff_seconds == 2.0
    assert err.status_code == 503
    assert str(err) == "일시 오류"


def test_retryable_error_status_code_defaults_none() -> None:
    # Act
    err = VisionRetryableError(
        "rate limit", RetryHint(kind="rate_limit", backoff_seconds=60.0)
    )

    # Assert
    assert err.status_code is None


def test_permanent_error_exposes_status() -> None:
    # Act
    err = VisionPermanentError("잘못된 요청", status_code=400)

    # Assert
    assert err.status_code == 400
    assert str(err) == "잘못된 요청"


def test_both_errors_caught_by_base() -> None:
    # Arrange
    retryable = VisionRetryableError(
        "x", RetryHint(kind="rate_limit", backoff_seconds=60.0)
    )
    permanent = VisionPermanentError("y")

    # Act / Assert
    for err in (retryable, permanent):
        with pytest.raises(VisionProviderError):
            raise err
