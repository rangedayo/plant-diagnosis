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


class CareWater(BaseModel):
    """계절별 물주기 (농사로 garden, 한글명)."""

    spring: Optional[str] = Field(default=None, description="봄 물주기")
    summer: Optional[str] = Field(default=None, description="여름 물주기")
    autumn: Optional[str] = Field(default=None, description="가을 물주기")
    winter: Optional[str] = Field(default=None, description="겨울 물주기")


class CareGuide(BaseModel):
    """[기능 (b)] 종명 키 케어 가이드 (농사로 garden 구조화 케어 필드).

    진단 결과와 무관하게 첨부되는 지속 관리 정보. (a) 정상화 RAG와 별개.
    종 미커버 시 응답의 care_guide는 None.
    """

    species_key: str = Field(description="정규화 종 키 (예: 드라세나, 몬스테라)")
    display_name: Optional[str] = Field(default=None, description="대표 표시명")
    src_cntntsNo: Optional[str] = Field(default=None, description="농사로 garden 콘텐츠 번호")
    scientific_name: Optional[str] = Field(default=None, description="학명")
    soil: Optional[str] = Field(default=None, description="토양")
    water: Optional[CareWater] = Field(default=None, description="계절별 물주기")
    light: Optional[str] = Field(default=None, description="광량")
    temperature: Optional[str] = Field(default=None, description="생육 적온")
    humidity: Optional[str] = Field(default=None, description="습도")
    fertilizer: Optional[str] = Field(default=None, description="비료")
    placement: Optional[str] = Field(default=None, description="배치 장소")
    manage_level: Optional[str] = Field(default=None, description="관리 난이도")
    winter_min_temp: Optional[str] = Field(default=None, description="겨울 최저온도")
    growth_height_cm: Optional[str] = Field(default=None, description="생육 높이(cm)")
    growth_area_cm: Optional[str] = Field(default=None, description="생육 면적(cm)")
    note: Optional[str] = Field(default=None, description="종 매핑 비고")


class DiagnosisResponse(BaseModel):
    """LangGraph 진단 완료 응답"""

    message: str = Field(default="diagnosis complete")
    analysis: Optional[AnalysisResult] = None
    structured_result: dict[str, Any] = Field(
        default_factory=dict,
        description="summary, current_state, cause, action_plan, status",
    )
    care_guide: Optional[CareGuide] = Field(
        default=None,
        description="[기능 (b)] 종명 키 케어 가이드 (진단 무관, status 무관 첨부; 미커버 시 None)",
    )


class HealthResponse(BaseModel):
    """헬스체크 응답"""

    status: str
    openai_configured: bool


class DiagnosisSnapshot(BaseModel):
    """[시계열 3단계] 비교 입력용 단일 진단 정성 스냅샷.

    프론트가 Firestore DiagnosisRecord에서 읽은 정성 필드만 전달(이미지·식물명 미전달,
    텍스트 전용 비교). date는 ISO 문자열.
    """

    date: str = Field(default="", description="진단 시각 ISO 문자열")
    status: str = Field(default="", description="진단 상태(건강/과습/건조/병해 의심/영양 부족)")
    summary: str = Field(default="", description="진단 요약")
    current_state: str = Field(default="", description="현재 상태 서술")
    cause: str = Field(default="", description="원인 서술")
    action_plan: list[str] = Field(default_factory=list, description="권장 조치")
    observed_symptoms: list[str] = Field(
        default_factory=list, description="관찰된 증상 키워드(한국어)"
    )


class CompareRequest(BaseModel):
    """[시계열 3단계] 직전 vs 이번 진단 비교 요청."""

    previous: DiagnosisSnapshot = Field(description="직전(더 오래된) 진단")
    current: DiagnosisSnapshot = Field(description="이번(최신) 진단")


class CompareResponse(BaseModel):
    """[시계열 3단계] 정성 비교 서술 응답(단일 필드)."""

    comparison: str = Field(description="한국어 자연어 정성 비교 서술")
