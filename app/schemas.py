"""
식물 진단 API 입출력 Pydantic 스키마
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """analyze 단계 관찰 결과 6필드 (generate 진단과 평행, [1-9] plant_id 대체)."""

    plant_name: Optional[str] = Field(
        default=None, description="식물 학명(영문, analyze 1위)"
    )
    plant_name_korean: Optional[str] = Field(
        default=None, description="식물 한국어 통명"
    )
    plant_confidence: Optional[Literal["low", "med", "high"]] = Field(
        default=None, description="식별 신뢰도 (low / med / high)"
    )
    alt_candidates: list[str] = Field(
        default_factory=list, description="대안 학명 후보(영문 학명)"
    )
    visual_description: str = Field(
        default="", description="한국어 시각 묘사(잎·줄기·색상·형태)"
    )
    observed_symptoms: list[str] = Field(
        default_factory=list, description="관찰된 증상 키워드(한국어)"
    )


class DiagnosisResponse(BaseModel):
    """LangGraph 진단 완료 응답"""

    message: str = Field(default="diagnosis complete")
    analysis: Optional[AnalysisResult] = None
    structured_result: dict[str, Any] = Field(
        default_factory=dict,
        description="summary, current_state, cause, action_plan, status",
    )


class HealthResponse(BaseModel):
    """헬스체크 응답"""

    status: str
    plant_id_configured: bool
    openai_configured: bool
