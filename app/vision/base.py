"""
VisionProvider 추상화의 핵심 인터페이스.

- AnalyzeResult: analyze 단계 출력 6필드 (phase2_decisions #1 — 관찰만, 진단 status는 generate 책임).
- VisionInput: provider 입력 (현재 image_bytes + mime_type만).
- VisionProvider: Protocol (정적 타입 체크 전용, @runtime_checkable 미사용).

AnalyzeResult는 VisionProvider와 강결합이라 app/schemas.py가 아닌 여기에 둔다.
main 응답용 DiagnosisResponse(app/schemas.py)는 별개로 유지한다.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class AnalyzeResult(BaseModel):
    """analyze 단계 출력 — 이미지에서 '관찰'한 사실만 담는다(진단·처방 아님)."""

    plant_name: str = Field(
        description="식물 학명(영문). 예: 'Dracaena reflexa'",
    )
    plant_name_korean: str = Field(
        description="식물 한국어 이름. 예: '드라세나 리플렉사'",
    )
    plant_confidence: Literal["low", "med", "high"] = Field(
        description="식물명 식별 신뢰도 (low / med / high 3단계).",
    )
    alt_candidates: list[str] = Field(
        default_factory=list,
        description="대안 학명 후보(영문 학명만, 확률·한국어명 미포함).",
    )
    visual_description: str = Field(
        description="이미지에 보이는 식물의 시각적 묘사(잎·줄기·색상·전체 형태 등).",
    )
    observed_symptoms: list[str] = Field(
        default_factory=list,
        description="관찰된 증상 키워드(한국어). 예: ['잎끝 갈변', '아래잎 황화'].",
    )


class VisionInput(BaseModel):
    """VisionProvider 입력 — 시계열 추적 필드(plant_handle 등)는 4단계에서 필요 시 추가."""

    image_bytes: bytes = Field(
        description="분석 대상 이미지의 원본 바이트.",
    )
    mime_type: Literal["image/jpeg", "image/png"] = Field(
        default="image/jpeg",
        description="이미지 MIME 타입 (image/jpeg 또는 image/png).",
    )


class VisionProvider(Protocol):
    """
    이미지를 받아 AnalyzeResult를 반환하는 비전 분석 provider 인터페이스.

    에러 처리 약속:
    - 재시도하면 성공할 수 있는 일시적 오류(429 rate limit / 5xx server error)는
      VisionRetryableError(RetryHint 첨부)를 발생시킨다.
    - 재시도해도 실패하는 영구 오류(잘못된 요청, 인증 실패, 파싱 불가 등)는
      VisionPermanentError를 발생시킨다.
    두 에러 모두 VisionProviderError 서브클래스이므로 호출부는
    `except VisionProviderError`로 일괄 포착할 수 있다.
    """

    async def analyze(self, vision_input: VisionInput) -> AnalyzeResult:
        ...
