# [1-9] state/schema 슬림화 — 작업 프롬프트 🔴 2차 회귀 게이트

> Claude Code 의뢰용. 사전 확인 → 백엔드 변경 → 프론트엔드 변경 → 검증 → 게이트 → 보고 흐름. 결정은 진단(영역 1·2·6·7·8.1 A / 영역 3 B / 영역 4·5 [1-10] 미룸) 확정 + Claude Code 사전 조사 결과 위에서 작성.

---

## 1. 컨텍스트 (한 줄)

[1-8] retrieve 정비(db7906b) 완료 후 **[1-9] state/schema 슬림화 + Plant.id 응답 잔재 제거 + 프론트 매핑 동시 변경**. 모노레포 단일 커밋. **2차 회귀 게이트** 🔴.

핵심 성격:
- **동작 무변경 목표** — state 슬림·응답 스키마 재구성·프론트 매핑만. LLM 호출·RAG·프롬프트·analyze·generate 본체 무변경 → 게이트 안전.
- **rag_failed 활성 LLM 경로는 보존** — Claude Code 사전 조사에서 활성 경로로 확인됨. 영역 4·5는 [1-10]으로 미룸. 본 작업에서 절대 손대지 않음.
- **LangGraph InvalidUpdateError 주의** — state TypedDict에서 제거하는 키는 초기 state dict 4곳(`app/main.py`·`scripts/run_eval.py`·`scripts/eval_rag.py`·`app/graph.py`의 analyze 브리지)에서도 동시 제거해야 함. 한 곳이라도 남으면 런타임 에러.
- **백·프론트 단일 커밋** — 모노레포라 중간 상태에서 화면 깨짐 방지 위해 한 커밋에 묶음.

원칙:
- **변수 격리** — 영역 4·5(rag_failed)는 동작 변화라 [1-10]으로 분리.
- **死 코드 발견 즉시 제거** — 영역 외 추가 잔재 발견 시 [1-9] 커밋에 묶기.
- **2회 측정 평균만 판정** — 단일 run으로 게이트 통과 선언 금지.

---

## 2. 사전 확인 (작업 시작 전 필수)

### 2.1 환경

```bash
git status              # 작업 트리 clean 확인
git log -1 --oneline    # HEAD가 db7906b ([1-8] 커밋)인지 확인
git branch --show-current
```

작업 트리 dirty이거나 HEAD가 예상과 다르면 **즉시 멈추고 보고**.

### 2.2 grep 검증

다음 명령 순서대로 실행, 결과를 표로 정리(보고에 포함):

```bash
# 영역 1·2 대상 키 사용처
grep -rn "disease_name\|is_healthy_prob\|top_candidates\|confidence" app/ scripts/ tests/
grep -rn "fallback_plant_name\|plant_filter_mode" app/ scripts/ tests/
grep -rn "PlantIdentificationResult\|PlantCandidateItem" app/ tests/

# description 처리 (사용처 0이면 [1-9] 제거, 1+개면 보존하고 [1-10] 미룸)
grep -rn "\bdescription\b" app/ scripts/ tests/
# DiagnosisState·dict key·매개변수만 카운트. 자연어 주석은 제외하고 판단.

# 영역 8.1 DiagnosisDebug
grep -rn "DiagnosisDebug\|return_debug" app/ scripts/ tests/

# 영역 4·5 보존 대상 — 절대 손대지 말 것 확인용
grep -rn "rag_failed\|REQUIRED_RAG_FAILED_PHRASE\|STRUCTURED_DIAGNOSIS_RAG_FAILED" app/ tests/
# 결과를 보고에 박되 코드는 그대로.

# 프론트 매핑
grep -rn "plant_id\|PlantIdResult\|is_healthy_prob\|disease_name\|confidence" types/ components/ lib/ pages/
grep -rn "percent\|format" components/ResultView.tsx
```

