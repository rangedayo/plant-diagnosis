# [1-8] retrieve 정비 — 작업 프롬프트

> Claude Code 의뢰용. 사전 확인 → 작업 → 검증 → 게이트 → 보고 흐름. 컨텍스트는 `docs/work_history/1-8_retrieve_정비_진단.md` (6개 영역 모두 A 권장 확정) 참조.

---

## 1. 컨텍스트 (한 줄)

[1-7.5] generate status 경로 정비 후 push 완료(2회 평균 게이트 통과) → **[1-8] retrieve 정비**. 사실상 死 코드 제거 작업. 단일 파일(`app/graph.py`) 중심, 라인 변경 ~50줄.

핵심 원칙:
- **변수 격리** — state TypedDict 변경·main.py 변경·RAG 가중치 변경은 [1-8] 범위 외 (각각 [1-9]·[1-9]·B 묶음).
- **死 코드 발견 즉시 제거** — 영역 5에서 추가 잔재 발견 시 [1-8] 커밋에 묶기.
- **2회 측정 평균만 판정** — 단일 run 결과로 게이트 통과 선언 금지.

---

## 2. 사전 확인 (작업 시작 전 필수)

### 2.1 환경

```bash
git status              # 작업 트리 clean 확인
git log -1 --oneline    # HEAD가 [1-7.5] 커밋인지 확인
git branch --show-current
```

작업 트리가 dirty이거나 HEAD가 예상과 다르면 **즉시 멈추고 보고**.

### 2.2 grep 검증 (사용처 표 작성용)

다음 명령을 순서대로 실행하고 결과를 표로 정리. 결과는 작업 완료 보고에 포함.

```bash
grep -rn "fallback_plant_name" app/ tests/ scripts/
grep -rn "FALLBACK_PLANT_SYSTEM\|FALLBACK_PLANT_USER_TEMPLATE" app/ tests/ scripts/
grep -rn "estimate_fallback_plant_with_gpt" app/ tests/ scripts/
grep -rn "_sanitize_fallback_plant_line" app/ tests/ scripts/
grep -rn "_fallback_hint_words\|_fallback_match_count" app/ tests/ scripts/
grep -rn "FALLBACK_WORD_MATCH_BONUS" app/ tests/ scripts/
grep -rn "plant_filter_mode" app/ tests/ scripts/
grep -rn "_final_plant_name" app/ tests/ scripts/
grep -rn "_build_rag_query" app/ tests/ scripts/
```

**판정 가이드**:
- `fallback_plant_name`: `app/graph.py`·`app/main.py`·`app/schemas.py`(또는 DiagnosisState 정의 위치) 외 발견 시 **즉시 보고**.
- `FALLBACK_PLANT_SYSTEM`·`estimate_fallback_plant_with_gpt`·`_sanitize_fallback_plant_line`: [1-6]에서 제거됐어야 함. 잔재 발견 시 [1-8] 커밋에 묶기(영역 5 A).
- `plant_filter_mode`: `_final_plant_name` 외 사용처 있으면 보고 (분기 의미 재검토 필요).
- `_final_plant_name`·`_build_rag_query`: 호출처 1군데(`retrieve_node`)인지 확인. 추가 호출처 있으면 보고.

---

## 3. 작업 항목

### 3.1 `app/graph.py` 변경 (주 작업)

#### A. `keyword_node` 출력 dict 정리

`"fallback_plant_name": None` 키 제거. 인접한 [1-9] 미루기 주석도 같이 정리.

```python
# Before
out = {
    "rag_query": query_ko,
    "keywords": keywords_ko,
    "keywords_en": keywords_en,
    # [1-9]서 키 자체 제거 예정. 현재는 retrieve의 fallback 참조를
    # 항상 None으로 흘려 보내기 위해 명시.
    "fallback_plant_name": None,
}

# After
out = {
    "rag_query": query_ko,
    "keywords": keywords_ko,
    "keywords_en": keywords_en,
}
```

#### B. `_final_plant_name` 헬퍼 제거

함수 정의 통째 삭제. `retrieve_node` 내 호출처 1군데를 직접 참조로 교체.

```python
# Before (retrieve_node 안)
fn = _final_plant_name(state)

# After
pn_raw = state.get("plant_name")
fn = str(pn_raw).strip() if pn_raw is not None and str(pn_raw).strip() else None
```

`fn`이 그 뒤 어떻게 쓰이는지 확인:
- `retrieve_node` 로그에서 `final_plant_name=%r`로 출력 → 그대로 유지.
- `_apply_plant_filter_after_similarity`에 `final_plant_name=fn` 인자로 전달 → 해당 함수가 `_ = final_plant_name  # 로그·API 호환용` 형태로 무사용 → **해당 인자도 영역 5에서 같이 제거 검토**. 다른 사용처 없으면 시그니처에서 제거.

