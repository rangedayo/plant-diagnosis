# [1-2] GeminiProvider 구현 프롬프트

> 목적: [1-1]에서 만든 `VisionProvider` Protocol을 구현하는 `GeminiProvider` 작성.
> google-genai SDK 의존성 추가, 실제 Gemini API 호출, 에러 매핑, 단위·통합 테스트까지.
>
> 작성일: 2026-05-29
> 단계: 리팩토링 1단계의 두 번째 하위 작업 ([1-2])
> 선행: [1-1] VisionProvider 추상화 완료 (push됨), [1-1.5] SDK 사전 조사 완료.

---

## 결정사항 (사용자 확정)

- **`get_gemini_api_key()` reader 위치**: `app/model_utils.py` — 기존 `get_plant_id_api_key`(L31)/`get_openai_api_key`(L135) 옆. env reader 컨벤션 통일. [1-10]에서 Plant.id reader 제거할 때 한곳에서 정리.
- **Vision 모델**: `gemini-2.5-flash`로 시작 (Phase 1 결정).
- **system_prompt 주입 시점**: GeminiProvider 생성자 (stateless 사용, 프롬프트는 [1-3]에서 확정).
- **temperature 인자**: 생성자에 추가하되 default `None` → SDK 기본값. [1-10] 후 A/B/C 튜닝 시 env로 주입.

## 핵심 설계 결정

