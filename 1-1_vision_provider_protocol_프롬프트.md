# [1-1] VisionProvider Protocol 구현 프롬프트

> 목적: analyze_node 도입을 위한 추상화 계층(Protocol + 출력 스키마 + 에러 계층 + Mock) 구축.
> 신규 파일만 생성, 기존 app/ 코드 일절 수정 금지.
>
> 작성일: 2026-05-29
> 단계: 리팩토링 1단계의 첫 번째 하위 작업 ([1-1])
> 선행: v8 baseline 마감(eval/baseline.json 식물명 90.0%), [1-1.5] SDK 사전 조사 완료.

---

## 결정사항 (사용자 확정)

- **`alt_candidates` 타입**: `list[str]` — 학명만, probability/한국어명 미포함. Gemini self-report 신뢰도 낮음 + 화면 표시 단순화.
- **`system_prompt` 주입 시점**: GeminiProvider 생성자에 박음. provider stateless 사용, 프롬프트는 [1-3]에서 한 번 확정 후 변경 안 함.
- **`VisionInput` 추가 필드**: 지금은 `image_bytes + mime_type`만. plant_handle/prior_diagnoses 같은 시계열 추적 필드는 4단계에서 필요 시 추가.

## 핵심 설계 결정

- **AnalyzeResult를 `vision/base.py`에 둠** (`app/schemas.py` 아님). VisionProvider와 강결합이라 분리 시 응집도 깨짐. main 응답용 `DiagnosisResponse`는 별개 유지.
- **데코레이터 미도입** (phase2_decisions #8 YAGNI). `_with_retry` helper는 [1-4] analyze_node 안에 inline. 2번째 Provider 추가 시 데코레이터로 승격.
- **GeminiProvider는 이번 단계에서 안 만듦**. [1-2] 별도 작업.
- **`@runtime_checkable` 안 붙임**. 정적 타입 체크 용도만.

---

## Claude Code에 붙여넣을 프롬프트

```
plant-diagnosis 리팩토링 1단계의 [1-1] VisionProvider Protocol을 구현한다.
신규 파일만 만든다. 기존 app/ 코드는 한 줄도 수정하지 마라.
GeminiProvider 실제 구현은 [1-2] 작업이라 이번엔 만들지 않는다.

[목표]
analyze_node 도입을 위한 추상화 계층. Protocol + 출력 스키마 + 에러 계층 + 테스트용 Mock까지.

[디렉토리/파일 신규 생성]
app/vision/
  __init__.py
  base.py
  errors.py
  mock.py
tests/__init__.py             # 없으면 생성
tests/vision/__init__.py
tests/vision/test_base.py
tests/vision/test_errors.py
tests/vision/test_mock.py

[app/vision/base.py — 인터페이스]
- AnalyzeResult(BaseModel): 6필드 (phase2_decisions #1)
  - plant_name: str
  - plant_name_korean: str
  - plant_confidence: Literal["low", "med", "high"]
  - alt_candidates: list[str] = Field(default_factory=list)
  - visual_description: str
  - observed_symptoms: list[str] = Field(default_factory=list)
  각 필드에 description= 한국어로 명시.
- VisionInput(BaseModel):
  - image_bytes: bytes
  - mime_type: Literal["image/jpeg", "image/png"] = "image/jpeg"
- VisionProvider(Protocol):
  - async def analyze(self, vision_input: VisionInput) -> AnalyzeResult: ...
  - docstring에 에러 처리 약속 명시 (VisionRetryableError/VisionPermanentError 발생).
- runtime_checkable 데코레이터는 붙이지 마라 (정적 타입 체크 용도만).

[app/vision/errors.py — 에러 계층]
- @dataclass(frozen=True) class RetryHint:
    kind: Literal["rate_limit", "server_error"]
    backoff_seconds: float
- class VisionProviderError(Exception): """VisionProvider 모든 에러의 베이스."""
- class VisionRetryableError(VisionProviderError):
    __init__(self, message: str, retry_hint: RetryHint, *, status_code: int | None = None)
    self.retry_hint, self.status_code 보관.
- class VisionPermanentError(VisionProviderError):
    __init__(self, message: str, *, status_code: int | None = None)
    self.status_code 보관.

[app/vision/mock.py — 테스트용 Mock]
- MockVisionProvider: VisionProvider Protocol 만족.
- __init__(self, result: AnalyzeResult | None = None, raise_error: Exception | None = None)
- async def analyze(self, vision_input: VisionInput) -> AnalyzeResult:
    raise_error 있으면 raise, 없으면 result 반환.
    result도 None이면 sensible default 반환 (plant_name="Unknown" 등 — 결정값 보고에 명시).
- [1-4] analyze_node 작성 시 단위 테스트에서 사용 예정.

[app/vision/__init__.py — public API]
다음만 export (GeminiProvider는 [1-2]에서 추가):
  AnalyzeResult, VisionInput, VisionProvider,
  VisionProviderError, VisionRetryableError, VisionPermanentError, RetryHint,
  MockVisionProvider

[tests/vision/test_base.py]
- AnalyzeResult 정상 인스턴스화(6필드 다 채움) 확인
- alt_candidates / observed_symptoms 빈 리스트 default 확인
- plant_confidence에 Literal 값 외 입력 시 ValidationError 발생 확인
- VisionInput mime_type 기본값 "image/jpeg" 확인
- VisionInput에 잘못된 mime_type 줄 때 ValidationError 발생 확인

[tests/vision/test_errors.py]
- RetryHint frozen 동작 확인 (속성 변경 시 FrozenInstanceError)
- VisionRetryableError 생성 + retry_hint, status_code 접근 가능 확인
- VisionPermanentError 생성 + status_code 접근 가능 확인
- 두 에러가 VisionProviderError 서브클래스 (except VisionProviderError로 잡힘)

[tests/vision/test_mock.py]
- MockVisionProvider에 result 주입 → analyze() 호출 시 그 result 반환 (asyncio 사용)
- raise_error 주입 → analyze() 호출 시 그 에러 발생
- 둘 다 None → default AnalyzeResult 반환 확인

[requirements.txt 수정]
- pytest, pytest-asyncio 추가 (없으면).
- google-genai는 이번엔 추가하지 마라 — [1-2]에서 GeminiProvider 구현 시 함께.

[제약]
- 기존 app/ 파일 일절 수정 금지. 신규 파일만.
- Python 3.12 기준. from __future__ import annotations 사용.
- 파일 인코딩 BOM 없는 UTF-8 (PowerShell Set-Content 금지).
- 들여쓰기 4칸. 타입 힌트 적극 사용.
- AnalyzeResult/VisionInput는 Pydantic v2 기준. default_factory는 Field()로 감싸기.
- Protocol은 typing.Protocol 사용 (abc.ABC 아님).

[검증]
1. pytest tests/vision/ -v 실행 → 전체 통과.
2. python -c "from app.vision import VisionProvider, AnalyzeResult, MockVisionProvider; print('ok')" → 'ok' 출력.
3. ruff/mypy 설정이 이미 있으면 함께 통과 확인. 없으면 생략.

[보고]
- 만든 파일 목록 + 각 라인 수.
- pytest 결과 (passed/failed 카운트, 실패 시 케이스).
- 구현 중 (추정) 또는 임의 결정한 부분 명시 (예: MockVisionProvider sensible default 값).
- git commit은 아직 하지 마라 — 결과 확인 후 다음 단계에서 함께.
```

---

## 의뢰 후 검증 포인트

- `pytest tests/vision/ -v` 전부 통과
- `from app.vision import ...` import 동작
- MockVisionProvider sensible default 값이 합리적인지 — 너무 그럴듯하면 실 분기 테스트에서 잘못된 보장을 줄 수 있어 "Unknown" 같은 명백히 가짜인 값이 좋음

## 다음 단계 (이거 끝난 뒤)

1. 보고 검토 + 회귀 없음 확인 (이번 작업은 신규 파일만이라 기존 동작 안 깨짐)
2. git commit (한글): "feat: VisionProvider 추상화 계층 추가 ([1-1])"
3. [1-2] GeminiProvider 구현 진입 — google-genai SDK 의존성 추가 + 실제 Gemini 호출 + 에러 매핑 + 통합 테스트

---

## 참고 — [1-1.5] SDK 사전 조사 결과 요약 (이 작업과 무관하지만 [1-2] 진입 시 사용)

- 패키지: `google-genai` (`google-generativeai`는 2025-08-31 EOL, 사용 금지)
- 에러: `from google.genai import errors` → `APIError` 베이스, `ClientError`(4xx)/`ServerError`(5xx) 분기. 429는 ClientError 안에 들어옴.
- async: `client.aio.models.generate_content(...)` 패턴
- Client 인스턴스: lifespan에서 단일 생성, 전역 공유 (httpx.AsyncClient와 동일 패턴)
- 구조화 출력: Pydantic `BaseModel` + `response_mime_type="application/json"` + `response_schema=...`, `response.parsed`로 타입 안전
- 알려진 함정: Pydantic default 값이 SDK 일부 버전에서 거부될 수 있음 ([1-2]에서 실제 테스트로 확인)
