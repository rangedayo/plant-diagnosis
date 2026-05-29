"""
테스트용 Mock VisionProvider.

[1-4] analyze_node 단위 테스트에서 성공/실패 분기를 주입하기 위해 사용한다.
result도 raise_error도 없으면 명백히 가짜인 default(plant_name="Unknown")를 반환한다 —
실 분기 테스트에서 그럴듯한 값으로 잘못된 보장을 주지 않도록 의도적으로 가짜값을 쓴다.
"""

from __future__ import annotations

from app.vision.base import AnalyzeResult, VisionInput


def _default_analyze_result() -> AnalyzeResult:
    """명백히 가짜인 sensible default — 진짜 분석 결과로 오인되지 않게 한다."""
    return AnalyzeResult(
        plant_name="Unknown",
        plant_name_korean="알 수 없음",
        plant_confidence="low",
        alt_candidates=[],
        visual_description="(mock) 분석 결과가 주입되지 않았습니다.",
        observed_symptoms=[],
    )


class MockVisionProvider:
    """VisionProvider Protocol을 만족하는 테스트용 구현."""

    def __init__(
        self,
        result: AnalyzeResult | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._result = result
        self._raise_error = raise_error

    async def analyze(self, vision_input: VisionInput) -> AnalyzeResult:
        _ = vision_input  # mock은 입력을 사용하지 않음
        if self._raise_error is not None:
            raise self._raise_error
        if self._result is not None:
            return self._result
        return _default_analyze_result()
