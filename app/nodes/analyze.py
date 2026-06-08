"""
analyze_node ([1-4], unwired) — [1-2] GeminiProvider + [1-3] ANALYZE_SYSTEM 결합 지점.

설계(1-4_analyze_node_프롬프트.md):
- make_analyze_node(provider): VisionProvider 의존성 주입 → analyze_node 클로저 반환.
  [1-5] build_diagnosis_graph()에서 GeminiProvider 인스턴스를 받아 노드를 생성한다.
- analyze_node 반환 dict는 v3 ANALYZE_SYSTEM의 6필드만. 기존 키 매핑은 [1-5] 영역.
- _with_retry: VisionRetryableError만 재시도(phase2_decisions #8). graph 와이어링은 [1-5].
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from app.vision.base import AnalyzeResult, VisionInput, VisionProvider
from app.vision.errors import VisionRetryableError


async def _with_retry(
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    max_attempts: int = 3,
    **kwargs: Any,
) -> Any:
    """
    VisionRetryableError 재시도. backoff은 e.retry_hint.backoff_seconds.
    VisionPermanentError 등 다른 예외는 잡지 않고 전파.
    max_attempts=3 = 총 시도 3회 (최초 + 재시도 2회). 일시적 429 흡수용 상향(eval 케이스 탈락 방지).

    TODO: extract to decorator when 2nd provider added (phase2_decisions #8)
    """
    attempt = 0
    while True:
        try:
            return await fn(*args, **kwargs)
        except VisionRetryableError as e:
            attempt += 1
            if attempt >= max_attempts:
                raise
            await asyncio.sleep(e.retry_hint.backoff_seconds)


def make_analyze_node(
    provider: VisionProvider,
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """
    VisionProvider 의존성 주입 → analyze_node 클로저 반환.
    [1-5] build_diagnosis_graph()에서 GeminiProvider 인스턴스를 받아 노드를 생성한다.
    """

    async def analyze_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        state["image_bytes"]에서 6필드 관찰 결과 추출.
        반환 dict는 6필드만 (기존 키 매핑은 [1-5] 영역).

        출력 키:
        - plant_name (str)
        - plant_name_korean (str)
        - plant_confidence ('low'|'med'|'high')
        - alt_candidates (list[str])
        - visual_description (str)
        - observed_symptoms (list[str])
        """
        image_bytes = state["image_bytes"]
        vision_input = VisionInput(
            image_bytes=image_bytes,
            mime_type="image/jpeg",  # [1-5]에서 main.py 결과와 동기화
        )
        result: AnalyzeResult = await _with_retry(provider.analyze, vision_input)
        return {
            "plant_name": result.plant_name,
            "plant_name_korean": result.plant_name_korean,
            "plant_confidence": result.plant_confidence,
            "alt_candidates": result.alt_candidates,
            "visual_description": result.visual_description,
            "observed_symptoms": result.observed_symptoms,
        }

    return analyze_node