**판정 가이드**:
- `disease_name`·`is_healthy_prob`·`top_candidates`·`confidence`·`fallback_plant_name`·`plant_filter_mode`·`PlantIdentificationResult`·`PlantCandidateItem`: 영역 1·2 제거 대상. 모든 사용처 파악해서 동시 정리.
- `description`: **분기 처리** — 사용처가 `DiagnosisState` TypedDict·초기 state dict·analyze 브리지만이면 [1-9] 제거. `keyword_node`·`generate_node`·`format_*` 헬퍼 등 실 사용처가 있으면 보존하고 [1-10] 미룸(보고 명시).
- `rag_failed` 관련: **현재 위치만 기록**, 코드 변경 0. 영역 4·5 [1-10] 작업의 기초 자료.

### 2.3 view (구조 파악)

다음 파일·범위를 view 후 영역별 변경 계획 확정:

```
app/vision/base.py          (AnalyzeResult Pydantic 모델 타입 — schemas의 AnalysisResult 신설 시 참조)
app/graph.py                (DiagnosisState TypedDict 정의, analyze 노드 브리지 코드)
app/schemas.py              (전체 — PlantIdentificationResult·DiagnosisResponse·DiagnosisDebug)
app/main.py                 (L186-207 초기 state dict, L227-251 응답 매핑)
scripts/run_eval.py         (L59-82 초기 state dict)
scripts/eval_rag.py         (L57~, L91 초기 state dict)
types/diagnosis.ts          (전체)
components/ResultView.tsx   (전체 — L9-14 percent, L17 plant_id 매핑, L56-57 meta)
```

---

## 3. 작업 항목

### 3.1 백엔드 변경

#### A. `app/schemas.py` — 새 모델 + 기존 모델 슬림

**신설**: `AnalysisResult` Pydantic 모델 (6필드)

```python
class AnalysisResult(BaseModel):
    plant_name: str | None = None              # 학명 (영문, analyze 1위)
    plant_name_korean: str | None = None       # 한국어 통명
    plant_confidence: Literal["low", "med", "high"] | None = None
    alt_candidates: list[str] = Field(default_factory=list)
    visual_description: str = ""               # 한국어 관찰 묘사
    observed_symptoms: list[str] = Field(default_factory=list)
```

타입 세부(Optional 여부)는 `app/vision/base.py`의 `AnalyzeResult` 모델과 일관 유지. view 결과 따라 조정.

**삭제**:
- `PlantIdentificationResult` 클래스 통째
- `PlantCandidateItem` 클래스 통째 (top_candidates용이라 동시 무용화)
- `DiagnosisDebug` 클래스 통째 (영역 8.1)

**`DiagnosisResponse` 재구성**:

```python
# Before
class DiagnosisResponse(BaseModel):
    message: str
    plant_id: PlantIdentificationResult
    structured_result: dict
    debug: DiagnosisDebug | None = None

# After
class DiagnosisResponse(BaseModel):
    message: str
    analysis: AnalysisResult | None = None
    structured_result: dict
    # debug 필드 제거 (영역 8.1)
```

#### B. `app/graph.py` — DiagnosisState 슬림 + analyze 브리지 정리

**`DiagnosisState` TypedDict 제거 키**:
- `disease_name`, `confidence`, `is_healthy_prob`, `top_candidates` (Plant.id 잔재)
- `fallback_plant_name`, `plant_filter_mode` ([1-8] 미루기 처리분)
- `description` (사용처 0 확인 후. 1+개면 보존하고 보고)

**유지 키**:
- `plant_name` (analyze가 채움, RAG·generate 입력)
- `plant_name_korean`, `plant_confidence`, `alt_candidates`, `visual_description`, `observed_symptoms` ([1-5]서 추가)
- `keywords`, `keywords_en`, `rag_query`, `rag_docs`, `sick_keys`, `rag_doc_sick_pairs`, `rag_failed`, `rag_no_docs`, `rag_weak_evidence`, `structured_result`
- `image_bytes` 등 입력 키

**analyze 노드 브리지 정리**:

```python
# Before (analyze_node wrapping closure 안)
bridged = {
    **out,
    "description": out["visual_description"],
    "disease_name": None,
    "confidence": None,
    "is_healthy_prob": None,
    "top_candidates": [],
}

# After
bridged = {
    **out,
    # description 사용처 0이면 줄도 제거. 1+개면 보존하고 보고.
}
```