- **`genai.Client` 인스턴스 위치**: 일단 GeminiProvider 생성자에서 생성·보관. [1-5] graph 와이어링 단계에서 FastAPI lifespan으로 옮길지 별도 결정.
- **에러 매핑 순서**: `ClientError` → `ServerError` 순으로 catch (둘 다 `APIError` 서브클래스라 순서 중요).
- **429 backoff**: Retry-After 헤더 추출 시도 → 실패 시 기본 60.0초. SDK 응답 구조는 [1-2] 구현 중 실험으로 확인 후 보고.
- **5xx backoff**: 고정 2.0초 (phase2_decisions #9).
- **Pydantic default 값 거부 함정**: SDK 사전 조사 #6에서 알려진 함정. 통합 테스트로 실증 → 거부되면 default 제거 + 호출자 측 빈 리스트 처리로 fallback.
- **Client 인스턴스 mock 패턴**: 단위 테스트는 `@patch("app.vision.gemini.genai.Client")`로 통째 패치.

---

## Claude Code에 붙여넣을 프롬프트

```
plant-diagnosis 리팩토링 1단계의 [1-2] GeminiProvider를 구현한다.
[1-1]에서 만든 VisionProvider Protocol·AnalyzeResult·VisionInput·에러 계층 위에 얹는다.
graph 와이어링은 [1-5] 작업이라 이번에 graph.py·main.py는 건드리지 않는다.

[목표]
- google-genai SDK 의존성 추가
- app/vision/gemini.py 신규 작성 — GeminiProvider 클래스
- app/model_utils.py에 get_gemini_api_key() 함수 추가 (기존 get_*_api_key 옆)
- tests/vision/test_gemini_provider.py 신규 작성 — 단위 테스트 5건 + 통합 테스트 1건

[수정/신규 파일]
신규: app/vision/gemini.py
신규: tests/vision/test_gemini_provider.py
수정: app/model_utils.py (get_gemini_api_key 1개 함수 추가만)
수정: app/vision/__init__.py (GeminiProvider export 추가)
수정: requirements.txt (google-genai 한 줄 추가)

[app/model_utils.py 수정 — 1곳만]
- get_openai_api_key()/get_rda_api_key() 정의 근처(파일 라인 ~135~140 부근)에 다음 함수 추가:

  def get_gemini_api_key() -> Optional[str]:
      return os.getenv("GEMINI_API_KEY")

- 그 외 model_utils.py는 한 줄도 수정하지 마라.

[app/vision/gemini.py — GeminiProvider 클래스]

import 패턴:
  from google import genai
  from google.genai import errors as genai_errors
  from google.genai import types
  from app import model_utils
  from app.vision.base import AnalyzeResult, VisionInput, VisionProvider
  from app.vision.errors import (
      RetryHint, VisionPermanentError, VisionRetryableError,
  )

클래스 시그니처:
  class GeminiProvider:
      def __init__(
          self,
          *,
          system_prompt: str,
          api_key: str | None = None,
          model: str = "gemini-2.5-flash",
          temperature: float | None = None,
      ) -> None:
          resolved_key = api_key or model_utils.get_gemini_api_key()
          if not resolved_key:
              raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")
          self._client = genai.Client(api_key=resolved_key)
          self._model = model
          self._system_prompt = system_prompt
          self._temperature = temperature

      async def analyze(self, vision_input: VisionInput) -> AnalyzeResult: ...

analyze() 구현:
- contents 구성:
    contents=[
        types.Part.from_text(self._system_prompt),
        types.Part.from_bytes(
            data=vision_input.image_bytes,
            mime_type=vision_input.mime_type,
        ),
    ]
- config dict:
    {
        "response_mime_type": "application/json",
        "response_schema": AnalyzeResult,
    }
    self._temperature가 None이 아니면 config에 "temperature": self._temperature 추가.
- 호출: await self._client.aio.models.generate_content(model=..., contents=..., config=...)

에러 매핑 (catch 순서 중요 — ClientError가 ServerError보다 먼저):
- except genai_errors.ClientError as e:
    if e.code == 429:
        backoff = _extract_retry_after(e) or 60.0
        raise VisionRetryableError(
            str(e),
            RetryHint(kind="rate_limit", backoff_seconds=backoff),
            status_code=e.code,
        ) from e
    raise VisionPermanentError(str(e), status_code=e.code) from e
- except genai_errors.ServerError as e:
    raise VisionRetryableError(
        str(e),
        RetryHint(kind="server_error", backoff_seconds=2.0),
        status_code=e.code,
    ) from e

응답 파싱:
- response.parsed가 AnalyzeResult 인스턴스가 아니면:
    raise VisionPermanentError(
        f"응답 스키마 검증 실패: parsed={type(response.parsed).__name__}"
    )
- 인스턴스면 그대로 반환.

_extract_retry_after(error: genai_errors.ClientError) -> float | None:
- ClientError에서 Retry-After 헤더 추출 시도.
- SDK가 헤더를 어디 노출하는지 확실치 않으므로:
  - 우선 e.response_json·e.message에서 'Retry-After' 키/필드 탐색
  - 없으면 None 반환 (호출부가 기본 60.0초 사용)
- 구현 중 SDK 실제 응답 구조를 print/log로 확인 후 보고에 명시 (추정 → 실증 전환).

[app/vision/__init__.py 수정]
- GeminiProvider를 base/errors/mock과 함께 export에 추가.

[tests/vision/test_gemini_provider.py — 단위 테스트 5건]
- pytest-asyncio 사용. genai.Client를 통째 패치:

  from unittest.mock import AsyncMock, patch, MagicMock

  @patch("app.vision.gemini.genai.Client")
  ...

- 테스트 케이스 5건:
  1. test_analyze_returns_parsed_result_on_success:
     mock_client.aio.models.generate_content를 AsyncMock으로 두고,
     response.parsed가 정상 AnalyzeResult 인스턴스인 응답 반환.
     analyze() 결과가 그 인스턴스인지 확인.

  2. test_analyze_raises_retryable_on_429:
     mock 호출이 genai_errors.ClientError(code=429)를 raise.
     VisionRetryableError 발생 + retry_hint.kind == "rate_limit" + backoff_seconds >= 60 확인.

  3. test_analyze_raises_retryable_on_5xx:
     mock 호출이 genai_errors.ServerError(code=503)를 raise.
     VisionRetryableError 발생 + retry_hint.kind == "server_error" + backoff_seconds == 2.0 확인.

  4. test_analyze_raises_permanent_on_4xx_non_429:
     mock 호출이 genai_errors.ClientError(code=400)를 raise.
     VisionPermanentError 발생 + status_code == 400 확인.

  5. test_analyze_raises_permanent_on_invalid_parsed:
     mock response.parsed가 None 또는 dict인 응답.
     VisionPermanentError 발생 확인.

- 각 테스트에 fake api_key="test-key" 주입 (실제 GEMINI_API_KEY 없어도 동작해야 함).
- genai_errors.ClientError·ServerError를 직접 raise할 때 생성자 시그니처는 SDK 실제 시그니처대로 맞춰라
  (모르면 구현 중 확인 후 보고에 명시. status_code/message 속성 접근이 핵심).

[tests/vision/test_gemini_provider.py — 통합 테스트 1건]
- @pytest.mark.integration 마커 + @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), ...)
- 실제 Gemini API 1회 호출:
  - 입력 이미지: test_data/main_eval/images/self_haengun_001.jpg
  - system_prompt: 임시로 "이 이미지를 한국어로 분석해서 6필드 JSON으로 반환하라" 정도. 
    [1-3]에서 정식 프롬프트 작성하므로 통합 테스트의 프롬프트는 자리표시(placeholder)로만 사용.
- 검증:
  - 6필드 다 채워졌는지 (빈 문자열·빈 리스트 허용)
  - response.parsed가 AnalyzeResult 인스턴스인지
  - **Pydantic default 값 거부 여부 실증** — alt_candidates/observed_symptoms의 default_factory=list가
    SDK에서 거부되면 통합 테스트가 ValidationError/ClientError로 실패. 결과를 보고에 명시:
    "default_factory=list 그대로 동작함" 또는 "거부됨 → AnalyzeResult에서 default 제거 필요".

[requirements.txt 수정]
- google-genai 한 줄 추가 (기존 의존성 항목 스타일대로, 버전 핀 없이).

[제약]
- 기존 app/ 코드 수정 범위는 다음 4곳만:
  1) app/model_utils.py — get_gemini_api_key() 함수 추가
  2) app/vision/__init__.py — GeminiProvider export 추가
  3) requirements.txt — google-genai 추가
  4) (신규) app/vision/gemini.py, tests/vision/test_gemini_provider.py
- graph.py, main.py, schemas.py, prompts.py, 기존 model_utils 다른 함수는 절대 수정 금지.
- 파일 인코딩 BOM 없는 UTF-8.
- Python 3.12, from __future__ import annotations 사용.
- 타입 힌트 적극 사용. async 메서드는 @pytest.mark.asyncio.

[검증]
1. pytest tests/vision/ -v (통합 테스트 포함) — 통합은 GEMINI_API_KEY 있을 때만.
   - 단위 테스트 5건 + 기존 [1-1] 테스트 13건 = 통합 빼고 18건 모두 passed.
   - 통합 테스트는 결과 보고에 별도 명시.
2. pytest tests/vision/ -v -m "not integration" — 통합 제외 18건 passed (CI 친화 모드).
3. python -c "from app.vision import GeminiProvider; print('ok')" → 'ok'.
4. python -c "from app import model_utils; print(model_utils.get_gemini_api_key() is not None)" → True (.env에 키 있다면).

[보고]
- 만든/수정한 파일 목록 + 라인 수.
- pytest 결과 (단위 5건 + 통합 1건 각각).
- 통합 테스트 실제 호출 결과:
  - response.parsed의 6필드 값 (간단 요약).
  - latency (1회 호출 기준).
  - **Pydantic default 값(`default_factory=list`) 거부 여부** — 통합 테스트가 통과했는지 실패했는지.
- _extract_retry_after 구현 시 SDK 응답에서 Retry-After 헤더가 실제로 어디 있는지 확인 결과
  (e.response_json, e.message, 다른 속성 — 추정에서 실증으로 전환된 사항 명시).
- genai_errors.ClientError/ServerError 생성자 시그니처 확인 결과 (테스트에서 직접 raise한 방식).
- 구현 중 (추정) 또는 임의 결정한 부분.
- git commit은 아직 하지 마라 — 결과 확인 후 다음 단계에서 함께.
```

---

## 의뢰 후 검증 포인트

- `pytest tests/vision/ -v -m "not integration"` 18건 통과 (단위 5건 신규 + 기존 13건)
- 통합 테스트 결과:
  - `response.parsed`의 6필드 실제 값 보고
  - Pydantic default 값 거부 여부 — 거부되면 AnalyzeResult 수정 후속 task 필요
- `_extract_retry_after` 실측 결과 — SDK 응답에서 Retry-After가 어디 있는지 명시 (추정 → 실증)
- 기존 app/ 코드 무변경 확인 (model_utils.py에 get_gemini_api_key 1개 함수 추가 외)

## 다음 단계 (이거 끝난 뒤)

1. 보고 검토 + 통합 테스트 결과 확인
2. Pydantic default 거부 시 AnalyzeResult 수정 별도 처리
3. git commit (한글): `feat: GeminiProvider 구현 + google-genai SDK 의존성 추가 ([1-2])`
4. **[1-3] analyze 프롬프트 설계 진입** — DESCRIBE_IMAGE_SYSTEM을 대체할 6필드 JSON 출력 프롬프트. "진단 X, 병명 추정 X, 처방 X" 3중 금지를 풀어내고 출력 형식·status enum·언어 3개만 강제.

---

## 참고 — [1-1.5] SDK 사전 조사 핵심 요약 (재게시)

- `google-genai` 사용 (`google-generativeai`는 2025-08-31 EOL).
- import: `from google import genai`, `from google.genai import errors, types`.
- 에러: `errors.APIError` 베이스, `ClientError`(4xx, 429 포함)/`ServerError`(5xx) 분기.
- async: `client.aio.models.generate_content(...)` 패턴.
- 구조화 출력: Pydantic BaseModel + `response_mime_type="application/json"` + `response_schema=...`, `response.parsed`로 타입 안전.
- 알려진 함정: Pydantic default 값이 SDK 일부 버전에서 거부됨 — 통합 테스트로 실증.
