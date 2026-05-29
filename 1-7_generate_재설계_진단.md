# [1-7] generate_node 재설계 진단

> 목적: [1-5]에서 발생한 is_healthy 보수화(precision 23.1→11.1%, recall 60→20%)를 정면 대응하기 위한 `generate_node` + `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` + `model_utils.generate_structured_diagnosis_with_gpt` 재설계의 **사전 진단**.
> 실제 Claude Code 의뢰 프롬프트(`1-7_generate_재설계_프롬프트.md`)는 이 진단에 사용자 확정을 받은 뒤 별도 작성.
>
> 작성일: 2026-05-30
> 단계: 리팩토링 1단계의 일곱 번째 하위 작업 ([1-7]) — **순서 변경: [1-6]/[1-8]보다 우선**
> 선행: [1-5] graph 와이어링 완료, after_phase1_wiring.json 측정 결과 is_healthy 보수화 확인.

---

## [1-7]의 성격 — 왜 [1-6]보다 먼저 와야 하는가

[1-5] 진단 md "롤백 전략" 분기에 미리 박아뒀던 그 경로다. 게이트는 통과(plant_korean -0.7%p, is_diseased 0%p)했지만 그 안에서 precision/recall은 절반 이하로 무너졌다. accuracy 보존은 우연한 상쇄(FP 10→8 감소가 FN 2→4 증가를 가린 것)일 뿐, 5장의 비건강 GT 중 3장 잡던 게 1장으로 줄었다는 게 핵심 사실. "내 식물이 아픈데 건강하대"가 늘었다 = **사용자 가치 직격**.

원래 [1-6](keyword 축소) → [1-7](generate) → [1-8](retrieve) → [1-9](스키마 슬림화 게이트)였지만, [1-9]가 두 번째 -5%p 게이트라 그 전에 baseline 수준 is_healthy 회복이 필수. [1-6]·[1-8]은 RAG 품질 관련이라 is_healthy 보수화의 근본 원인이 아니다. **generate가 입력을 어떻게 해석하는지가 원인**이므로 [1-7]을 앞당긴다.

