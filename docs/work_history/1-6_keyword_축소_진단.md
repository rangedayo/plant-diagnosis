# [1-6] keyword_node 축소 진단

> 목적: decision #2("keyword_node는 영문 번역 전용으로 축소") 실행. 현재 keyword_node는 description 기반 RAG 증상 쿼리 생성을 위해 GPT-4o-mini를 2~3회 호출하는 무거운 노드인데, analyze가 한국어 `observed_symptoms`를 이미 만들어주는 [1-7] 이후 상태에선 이 호출들이 대부분 중복·낭비.
> 실제 Claude Code 의뢰 프롬프트(`1-6_keyword_축소_프롬프트.md`)는 이 진단에 사용자 확정을 받은 뒤 별도 작성.
>
> 작성일: 2026-05-30
> 단계: 리팩토링 1단계의 여섯 번째 하위 작업 ([1-6])
> 선행: [1-5] graph 와이어링, [1-7] generate 재설계 (v1 채택) — 모두 push 완료.

---

## [1-6]의 성격 — 가벼운 RAG 정리 작업

[1-7]까지 끝낸 상태에서 keyword_node는 죽은 호출의 무덤이다.

현재 keyword_node 본체(graph.py L341~371) 흐름:
1. `state.get("plant_name")` 없으면 `estimate_fallback_plant_with_gpt(desc)` 호출 — GPT-4o-mini 1콜
2. `build_rag_search_query_with_gpt(desc, pn, dn, conf, fb, ihp, tc, mode)` 호출 — 내부에서 `RAG_QUERY_SYMPTOM_SYSTEM`으로 description 기반 한국어 증상 키워드 추출 — GPT-4o-mini 1콜
3. `generate_english_keywords(keywords_ko)` 호출 — GPT-4o-mini 1콜로 한국어→영문 번역

[1-5] 이후 다음 입력이 다 죽었다:
- `state.get("plant_name")` — analyze가 항상 학명을 채워줌 → `estimate_fallback_plant_with_gpt`는 호출 안 됨
- `state.get("disease_name")` — None (analyze가 안 만듦)
- `state.get("confidence")` — None
- `state.get("is_healthy_prob")` — None
- `state.get("top_candidates")` — []

즉 `build_rag_search_query_with_gpt`는 description만으로 증상 키워드를 재추출하고 있다. 그런데 **이미 analyze가 `observed_symptoms`를 한국어 명사구 리스트로 만들어줬다**. 같은 description을 두 번 분석해서 한 번은 6필드 JSON으로, 또 한 번은 RAG용 증상 키워드로 뽑는 중복. 호출 1회 + ~5초 latency 낭비.

decision #2의 본 의미: **analyze가 만든 observed_symptoms를 그대로 RAG에 쓰고, keyword_node는 한→영 번역만 한다**. 즉 LLM 호출 2~3회 → 1회로 축소.

**[1-6]은 회귀 게이트 대상이 아니다.** 다만 RAG 품질에 영향 줄 수 있는 변화라 plant_korean·is_diseased는 보전돼야 함. 측정은 회귀 없음 확인 위주.

---

## 결정 영역 1 — observed_symptoms를 RAG 쿼리에 어떻게 쓸지

analyze 출력 예시: `observed_symptoms = ["잎끝 갈변", "잎 표면 노란 반점"]`. 기존 `keywords_ko`는 공백·쉼표 혼재된 6단어 이내 토큰 리스트. 형식이 약간 다름.

**옵션 A — observed_symptoms를 한국어 키워드 리스트로 그대로 채택**
- `keywords_ko = state.get("observed_symptoms") or []`
- `build_rag_search_query_with_gpt` 호출 제거
- `RAG_QUERY_SYMPTOM_SYSTEM` 프롬프트 사용 안 함 (상수는 [1-9]/Phase 2에서 제거)
- `rag_query`는 코드에서 직접 조립: `plant_name + " " + " ".join(observed_symptoms)`, 최대 N단어

**옵션 B — observed_symptoms를 GPT-4o-mini로 한 번 더 가공해서 키워드 추출**
- 기존 흐름 유지 + 입력만 description → observed_symptoms로 변경
- analyze가 이미 명사구로 만든 걸 또 명사구로 추출 → 의미 없음
- 호출 절약 목적 위반

