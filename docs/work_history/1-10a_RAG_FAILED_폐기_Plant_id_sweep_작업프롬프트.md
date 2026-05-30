# [1-10a] RAG_FAILED 폐기 + Plant.id sweep + 잔재 정리 — 작업 프롬프트

> Claude Code 의뢰용. A 묶음 마무리의 코드 정리 자리. [1-10b] temperature 튜닝·최종 측정·문서 갱신은 별도 작업으로 분리.
>
> 결정 확정: 영역 1 B (2단 분할 첫 자리) / 영역 2 A (200+백엔드 정적 안내) / 영역 3 A (Plant.id sweep 일괄) / 영역 4·5는 [1-10b].

---

## 1. 컨텍스트 (한 줄)

[1-9] 후속(db7906b 다음 푸시 완료) → **[1-10a] 코드 정리 단일 커밋**. RAG_FAILED 활성 LLM 경로 폐기(decision #3 실행) + Plant.id 함수·env·docs 완전 제거 + [1-9]서 미룬 description·`disease_name` read 잔재 정리. 백·프론트 동시 모노레포 단일 커밋.

핵심 성격:
- **RAG_FAILED 폐기 = 동작 변화** — 활성 LLM 경로 1개 사라지고 정적 안내로 대체. 다만 평가셋 33장에서 `rag_failed=True` 케이스 거의 0건일 가능성 큼 → 측정 영향 매우 작음.
- **Plant.id 함수 sweep = 동작 무변경** — 이미 호출처 0([1-5] 와이어링 후). 死 코드만 제거.
- **잔재 정리 = 동작 무변경** — description·`disease_name` read 모두 None 반환이라 동작 동일.
- **모노레포 단일 커밋** — [1-9] 패턴 그대로.

원칙:
- **변수 격리** — temperature·최종 측정은 [1-10b]. 본 작업에서 절대 손대지 않음.
- **死 코드 발견 즉시 제거** — 영역 외 추가 잔재 발견 시 [1-10a] 커밋에 묶기.
- **2회 측정 평균만 판정** — 단일 run으로 게이트 통과 선언 금지.

---

## 2. 사전 확인 (작업 시작 전 필수)

### 2.1 환경

```bash
git status              # 작업 트리 clean 확인
git log -1 --oneline    # HEAD가 [1-9] 푸시 커밋인지 확인
git branch --show-current
```

작업 트리 dirty이거나 HEAD가 예상과 다르면 **즉시 멈추고 보고**.

### 2.2 grep 검증

```bash
# RAG_FAILED 분기 — 본 작업 제거 대상
grep -rn "rag_failed" app/ tests/
grep -rn "REQUIRED_RAG_FAILED_PHRASE" app/ tests/
grep -rn "STRUCTURED_DIAGNOSIS_RAG_FAILED" app/ tests/
grep -rn "default_structured_fallback" app/ tests/

# Plant.id 함수 sweep — 본 작업 제거 대상
grep -rn "identify_plant_disease_api\|fetch_plant_identification_json" app/ scripts/ tests/
grep -rn "get_plant_id_api_key\|get_plant_id_health_mode" app/ scripts/ tests/
grep -rn "format_top_candidates_for_prompt\|format_is_healthy_for_prompt" app/ scripts/ tests/
grep -rn "parse_identification_response\|_parse_identification_json" app/ scripts/ tests/
grep -rn "PLANT_ID_IDENTIFICATION_URL\|PLANT_ID_API_KEY" app/ scripts/ tests/ .env.example README.md docs/

# 잔재 정리
grep -rn "disease_name" app/graph.py    # retrieve_node의 read 3곳 ([1-9] 보고: L384,395,418)
grep -rn "\bdescription\b" app/ scripts/ tests/    # [1-9]서 보존된 곳 (generate_node 폴백·eval_rag.py:91)

# 프론트 영향
grep -rn "502\|HTTPStatusError" lib/ pages/ components/
grep -rn "요약 정보 없음\|추가 진단 필요" components/ pages/ lib/
```

**판정 가이드**:
- `rag_failed`: 본 작업에서 분기 본체·인자·전용 프롬프트 호출 모두 제거. **단 graph state·retrieve_node의 `rag_failed` 플래그 자체는 보존** (시스템 예외 발생을 알리는 신호로 유지, generate_node에서 분기만 정리).
- `default_structured_fallback`: `rag_failed=True` 분기에 정적 안내 텍스트(영역 2 A)를 박는 위치. 단순 제거 아님 — **재작성**.
- Plant.id 함수들: 사용처 0 확인 후 sweep. 호출처 발견 시 즉시 보고.
- `disease_name` read: [1-9] 보고에 박힌 그대로 ([1-9] 작업프롬프트 §3.1.B "retrieve_node 본체 무변경"으로 보존된 잔재). 본 작업에서 정리.
- `description`: [1-9]서 사용처 살아있음으로 보존됨. 본 작업에서 정리 — 사용처 정리 후 키 제거.

### 2.3 view (구조 파악)

```
app/model_utils.py          (전체 — generate_structured_diagnosis_with_gpt·default_structured_fallback·Plant.id 함수군)
app/prompts.py              (STRUCTURED_DIAGNOSIS_RAG_FAILED_* 위치)
app/graph.py                (retrieve_node L384·395·418 disease_name read, generate_node L626 description 폴백, DiagnosisState)
app/main.py                 (Plant.id HTTPStatusError catch, 초기 state dict)
scripts/run_eval.py         (초기 state dict)
scripts/eval_rag.py         (초기 state dict + L91 description read)
lib/api.ts                  (전체 — 502 catch L12-23)
pages/index.tsx             (L49-52, 91 에러 catch)
components/ResultView.tsx   (전체 — 폴백 톤)
.env.example                (PLANT_ID_API_KEY 라인)
README.md                   (Plant.id 관련 언급 전체)
```

---

## 3. 작업 항목

### 3.1 백엔드 — RAG_FAILED 폐기 (영역 4·5 [1-10] 동행분)

#### A. `app/model_utils.py`

**`generate_structured_diagnosis_with_gpt` 재구성**:

```python
# Before (활성 LLM 경로)
if rag_failed:
    user = prompts.STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_USER_TEMPLATE.format(...)
    system = prompts.STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM
    # ... LLM 호출 ...
else:
    # 정상 경로
    ...

# After
if rag_failed:
    # LLM 호출 폐기 (decision #3). 정적 안내로 즉시 반환.
    return default_structured_fallback(rag_failed=True)
# 정상 경로만 진행
```

**`default_structured_fallback` 재작성** (영역 5 A — 백엔드 정적 안내):

```python
def default_structured_fallback(*, rag_failed: bool = False) -> dict[str, Any]:
    if rag_failed:
        return {
            "summary": "근거 자료가 부족해 정확한 진단을 제시하기 어려워요. 사진을 다시 촬영하거나 환경을 점검해 보세요.",
            "current_state": "이미지의 관찰 묘사만으로는 상태를 단정하기 어렵습니다.",
            "cause": "참고할 수 있는 근거 자료가 충분하지 않아 원인을 특정하기 어렵습니다.",
            "action_plan": [
                "환경(빛·물·통풍·습도)을 점검해 주세요.",
                "잎의 변화를 며칠 더 관찰한 뒤 다시 촬영해 주세요.",
            ],
            "status": "병해 의심",  # 안전망 — 사용자 점검 행동 유도
        }
    # 비-rag_failed 분기는 [1-7] 결정 유지 (status="병해 의심" 등)
    return {
        "summary": "...",  # 기존 텍스트 유지
        ...
    }
```

정확한 안내 텍스트는 사용자 결정 영역. **위 안내 텍스트는 초안** — 사용자가 톤·문구 조정 권장. 보고에 박힌 안내 텍스트 그대로 사용자 검토.

**`normalize_structured_result` 정리**:
- `rag_failed` 인자가 살아있으면 제거 또는 무시 처리 (사전 grep 결과 따라).

**상수·헬퍼 제거**:
- `REQUIRED_RAG_FAILED_PHRASE` 상수 → 제거
- `STRUCTURED_DIAGNOSIS_RAG_FAILED_*` 프롬프트 호출 → 제거

#### B. `app/prompts.py`

**상수 통째 삭제**:
- `STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM`
- `STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_USER_TEMPLATE`

#### C. `app/main.py`

`rag_failed` 응답 처리 잔재가 있으면 정리. **단 graph state의 `rag_failed` 플래그 자체는 보존** (retrieve_node가 박는 플래그는 generate_node가 위 분기로 처리하니 외부 응답 처리엔 영향 없음 예상). 사전 grep으로 main.py에 rag_failed 참조 있으면 분기 정리.

### 3.2 백엔드 — Plant.id 함수 sweep (영역 3)

#### A. `app/model_utils.py` 제거 대상

함수 (sweep 일괄):
- `identify_plant_disease_api`
- `fetch_plant_identification_json`
- `get_plant_id_api_key`
- `get_plant_id_health_mode`
- `format_top_candidates_for_prompt`
- `format_is_healthy_for_prompt`
- `parse_identification_response`
- `_parse_identification_json`

상수·URL:
- `PLANT_ID_IDENTIFICATION_URL`

기타 헬퍼 발견 시 동반 제거.

#### B. `app/main.py`

```python
# 제거 대상
except httpx.HTTPStatusError as e:
    logger.warning("Plant.id HTTP 오류: %s", e)
    raise HTTPException(
        status_code=502,
        detail=f"Plant.id API 오류: {e.response.status_code}",
    ) from e
```

- `httpx.HTTPStatusError` catch 블록 통째 제거
- `import httpx`는 다른 사용처(`AsyncClient`) 있으면 유지, 없으면 제거
- 헬스 엔드포인트(`/health`)에 Plant.id 의존 있으면 정리 — 사전 grep으로 확인

#### C. `app/graph.py`·`scripts/`·`tests/`

- `build_diagnosis_graph(client, vision_provider)`의 `client: httpx.AsyncClient` 의존 — Plant.id 외 사용처가 있는지 확인. 없으면 시그니처에서 제거. 있으면 (예: RAG 검색 HTTP 호출) 유지.
- tests/에서 Plant.id 함수 mock하는 테스트가 있으면 통째 제거.

#### D. `.env.example`·`README.md`

```bash
# .env.example 제거 대상
PLANT_ID_API_KEY=...
PLANT_ID_HEALTH=...   # 있으면

# README.md 정리 대상
- "한 번 진단에 외부 API를 7회(Plant.id·OpenAI×6) 호출" → "외부 API 4회(Gemini·OpenAI 3회)"
- "(현재) Plant.id API 키 — /health 엔드포인트 호환용" 줄 통째 제거
- 기타 Plant.id 언급
```

README의 정확한 갱신 분량은 [1-10b](문서 갱신)에서 마무리. **본 작업에서는 잘못된 정보(7회 호출, Plant.id 의존) 즉시 정정 수준만**.

#### E. `scripts/test_plant_id.py`

**통째 삭제** (`git rm scripts/test_plant_id.py`).

### 3.3 백엔드 — 잔재 정리

#### A. `app/graph.py` retrieve_node의 `disease_name` read 제거

```python
# Before (L384, 395, 418 — [1-9] 보고에서 발견)
dn = state.get("disease_name")
# ...
state.get("disease_name"),  # logger.info 인자
# ...
"disease_name=%r ..."  # log format
```

3곳 모두 정리. `dn` 변수 사용처 함께 따라가서 제거. 로그 포맷 문자열도 `disease_name` 부분 제거.

#### B. `app/graph.py` `description` 키 사용처 정리

- `generate_node` L626 — `state.get("description")` 폴백 read. `visual_description` 직접 사용으로 전환 또는 줄 제거(사용처 사전 grep 따라).
- `DiagnosisState` TypedDict에서 `description` 키 제거.

#### C. 초기 state dict 동기화 ([1-9]·LangGraph InvalidUpdateError 패턴 동일)

`description` 키 제거 동기화 — 4곳:
- `app/main.py` 초기 state dict
- `scripts/run_eval.py` 초기 state dict
- `scripts/eval_rag.py` L57~ 초기 state dict + L91 description read 정리
- `app/graph.py` analyze 노드 브리지에 description 매핑 잔존 있으면 제거

### 3.4 프론트엔드 변경

#### A. `lib/api.ts:12-23` — 502 catch 단순화

RAG 실패가 200으로 전환됨. 502는 다른 진짜 에러(서버 다운·네트워크)만:

```typescript
// Before — RAG 실패 시 errorBody.detail 매핑 경로
if (!response.ok) {
    const errorBody = await response.json();
    throw new Error(errorBody.detail || '진단 요청 실패');
}

// After — 단순화 (RAG 실패 200으로 갈아탔으니 detail 매핑 경로 단순)
if (!response.ok) {
    throw new Error(`진단 요청 실패 (${response.status})`);
}
```

정확한 형태는 view 후 결정. 핵심: 502 케이스가 줄어드니 catch 단순화.

#### B. `pages/index.tsx:49-52,91` — 에러 UI 단순화

502 안 옴 → catch→setError→home 복귀 로직에서 RAG 실패 시나리오 제거. 정확한 변경 범위 view 후 결정.

#### C. `components/ResultView.tsx` — 폴백 톤 조정

기존 폴백("요약 정보 없음", "추가 진단 필요")은 빈 structured_result에 대한 폴백인데, 이제 백엔드가 안내 텍스트 채워서 보내니 폴백이 호출되는 케이스가 거의 0. 다만 안전망 톤 정직하게:

```tsx
// Before
summary: result.structured_result.summary || "요약 정보 없음",
action_plan: result.structured_result.action_plan || ["추가 진단 필요"],

// After (제안 — 정확한 톤은 사용자 결정)
summary: result.structured_result.summary || "진단 정보가 없어요.",
action_plan: result.structured_result.action_plan || ["환경 점검 후 다시 촬영해 주세요."],
```

폴백 텍스트는 사용자 결정 영역. **위 텍스트는 초안** — 보고에 박은 후 사용자 검토.

### 3.5 변경 금지 (범위 외)

다음은 절대 손대지 않음:

**[1-10b] 영역**:
- `app/vision/gemini.py` temperature 설정
- `app/model_utils.generate_structured_diagnosis_with_gpt`의 GPT temperature
- 1단계 최종 measurement 산출 (`eval/after_phase1.json`)
- `docs/refactoring_log.md` 1단계 전체 정리
- `README.md` 진행 현황·"무엇을 만들고 있나" 큰 정리 (잘못된 정보 즉시 정정 외)

**B 묶음(데이터셋 교체) 영역**:
- RAG 가중치 (`GENERIC_DOC_PENALTY`·`PLANT_NAME_MATCH_BOOST`·NCPMS 0.8·UC_IPM 0.85)
- 벡터 DB 컬렉션 자체 (`data/vector_db/`)

**배포 영역**:
- `BACKEND_API_URL` env
- docker-compose

**유지 영역**:
- `rag_failed` graph state 플래그 자체 (retrieve_node가 박는 신호 — generate_node 분기 폐기로 충분, 플래그 자체는 보존)
- `rag_no_docs`·`rag_weak_evidence` 플래그 (별도 신호)
- analyze·keyword·retrieve 노드 본체 (변경 0)

위 중 하나라도 변경 필요 판단되면 **작업 중단 후 보고**.

---

## 4. 검증

### 4.1 정적

```bash
# Python import 끊김 없는지
python -c "from app.main import app; print('ok')"
python -c "from app.graph import build_diagnosis_graph; print('ok')"
python -c "from app.model_utils import default_structured_fallback; print('ok')"

# 제거된 심볼 import 안 되는지
python -c "from app.model_utils import identify_plant_disease_api" 2>&1 | grep -i error
# 기대: ImportError
python -c "from app.prompts import STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM" 2>&1 | grep -i error
# 기대: ImportError

# 단위·통합 테스트
pytest tests/ -v
```

테스트가 Plant.id 함수 mock하면 동반 제거.

### 4.2 프론트 정적

```bash
npx tsc --noEmit
```

### 4.3 측정 (게이트 판정용)

**Dry run 1회**:

```bash
RUN_EVAL_OUT=after_phase1_cleanup_dry.json python scripts/run_eval.py --limit 1
```

LangGraph 채널 에러·import 에러 사전 차단.

**본 측정 2회**:

```bash
RUN_EVAL_OUT=after_phase1_cleanup_run1.json python scripts/run_eval.py
RUN_EVAL_OUT=after_phase1_cleanup_run2.json python scripts/run_eval.py
```

산출: `eval/after_phase1_cleanup_run1.json`, `eval/after_phase1_cleanup_run2.json`.

---

## 5. 게이트 ([1-9] 평균 대비 -5%p 이내)

| 지표 | [1-9] avg | [1-10a] 게이트 (≥) |
|---|---|---|
| plant_korean | 91.07% | 86.07% |
| recall | 100% | 95% |
| precision | 22.73% | 17.73% |
| accuracy | 48.48% | 43.48% |
| JSON | 100% | 100% 절대 |
| latency | 20.62s | 무변경 또는 ± |

**예상**: 
- 평가셋 33장에서 `rag_failed=True` 케이스가 거의 없을 가능성 큼 → RAG_FAILED 폐기는 측정값 영향 0~미미
- Plant.id sweep·잔재 정리는 동작 무변경 → 측정 영향 0
- 즉 [1-9]와 비트 단위 동일하거나 매우 가깝게 나와야 정상

회귀 잡히면:
- 측정 스크립트 매핑 회귀일 가능성 우선 의심
- 실제 동작 회귀는 매우 드묾 — `description`·`disease_name` 제거가 retrieve·generate에 영향 줬는지 케이스별 확인

---

## 6. 롤백 전략

게이트 미통과 또는 화면 깨짐 시:

1. **즉시 `git revert HEAD`** — 단일 커밋이라 1회 revert로 [1-9] 푸시 상태 복원.
2. 원인 진단:
   - 회귀 결정성 (run1 vs run2)
   - 어느 변경이 원인인지 — RAG_FAILED 폐기 / Plant.id sweep / 잔재 정리 중
   - 백엔드 회귀 vs 프론트 화면 깨짐
3. 분기:
   - 측정 스크립트 회귀 → 스크립트 패치 후 재커밋
   - 잔재 정리 영향(`description` 또는 `disease_name` 제거가 generate·retrieve에 영향) → 해당 잔재만 보존하고 재커밋
   - RAG_FAILED 폐기 영향 → 케이스 분석. 정적 안내 텍스트 톤 조정 또는 일시 보류

---

## 7. 작업 완료 후 보고

### 7.1 사전 grep 결과 표

| 검색 대상 | 발견 위치 | 처리 |
|---|---|---|
| `rag_failed` 분기·상수 | (위치) | 영역 4 폐기 |
| `STRUCTURED_DIAGNOSIS_RAG_FAILED_*` | (위치) | 영역 4 제거 |
| Plant.id 함수군 | (위치) | sweep 일괄 제거 |
| `PLANT_ID_API_KEY` 등 env·docs | (위치) | 정리 |
| `disease_name` read | (위치) | 잔재 정리 |
| `description` 사용처 | (위치) | 정리 |
| 프론트 502·폴백 텍스트 | (위치) | 변경 |

### 7.2 변경 통계

```bash
git diff --stat
```

라인 추가/삭제 수, 변경 파일 목록.

### 7.3 안내 텍스트 변경 보고 (사용자 검토 필요)

**백엔드 `default_structured_fallback(rag_failed=True)` 안내 텍스트**:
- summary: (실제 박은 텍스트)
- current_state: (실제 박은 텍스트)
- cause: (실제 박은 텍스트)
- action_plan: (실제 박은 리스트)
- status: 병해 의심

**프론트 `ResultView` 폴백 텍스트**:
- summary 폴백: (실제 박은 텍스트)
- action_plan 폴백: (실제 박은 리스트)

→ 사용자가 톤·문구 검토 후 OK 또는 조정.

### 7.4 측정 결과 표

| 지표 | [1-9] avg | run1 | run2 | [1-10a] avg | 게이트 | 판정 |
|---|---|---|---|---|---|---|
| plant_korean | 91.07% | ? | ? | ? | ≥86.07% | ✅/❌ |
| recall | 100% | ? | ? | ? | ≥95% | ✅/❌ |
| precision | 22.73% | ? | ? | ? | ≥17.73% | ✅/❌ |
| accuracy | 48.48% | ? | ? | ? | ≥43.48% | ✅/❌ |
| JSON | 100% | ? | ? | ? | 100% | ✅/❌ |
| latency | 20.62s | ? | ? | ? | 게이트 외 | 참고 |

결정적/비결정적 여부 명시. `rag_failed=True` 케이스 발생 건수도 보고(예상 0~소수).

### 7.5 발견한 추가 死 코드 (있으면)

영역 외 잔재 발견 시 목록 + [1-10a]에 묶었는지 / [1-10b] 또는 별도 미뤘는지.

### 7.6 프론트 화면 깨짐 없는지 확인

`next dev` 또는 `next build`로 진단 화면 정상 동작 확인 결과.

### 7.7 커밋 메시지 (제안, push 전 사용자 확정)

```
refactor: RAG_FAILED 폐기 + Plant.id 함수 sweep + 잔재 정리 ([1-10a])

RAG_FAILED 폐기 (영역 4·5, [1-9]서 미룸):
- model_utils.generate_structured_diagnosis_with_gpt의 rag_failed=True 분기 제거
  (활성 LLM 경로 → 정적 안내로 즉시 반환)
- default_structured_fallback(rag_failed=True)에 정직 안내 텍스트 박음
- REQUIRED_RAG_FAILED_PHRASE·STRUCTURED_DIAGNOSIS_RAG_FAILED_* 상수·프롬프트 삭제
- 응답 형태 200 + structured_result에 안내 (decision #3 본의: LLM 호출 0, 정직)
- 프론트 lib/api.ts 502 catch 단순화, pages/index.tsx 에러 UI 단순화
- ResultView 폴백 톤 정직 조정

Plant.id 함수 sweep (영역 3):
- model_utils.py 8개 함수 일괄 제거 (identify_plant_disease_api 등)
- main.py HTTPStatusError catch 제거
- .env.example PLANT_ID_API_KEY 라인 제거
- README.md Plant.id 즉시 정정 (외부 호출 7→4회 등)
- scripts/test_plant_id.py 통째 삭제

잔재 정리 ([1-9]서 미룸):
- graph.py retrieve_node의 disease_name read 3곳 (L384·395·418) 제거
- description 키 사용처(generate_node 폴백·eval_rag.py:91) 정리
- DiagnosisState TypedDict에서 description 제거
- 초기 state dict 동기화 4곳 (LangGraph InvalidUpdateError 방지)

범위 외 (보존, [1-10b]):
- temperature 튜닝, 1단계 최종 measurement, refactoring_log·README 전체 갱신
- rag_failed graph state 플래그 자체 (신호 보존)

measurement: eval/after_phase1_cleanup_run{1,2}.json
gate: -5%p 이내 회귀 없음 (2회 평균 [1-9] 대비, 동작 변화 작음 기대)
```

### 7.8 커밋·push (사용자 확정 후)

```bash
git add app/model_utils.py app/prompts.py app/graph.py app/main.py
git add scripts/run_eval.py scripts/eval_rag.py
git rm scripts/test_plant_id.py
git add .env.example README.md
git add tests/        # 동반 갱신 있으면
git add lib/api.ts pages/index.tsx components/ResultView.tsx types/diagnosis.ts
git add eval/after_phase1_cleanup_run1.json eval/after_phase1_cleanup_run2.json
git add docs/work_history/1-10a_RAG_FAILED_폐기_Plant_id_sweep_작업프롬프트.md
git status            # untracked·미스테이징 0 최종 확인 ([1-2.5] 교훈)
git commit -m "..."
git push
```

---

## 8. 작업 순서 요약

1. **사전 확인** §2 — git·grep·view. 환경 이상 시 즉시 중단·보고.
2. **백엔드 RAG_FAILED 폐기** §3.1 (model_utils → prompts → main). 안내 텍스트는 진단 초안 그대로 박되 보고에서 사용자 검토.
3. **백엔드 Plant.id sweep** §3.2 (model_utils → main → graph → env·docs → scripts).
4. **백엔드 잔재 정리** §3.3 (disease_name read → description 정리 → 초기 state dict 4곳 동기화).
5. **프론트엔드 변경** §3.4 (api.ts → index.tsx → ResultView.tsx). 폴백 텍스트 초안 그대로 박되 보고에서 사용자 검토.
6. **정적 검증** §4.1·4.2 (Python import·pytest·tsc). 실패 시 즉시 중단·보고.
7. **Dry run 1회** §4.3.
8. **측정 2회** §4.3.
9. **게이트 판정** §5. 미통과 시 §6 롤백.
10. **보고** §7 — 사용자 확정 대기.
11. 사용자 OK 후 **커밋·push** §7.8.

---

## 9. 주의 사항 (재강조)

- **`rag_failed` graph state 플래그 보존**: 분기 본체만 제거, 플래그 자체는 유지. retrieve_node가 RAG 시스템 예외 시 박는 신호이며 generate_node가 위 분기로 처리.
- **안내 텍스트 사용자 검토 필수**: 백엔드 `default_structured_fallback`과 프론트 ResultView 폴백 텍스트는 사용자 결정 영역. 초안 박되 보고에서 명시.
- **LangGraph InvalidUpdateError**: `description` 키 제거 시 초기 state dict 4곳 동기화 필수 ([1-9] 패턴 동일).
- **측정 영향 작음 기대**: 평가셋 33장에서 `rag_failed=True` 케이스 0~소수 예상. 회귀가 잡히면 측정 스크립트 매핑 우선 의심.
- **[1-10b] 분리 엄수**: temperature·최종 measurement·문서 전체 갱신은 본 작업에서 절대 손대지 않음.
