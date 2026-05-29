"""
VisionProvider 추상화 패키지 public API.

GeminiProvider는 [1-2]에서 추가 예정 (이번 [1-1]에서는 미포함).
"""

from __future__ import annotations

from app.vision.base import AnalyzeResult, VisionInput, VisionProvider
from app.vision.errors import (
    RetryHint,
    VisionPermanentError,
    VisionProviderError,
    VisionRetryableError,
)
from app.vision.gemini import GeminiProvider
from app.vision.mock import MockVisionProvider

__all__ = [
    "AnalyzeResult",
    "VisionInput",
    "VisionProvider",
    "VisionProviderError",
    "VisionRetryableError",
    "VisionPermanentError",
    "RetryHint",
    "MockVisionProvider",
    "GeminiProvider",
]