`description = visual_description` 매핑 줄은 description 사용처 grep 결과 따라 결정. Plant.id 키 4개(`disease_name` 등)는 모두 제거.

**graph.py 내 다른 변경 없음** — keyword_node·retrieve_node·generate_node 본체 무변경.

#### C. `app/main.py` — 초기 state slim + 응답 매핑 재작성

**L186-207 초기 state dict 슬림** (LangGraph InvalidUpdateError 방지 핵심):

```python
# Before (예시 — 정확 라인은 view 후 확정)
out = await graph.ainvoke({
    "image_bytes": image_bytes,
    "plant_filter_mode": "strict",
    "plant_name": None,
    "plant_name_korean": None,
    "plant_confidence": None,
    "alt_candidates": [],
    "visual_description": "",
    "observed_symptoms": [],
    "disease_name": None,
    "confidence": None,
    "is_healthy_prob": None,
    "top_candidates": [],
    "description": "",
    "keywords": [],
    "rag_query": "",
    "fallback_plant_name": None,
    "rag_docs": [],
    ...
    "structured_result": {},
})

# After — 제거 키들 일괄 삭제
out = await graph.ainvoke({
    "image_bytes": image_bytes,
    "plant_name": None,
    "plant_name_korean": None,
    "plant_confidence": None,
    "alt_candidates": [],
    "visual_description": "",
    "observed_symptoms": [],
    # description은 사용처 grep 결과 따라
    "keywords": [],
    "rag_query": "",
    "rag_docs": [],
    ...
    "structured_result": {},
})
```

**L227-251 응답 매핑 재작성**:

```python
# Before (예시 — 정확 라인 view 후 확정)
_tc = out.get("top_candidates") or []
_cand: list[PlantCandidateItem] = []
for item in _tc:
    if isinstance(item, dict):
        try:
            _cand.append(PlantCandidateItem.model_validate(item))
        except ValidationError:
            continue
pid = PlantIdentificationResult(
    plant_name=out.get("plant_name"),
    disease_name=out.get("disease_name"),
    confidence=out.get("confidence"),
    is_healthy_prob=out.get("is_healthy_prob"),
    top_candidates=_cand,
)
dbg: DiagnosisDebug | None = None
if return_debug:
    dbg = DiagnosisDebug(
        keywords=list(out.get("keywords") or []),
        sick_keys=list(out.get("sick_keys") or []),
    )

sr = out.get("structured_result")
if not isinstance(sr, dict) or not sr:
    sr = model_utils.default_structured_fallback()

return DiagnosisResponse(
    message="diagnosis complete",
    plant_id=pid,
    structured_result=sr,
    debug=dbg,
)

# After
analysis = AnalysisResult(
    plant_name=out.get("plant_name"),
    plant_name_korean=out.get("plant_name_korean"),
    plant_confidence=out.get("plant_confidence"),
    alt_candidates=list(out.get("alt_candidates") or []),
    visual_description=str(out.get("visual_description") or ""),
    observed_symptoms=list(out.get("observed_symptoms") or []),
)

sr = out.get("structured_result")
if not isinstance(sr, dict) or not sr:
    sr = model_utils.default_structured_fallback()

return DiagnosisResponse(
    message="diagnosis complete",
    analysis=analysis,
    structured_result=sr,
)
```

**부수 정리**:
- `PlantIdentificationResult`·`PlantCandidateItem`·`DiagnosisDebug` import 제거
- `AnalysisResult` import 추가
- `return_debug` 파라미터 — `dbg` 변수가 사라지니 호출처에서도 미사용. 함수 시그니처 유지(API 호환)하되 함수 본체에서 무시. 또는 grep 결과 따라 시그니처에서 함께 제거. 보고 권장.
- `ValidationError` import — 다른 사용처 없으면 제거.

#### D. `app/model_utils.py` — 잔재 정리 (있으면)

**`default_structured_fallback`·`generate_structured_diagnosis_with_gpt`** 본체에서 `disease_name`·`confidence`·`is_healthy_prob`·`top_candidates` 참조 잔재가 있는지 grep으로 확인. 있으면 제거.