**옵션 C — observed_symptoms + description 둘 다 입력으로 한 번 GPT 호출**
- 절충안. observed_symptoms를 우선하되 description의 보조 정보도 활용
- 그러나 [1-7]에서 generate가 둘 다 받는 책임 분리(관찰 = analyze, 진단 = generate) — keyword가 또 description을 보면 책임 흐름이 흐려짐

**권장: 옵션 A**
근거 — decision #2의 본 의미가 "영문 번역 전용". observed_symptoms를 그대로 쓰면 호출 절약 목적 달성 + analyze의 출력을 신뢰하는 책임 분리 흐름 일관. observed_symptoms over-reporting 문제([1-7] 후 잔존 FP 14건의 근본 원인)는 [1-3] v4에서 별도 대응.

**위험**: observed_symptoms가 빈 배열일 때 RAG 쿼리가 식물명만 남음 → 검색 품질 저하 가능. 다만 빈 배열 = "건강해 보임" 신호라 검색 의미가 약해도 OK. retrieve에서 docs 0건 → rag_no_docs 플래그 자연스럽게 작동.

---

## 결정 영역 2 — `build_rag_search_query_with_gpt` 함수 처분

`model_utils.build_rag_search_query_with_gpt`는 위 흐름의 핵심. 다른 호출처가 있는지 확인해야 안전하게 제거 가능.

**현재 호출처 (project_knowledge_search 결과)**:
- `app/graph.py` keyword_node 한 곳만 호출

**옵션 A — 함수 완전 제거**
- 더 깔끔. 死 코드 0
- `RAG_QUERY_SYMPTOM_SYSTEM` / `RAG_QUERY_SYMPTOM_USER_TEMPLATE` 상수도 같이 제거
- 관련 헬퍼(`_parse_symptom_keywords_from_llm`, `_symptom_token_allowed`, `RAG_SYMPTOM_KEYWORD_MAX`) 도 정리 — 단 다른 곳에서 안 쓰는지 확인 필요

**옵션 B — 함수 보존, keyword_node에서만 호출 제거**
- 호환성 안전망. 다만 사용처 0의 死 함수가 남음
- decision #2의 "축소"보다 "회피"에 가까운 처리

**권장: 옵션 A**
근거 — [1-9]에서 어차피 자료 정리해야 함. [1-6]에서 사용처와 함수를 한 번에 정리하는 게 작업 효율적. 死 코드를 남기는 건 phase2_decisions의 정신("정직한 시스템")에 어긋남.

**위험**: 다른 모듈에서 import하는 곳이 있으면 그 import가 깨짐. 작업 프롬프트에서 grep으로 사전 확인.

---

## 결정 영역 3 — `estimate_fallback_plant_with_gpt` 함수 처분

analyze가 항상 plant_name을 채워주는 [1-5] 후 상태에선 `estimate_fallback_plant_with_gpt`는 사실상 호출 안 됨(keyword_node의 `if pn is None or not str(pn).strip()` 분기에 안 걸림).

**옵션 A — 함수 + 관련 상수 + state 키 `fallback_plant_name` 모두 제거**
- 함수: `estimate_fallback_plant_with_gpt`
- 상수: `FALLBACK_PLANT_SYSTEM`, `FALLBACK_PLANT_USER_TEMPLATE`, `_sanitize_fallback_plant_line` 헬퍼
- state 키: `fallback_plant_name`은 `DiagnosisState` TypedDict에서 제거
- retrieve_node의 `_final_plant_name` / `_build_rag_query` 같은 헬퍼에서 `fallback_plant_name` 참조 제거 — 이 부분이 [1-8] 영역과 약간 겹침

**옵션 B — 함수만 호출 제거하고 정의는 보존**
- state 키 `fallback_plant_name`도 빈 값으로 보존
- retrieve의 fallback 단어 매칭 보너스 로직 그대로 유지

**옵션 C — [1-6]에선 keyword_node의 호출만 제거, 함수·상수·state·retrieve 영향은 [1-9]에서 일괄**
- 변수 격리 가장 강함
- 다만 [1-6]에서 keyword_node 본체를 어차피 재작성하므로 한 번에 처리 가능