#### C. `_build_rag_query` 헬퍼 제거

함수 정의 통째 삭제. `retrieve_node` 내 호출처 직접 참조로 교체.

```python
# Before
query_ko = (_build_rag_query(state) or "").strip()

# After
query_ko = (state.get("rag_query") or "").strip()
```

#### D. fallback 매칭 인프라 일괄 제거

다음을 모두 삭제:
- `_fallback_hint_words(fallback: str | None) -> list[str]` 함수
- `_fallback_match_count(doc: str, words: list[str]) -> int` 함수
- `FALLBACK_WORD_MATCH_BONUS` 상수

`_final_rank_score` 시그니처에서 `fallback_words` 파라미터 제거. 본체에서:
- `mc = _fallback_match_count(doc, fallback_words)` 블록 전체 삭제
- `detail["fallback_match_count"]` / `detail["fallback_bonus"]` 필드 삭제

`_apply_plant_filter_after_similarity` 본체에서:
- `fb_raw = state.get("fallback_plant_name")` 삭제
- `fallback_words = _fallback_hint_words(...)` 삭제
- `_final_rank_score(..., fallback_words=fallback_words)` 호출에서 인자 제거
- `if fallback_words: logger.info("retrieve: fallback_words=...")` 블록 삭제

#### E. `retrieve_node` 로그 정리

```python
# Before
logger.info(
    "retrieve: plant_name=%r disease_name=%r fallback_plant_name=%r final_plant_name=%r query_ko=%r query_en=%r",
    pn, dn, state.get("fallback_plant_name"), fn, query_ko, query_en,
)

# After
logger.info(
    "retrieve: plant_name=%r disease_name=%r final_plant_name=%r query_ko=%r query_en=%r",
    pn, dn, fn, query_ko, query_en,
)
```

### 3.2 영역 5 추가 死 코드 정리

사전 grep에서 발견된 추가 잔재가 있을 경우:

- `app/prompts.py`에 `FALLBACK_PLANT_SYSTEM` / `FALLBACK_PLANT_USER_TEMPLATE` 잔재 → 제거
- `app/model_utils.py`에 `estimate_fallback_plant_with_gpt` / `_sanitize_fallback_plant_line` 잔재 → 제거

발견 즉시 [1-8] 커밋에 묶음. 발견 못 하면 보고에 "추가 死 코드 없음" 명시.

### 3.3 변경 금지 (범위 외)

다음은 절대 손대지 않음:

- `DiagnosisState` TypedDict의 `fallback_plant_name` / `plant_filter_mode` 키 → **[1-9] state 슬림화**
- `app/main.py`의 초기 state dict `"fallback_plant_name": None` / `"plant_filter_mode": "strict"` → **[1-9]**
- 프론트(`Next.js`) 영향 코드 → **[1-9]**
- RAG 가중치 상수: `GENERIC_DOC_PENALTY`, `PLANT_NAME_MATCH_BOOST`, NCPMS/UC_IPM 임베딩 가중치 → **B 묶음(데이터셋 교체)**

위 중 하나라도 변경 필요 판단되면 **작업 중단 후 보고**.

---

## 4. 검증

### 4.1 정적 검증

```bash
# import 끊김 없는지
python -c "from app.graph import build_diagnosis_graph; print('ok')"

# 단위 테스트
pytest tests/ -v
```

테스트 코드가 `fallback_plant_name` 키를 참조하면(예: state mock dict에 박혀 있음) **테스트 코드도 같이 정리**(테스트 정리도 [1-8] 범위). 단, state TypedDict 자체 변경 없으니 키를 빈 값으로 두는 mock은 그대로 작동해야 함.

### 4.2 측정 2회 (게이트 판정용)

```bash
RUN_EVAL_OUT=after_phase1_retrieve_run1.json python scripts/run_eval.py
RUN_EVAL_OUT=after_phase1_retrieve_run2.json python scripts/run_eval.py
```

산출물: `eval/after_phase1_retrieve_run1.json`, `eval/after_phase1_retrieve_run2.json`.

---

## 5. 게이트 ([1-7.5] 2회 평균 대비 -5%p 이내)

| 지표 | [1-7.5] 평균 | [1-8] 게이트 (≥) | 미달 시 |
|---|---|---|---|
| plant_korean | 89.9% | 84.9% | revert |
| recall | 100% | 95% | revert |
| precision | 23.8% | 18.8% | revert |
| accuracy | 51.5% | 46.5% | revert |
| JSON | 100% | 100% (절대) | revert |
| latency | 21.4s | 무변경 또는 감소 | 게이트 외, 회귀 시 보고 |