**절대 손대지 않음**:
- `rag_failed=True` 분기 — 영역 4 [1-10]
- `REQUIRED_RAG_FAILED_PHRASE` 상수 — 영역 4 [1-10]
- `STRUCTURED_DIAGNOSIS_RAG_FAILED_*` 프롬프트 호출 — 영역 4 [1-10]
- `normalize_structured_result`의 `rag_failed` 파라미터 — 영역 4 [1-10]

#### E. `scripts/run_eval.py` L59-82 — 초기 state dict 슬림

C와 동일한 키 제거. 측정 스크립트가 `out.get("plant_name")` 등 graph state 직접 read하는 부분은 무변경 (sub-object화는 응답 표면만 영향, state는 그대로).

#### F. `scripts/eval_rag.py` L57~,L91 — 초기 state dict 슬림

C·E와 동일한 키 제거.

#### G. `tests/` — schema 참조 동반 갱신

사전 grep에서 잡힌 테스트가 `PlantIdentificationResult`·`PlantCandidateItem`·`DiagnosisDebug`·제거 키를 mock하거나 검증하면 동반 갱신. 단위 테스트 다수 무영향 예상(스키마 직접 검증은 적음).

### 3.2 프론트엔드 변경

#### A. `types/diagnosis.ts` — 응답 타입 재구성

**삭제**:
- `PlantIdResult` 인터페이스 (L6-12 추정)
- `DiagnosisResponse.plant_id` 필드 (L24 추정)

**신설**:
- `AnalysisResult` 인터페이스 (6필드, 백 `AnalysisResult` 모델과 일관)
- `DiagnosisResponse.analysis: AnalysisResult | null`

`DiagnosisDebug` 관련 타입은 조사상 프론트에 없음 — 변경 0.

#### B. `components/ResultView.tsx` — 매핑 변경 + 死 코드 제거

**L17 (식물명 소스 교체)**:

```tsx
// Before
{result.plant_id.plant_name}

// After
{result.analysis?.plant_name_korean ?? result.analysis?.plant_name ?? "식물명 미식별"}
```

한국어 통명 우선, 없으면 학명, 없으면 안내 텍스트. 정확한 위치·표현은 view 후 일관성 확보.

**L56-57 (meta 표시 라인 제거)**:

```tsx
// Before
신뢰도: {percent(result.plant_id.confidence)}
건강 확률: {percent(result.plant_id.is_healthy_prob)}

// After
// 두 줄 통째 삭제 (confidence·is_healthy_prob 백엔드에서 사라짐)
```

대체 표현으로 `plant_confidence` ("식별 신뢰도: 높음/보통/낮음")를 띄울지는 [1-10] UX 결정. **본 작업에서는 두 줄 삭제만**.

**L9-14 (percent 헬퍼 무용화)**:

```tsx
// Before
function percent(v: number | null | undefined): string { ... }

// After
// 함수 통째 삭제. 사용처 0 됨(영역 6 사전 grep으로 확인).
```

ResultView 다른 부분(폴백 텍스트·structured_result 매핑) **그대로 보존** — 영역 5 [1-10].

### 3.3 변경 금지 (범위 외, [1-10] 또는 후속)

다음은 절대 손대지 않음:

**영역 4 [1-10]**:
- `app/model_utils.generate_structured_diagnosis_with_gpt`의 `rag_failed=True` 분기 본체
- `app/model_utils.REQUIRED_RAG_FAILED_PHRASE` 상수
- `app/prompts.STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM`·`_USER_TEMPLATE`
- `app/main.py`의 rag_failed 응답 분기(있으면)
- `lib/api.ts` L12-23 502 catch 경로
- `pages/index.tsx` L49-52, L91 에러 UI 로직

**영역 5 [1-10]**:
- `components/ResultView.tsx`의 폴백 텍스트 톤 ("요약 정보 없음", "추가 진단 필요")
- `model_utils.default_structured_fallback`의 안내 메시지 내용

