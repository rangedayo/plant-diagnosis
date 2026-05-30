# [1-4] analyze_node (unwired) 구현 프롬프트

> 목적: [1-2] GeminiProvider + [1-3] ANALYZE_SYSTEM을 묶어 analyze_node를 작성. 단 graph 와이어링은 안 함 ([1-5] 작업).
> 의존성 주입 패턴(factory) + 재시도 helper inline + 단위 테스트까지.
>
> 작성일: 2026-05-29
> 단계: 리팩토링 1단계의 네 번째 하위 작업 ([1-4])
> 선행: [1-3] `ANALYZE_SYSTEM`·`ANALYZE_USER_TEMPLATE` 상수 `app/prompts.py` 확정·push 완료.

---

## 작업 범위

- **신규 파일만** — graph.py·main.py·prompts.py·기존 model_utils 무변경.
- **graph 와이어링 X** — `add_node`/`add_edge` 호출 안 함. [1-5] 작업.
- **DiagnosisState 변경 X** — TypedDict 새 키 추가는 [1-5]/[1-9] 영역.

## 핵심 설계 결정

### 1. 의존성 주입 패턴 — factory 함수

`make_analyze_node(provider: VisionProvider)` → `analyze_node` 클로저 반환.

근거:
- [1-5] `build_diagnosis_graph()`에서 GeminiProvider 인스턴스 받아 노드 생성하는 패턴과 호환
- 테스트에서 `MockVisionProvider` 주입 가능
- GeminiProvider 인스턴스가 module-level 싱글톤이 아니라 FastAPI lifespan에 묶일 수 있게 함 ([1-5] 결정)

### 2. 출력 dict — 6필드만

`analyze_node` 반환 dict는 v3 ANALYZE_SYSTEM의 6필드 그대로:
`plant_name`, `plant_name_korean`, `plant_confidence`, `alt_candidates`, `visual_description`, `observed_symptoms`.