**권장: 옵션 A + 단, retrieve_node 쪽 변경 최소화**
근거 — keyword_node와 함수·상수는 [1-6]에서 정리. 다만 retrieve_node의 `_final_plant_name`·`_build_rag_query`에서 `fallback_plant_name` 참조 부분은 [1-8] 영역이라 [1-6]에선 `state.get("fallback_plant_name")`이 항상 None을 반환하게 두고, retrieve는 None 처리만 작동하면 통과. state TypedDict에서 키 제거는 [1-9] 슬림화에서 한 번에.

즉:
- [1-6]: 함수·상수·헬퍼 제거 + keyword_node에서 호출 제거 + DiagnosisState의 `fallback_plant_name` 키는 일단 보존(None 디폴트)
- [1-8]/[1-9]: retrieve_node 정비 + state 슬림화에서 키 자체 제거

**위험**: retrieve_node의 fallback 매칭 로직이 None 입력에 안전한지 확인 필요. 사전 점검 항목.

---

## 결정 영역 4 — keyword_node 본체 새 구조

옵션 A 채택 시 새 keyword_node:

```python
async def keyword_node(state: DiagnosisState) -> dict:
    keywords_ko = list(state.get("observed_symptoms") or [])
    keywords_en = (
        await model_utils.generate_english_keywords(keywords_ko)
        if keywords_ko else []
    )
    plant_name = state.get("plant_name") or ""
    
    # rag_query: plant_name + observed_symptoms 토큰 결합
    parts = []
    if plant_name.strip():
        parts.append(plant_name.strip())
    parts.extend(keywords_ko)
    query_ko = " ".join(parts)[:200]  # 안전망 길이 제한
    
    return {
        "rag_query": query_ko,
        "keywords": keywords_ko,
        "keywords_en": keywords_en,
        "fallback_plant_name": None,  # [1-9]서 키 자체 제거
    }
```

**고려 사항**:
- observed_symptoms가 빈 배열 → keywords_ko·en 모두 빈 배열, rag_query는 plant_name만
- observed_symptoms over-reporting 케이스 → 그대로 RAG 쿼리에 들어감 ([1-3] v4가 해결)
- generate_english_keywords가 빈 입력에 안전한지 확인 → 위 코드의 `if keywords_ko else []` 가드로 회피

**결정 영역 4-1 — rag_query 길이 제한**: 기존엔 `RAG_QUERY_MAX_WORDS=14`로 단어 단위. observed_symptoms는 명사구라 단어 단위로 자르면 의미 단절. **문자 단위 200자 컷이 안전**. 또는 명사구 단위 5개로 컷.

**권장**: 명사구 단위 5개 + 후행 plant_name 결합. `observed_symptoms[:5] + [plant_name]` 식으로. 단, 코드 단순성 위해 `keywords_ko[:5]` 만 적용. plant_name은 항상 포함.

---

## 결정 영역 5 — query_en (영문 RAG 쿼리)

`retrieve_node`는 `query_en = " ".join(state.get("keywords_en") or []).strip()`을 main_rag(영문 RAG) 검색에 사용. observed_symptoms는 한국어이므로 영문 변환이 필수.

**옵션 A — generate_english_keywords로 observed_symptoms 영문 번역 (기존 헬퍼 그대로 활용)**
- `ENGLISH_KEYWORD_SYSTEM` 프롬프트가 이미 "도감 검색용 영어 키워드"로 작성됨 — observed_symptoms 같은 명사구 입력에도 그대로 작동
- 기존 헬퍼 재사용 = 코드 최소 변경
- GPT-4o-mini 1콜 (이게 [1-6] 후 keyword_node의 유일한 LLM 호출)

**옵션 B — Gemini analyze가 영문 observed_symptoms_en도 출력하도록 v4 프롬프트**
- 호출 0회. 그러나 [1-3] 영역 침범
- analyze 6필드 → 7필드 (스키마 변경) → 측정 광범위 영향
- 비추천 ([1-6] 책임 범위 초과)

**옵션 C — 영문 RAG 검색을 한국어 검색으로 단순화**
- main_rag 컬렉션을 한국어 RAG로 교체 — 데이터셋 영역 (Phase 3)
- [1-6]엔 너무 큼

**권장: 옵션 A**
근거 — 기존 헬퍼 그대로 활용. 호출 1회는 keyword_node의 본 책임("영문 번역 전용")과 일치. decision #2의 본 의미 100% 실현.