**[1-10] Plant.id 함수 완전 제거 영역**:
- `app/model_utils`의 `identify_plant_disease_api`·`fetch_plant_identification_json`·`get_plant_id_api_key`·`get_plant_id_health_mode`·`format_top_candidates_for_prompt`·`format_is_healthy_for_prompt`·`parse_identification_response` 등
- `app/main.py`의 `httpx.HTTPStatusError as e: logger.warning("Plant.id HTTP 오류")` catch
- `.env`의 `PLANT_ID_API_KEY` reader
- `scripts/test_plant_id.py`

**B 묶음(데이터셋 교체)**:
- RAG 가중치 상수 (`GENERIC_DOC_PENALTY`, `PLANT_NAME_MATCH_BOOST`, NCPMS 0.8, UC_IPM 0.85)

**배포 영역**:
- `BACKEND_API_URL` env
- docker-compose

위 중 하나라도 변경 필요 판단되면 **작업 중단 후 보고**.

---

## 4. 검증

### 4.1 정적

```bash
# Python import 끊김 없는지
python -c "from app.main import app; from app.schemas import AnalysisResult, DiagnosisResponse; print('ok')"
python -c "from app.graph import build_diagnosis_graph; print('ok')"

# 제거된 심볼 import 안 되는지
python -c "from app.schemas import PlantIdentificationResult" 2>&1 | grep -i error
# 기대: ImportError

# 단위·통합 테스트
pytest tests/ -v
```

테스트가 schema mock에서 깨지면 mock 코드 동반 갱신(영역 G).

### 4.2 프론트 정적

```bash
# TypeScript 컴파일 (Next.js 빌드 또는 tsc --noEmit)
npx tsc --noEmit
# 또는 next dev 띄워서 진단 화면 한 번 통과시켜 화면 깨짐 없는지 확인
```

### 4.3 측정 (게이트 판정용)

**Dry run 1회** (게이트 측정 전):

```bash
RUN_EVAL_OUT=after_phase1_state_dry.json python scripts/run_eval.py --limit 1
# 또는 동등한 1장 측정 옵션. run_eval.py가 응답 매핑 변경 영향 안 받는지 확인.
```

LangGraph 채널 에러나 응답 매핑 에러 발생하면 즉시 중단·보고.

**본 측정 2회**:

```bash
RUN_EVAL_OUT=after_phase1_state_run1.json python scripts/run_eval.py
RUN_EVAL_OUT=after_phase1_state_run2.json python scripts/run_eval.py
```

산출물: `eval/after_phase1_state_run1.json`, `eval/after_phase1_state_run2.json`.

---

## 5. 게이트 ([1-7.5] 평균 대비 -5%p 이내, 2차 회귀 게이트 🔴)

| 지표 | [1-7.5] | [1-8] | [1-9] 게이트 (≥) | 미달 시 |
|---|---|---|---|---|
| plant_korean | 89.9% | 90.0% | 84.9% | revert |
| recall | 100% | 100% | 95% | revert |
| precision | 23.8% | 23.81% | 18.8% | revert |
| accuracy | 51.5% | 51.52% | 46.5% | revert |
| JSON | 100% | 100% | 100% 절대 | revert |
| latency | 21.4s | 21.09s | 무변경/± | 게이트 외 |

**예상**: 백엔드 동작 무변경(state·schema 정리만, LLM·RAG·프롬프트 무변경) → 회귀 0 예상. 측정값이 [1-8]과 비트 단위 동일이거나 매우 가깝게 나와야 정상.

만약 회귀가 잡히면:
- 측정 스크립트 매핑 회귀일 가능성 우선 의심 (응답 sub-object화 영향)
- 실제 동작 회귀는 매우 드묾 — 발생 시 케이스별 비교

---

## 6. 롤백 전략

게이트 미통과 또는 화면 깨짐 시:

1. **즉시 `git revert HEAD`** — 단일 커밋이라 1회 revert로 [1-8] 상태(db7906b) 복원. 백·프론트 동시 복원.
2. 원인 진단:
   - 어떤 지표가 얼마나 회귀했는지
   - 결정적(run1==run2)인지 비결정적인지
   - 백엔드 동작 회귀인지 측정 스크립트 매핑 회귀인지 — run_eval.py 변경 부분 우선 의심
   - 프론트 화면 깨짐이면 매핑 케이스별 식별(ResultView·types)