**기존 키(`description`, `confidence`, `is_healthy_prob`, `top_candidates`, `disease_name`)와의 매핑은 [1-5] 영역**. [1-4]에서는 단순 매핑만 (v8 원칙 #3 변수 격리).

### 3. 재시도 helper — inline

`phase2_decisions #8`에 따라 `_with_retry` helper를 `analyze.py` 안에 inline 정의. `# TODO: extract to decorator when 2nd provider added` 주석 포함.

- `max_attempts = 2` (총 시도 2회 = 최초 + 재시도 1회)
- 429 60초 대기 × 1회 재시도 = 사용자 대기 한계 안
- `VisionRetryableError`만 잡고 `e.retry_hint.backoff_seconds` sleep 후 재시도
- `VisionPermanentError`는 잡지 않고 그대로 전파

### 4. 파일 위치 — `app/nodes/` 신규 디렉토리

근거:
- `graph.py`가 이미 700+ 라인이라 더 키우면 가독성 ↓
- [1-6~8]에서 다른 노드들도 모듈화 검토 예정 — analyze가 그 시작점
- `tests/nodes/`도 같이 신규 디렉토리

### 5. mime_type

`VisionInput(mime_type="image/jpeg")` 고정. [1-5] 와이어링 시 `main.py`의 magic number 결과와 동기화 (현 단계 범위 외).

---

## Claude Code에 붙여넣을 프롬프트

```
plant-diagnosis 리팩토링 1단계의 [1-4] analyze_node (unwired)를 구현한다.
graph.py·main.py·prompts.py·기존 model_utils는 한 줄도 수정하지 마라.
analyze_node는 graph에 add_node 하지 않는다 — 와이어링은 [1-5] 작업이다.

[목표]
- VisionProvider Protocol을 받아 analyze_node를 만드는 factory 함수
- 재시도 로직 inline helper (_with_retry)
- 단위 테스트 5건

[디렉토리/파일 신규 생성]
app/nodes/__init__.py            # 빈 파일
app/nodes/analyze.py             # make_analyze_node + _with_retry
tests/nodes/__init__.py          # 빈 파일
tests/nodes/test_analyze.py      # 단위 테스트 5건

[app/nodes/analyze.py 구조]

import 패턴:
  from __future__ import annotations
  import asyncio
  from typing import Any, Awaitable, Callable
  from app.vision.base import AnalyzeResult, VisionInput, VisionProvider
  from app.vision.errors import VisionRetryableError

함수 1: _with_retry
  async def _with_retry(
      fn: Callable[..., Awaitable[Any]],
      *args: Any,
      max_attempts: int = 2,
      **kwargs: Any,
  ) -> Any:
      """
      VisionRetryableError 재시도. backoff은 e.retry_hint.backoff_seconds.
      VisionPermanentError 등 다른 예외는 잡지 않고 전파.
      max_attempts=2 = 총 시도 2회 (최초 + 재시도 1회).

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

함수 2: make_analyze_node factory
  def make_analyze_node(provider: VisionProvider):
      """
      VisionProvider 의존성 주입 → analyze_node 클로저 반환.
      [1-5] build_diagnosis_graph()에서 GeminiProvider 인스턴스를 받아 노드 생성한다.
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
              mime_type="image/jpeg",  # [1-5]에서 main.py와 동기화
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

[tests/nodes/test_analyze.py — 단위 테스트 5건]

- pytest-asyncio strict + @pytest.mark.asyncio (기존 [1-1]/[1-2] 패턴과 동일)
- MockVisionProvider 활용 (app.vision.MockVisionProvider — [1-1]에서 만든 것)
- asyncio.sleep mock: unittest.mock.patch("asyncio.sleep", new_callable=AsyncMock)

테스트 케이스:

1. test_analyze_node_returns_6_fields_on_success:
   - 미리 정의한 AnalyzeResult를 MockVisionProvider에 주입
   - make_analyze_node로 노드 생성 → state={"image_bytes": b"...JPEG..."}로 호출
   - 반환 dict가 정확히 6개 키 + 각 값 일치 확인

2. test_analyze_node_propagates_permanent_error:
   - MockVisionProvider에 VisionPermanentError 주입
   - analyze_node 호출 → VisionPermanentError 그대로 raise
   - asyncio.sleep mock 호출 횟수 == 0 (재시도 없음 확인)

3. test_analyze_node_retries_on_retryable_error_then_succeeds:
   - 1회째 VisionRetryableError, 2회째 정상 AnalyzeResult 반환하는 분기형 provider
     → MockVisionProvider는 단일 응답이라 한계 있음. 이 테스트만 별도 헬퍼 클래스 또는
        unittest.mock.AsyncMock + side_effect=[error, result] 패턴으로 구성.
   - analyze_node 호출 → 두 번째 시도 결과 반환
   - asyncio.sleep mock 호출 횟수 == 1 + 인자 == e.retry_hint.backoff_seconds 확인

4. test_analyze_node_raises_after_max_attempts:
   - 항상 VisionRetryableError raise하는 provider (side_effect=[error1, error2])
   - analyze_node 호출 → 2회 시도 후 VisionRetryableError raise
   - asyncio.sleep mock 호출 횟수 == 1 (max_attempts-1)

5. test_with_retry_uses_backoff_seconds_from_retry_hint:
   - RetryHint(kind="rate_limit", backoff_seconds=60.0) 케이스와
     RetryHint(kind="server_error", backoff_seconds=2.0) 케이스 각각 검증
   - asyncio.sleep mock에 전달된 인자가 일치하는지 확인
   - 이 테스트는 _with_retry를 직접 호출해도 됨 (make_analyze_node 거치지 않고)

[제약]
- 기존 app/ 코드 수정 금지. 신규 파일만.
- analyze_node는 graph에 add_node 하지 않는다 — [1-5] 작업.
- DiagnosisState (app.graph) 변경 금지. state 인자 타입은 dict[str, Any].
- prompts.ANALYZE_SYSTEM/ANALYZE_USER_TEMPLATE는 이번 단계에서 import 하지 마라
  ([1-5]에서 GeminiProvider 인스턴스화 시 호출부가 사용. analyze_node는 provider만 받음).
- Python 3.12, from __future__ import annotations.
- 들여쓰기 4칸. 타입 힌트 적극 사용.
- 파일 인코딩 BOM 없는 UTF-8.

[검증]
1. pytest tests/ -v -m "not integration" → 기존 18건 + 신규 5건 = 23건 모두 passed.
2. python -c "from app.nodes.analyze import make_analyze_node, _with_retry; print('ok')" → 'ok'.
3. ruff/mypy 설정이 있으면 함께 통과 확인. 없으면 생략.

[보고]
- 만든 파일 목록 + 라인 수.
- pytest 결과 (passed/failed).
- 분기형 provider/AsyncMock 패턴 구현 방식 간단 설명 (테스트 케이스 3, 4번).
- _with_retry 구현 중 (추정) 또는 임의 결정한 부분 명시.
- git commit은 아직 하지 마라.
```

---

## 의뢰 후 검증 포인트

- 23/23 passed (기존 18 + 신규 5)
- `analyze_node`가 6필드만 반환 (기존 키 매핑 없음)
- `_with_retry`가 `VisionRetryableError`만 잡고 `VisionPermanentError`는 전파
- `asyncio.sleep` mock으로 실제 대기 안 함 → 테스트 0.x초 안에 완료
- 회귀 없음 — `app/nodes/` 신규 디렉토리만, 기존 코드 무변경

## 다음 단계 (이거 끝난 뒤)

1. 보고 검토 + 회귀 없음 확인
2. git commit (한글): `feat: analyze_node factory + _with_retry helper 추가 ([1-4])`
3. git push
4. **[1-5] graph 와이어링 진입** — 가장 큰 작업:
   - `build_diagnosis_graph()`에서 `GeminiProvider(system_prompt=ANALYZE_SYSTEM)` 인스턴스 생성
   - `make_analyze_node(provider)`로 analyze_node 생성 → `add_node`
   - `identify_node`/`describe_node` 제거 + 엣지 재배선
   - **DiagnosisState 매핑 결정**: 6필드 키 추가 + 기존 키와의 호환 처리
   - **회귀 게이트 -5%p 측정** (`eval/after_phase1_wiring.json` 또는 유사 이름)

---

## 미리 알아둘 점 — [1-5]는 위험 단계

[1-5]는 회귀 게이트가 있는 첫 번째 작업이야. v8 원칙 #3 (변수 격리)에 따라 분리해서 진행 예정:
- 와이어링 + 매핑만 → 측정 → 게이트 통과 → commit
- 게이트 미통과 시 디버깅 (프롬프트? 매핑?) → 재측정

[1-5] 진입 전 별도 진단 프롬프트가 필요할 수 있어 ([1-5] 작업 자체가 크므로 v7 원칙대로 진단 먼저). 그 결정은 [1-4] 완료 후에 함께 논의.