**위험**: `ENGLISH_KEYWORD_SYSTEM` 프롬프트가 "색·증상·부위가 드러나도록" 가이드라 description 기반에 최적화됐을 수 있음. observed_symptoms는 이미 색·증상·부위 명사구라 무리 없을 듯. 측정으로 확인.

---

## 결정 영역 6 — `RAG_QUERY_SYMPTOM_*` / `KEYWORD_*` 상수 처분

`app/prompts.py`에 다음 미사용 상수들 남음:
- `RAG_QUERY_SYMPTOM_SYSTEM` / `RAG_QUERY_SYMPTOM_USER_TEMPLATE` — `build_rag_search_query_with_gpt` 제거 시 사용처 0
- `KEYWORD_SYSTEM` / `KEYWORD_USER_TEMPLATE` — 더 이상 사용 안 함 ([1-3] 전부터 이미 미사용일 수 있음, 사전 확인)
- `FALLBACK_PLANT_SYSTEM` / `FALLBACK_PLANT_USER_TEMPLATE` — `estimate_fallback_plant_with_gpt` 제거 시 사용처 0
- `DESCRIBE_IMAGE_SYSTEM` / `DESCRIBE_IMAGE_USER_TEMPLATE` — `describe_node` 제거([1-5])로 이미 미사용

**옵션 A — [1-6]에서 미사용 상수 모두 제거**
- 코드 정리 효과 극대
- 진단 md 결정 6·7(weak phrase, action_plan padding)을 Phase 2로 미루기로 했는데, 상수 제거는 그와 별개의 "코드 청소" 영역이라 [1-6]에 포함 가능

**옵션 B — [1-6]에선 keyword 본체만 정리, 상수 제거는 Phase 2에서 일괄**
- 변수 격리 더 강함

**권장: 옵션 A**
근거 — 위 상수들은 사용처 0인 사실 명백. [1-9] 스키마 슬림화나 Phase 2 강제 로직 완화와 영역이 달라 별도 관리할 이유 없음. [1-6] 작업에서 keyword 본체 정리하면서 한 번에 청소가 자연스러움.

**위험**: 다른 모듈에서 import하는 곳이 있으면 깨짐. 사전 grep 확인.

---

## 결정 영역 7 — 단일 커밋 vs 분리

영향 파일:
1. `app/graph.py` — keyword_node 본체 재작성
2. `app/model_utils.py` — `build_rag_search_query_with_gpt`, `estimate_fallback_plant_with_gpt`, `_sanitize_fallback_plant_line`, `_parse_symptom_keywords_from_llm`, `_symptom_token_allowed`, `RAG_SYMPTOM_KEYWORD_MAX`, `RAG_QUERY_MAX_WORDS` 등 제거
3. `app/prompts.py` — 미사용 상수 제거 (RAG_QUERY_SYMPTOM_*, KEYWORD_*, FALLBACK_PLANT_*, DESCRIBE_IMAGE_*)

**권장: 단일 커밋** — `feat: keyword_node 축소, RAG 쿼리 직접 조립 ([1-6])`

근거 — 3개 파일이 한 흐름의 일부(keyword 본체 정비 + 그 함수 제거 + 그 프롬프트 제거). 분리할 의미 없음. 측정 1회로 충분.

**총 라인 변경 추정**: -150~-200줄 (제거 위주). +30~50줄 (새 keyword_node).

---

## 결정 영역 8 — 측정 방법