3. 분기:
   - 측정 스크립트 회귀 → 스크립트만 패치 후 재커밋
   - 매핑 회귀 → 영역 3 옵션 재검토 (top-level 평면 A로 갈아탈지)
   - 게이트 미통과 동작 회귀 → 매우 드묾, 케이스 분석 후 부분 revert 또는 [1-9] 영구 보류

---

## 7. 작업 완료 후 보고 (사용자에게 다음을 정리)

### 7.1 사전 grep 결과 표

| 검색 대상 | 발견 위치 | 처리 |
|---|---|---|
| `disease_name` | (위치) | 영역 1·2 제거 |
| `is_healthy_prob` | (위치) | 영역 1·2 제거 |
| `top_candidates` | (위치) | 영역 1·2 제거 |
| `confidence` | (위치) | 영역 1·2 제거 |
| `fallback_plant_name`·`plant_filter_mode` | (위치) | 영역 1 제거 |
| `description` | (위치) | **분기 결과 명시: [1-9] 제거 / [1-10] 미룸** |
| `PlantIdentificationResult`·`PlantCandidateItem` | (위치) | 영역 2 제거 |
| `DiagnosisDebug`·`return_debug` | (위치) | 영역 8.1 제거 |
| `rag_failed`·`REQUIRED_RAG_FAILED_PHRASE`·`STRUCTURED_DIAGNOSIS_RAG_FAILED` | (위치) | **보존**(영역 4 [1-10]). 위치만 기록 |
| 프론트 `plant_id`·`PlantIdResult`·`is_healthy_prob` 등 | (위치) | 영역 3·6 매핑 변경 |
| `percent()` | (위치·사용처) | 사용처 0 확인 → 제거 |

### 7.2 변경 통계

```bash
git diff --stat
```

라인 추가/삭제 수, 변경 파일 목록.

### 7.3 description 처리 결과

`description` 사용처 grep 결과 명시. [1-9]에서 제거했는지 / [1-10] 미뤘는지 + 근거.

### 7.4 측정 결과 표

| 지표 | [1-7.5] avg | [1-8] | [1-9] run1 | [1-9] run2 | [1-9] avg | 게이트 | 판정 |
|---|---|---|---|---|---|---|---|
| plant_korean | 89.9% | 90.0% | ? | ? | ? | ≥84.9% | ✅/❌ |
| recall | 100% | 100% | ? | ? | ? | ≥95% | ✅/❌ |
| precision | 23.8% | 23.81% | ? | ? | ? | ≥18.8% | ✅/❌ |
| accuracy | 51.5% | 51.52% | ? | ? | ? | ≥46.5% | ✅/❌ |
| JSON | 100% | 100% | ? | ? | ? | 100% | ✅/❌ |
| latency | 21.4s | 21.09s | ? | ? | ? | 게이트 외 | 참고 |

결정적/비결정적 여부 명시. 동작 무변경이라 비트 단위 동일 기대.

### 7.5 발견한 추가 死 코드 (있으면)

영역 1·2·8.1 외에 grep으로 잡힌 잔재(`format_is_healthy_for_prompt`·`format_top_candidates_for_prompt` 등 Plant.id 보조 함수)가 더 있으면 목록. **[1-9]에서 처리한 것 / [1-10]으로 미룬 것** 분리 보고.

### 7.6 프론트 화면 깨짐 없는지 확인

`next dev` 또는 `next build`로 진단 화면 정상 동작 확인 결과 보고.

### 7.7 커밋 메시지 (제안, push 전 사용자 확정)