**예상**: fallback 보너스가 [1-6] 이후 실제로 한 번도 작동 안 했을 가능성 매우 큼(`fallback_plant_name`이 항상 None이라 `fallback_words`가 항상 빈 리스트). 즉 retrieve 동작 자체엔 실효 변화 없어야. 회귀 가능성 매우 낮음. 측정은 "회귀 없음 확인" 용도.

**결정적 측정 확인**: run1·run2가 같은 값이면 결정적. 다르면 generate 단계 노이즈 ±range를 보고에 명시.

---

## 6. 롤백 전략

게이트 미통과 시:

1. **즉시 `git revert HEAD`** — 단일 커밋이라 1회 revert로 [1-7.5] 상태 복원.
2. 원인 진단:
   - 어떤 지표가 얼마나 회귀했는지
   - 회귀가 결정적인지 비결정적인지 (run1 vs run2)
   - fallback 매칭 보너스가 실제로 작동한 케이스가 있었나? 이전 로그 grep으로 확인: `grep "fallback_bonus" logs/*.log` 또는 평가 산출물 분석
3. 결과를 사용자에게 보고 → 재시도 vs [1-9] 일괄 처리로 미루기 결정.

---

## 7. 작업 완료 후 보고 (사용자에게 다음을 정리해서 보고)

### 7.1 사전 grep 결과 표

| 검색어 | 발견 위치 | 처리 |
|---|---|---|
| `fallback_plant_name` | (위치 나열) | 영역 1·E 처리 |
| `FALLBACK_PLANT_SYSTEM` | (위치 또는 "없음") | 영역 5 처리 또는 N/A |
| ... | ... | ... |

### 7.2 변경 통계

```bash
git diff --stat
```

라인 추가/삭제 수, 변경 파일 목록.

### 7.3 측정 결과 표

| 지표 | [1-7.5] avg | [1-8] run1 | [1-8] run2 | [1-8] avg | 게이트 | 판정 |
|---|---|---|---|---|---|---|
| plant_korean | 89.9% | ? | ? | ? | ≥84.9% | ✅/❌ |
| recall | 100% | ? | ? | ? | ≥95% | ✅/❌ |
| precision | 23.8% | ? | ? | ? | ≥18.8% | ✅/❌ |
| accuracy | 51.5% | ? | ? | ? | ≥46.5% | ✅/❌ |
| JSON | 100% | ? | ? | ? | 100% | ✅/❌ |
| latency | 21.4s | ? | ? | ? | (게이트 외) | 참고 |

결정적/비결정적 여부 명시.

### 7.4 발견한 추가 死 코드 (있으면)

영역 5 결과. 없으면 "없음" 명시.

### 7.5 커밋 메시지 (제안, 푸시 전 사용자 확정)

```
refactor: retrieve 정비, fallback_plant_name 死 코드 제거 ([1-8])

- _final_plant_name·_build_rag_query 헬퍼 제거(인라인화)
- _fallback_hint_words·_fallback_match_count·FALLBACK_WORD_MATCH_BONUS 삭제
- _final_rank_score·_apply_plant_filter_after_similarity에서 fallback 분기 제거
- retrieve 로그·keyword_node 출력에서 fallback_plant_name 참조 제거
- (영역 5에서 발견된 추가 잔재 있으면 여기 추가)

state TypedDict·main.py 초기값·프론트 영향은 [1-9] 슬림화로 미룸.
RAG 가중치(NCPMS·UC_IPM·plant_name_match_boost)는 B 묶음에서.

measurement: eval/after_phase1_retrieve_run{1,2}.json
gate: -5%p 이내 회귀 없음 (2회 평균 [1-7.5] 대비)
```

### 7.6 커밋·push (사용자 확정 후만)

```bash
git add app/graph.py
git add eval/after_phase1_retrieve_run1.json eval/after_phase1_retrieve_run2.json
git add docs/work_history/1-8_retrieve_정비_진단.md
git add docs/work_history/1-8_retrieve_정비_작업프롬프트.md
# 영역 5 추가 파일 있으면 함께
git status   # untracked 없는지 최종 확인 ([1-2.5] 교훈)
git commit -m "..."
git push
```

**중요**: untracked 파일이 남아 있으면 안 됨([1-2.5] 사라진 파일 교훈). `git status`로 cleanness 확인 후 push.

---

## 8. 작업 순서 요약

1. 사전 확인 (§2)
2. `app/graph.py` 변경 §3.1 A→B→C→D→E 순서
3. 영역 5 추가 잔재 정리 §3.2
4. 정적 검증 §4.1 (실패 시 즉시 중단·보고)
5. 측정 2회 §4.2
6. 게이트 판정 §5 (미통과 시 §6 롤백)
7. 보고 §7 (사용자 확정 대기)
8. 사용자 OK 후 커밋·push §7.6