[1-7]은 **회귀 게이트(decision #5) 대상이 아니다**. 그래서 [1-5]보다 손을 더 과감하게 댈 수 있지만, [1-9] 진입 전에 암묵적 기준 "v8 baseline(precision 23%·recall 60%) 회복 이상"을 통과해야 함. 그 회복이 [1-7]의 사실상 게이트.

---

## 보수화 메커니즘 — 가설 분해

`eval/after_phase1_wiring.json` + 현재 코드(`app/prompts.py`, `app/model_utils.py`, `app/graph.py`)를 교차 검토한 결과, is_healthy 보수화는 3개 메커니즘의 합으로 추정된다.

**메커니즘 1 — Plant.id `is_healthy_prob` 신호 소멸**
이전엔 `is_healthy_prob=0.4~0.7` 같은 중간값이 들어오면 모델이 "확률 자체가 애매하니 병해 의심 쪽"으로 기울었음. [1-5] 후 이 자리에 `format_is_healthy_for_prompt(None)="없음"`이 들어감. 모델은 "확률 정보 없음 = 추정 근거 부족 = 안전한 디폴트로"라는 판단으로 기울 수밖에 없음.

**메커니즘 2 — `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`의 "건강에 가깝게" 가이드**
현재 프롬프트에 다음 줄이 박혀 있음:
> "건강 확률이 높거나 병징이 거의 없으면 status는 '건강'에 가깝게, summary/current_state에 안심·관찰 톤 반영."

[1-5] 후 generate는 `observed_symptoms`를 **입력으로 받지 않는다**(brige는 description만). 따라서 "병징이 거의 없음"이 모델의 default 가정이 됨. 즉 프롬프트가 보수화 방향으로 능동적으로 가이드하는 중.

**메커니즘 3 — `normalize_structured_result`의 status fallback**
`app/model_utils.py`:
```python
status = str(data.get("status", "")).strip()
if status not in ALLOWED_STRUCT_STATUS:
    status = "건강"
```
모델이 enum 외 출력을 내거나 빈 값을 내면 "건강"으로 강제. 또 `default_structured_fallback()`도 비-rag_failed 분기에서 `status="건강"`. **디폴트 자체가 보수적**.

세 메커니즘이 합쳐서 보수화 발생. [1-7]은 이 셋 모두를 다룬다.

---

## 결정 영역 1 — "Plant.id 팩트" 섹션 처분

현재 `generate_node`(graph.py L380~410)의 context_summary:
```
묘사:
{desc}

[Plant.id 팩트]
- 식물명(분류 1위): {pn}
- 분류 신뢰도: {conf}  ← None
- 건강일 추정 확률 is_healthy (0~1): 없음  ← format_is_healthy_for_prompt(None)
- 분류 상위 후보(최대 3): 없음  ← format_top_candidates_for_prompt([])
- 질병/비질병 힌트(1위): None  ← state.get('disease_name') f-string
```

[1-5] 후 4줄 중 3줄이 "없음"/"None". 이미 정보 가치 0.

**옵션 A — "Plant.id 팩트" 섹션 통째 제거, analyze 6필드 기반 새 섹션으로 교체**
- 새 섹션 예시:
```
묘사:
{visual_description}

[관찰 정보]
- 식물명(학명 1위): {plant_name}
- 식물명(통명): {plant_name_korean}
- 식별 신뢰도: {plant_confidence}  ← Literal "low"/"med"/"high"
- 대안 후보: {alt_candidates}  ← list[str], 없으면 "없음"
- 관찰된 증상: {observed_symptoms}  ← list[str], 비어있으면 "관찰된 이상 없음"
```
- 모든 필드가 analyze 6필드 그대로 → state에서 직접 읽기

**옵션 B — "Plant.id 팩트" 섹션 통째 제거, 그 자리에 아무것도 안 넣음**
- context_summary가 묘사만으로 줄어듦
- 6필드 정보 활용 0 → analyze 6필드의 가치 무화

**옵션 C — 일부만 교체 (예: alt_candidates만 추가)**
- 어중간. 회귀 원인 분리 가능하나 추후 작업에서 다시 손대야 함

**권장: 옵션 A**
근거 — analyze가 6필드를 만들어주는데 generate가 안 쓰면 [1-1]~[1-5] 작업의 정보 가치가 죽음. [1-7]의 책임이 "generate를 analyze 출력에 맞게 재설계"인데 옵션 B/C는 그 책임을 다하지 못함.

**위험**: `plant_confidence`, `alt_candidates`, `observed_symptoms`를 받은 GPT-4o-mini가 어떻게 반응할지는 미지수. 다음 결정 영역(2,3,4)에서 각 필드의 사용법 명시로 위험 완화.

---

## 결정 영역 2 — observed_symptoms 활용 (보수화 직격 대응)

메커니즘 2 대응. analyze가 한국어 명사구 리스트로 증상을 만들어주는데 generate는 이걸 안 본다. [1-7]에서 가장 중요한 변경.

**옵션 A — 새 섹션 "관찰된 증상" 추가, 빈 배열일 때 명시적 "관찰된 이상 없음" 표기**
- 모델이 `observed_symptoms=[]`을 받으면 → "관찰 단계에서 이상 없음 보고" → status="건강" 정당화 가능
- 모델이 `observed_symptoms=["잎끝 갈변", "잎 노란 반점"]`을 받으면 → "병징 있음" → status="병해 의심" 정당화 가능
- 프롬프트에 "관찰된 증상이 있으면 status='건강'을 선택하지 마세요" 가이드 추가

**옵션 B — observed_symptoms를 RAG 쿼리에 우선 사용, generate엔 안 보냄**
- [1-6] keyword_node 축소 영역 침범
- [1-7] 범위 위반

**권장: 옵션 A + 프롬프트 가이드 강화**
근거 — 이게 보수화 직격 대응. analyze [1-3] v3 프롬프트가 "이상이 보이지 않으면 빈 배열 []"을 명시했으므로 빈 배열의 의미가 명확함. generate가 이걸 신뢰해서 status 결정에 사용하는 게 책임 분리(decision #1)의 본 모습.

**구체적 프롬프트 변경**:
```
- 관찰된 증상(observed_symptoms)이 비어 있으면 식물에 가시적 이상이 없다는 신호입니다. 이 경우 status="건강"이 적절합니다.
- 관찰된 증상이 1개 이상 있으면 status="건강" 선택을 금지합니다. 증상 양상에 따라 "병해 의심"·"과습"·"건조"·"영양 부족" 중 적절한 것을 선택하세요.
```

**위험**: analyze 단계의 over-reporting이 generate를 과도하게 "병해 의심" 쪽으로 밀 수 있음. [1-3] v3에서 observed_symptoms 과잉 억제 가이드를 추가했으니 그 부분은 이미 어느 정도 방어됨. 측정으로 확인.

---

## 결정 영역 3 — alt_candidates / plant_confidence 활용

`plant_confidence`가 "low"면 종 식별이 불확실하다는 정직한 신호. generate가 이를 받으면 cause/action_plan에 보수성 반영 가능.

**옵션 A — 둘 다 새 섹션에 노출, 프롬프트에서 활용 지침 명시**
- "plant_confidence='low'이면 cause·action_plan에서 종 단정을 피하고 일반적 환경 점검 톤으로"
- "alt_candidates에 후보가 있으면 cause에서 '~ 또는 ~ 가능성'으로 언급 가능"

**옵션 B — context_summary에 노출만, 활용 가이드 없이 모델이 알아서**
- 미니멀. 하지만 활용 가이드 없으면 모델이 무시할 가능성 큼.

**권장: 옵션 A**
근거 — analyze가 self-report enum으로 명시적으로 만들어준 정보. generate가 이걸 무시하면 책임 분리의 의미 약함. 활용 지침은 1~2줄로 짧게.

**위험**: 프롬프트 길이 증가. 현재 STRUCTURED_DIAGNOSIS_JSON_SYSTEM이 약 700자인데 [1-7] 후 1000~1100자 정도로 증가 예상. GPT-4o-mini는 충분히 처리 가능 범위.

---

## 결정 영역 4 — "건강에 가깝게" 가이드 제거 (보수화 직격 대응)

메커니즘 2 정면 제거. 현재 프롬프트:
> "건강 확률이 높거나 병징이 거의 없으면 status는 '건강'에 가깝게, summary/current_state에 안심·관찰 톤 반영."

**옵션 A — 줄 통째 삭제, observed_symptoms 기반 가이드로 대체** (결정 영역 2와 연계)
- 결정 영역 2의 새 가이드("관찰된 증상이 비어 있으면 '건강' 적절, 1개 이상이면 '건강' 금지")가 이 줄을 대체.

**옵션 B — 줄 유지, "건강 확률이" 부분만 제거 (대신 "병징이 거의 없으면" 유지)**
- 절반만 제거. "병징"의 판단 기준이 모호 → observed_symptoms 보지 않고 모델 주관 판단.

**옵션 C — 줄 유지하고 표현만 완화** ("안심·관찰 톤 반영" → "관찰을 권하는 톤")
- 보수화의 근본 원인을 그대로 둠.

**권장: 옵션 A**
근거 — 메커니즘 2 정면 제거. 결정 영역 2와 한 쌍으로 작동.

**위험**: 모델이 "건강" 디폴트 bias를 완전히 잃고 반대 방향(과잉 "병해 의심")으로 쏠릴 수 있음. 측정에서 FP(건강 식물을 병해로 오진) 다시 증가할 가능성. 다만 v8 baseline의 FP 10건 자체가 이미 높았던 수치라 약간 증가해도 -5%p 안에서 충분.

---

## 결정 영역 5 — `normalize_structured_result` status fallback

메커니즘 3 대응. 현재:
```python
if status not in ALLOWED_STRUCT_STATUS:
    status = "건강"
```

**옵션 A — fallback을 "병해 의심"으로 변경**
- 불확실 시 안전한 쪽이 "병해 의심"(사용자가 점검 행동하게 유도) vs "건강"(아무것도 안 함). 사용자 가치 관점에선 "병해 의심"이 더 안전.

**옵션 B — fallback "건강" 유지**
- 모델이 enum 출력 잘 지키면 fallback이 거의 안 탐. 다만 measure 결과 가끔 unknown status가 나오면 보수화 누적.

**옵션 C — fallback 없이 raw status 보존 + JSON 스키마(Pydantic Literal) enforce**
- generate를 Gemini로 옮기고 response_schema로 강제하면 가능. 하지만 GPT-4o-mini의 `response_format={"type": "json_object"}`는 키 보장만 하고 enum 보장은 안 함. 현재 구조에선 어려움.

**권장: 옵션 A**
근거 — 메커니즘 3 직접 대응 + 사용자 가치 안전성. ALLOWED_STRUCT_STATUS=`["건강","과습","건조","병해 의심","영양 부족"]`이 enum이고 모델 출력은 대부분 enum 안에 떨어지므로 fallback은 안전망에 가까움. 그 안전망이 "건강"인 것 자체가 보수화의 잠재 원인.

**위험**: 모델이 정상적으로 "건강"을 출력하는 케이스를 fallback이 안 건드림. fallback은 unknown 케이스만 영향이라 측정 영향 미미. 그래도 변경.

**부수 처리 — `default_structured_fallback`도 동일**:
non-rag_failed 분기에서 `status="건강"` → `status="병해 의심"`. JSON 파싱 완전 실패 시 사용자에게 "병해 의심" 보여줘서 점검 행동 유도.

---

## 결정 영역 6 — REQUIRED_WEAK_EVIDENCE_PHRASE 강제

현재 `rag_weak_evidence=True`면:
1. user prompt에 "summary에 반드시 'XX 문구'를 자연스럽게 포함하세요" 강제 instruction 끼움
2. 응답 후 summary에 문구 없으면 prefix로 강제 append

**Phase 2 영역**. phase2_refactoring_plan에서 "강제 = 출력 형식·status enum·언어 3개만"이라고 명시. REQUIRED_WEAK_EVIDENCE_PHRASE는 이 3개에 안 들어감 → 풀어야 할 강제 로직.

**옵션 A — 강제 제거, 자연어 가이드로 완화**
- prompt에서 "유사도가 높지 않을 때는 단정 표현을 피하고 관찰·재촬영 권유 톤으로" 정도만 남김
- post-hoc append 제거
- summary에 강제 문구 prefix 사라짐

**옵션 B — 그대로 유지** ([1-7] 책임 범위 외)
- Phase 2-1~2-7로 미루기

**권장: 옵션 A (포함)**
근거 — generate 프롬프트를 한 번 재설계할 거면 이 강제도 같이 푸는 게 자연. 별도 Phase 2-x 진입 시 generate 프롬프트를 다시 열어 손대는 건 작업 효율 낮음. 다만 [1-7] 범위 폭주 우려가 있으면 옵션 B로 미루는 것도 가능.

**위험**: weak evidence 시 사용자에게 명시적 경고가 사라짐 → 진단 신뢰도 표시 약화. 다만 자연어 가이드가 충분히 들어가면 모델이 자발적으로 "근거가 약합니다" 같은 톤을 summary에 포함할 가능성 큼.

---

## 결정 영역 7 — action_plan 2개 패딩 후처리

현재 `normalize_structured_result`:
```python
_pad = ["지속적으로 관찰하세요.", "빛·물·통풍·습도 환경을 점검하세요."]
while len(plan) < 2:
    plan.append(_pad[len(plan) % 2])
```

**Phase 2 영역**. 강제 후처리.

**옵션 A — 패딩 제거, 프롬프트에서 "action_plan은 2개 이상" 가이드만 유지**
- 모델이 따르면 OK, 안 따르면 1개로 끝남
- 프론트 ResultView가 빈 배열·1개도 보여주도록 동시 변경 필요? 또는 그냥 보여줘도 깨지지 않음

**옵션 B — 패딩 유지** ([1-7] 책임 범위 외)
- Phase 2로 미루기

**권장: 옵션 A (포함)**
근거 — 결정 영역 6과 같은 논리. 한 번에 정리.

**위험**: 모델이 1개만 출력하는 케이스가 가끔 나오면 사용자 UI에서 빈약하게 보일 수 있음. 측정에서 빈도 확인.

---

## 결정 영역 8 — STRUCTURED_DIAGNOSIS_RAG_FAILED 분기 폐기 (decision #3)

phase2_decisions #3에서 결정. RAG 시스템 오류(`rag_failed=True`) 시 가짜 답변 생성 폐기, 빈 dict 반환 + 프론트 에러 UI.

**옵션 A — [1-7]에서 포함 처리**
- `generate_structured_diagnosis_with_gpt`의 `if rag_failed:` 분기 제거 → 빈 dict 반환
- `STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM`/USER_TEMPLATE 프롬프트 제거
- `default_structured_fallback`의 `rag_failed=True` 분기 제거
- `REQUIRED_RAG_FAILED_PHRASE` 상수 제거
- `normalize_structured_result(rag_failed=...)` 인자 단순화

**옵션 B — 별도 작업으로 분리**
- 프론트 에러 UI 변경이 필요한데 그건 [1-9] 영역에 자연스럽게 묶일 수 있음. [1-7]은 generate 자체에 집중.

**권장: 옵션 A**
근거 — decision #3 실행이 한 번에 정리되는 게 깔끔. 프론트 에러 UI는 [1-9]에서 별도. 백엔드는 빈 dict 반환만 하면 됨. main.py의 응답 매핑도 `if not isinstance(sr, dict) or not sr: sr = model_utils.default_structured_fallback()` 부분을 빈 dict 보존으로 변경.

**위험**: 프론트가 아직 빈 structured_result를 처리하지 못하면 진단 화면이 깨질 수 있음. [1-9]까지 백엔드만 변경, 프론트는 [1-9]에서 동시 처리. 그동안은 백엔드가 빈 dict를 반환해도 main.py 디폴트 매핑이 안전망 역할? — 확인 필요. main.py L211-224 보면 빈 dict 그대로 통과시키므로 프론트가 부서질 가능성 있음.

**완화** — main.py에서 "rag_failed이고 빈 dict면 502 같은 명시적 에러 응답으로 변환" 처리를 [1-7]에 포함. 프론트가 부서지지 않게 백엔드가 명시적 에러로 차단. [1-9]에서 프론트 정식 처리 후 502 → 200+empty로 전환.

이 부수 변경까지 포함하면 [1-7] 범위가 약간 커짐. 결정 필요.

---

## 결정 영역 9 — 작업 분할 — 단일 커밋 vs 분리

영향 파일:
1. `app/prompts.py` — STRUCTURED_DIAGNOSIS_JSON_SYSTEM 재작성 + JSON_USER_TEMPLATE 수정 + RAG_FAILED 프롬프트 제거
2. `app/model_utils.py` — generate_structured_diagnosis_with_gpt 재구성 + normalize_structured_result fallback 변경 + default_structured_fallback 변경 + REQUIRED_WEAK_EVIDENCE_PHRASE 강제 제거 + REQUIRED_RAG_FAILED_PHRASE 상수 제거 + rag_failed 분기 제거
3. `app/graph.py` — generate_node의 context_summary 재조립 (analyze 6필드 직접 사용)
4. `app/main.py` — rag_failed 시 502 에러 변환 (결정 영역 8 옵션 A 채택 시)

**옵션 A — 단일 커밋**
- 메시지: `feat: generate_node 재설계, observed_symptoms 활용 + 강제 로직 일부 완화 ([1-7])`
- 측정·검증 후 단일 커밋
- 영향 4개 파일 한 묶음

**옵션 B — 2단 분리**
- 커밋 1: 입력 변경 (context_summary 재조립 + STRUCTURED_DIAGNOSIS_JSON_SYSTEM 재작성)
- 커밋 2: 후처리 완화 (normalize fallback + action_plan 패딩 제거 + RAG_FAILED 분기 제거)
- 측정도 2번

**권장: 옵션 A**
근거 — 측정이 2번이면 cost·시간 2배 + 회귀 원인 분리도 의미 약함 ([1-7] 자체가 generate 정비 한 덩어리). 두 변경이 합쳐서 is_healthy 회복 효과를 내야 함. 분리하면 단일 커밋의 효과를 측정하기 어려움.

**위험**: 단일 커밋이라 회귀 시 revert 단위가 커짐. 다만 [1-7]은 게이트 대상이 아니라 회귀해도 [1-9] 진입 전 재시도 가능. revert 위험 낮음.

---

## 결정 영역 10 — 측정 방법

**산출물**: `eval/after_phase1_generate.json` (decision #5 명시 파일명 아님, [1-7]만의 측정).

**목표 (암묵적 게이트)**:
- is_healthy precision: 23.1% 회복 + 가능하면 그 이상 (메커니즘 3 해소 효과)
- is_healthy recall: 60% 회복 + 가능하면 그 이상 (메커니즘 1+2 해소 효과)
- plant_korean accuracy: [1-5] 89.3% 유지 (이 작업은 analyze에 손 안 댐 → 변동 없어야 정상)
- is_diseased accuracy: 가능하면 baseline 63.6% 이상 (회복 + 알파)
- JSON 파싱 실패율: 0% 유지

**비교 대상**: v8 baseline + after_phase1_wiring 둘 다 비교. v8 회복이 최우선, [1-5]보다 악화는 절대 금지.

**측정 워크플로**:
1. [1-7] 작업 완료 → 커밋 전 측정
2. `python scripts/run_eval.py` (RUN_EVAL_OUT 환경변수로 출력 경로 지정 가능 — [1-5]에서 추가됨)
3. v8 baseline / after_phase1_wiring 둘 다와 비교표 작성
4. is_healthy precision·recall 회복 확인
5. 회복했으면 커밋·push. 안 했으면 프롬프트 재조정.

**가설 예측**:
- is_healthy precision: 11.1% → 25~35% (메커니즘 3 fallback 변경 + 메커니즘 2 가이드 제거)
- is_healthy recall: 20% → 60~80% (observed_symptoms 입력 추가가 핵심 — 모델이 "병징 보고됨"을 직접 보면 FN 줄어듦)
- plant_korean: 89.3% 유지 (analyze 무변경)
- latency: 32.4s 유지 또는 약간 감소 (프롬프트 길이는 비슷, 후처리 일부 제거)

**위험 — 측정 표본 5장의 노이즈**: GT unhealthy 5장의 노이즈가 커서 precision/recall이 1~2 케이스 흔들림에 표면적으로 크게 변동. 그래도 방향성(상승/하강)은 명확히 보임. 표본 확대는 [3단계] 데이터셋 교체 영역.

---

## 권장 작업 분할 — 단일 커밋 (재확인)

**커밋 메시지 (권장)**: `feat: generate_node 재설계, observed_symptoms 활용 + 강제 로직 일부 완화 ([1-7])`

**작업 묶음**:

1. `app/prompts.py`
   - `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 재작성: "Plant.id 팩트" 표현 제거, "건강에 가깝게" 가이드 제거, observed_symptoms 활용 가이드 추가, plant_confidence/alt_candidates 활용 가이드 추가
   - `STRUCTURED_DIAGNOSIS_JSON_USER_TEMPLATE` 수정: weak_instruction 강제 표현 완화
   - `STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM` / `STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_USER_TEMPLATE` 제거

2. `app/graph.py`
   - `generate_node` context_summary 재조립: analyze 6필드 직접 사용 (plant_name, plant_name_korean, plant_confidence, alt_candidates, visual_description, observed_symptoms)
   - 기존 `format_is_healthy_for_prompt(ihp)`, `format_top_candidates_for_prompt(tc)`, `state.get('disease_name')` 호출 제거

3. `app/model_utils.py`
   - `generate_structured_diagnosis_with_gpt` 재구성:
     - `rag_failed=True` 분기 통째 제거 → 빈 dict `{}` 반환
     - `REQUIRED_WEAK_EVIDENCE_PHRASE` post-hoc append 제거
     - `REQUIRED_RAG_FAILED_PHRASE` post-hoc append 제거
     - `weak_instruction` 강제 문구 완화 (자연어 가이드만)
   - `normalize_structured_result`:
     - status fallback "건강" → "병해 의심"
     - action_plan 2개 패딩 제거
     - `rag_failed` 인자 제거
   - `default_structured_fallback`:
     - non-rag_failed 분기 status "건강" → "병해 의심"
     - rag_failed 분기 제거
   - 상수 `REQUIRED_RAG_FAILED_PHRASE` / (필요시) `REQUIRED_WEAK_EVIDENCE_PHRASE` 정리

4. `app/main.py`
   - rag_failed 시 빈 dict 보호: `if rag_failed: raise HTTPException(502, "진단 정보를 가져오지 못했습니다")` 추가
   - 또는 state에 rag_failed 플래그를 응답 전 확인하는 분기 추가
   - structured_result 빈 dict 시 `default_structured_fallback()` 호출 제거 → 빈 dict 그대로 전달 (백엔드 측 안전망 해제, 502가 더 정직)

5. 측정
   - `python scripts/run_eval.py` (RUN_EVAL_OUT=eval/after_phase1_generate.json)
   - v8 baseline / after_phase1_wiring 비교

6. 회복 확인 시 커밋·push.

**총 라인 변경 추정**: 200~300줄. 프롬프트 재작성 + model_utils 함수 본체 정비 + graph generate_node + main.py 1~2줄.

---

## 롤백 전략

[1-7]은 회귀 게이트 대상 아님. 다만 다음 두 케이스에서 재시도:
1. **is_healthy 회복 실패** (precision <23% 또는 recall <60%): 프롬프트 가이드 재조정. 결정 영역 2의 "관찰된 증상이 1개 이상 있으면 '건강' 금지" 가이드 강도 조정. 단일 커밋이라 `git reset --soft HEAD~1` 후 프롬프트 패치 → 재측정 → 재커밋.
2. **plant_korean 회귀** (analyze 무변경인데도 -5%p): 예상치 못한 영향. 매우 드물 것. 발생 시 [1-7] revert + 원인 분석.

`eval/after_phase1_wiring.json`은 git에 있으니 비교 baseline 보존.

---

## 다음 단계 연계

[1-7] 통과 후:
- **[1-6] keyword_node 축소** (decision #2): observed_symptoms를 영문 번역해서 RAG 쿼리에 사용. `build_rag_search_query_with_gpt` 호출 제거 또는 단순화.
- **[1-8] retrieve_node 정비**: keyword 변경에 따른 후속 정리.
- **[1-9] state/schema 슬림화 + 프론트 동시** 🔴 두 번째 회귀 게이트: 죽은 키 일괄 제거 + 6신규 키 응답 노출 + types/diagnosis.ts·ResultView 동시 변경 + rag_failed 시 백엔드 502 → 200+empty 전환(프론트 에러 UI 동시 구현).
- **[1-10]**: Plant.id 완전 제거 + 1단계 baseline (eval/after_phase1.json) + temperature A/B/C 튜닝.

---

## 사용자 확정 대기 항목

작업 프롬프트(`1-7_generate_재설계_프롬프트.md`)를 만들기 전 확인:

1. **결정 영역 1 권장 (옵션 A — "Plant.id 팩트" 통째 제거 + analyze 6필드 새 섹션)** 동의?
2. **결정 영역 2 권장 (옵션 A — observed_symptoms 새 섹션 + 프롬프트 가이드 "1개 이상이면 '건강' 금지")** 동의?
3. **결정 영역 3 권장 (옵션 A — plant_confidence/alt_candidates 활용 가이드 포함)** 동의?
4. **결정 영역 4 권장 (옵션 A — "건강에 가깝게" 줄 통째 삭제)** 동의?
5. **결정 영역 5 권장 (옵션 A — status fallback "건강" → "병해 의심" + default_structured_fallback 동일)** 동의?
6. **결정 영역 6 (REQUIRED_WEAK_EVIDENCE_PHRASE 강제 완화) — [1-7]에 포함 vs Phase 2로 미루기**: 포함 권장. 동의?
7. **결정 영역 7 (action_plan 2개 패딩 제거) — [1-7]에 포함 vs Phase 2로 미루기**: 포함 권장. 동의?
8. **결정 영역 8 (STRUCTURED_DIAGNOSIS_RAG_FAILED 분기 폐기 — decision #3 실행) — [1-7]에 포함 + main.py 502 변환**: 포함 권장. 동의?
9. **결정 영역 9 권장 (단일 커밋)** 동의?
10. **`REQUIRED_WEAK_EVIDENCE_PHRASE` 상수 — 완전 제거 vs 상수만 남기고 미사용**: 결정 영역 6 옵션 A 채택 시 상수도 같이 제거 권장. 동의?

위 10개에 답을 박아주면 작업 프롬프트 md 작성으로 넘어감.

---

## 부록 — [1-7] 작업 후 자동 점검 항목

```bash
# 1. 단위 테스트 회귀 없음 (analyze_node, vision/* 등 무영향)
pytest tests/ -v -m "not integration"
# 기대: 23/23 passed

# 2. import 정합성
python -c "from app.graph import build_diagnosis_graph; from app.main import app; from app.model_utils import generate_structured_diagnosis_with_gpt; print('ok')"

# 3. 상수 제거 확인 (RAG_FAILED 관련)
python -c "from app import prompts; assert not hasattr(prompts, 'STRUCTURED_DIAGNOSIS_RAG_FAILED_JSON_SYSTEM'); print('ok')"

# 4. 회귀 측정
RUN_EVAL_OUT=eval/after_phase1_generate.json python scripts/run_eval.py
# 기대: v8 precision 23% / recall 60% 이상 회복

# 5. 라이브 호출 1회 (수동, GEMINI_API_KEY + OPENAI_API_KEY 필요)
# self_haengun_002.jpg (unhealthy) 업로드 → status가 "건강"이 아닌지 확인
```