```
refactor: state/schema 슬림화, Plant.id 응답 잔재 제거 + 프론트 매핑 동시 ([1-9])

백엔드:
- DiagnosisState 죽은 키 제거 (disease_name·confidence·is_healthy_prob·top_candidates·
  fallback_plant_name·plant_filter_mode[·description])
- schemas.py: PlantIdentificationResult·PlantCandidateItem·DiagnosisDebug 삭제
- schemas.py: AnalysisResult 신설, DiagnosisResponse 재구성 (plant_id 제거, analysis 추가, debug 제거)
- app/main.py: 초기 state slim + 응답 매핑 재작성 (PlantIdentificationResult → AnalysisResult)
- scripts/run_eval.py·scripts/eval_rag.py: 초기 state dict slim
- app/graph.py: analyze 브리지에서 Plant.id 키 4개 제거

프론트:
- types/diagnosis.ts: PlantIdResult 제거, AnalysisResult 신설, DiagnosisResponse 재구성
- components/ResultView.tsx: plant_id 매핑 → analysis.plant_name_korean, percent() 헬퍼 제거,
  confidence·is_healthy_prob meta 라인 제거

범위 외 (보존):
- rag_failed 활성 LLM 경로·REQUIRED_RAG_FAILED_PHRASE·STRUCTURED_DIAGNOSIS_RAG_FAILED 프롬프트 → [1-10]
- ResultView 폴백 톤, lib/api.ts 502 catch, pages/index.tsx 에러 UI → [1-10]
- Plant.id 함수 본체(identify_plant_disease_api 등) → [1-10]
- RAG 가중치 → B 묶음(데이터셋 교체)

measurement: eval/after_phase1_state_run{1,2}.json
gate: -5%p 이내 회귀 없음 (2회 평균 [1-7.5]/[1-8] 대비, 동작 무변경 기대)
```

### 7.8 커밋·push (사용자 확정 후)

```bash
git add app/schemas.py app/graph.py app/main.py
git add app/model_utils.py    # 잔재 정리 있으면
git add scripts/run_eval.py scripts/eval_rag.py
git add tests/                # 동반 갱신 있으면
git add types/diagnosis.ts components/ResultView.tsx
git add eval/after_phase1_state_run1.json eval/after_phase1_state_run2.json
git add docs/work_history/    # 진단·작업프롬프트 md (사용자가 박을 경우)
git status                    # untracked 0 최종 확인 ([1-2.5] 교훈)
git commit -m "..."
git push
```

**중요**: `git status`에서 untracked·미스테이징 0 확인 후 push. 모노레포 단일 커밋이라 백·프론트 동시 푸시되어야 중간 상태 깨짐 방지.

---

## 8. 작업 순서 요약

1. **사전 확인** (§2) — git·grep·view. 환경 이상 시 즉시 중단·보고.
2. **백엔드 변경** §3.1 — `schemas.py` → `graph.py` → `main.py` → `model_utils.py`(잔재) → `scripts/` 순서 권장 (의존성 흐름).
3. **프론트엔드 변경** §3.2 — `types/diagnosis.ts` → `components/ResultView.tsx`.
4. **정적 검증** §4.1·4.2 (Python import·pytest·tsc). 실패 시 즉시 중단·보고.
5. **Dry run 1회** §4.3 — LangGraph 채널 에러 사전 차단.
6. **측정 2회** §4.3.
7. **게이트 판정** §5. 미통과 시 §6 롤백.
8. **보고** §7 — 사용자 확정 대기.
9. 사용자 OK 후 **커밋·push** §7.8.

---

## 9. 주의 사항 (재강조)

- **LangGraph InvalidUpdateError**: state TypedDict에서 제거한 키를 초기 state dict에 남겨두면 런타임 에러. 4곳(main.py·run_eval.py·eval_rag.py·graph.py analyze 브리지) 모두 동기화 필수.
- **rag_failed 보존**: 영역 4·5 [1-10] 미루기. 진단 md에 박혔던 "[1-7]에서 이미 제거됨" 가정은 **틀렸음** — Claude Code 사전 조사에서 활성 LLM 경로로 확인됨. 본 작업에서 절대 손대지 않음.
- **백·프론트 동시 단일 커밋**: 모노레포라 중간 상태에서 화면 깨짐 방지. 백엔드만 먼저 커밋·푸시 절대 금지.
- **측정 무변경 기대**: 동작 변화 없는 작업이라 [1-8]과 비트 단위 동일이거나 매우 가까워야 정상. 회귀가 잡히면 측정 스크립트 매핑 버그 우선 의심.
