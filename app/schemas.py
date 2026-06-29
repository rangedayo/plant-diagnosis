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


class RefineContext(BaseModel):
    """[챗봇 2차 보정] 1차 generate가 쓴 RAG 컨텍스트 — 2차 generate-only 재실행 재료.

    generate-only 재실행에 필요한 비-analyze 입력(RAG 문서·타입 분포·플래그)을 1차 응답에
    실어 2차 요청(RefineRequest)으로 echo-back한다. Gemini·임베딩 재호출 회피용.
    `/compare`의 DiagnosisSnapshot echo-back과 동형 패턴(클라이언트가 서버 산출 컨텍스트 보유).
    """

    rag_docs: list[str] = Field(
        default_factory=list, description="generate에 주입된 RAG 카드 본문(태그 포함)"
    )
    top_3_problem_type_weighted: dict[str, Any] = Field(
        default_factory=dict, description="top_3 sim 가중 다수결(majority/distribution/top_problem_type)"
    )
    rag_failed: bool = Field(default=False, description="RAG 시스템 실패 플래그")
    rag_no_docs: bool = Field(default=False, description="검색 통과 문서 0건 플래그")
    rag_weak_evidence: bool = Field(default=False, description="약한 유사도 플래그")


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
    refine_context: Optional[RefineContext] = Field(
        default=None,
        description="[챗봇 2차 보정] 2차 generate-only 재실행용 RAG 컨텍스트 echo-back 재료",
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


class TrendRequest(BaseModel):
    """[추이 요약] 같은 식물의 진단 이력 전체(시간순)를 받아 전반 흐름을 요약 요청.

    /compare가 직전 vs 이번 2건을 비교하는 것과 달리, 이력 N건의 큰 그림(호전/악화/등락)을
    아주 간결하게 요약한다. diagnoses는 오래된→최신 순서로 전달한다.
    """

    diagnoses: list[DiagnosisSnapshot] = Field(
        description="진단 이력 스냅샷(오래된→최신, 2건 이상)"
    )


class TrendResponse(BaseModel):
    """[추이 요약] 전반 추이 요약 응답(단일 필드)."""

    trend: str = Field(description="한국어 자연어 추이 요약 서술")


class FollowupAnswer(BaseModel):
    """[챗봇 2차 보정] 객관식 문답 1쌍 (질문 + 선택 답변)."""

    question: str = Field(default="", description="객관식 질문 텍스트")
    answer: str = Field(default="", description="사용자가 고른 답변 텍스트")


class RefineRequest(BaseModel):
    """[챗봇 2차 보정] /diagnose/refine 요청 — 1차 재료 echo-back + 객관식 답변.

    Gemini(analyze)·임베딩(retrieve) 재호출 없이 generate+guard만 재실행한다:
    analysis(1차 analyze 6필드)와 refine_context(1차 RAG 컨텍스트)를 그대로 되돌려받고,
    answers를 참고 맥락으로 합류. observed_symptoms는 1차 값 불변 → cardinal_miss=0 보존.
    """

    analysis: AnalysisResult = Field(description="1차 analyze 6필드(증상 포함, 불변 전달)")
    refine_context: RefineContext = Field(description="1차 RAG 컨텍스트(echo-back)")
    answers: list[FollowupAnswer] = Field(
        default_factory=list, description="객관식 문답 결과"
    )
