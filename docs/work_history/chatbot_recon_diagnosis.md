# 정찰 보고서: 챗봇(객관식 문답 → 2차 보정 진단) 설계용 파이프라인 recon

> READ-ONLY 정찰. 코드·프롬프트·스키마·프론트 일절 무수정. 측정 미실행(Gemini 과금 0).
> 핵심 질문 = **generate 노드 재사용 가능성** + **analyze·RAG 재호출 회피 가능성**.

---

## 0. 요약 (핵심 질문 결론)

| 질문 | 결론 | 근거 요약 |
|---|---|---|
| 객관식 답변을 generate에 주입 가능한가 | **확인됨 (조건부)** | `context_summary`는 generate_node에서 조립되는 자유형 f-string → 새 섹션 추가는 순수 가산. 단 답변이 generate에 닿으려면 `DiagnosisState` 새 필드 + 진입 경로 필요 |
| 2차에서 **Gemini(analyze) 재호출 회피** 가능한가 | **확인됨** | analyze 6필드는 이미 `DiagnosisResponse.analysis`로 응답에 노출됨 → 재사용 가능 |
| 2차에서 **RAG(임베딩) 재호출 회피** 가능한가 | **조건부** | generate가 쓰는 `rag_docs`·`top_3_problem_type_weighted`·rag 플래그가 **현재 응답에 미노출**(state에만 존재) → 영속/노출해야 generate-only 재실행 가능 |
| generate만 재실행 가능한가 (그래프 그대로) | **확인 안 됨 → 조건부** | 컴파일된 그래프는 `analyze`에서만 시작하는 고정 선형 체인 → 그래프 그대로는 generate 단독 호출 불가. generate 본문을 공유 callable로 분리하거나 별도 미니그래프 필요 |
| 2차 응답이 1차 스키마(`DiagnosisResponse`) 재사용 가능한가 | **확인됨** | 2차 산출도 동일 5키 `structured_result` → 응답 스키마 재사용 가능. 요청 스키마만 신설 필요 |

---

## 1. 진입점·파이프라인 흐름

