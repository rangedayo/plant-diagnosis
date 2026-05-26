"""
식물 진단 API 입출력 Pydantic 스키마
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PlantCandidateItem(BaseModel):
    """Plant.id 분류 상위 후보 한 항목"""

    name: Optional[str] = Field(default=None, description="후보 학명")
    probability: Optional[float] = Field(default=None, description="확률 (0~1)")


class PlantIdentificationResult(BaseModel):
    """Plant.id 1차 식별 결과 요약"""

    plant_name: Optional[str] = Field(default=None, description="식물명(1위)")
    disease_name: Optional[str] = Field(default=None, description="병해/질병명")
    confidence: Optional[float] = Field(
        default=None, description="1위 분류 신뢰도 (0~1)"
    )
    is_healthy_prob: Optional[float] = Field(
        default=None,
        description="Plant.id is_healthy: 이미지에 건강한 식물일 추정 확률 (0~1)",
    )
    top_candidates: list[PlantCandidateItem] = Field(
        default_factory=list,
        description="분류 상위 후보(최대 3개): name, probability",
    )


class DiagnosisDebug(BaseModel):
    """LangGraph 중간 결과 디버그"""

    keywords: list[str] = Field(default_factory=list)
    sick_keys: list[str] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    """LangGraph 진단 완료 응답"""

    message: str = Field(default="diagnosis complete")
    plant_id: Optional[PlantIdentificationResult] = None
    structured_result: dict[str, Any] = Field(
        default_factory=dict,
        description="summary, current_state, cause, action_plan, status",
    )
    debug: Optional[DiagnosisDebug] = None


class HealthResponse(BaseModel):
    """헬스체크 응답"""

    status: str
    plant_id_configured: bool
    openai_configured: bool