**산출물**: `eval/after_phase1_keyword.json` (decision #5 명시 파일명 아님, [1-6]만의 측정).

**목표**:
- plant_korean 89.3% 유지 (keyword 변경은 식물명에 영향 없음 — analyze 무변경)
- is_healthy precision 26.3% 유지 (generate 무변경)
- is_healthy recall 100% 유지 (generate 무변경)
- JSON 100% 유지
- **latency 32.4s → 27~30s 감소 기대** (GPT-4o-mini 호출 1~2회 줄어듦)
- RAG hit 품질 (per_case rag_docs 빈 케이스 비율)이 비슷하거나 개선

**위험 케이스**:
- observed_symptoms 빈 배열 케이스가 plant_name만으로 RAG 검색 → 도감 docs 못 가져옴 → 기존엔 description 기반으로 광범위 검색하던 게 사라짐. status가 흔들릴 수 있음.
- 그러나 [1-7]에서 `observed_symptoms = []` → status="건강" 가이드가 작동하므로 RAG 의존성 자체가 낮은 경우라 큰 영향 없을 듯.

**측정 워크플로**:
1. [1-6] 작업 완료 → 커밋 전 측정
2. `RUN_EVAL_OUT=after_phase1_keyword.json python scripts/run_eval.py`
3. v8 baseline / after_phase1_wiring / after_phase1_generate 셋과 비교
4. precision/recall 유지 + latency 감소 확인
5. 통과 시 커밋·push

**가설 예측**:
- plant_korean: 89.3% 유지 (analyze 무변경)
- precision: 26.3% 유지 (generate 무변경, RAG 입력은 약간 다르지만 status 결정은 observed_symptoms 가이드가 주도)
- recall: 100% 유지
- latency: 32.4s → 27~30s (GPT 호출 1~2회 절감, 1회당 1~3s 추정)
- RAG hit: 비슷 또는 약간 저하 (observed_symptoms over-reporting이 RAG 쿼리로 그대로 들어가는데, "잎끝 갈변" 같은 의학용어 없는 명사구는 도감 검색에 약할 수 있음. 다만 영문 변환에서 "marginal leaf browning" 같은 도감 용어로 변환되면 보완됨)

---

## 권장 작업 분할

**커밋 메시지 (권장)**: `feat: keyword_node 축소, RAG 쿼리 직접 조립 ([1-6])`

**작업 묶음**:

1. `app/graph.py`
   - `keyword_node` 본체 재작성 (결정 영역 4 안)
   - `estimate_fallback_plant_with_gpt` 호출 제거
   - `build_rag_search_query_with_gpt` 호출 제거
   - DiagnosisState의 `fallback_plant_name` 키는 일단 유지 ([1-9]서 제거)

2. `app/model_utils.py`
   - `build_rag_search_query_with_gpt` 함수 제거
   - `estimate_fallback_plant_with_gpt` 함수 제거
   - 헬퍼 제거: `_sanitize_fallback_plant_line`, `_parse_symptom_keywords_from_llm`, `_symptom_token_allowed`
   - 상수 제거: `RAG_SYMPTOM_KEYWORD_MAX`, `RAG_QUERY_MAX_WORDS`
   - `generate_english_keywords` 유지 (keyword_node가 계속 사용)

3. `app/prompts.py`
   - `RAG_QUERY_SYMPTOM_SYSTEM` / `RAG_QUERY_SYMPTOM_USER_TEMPLATE` 제거
   - `KEYWORD_SYSTEM` / `KEYWORD_USER_TEMPLATE` 제거 (사용처 0 확인 후)
   - `FALLBACK_PLANT_SYSTEM` / `FALLBACK_PLANT_USER_TEMPLATE` 제거
   - `DESCRIBE_IMAGE_SYSTEM` / `DESCRIBE_IMAGE_USER_TEMPLATE` 제거 ([1-5]에서 describe_node 제거됐으니 이미 미사용)
   - `ANALYZE_*` / `ENGLISH_KEYWORD_*` / `STRUCTURED_DIAGNOSIS_JSON_*` 유지

4. 사전 grep 확인 (작업 프롬프트에 박을 항목)
   - `grep -r "build_rag_search_query_with_gpt" app/ tests/ scripts/` → graph.py 1곳 외 없는지
   - `grep -r "estimate_fallback_plant_with_gpt" app/ tests/ scripts/` → graph.py 1곳 외 없는지
   - `grep -r "RAG_QUERY_SYMPTOM" app/ tests/ scripts/` → model_utils.py 1곳 외 없는지
   - `grep -r "KEYWORD_SYSTEM\|KEYWORD_USER_TEMPLATE" app/ tests/ scripts/`
   - `grep -r "FALLBACK_PLANT_SYSTEM\|FALLBACK_PLANT_USER_TEMPLATE" app/ tests/ scripts/`
   - `grep -r "DESCRIBE_IMAGE_SYSTEM\|DESCRIBE_IMAGE_USER_TEMPLATE" app/ tests/ scripts/`
   - 모두 0건이면 안전 제거. 발견 시 보고 후 결정.

5. retrieve_node 영향 확인 (사전 점검)
   - `state.get("fallback_plant_name")` 참조 부분이 None 처리에 안전한지 확인
   - `_final_plant_name` / `_build_rag_query` 헬퍼가 None 입력에 NPE 안 던지는지

6. 측정
   - `RUN_EVAL_OUT=after_phase1_keyword.json python scripts/run_eval.py`
   - v8 baseline / after_phase1_wiring / after_phase1_generate 셋과 비교
   - 핵심: precision/recall 유지 + latency 감소

7. 회귀 없으면 단일 커밋·push.

---

## 롤백 전략

[1-6]은 회귀 게이트 대상 아님. 다음 두 케이스에서 재시도:

1. **plant_korean 회귀** (-5%p 초과): keyword 변경이 분류에 영향 줄 이유 없지만 만약 발생 → 단일 커밋 revert + 원인 진단
2. **precision/recall 회귀** ([1-7] 상태 회복 못 함): RAG 입력 변화가 generate에 영향. 가능성 낮음. 발생 시 케이스별 비교로 원인 분석.

단일 커밋이라 `git revert HEAD` 1회로 [1-7] 직후 상태 복원.

---

## 다음 단계 연계

[1-6] 통과 후:
- **[1-8] retrieve_node 정비**: `fallback_plant_name` 참조 제거, `_final_plant_name`·`_build_rag_query` 헬퍼 단순화. main_rag/ncpms_rag 가중치 조정 검토.
- **[1-3] v4 — analyze observed_symptoms over-reporting 추가 억제**: [1-9] 진입 전 FP 회복 시도. 접란·드라세나·산세베리아 자연 변색 케이스 직격.
- **[1-9] state/schema 슬림화 + 프론트 동시** 🔴 두 번째 회귀 게이트: 죽은 키 일괄 제거 (is_healthy_prob, top_candidates, disease_name, confidence, **fallback_plant_name 포함**) + DiagnosisResponse + types/diagnosis.ts + ResultView + rag_failed 시 백엔드/프론트 에러 UI 동시.
- **[1-10]**: Plant.id 완전 제거 + eval/after_phase1.json + temperature A/B/C 튜닝.

---

## 사용자 확정 대기 항목

작업 프롬프트(`1-6_keyword_축소_프롬프트.md`)를 만들기 전 확인:

1. **결정 영역 1 권장 (옵션 A — observed_symptoms를 한국어 키워드로 그대로 채택)** 동의?
2. **결정 영역 2 권장 (옵션 A — build_rag_search_query_with_gpt 완전 제거)** 동의?
3. **결정 영역 3 권장 (옵션 A — estimate_fallback_plant_with_gpt 등 제거, state 키 fallback_plant_name은 [1-9]서 제거)** 동의?
4. **결정 영역 4-1 권장 (rag_query: keywords_ko[:5] + plant_name 결합)** 동의?
5. **결정 영역 5 권장 (옵션 A — generate_english_keywords 재사용으로 영문 번역)** 동의?
6. **결정 영역 6 권장 (옵션 A — 미사용 프롬프트 상수 일괄 제거)** 동의?
7. **결정 영역 7 권장 (단일 커밋)** 동의?

위 7개에 답을 박아주면 작업 프롬프트 md 작성으로 넘어감.

---

## 부록 — [1-6] 작업 후 자동 점검 항목

```bash
# 1. 단위 테스트 회귀 없음
pytest tests/ -v -m "not integration"
# 기대: 23/23 passed (analyze/vision 무영향)

# 2. import 정합성
python -c "from app.graph import build_diagnosis_graph; from app.main import app; print('ok')"

# 3. 제거된 함수 import 안 되는지 확인
python -c "from app.model_utils import build_rag_search_query_with_gpt" 
# 기대: ImportError

# 4. 미사용 상수 제거 확인
python -c "from app import prompts; assert not hasattr(prompts, 'RAG_QUERY_SYMPTOM_SYSTEM'); print('ok')"
python -c "from app import prompts; assert not hasattr(prompts, 'FALLBACK_PLANT_SYSTEM'); print('ok')"

# 5. 회귀 측정
RUN_EVAL_OUT=after_phase1_keyword.json python scripts/run_eval.py
# 기대: precision/recall 유지, latency 감소

# 6. 라이브 호출 1회 (수동)
# self_haengun_002.jpg (unhealthy) 업로드 → status="병해 의심" 유지 확인
```