**진입점** `POST /diagnose` ([app/main.py:121-216](../../app/main.py#L121-L216)):
- 업로드 검증(확장자·5MB·매직넘버) → 이미지 RGB 정규화 → `graph.ainvoke(초기 state)` ([main.py:170-188](../../app/main.py#L170-L188)) → `DiagnosisResponse` 조립 ([main.py:211-216](../../app/main.py#L211-L216)).

**그래프 노드 순서** ([app/graph.py:836-846](../../app/graph.py#L836-L846)):
```
analyze → keyword → retrieve → generate → END   (set_entry_point("analyze"))
```

| 노드 | 외부 호출 | 입력 | 출력(state 기여) | 코드 |
|---|---|---|---|---|
| analyze | **Gemini vision** | image_bytes | 6필드(plant_name, plant_name_korean, plant_confidence, alt_candidates, visual_description, observed_symptoms) | [graph.py:451-460](../../app/graph.py#L451-L460) |
| keyword | **gpt-4o-mini** (영문 번역 1콜) | observed_symptoms | rag_query, keywords, keywords_en | [graph.py:462-493](../../app/graph.py#L462-L493) |
| retrieve | **OpenAI 임베딩(ada-002)** + Chroma | rag_query/keywords_en, plant_name | rag_docs(태그), rag_metas, rag_sims, top_3_problem_type_weighted, rag_failed/no_docs/weak | [graph.py:495-748](../../app/graph.py#L495-L748) |
| generate | **gpt-4o-mini** + (조건부)guard cause 재생성 | 아래 §2 | structured_result, status_guard, care_guide | [graph.py:750-834](../../app/graph.py#L750-L834) |

→ **2차당 잠재 과금원 3개**: Gemini(analyze), 임베딩(retrieve), gpt-4o-mini(keyword·generate). 2차에서 analyze·retrieve를 재사용하면 Gemini·임베딩 0, gpt-4o-mini(generate) 1콜만 남음.

---

## 2. generate 노드 재사용 가능성 (핵심)

**generate_node가 받는 context 구조** ([graph.py:750-795](../../app/graph.py#L750-L795)):
- `context_summary` (f-string, [graph.py:775-787](../../app/graph.py#L775-L787)): 묘사(visual_description) + [관찰 정보](plant_name/통명/신뢰도/대안후보/observed_symptoms) + [검색 자료 타입 분포](majority/top_pt/dist).
- `rag_chunks` = `"\n\n".join(rag_docs)` ([graph.py:788](../../app/graph.py#L788)).
- 플래그: rag_failed, rag_no_docs, rag_weak_evidence.

**generate 함수 시그니처** ([app/model_utils.py:179-244](../../app/model_utils.py#L179-L244)):
```python
generate_structured_diagnosis_with_gpt(context_summary, rag_chunks, *, rag_failed, rag_no_docs, rag_weak_evidence)
```
USER 템플릿 ([app/prompts.py:106-116](../../app/prompts.py#L106-L116))이 보간하는 변수 = `{context_summary}`, `{no_rag_block}`, `{rag_chunks}`, `{weak_instruction}` 4개뿐. **SYSTEM 프롬프트는 무포맷 상수**(`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`).

### 2-1. 객관식 답변 주입 채널 → **`context_summary` 가산** (확인됨)
`context_summary`는 generate_node 내부에서 조립되는 자유형 문자열 ([graph.py:775-787](../../app/graph.py#L775-L787)). 여기에 `[사용자 추가 입력]\n- 마지막 물 준 시점: …\n- 주로 두는 위치: …` 섹션을 **덧붙이는 것은 순수 가산**이며 LLM 호출 경로의 스키마(키 개수·response_format)는 무변경. **별도 필드 불필요** — context_summary 합류로 충분.
- 단, generate 프롬프트에 "사용자 추가 입력을 어떻게 가중할지" 규칙 추가 필요(설계 시). 이는 §5 가드·게이트와 교락(아래).

### 2-2. 답변이 generate에 닿는 경로 → **state 새 필드 + 진입 경로 필요** (조건부)
generate_node는 오직 `state`(DiagnosisState)에서만 읽음. 답변을 넣으려면:
- `DiagnosisState`에 `user_answers` 류 필드 추가 ([graph.py:129-155](../../app/graph.py#L129-L155), TypedDict라 가산 trivial), **그리고**
- 진입점이 그 필드를 채워야 함. 현재 `/diagnose`는 답변 슬롯 없이 초기 state 구성 ([main.py:172-188](../../app/main.py#L172-L188)) → 2차용 별도 진입(엔드포인트/그래프) 필요.

### 2-3. analyze·RAG 재호출 회피 → analyze=확인됨 / RAG=조건부
- **그래프 그대로는 generate 단독 실행 불가**: `ainvoke`는 항상 entry_point `analyze`에서 시작 ([graph.py:841](../../app/graph.py#L841)), 노드 선택 진입점 없음. → generate 본문을 **공유 callable로 분리**하거나 **generate-only 미니그래프** 신설이 전제.
- **Gemini(analyze) 회피 = 확인됨**: analyze 6필드는 이미 `DiagnosisResponse.analysis`로 프론트에 노출 ([main.py:193-200](../../app/main.py#L193-L200), [schemas.py:10-30](../../app/schemas.py#L10-L30)) → 2차가 이를 되돌려주면 재호출 0.
- **임베딩(RAG) 회피 = 조건부**: generate가 쓰는 `rag_docs`(태그), `top_3_problem_type_weighted`, rag 플래그는 **state에만 존재하고 응답엔 미노출** ([graph.py:735-745](../../app/graph.py#L735-L745)는 state 기여, [main.py:211-216](../../app/main.py#L211-L216)는 미surface). → generate-only 재실행하려면 이들을 **영속(서버 캐시) 또는 응답 노출**해야 함. 그렇지 않으면 retrieve 재실행(임베딩 재과금) 불가피.
  - 단 RAG는 `observed_symptoms`(이미지 유래)로 쿼리됨 ([graph.py:467-485](../../app/graph.py#L467-L485)). 2차 답변이 observed_symptoms를 바꾸지 않으면 **1차 RAG 결과 재사용이 논리적으로 타당**(동일 쿼리 → 동일 문서). 답변으로 RAG 검색을 바꾸려면(위치→광 카드) retrieve 재실행 필요(설계 분기 B).

---

## 3. API·스키마 계약

**`DiagnosisResponse`** ([schemas.py:67-79](../../app/schemas.py#L67-L79)): message, analysis(6필드), `structured_result: dict`(summary/current_state/cause/action_plan/status), care_guide.
- **2차 응답 = 동일 스키마 재사용 확인됨**: 2차 산출도 같은 5키 structured_result → `DiagnosisResponse` 그대로 가능.
- **2차 요청 = 신설 필요**: 질문·답변 + 재사용할 1차 컨텍스트를 담을 요청 스키마.

**선례 패턴 — `DiagnosisSnapshot`** ([schemas.py:89-104](../../app/schemas.py#L89-L104)): `/compare`가 이미 "1차 결과의 정성 필드(status/summary/current_state/cause/action_plan/observed_symptoms)를 프론트→서버로 되돌리는" 요청 패턴을 확립 ([main.py:219-238](../../app/main.py#L219-L238), [lib/api.ts:44-68](../../lib/api.ts#L44-L68)). **2차 보정 요청도 이 선례를 따라 `RefineRequest(snapshot + answers + 재사용 RAG 컨텍스트)` 형태로 깔끔히 확장 가능**(구조만 — 구현 X).

---

## 4. 프론트엔드 결과 화면

**state 관리** ([pages/index.tsx:19-67](../../pages/index.tsx#L19-L67)):
- `screen: "home"|"loading"|"result"|"care"|"myPlants"|"timeline"` ([index.tsx:17](../../pages/index.tsx#L17)), `result: DiagnosisResponse|null`, `file`/`previewUrl`.
- `runDiagnosis(file)`: `diagnosePlant` → `setResult(data)` → `setScreen("result")` ([index.tsx:43-67](../../pages/index.tsx#L43-L67)).
- **fresh vs history 격리 선례**: `historyDiagnosis`/`selectedPlant`를 `result`와 별도 state로 분리해 격리 ([index.tsx:28-30](../../pages/index.tsx#L28-L30), [index.tsx:146-168](../../pages/index.tsx#L146-L168)). → 1차/2차도 **별도 state(`refinedResult`)로 분리**하면 1차 보존·1차↔2차 비교 표시까지 자연스럽게 확장(이 선례와 동형).

**ResultView 렌더 구조** ([components/ResultView.tsx](../../components/ResultView.tsx)): 사진+배지 → [진단 요약](필드) → [이렇게 판단했어요](cause) → [처방](action_plan) → 케어 내비. Props = result, imageUrl, onReset, onViewCare, onSave, **mode("fresh"|"history")** ([ResultView.tsx:5-14](../../components/ResultView.tsx#L5-L14)).
- **객관식 질문 UI 위치 후보**: 처방 카드 아래(케어 내비 위)에 새 섹션, 또는 별도 screen `"refine"`.
- **mode 게이팅 주의**: ResultView는 fresh·history 공용. 과거 기록(history)에는 라이브 보정이 무의미 → **질문 UI는 `mode==="fresh"`에서만** 노출해야 함.

---

## 5. 비결정성·게이트 영향 (리스크 식별만, 측정 범위 외)

**status guard 구조** ([graph.py:94-126](../../app/graph.py#L94-L126), 호출 [graph.py:798-815](../../app/graph.py#L798-L815)): generate 출력 뒤 `apply_status_guard(status, observed_symptoms, top_1)`가 이진(건강↔비건강) enum만 교정. **병변 토큰 veto**([graph.py:55-61](../../app/graph.py#L55-L61), [graph.py:112-113](../../app/graph.py#L112-L113))가 FN-0(cardinal_miss 0) 안전판 — **`observed_symptoms`를 키로 작동**.

**식별된 리스크**:
1. **2차는 평가 하니스 부재**: run_eval은 1차(이미지→진단)만 측정. **cardinal_miss=0 보장은 1차 한정** — 2차 generate 출력은 현 게이트로 측정 불가. (측정은 이번 범위 아님, 구조적 공백으로 기록.)
2. **guard 입력 불변성이 recall 사수의 전제**: 2차 답변을 context_summary 가산으로만 쓰고 **`observed_symptoms`(이미지 유래)를 불변 유지**하면, 2차 generate가 다른 status를 내도 guard veto가 동일하게 FN-0을 사수. 반대로 **답변이 observed_symptoms를 변형하거나 guard를 우회**하면 recall 게이트가 깨짐 → 설계 시 "2차 출력도 동일 observed_symptoms로 `apply_status_guard` 통과" 권고.
3. **답변→status 가중 규칙과 cosmetic 예외 교락**: 물주기/위치 답변은 과습/건조/광 부족(abiotic 축) 변별에 고레버리지(과거 라운드의 과습·건조 분산 병목과 정확히 겹침). 단 generate 프롬프트에 답변→status 가설 규칙을 넣으면 §2의 cosmetic·경미 판정 룰과 상호작용 → 변수 격리 측정 필요(향후 라운드).

---

## 6. 설계 분기 후보 (우선순위는 사용자 결정, §6.6)

### 분기 A — generate-only 재실행 / 가산 context / 정적 질문 (최저 과금, MVP 권장)
- generate_node 본문을 공유 callable로 분리 + `/diagnose/refine` 신설. 1차 응답에 RAG 컨텍스트(rag_docs/top_3_problem_type/observed_symptoms/flags)를 노출하거나 서버 캐시 → 2차는 그 컨텍스트 + 답변(context_summary 가산)으로 **generate+guard만 재실행**. **Gemini 0·임베딩 0**, gpt-4o-mini 1콜.
- **분기 조건**: `DiagnosisResponse`에 RAG 컨텍스트 필드 확장(또는 서버측 보관)을 수용. 답변이 "검색 결과를 바꾸지 않고 generate 추론만 보정"하면 충분하다고 볼 때.

### 분기 B — 답변을 RAG 쿼리에 반영한 부분 재실행 (고충실도, 임베딩 재과금)
- 답변이 retrieve 검색을 바꿈(위치→광 카드 등) → keyword→retrieve→generate 재실행(analyze는 6필드 재사용으로 Gemini 회피). 임베딩(ada-002, 저가) 재과금.
- **분기 조건**: 답변이 "어떤 카드를 검색하는지"까지 바꿔야 한다고 볼 때(abiotic 변별을 RAG 층에서 강화).

### 분기 C — 서사 보정 전용 (최저 blast radius, status 재평가 안 함)
- `/compare`형 얇은 신설 콜: 1차 structured_result + 답변 → LLM이 **설명문만 보정**(status 재분류 X). 가드·게이트 무관.
- **분기 조건**: 2차 = 톤·설명 보정일 뿐 status를 다시 판정하지 않는다고 볼 때(가장 안전하나 "보정 진단"의 가치는 약함).

---

## 7. 정찰 한계 (정직)

- 본 보고서는 **코드 정적 분석 기반** — 런타임 동작·실제 LLM 출력은 미검증(측정 범위 외).
- 2차 품질·cardinal_miss 영향은 **하니스 부재로 현재 측정 불가**(§5-1). 설계 채택 후 2차 전용 평가 설계가 별도 선결 과제.
- `DiagnosisState` 영속/캐시 방식(서버 메모리 vs Firestore 재전달)은 인증·시계열 트랙([시계열 3단계] 무인증 정책, [main.py:219-225](../../app/main.py#L219-L225))과 정합 검토 필요 — 본 recon 범위 밖.
