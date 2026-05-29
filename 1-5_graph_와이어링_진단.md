# [1-5] graph 와이어링 진단

> 목적: [1-4]에서 unwired 상태로 만든 `analyze_node`를 LangGraph에 끼우고 `identify_node` + `describe_node`를 대체하는 작업의 **사전 진단**.
> 실제 Claude Code 의뢰 프롬프트(`1-5_graph_와이어링_프롬프트.md`)는 이 진단에 사용자 확정을 받은 뒤 별도로 작성.
>
> 작성일: 2026-05-29
> 단계: 리팩토링 1단계의 다섯 번째 하위 작업 ([1-5]) — **첫 회귀 게이트 (decision #5, -5%p)**
> 선행: [1-1] Protocol / [1-2] GeminiProvider / [1-3] 프롬프트 v3 / [1-4] analyze_node factory 완료. [1-3]/[1-4]는 push 대기.

---

## [1-5]의 성격 — 왜 진단을 먼저 박는가

지금까지 [1-1]~[1-4]는 **신규 파일만** 만들고 기존 코드를 한 줄도 안 건드렸다. 그래프와 main.py와 schemas.py와 프론트가 전부 옛 경로로 동작 중이라는 뜻이다. `app/vision/`과 `app/nodes/`는 GitHub에 박혀 있지만 런타임에서는 사용되지 않는다.

[1-5]는 **그 격리를 깨는 첫 작업**이다. 그래프가 analyze 경로로 갈아타는 순간 `identify_node`(Plant.id 호출)와 `describe_node`(GPT-4o-mini 묘사 호출)가 사라지고, 그 출력에 의존하던 `keyword_node`·`retrieve_node`·`generate_node`·`main.py:211-224 응답 매핑`·`프론트`까지 연쇄 영향권에 들어간다. v8 baseline의 모든 수치(식물명 90% / is_healthy precision 23%·recall 60% / status 분포 / 평균 21.1s)는 이 순간을 기준으로 재측정되고, decision #5에 따라 어느 지표든 -5%p 회귀하면 머지가 막힌다.

연쇄 영향이 많다는 건 **결정 한 번에 실수할 자리도 많다**는 뜻이다. 그래서 코드를 짜기 전에 8개 결정 영역을 분리해 각각 옵션·권장·위험·미루기를 박아둔다. 이 진단을 통과한 결정만 작업 프롬프트에 들어간다.

---

## 결정 영역 1 — DiagnosisState 매핑 전략

`make_analyze_node()`는 6필드 dict를 반환한다(`plant_name`·`plant_name_korean`·`plant_confidence`·`alt_candidates`·`visual_description`·`observed_symptoms`). 기존 `DiagnosisState` TypedDict(graph.py 상단)는 `plant_name`만 공유하고 나머지 5개는 새 키다. 그리고 기존 키 9개(`disease_name`·`confidence`·`is_healthy_prob`·`top_candidates`·`description`·`keywords`·`keywords_en`·`rag_query`·`fallback_plant_name`)는 여전히 하위 노드와 응답 매핑이 의존한다.

**옵션 A — 6필드 신규 키만 추가, 기존 키는 그대로 유지하되 빈 값으로 채움 (브리지)**
- analyze 출력의 `plant_name`은 기존 `plant_name`에 그대로 덮어쓰기 (학명 영문, 형식 동일).
- `visual_description` → `description`도 같은 키에 매핑(둘 다 한국어 묘사). 즉 `description = visual_description`. 그러면 keyword_node·generate_node의 `state.get("description")` 호출이 그대로 작동.
- `disease_name`·`confidence`·`is_healthy_prob`·`top_candidates`는 analyze가 만들지 못하니 `None`/`None`/`None`/`[]`로 박음.
- 6개 신규 키(`plant_name_korean`·`plant_confidence`·`alt_candidates`·`visual_description`·`observed_symptoms`)도 별도로 state에 추가.

**옵션 B — 6필드만 추가하고 generate_node를 새 키 직접 읽도록 동시 수정**
- 깔끔하지만 [1-5]의 책임 범위가 폭주(generate 프롬프트도 변경 → [1-7] 영역 침범).
- 회귀 원인 분리 불가능.

**권장: 옵션 A (브리지 패턴)**
근거 — [1-4] 보고에서 결정한 변수 격리 원칙. [1-5]는 그래프 경로 전환만 측정하고, generate 프롬프트는 [1-7]에서 분리. `description = visual_description` 브리지는 keyword·generate를 한 줄도 안 건드리고 작동시키는 가장 싼 방법.

**위험**: `description`이 GPT-4o-mini "묘사형"에서 Gemini "관찰형"으로 톤이 미묘하게 바뀐다 → keyword 추출이 약간 흔들릴 수 있음. 회귀 게이트가 잡아낼 영역이라 측정으로 확인.

---

## 결정 영역 2 — 기존 키 처분 ([1-9]까지 어떻게 살려둘지)

`is_healthy_prob`·`top_candidates`·`disease_name`·`confidence`는 Plant.id 전용 정보다. analyze는 이걸 생성하지 못하고 또 책임도 없다(decision #1: 진단은 generate).

**권장: 전부 빈 값으로 채워 state에 박아둠 + 응답 매핑까지 무변경**
- generate_node의 `format_is_healthy_for_prompt(None)` → "없음" 출력 (`app/model_utils.py`에 이미 존재).
- `format_top_candidates_for_prompt([])` → "없음" 출력 (동일).
- main.py 응답 매핑의 `PlantIdentificationResult(plant_name=..., disease_name=None, confidence=None, is_healthy_prob=None, top_candidates=[])`는 `Optional` 타입이라 그대로 통과.
- 즉 [1-5]에서는 **빈 값 흘려보내기**만, [1-9]에서 state·schemas·types·프론트 동시 제거.

**위험 — generate가 "Plant.id 팩트" 섹션의 None을 보고 보수적으로 "건강"으로 도망갈 수 있음**
v8 baseline의 is_healthy precision 23%·recall 60%는 이미 약점이다. Plant.id 신호가 사라지면 generate가 더 보수적이 되어 FP가 줄어들 수도 있고(precision↑), 반대로 신호 부족으로 "건강" 디폴트가 늘어 recall이 떨어질 수도 있다. 사전 예측 불가 → 측정으로 확인.

**완화 — generate 프롬프트는 [1-5]에서 절대 손대지 않는다.** 측정 후 회귀가 -5%p 넘으면 [1-7]을 [1-6]/[1-8]보다 먼저 처리하는 순서 변경으로 대응(작업 프롬프트에 분기 기록).

---

## 결정 영역 3 — keyword_node 입력 변경

decision #2: keyword_node는 "영문 번역 전용으로 축소". 하지만 그 축소는 함수 본체를 거의 새로 쓰는 작업이라 [1-5]에서 다루면 회귀 원인 분리가 깨진다.

**권장: [1-5]에서는 keyword_node 본체 무변경. 입력 브리지만 작동.**
- analyze가 `description = visual_description` 브리지로 채워주면 `state.get("description")` 그대로 작동.
- `state.get("plant_name")` — analyze가 학명을 채워주니 그대로 작동.
- `state.get("disease_name")`·`is_healthy_prob`·`top_candidates`·`confidence` — None/[]/None 흘려보내기. `build_rag_search_query_with_gpt` 안에서 None 처리되는지 확인 필요(현재 코드 미확인 부분 — 작업 프롬프트의 사전 확인 항목으로 박음).
- `observed_symptoms`는 [1-5]에서 활용 안 함. [1-6]에서 keyword가 영문 번역 전용으로 축소될 때 입력으로 들어옴.

**위험**: `build_rag_search_query_with_gpt`가 None 인자에 NPE 던지면 [1-5] 작업 중에 발견. 작업 프롬프트에서 "사전 확인" 항목으로 둠.

---

## 결정 영역 4 — generate_node 영향

graph.py L380~395 generate_node 코드 본체:
```python
desc = state.get("description") or ""
pn = state.get("plant_name")
conf = state.get("confidence")
ihp = state.get("is_healthy_prob")
tc = state.get("top_candidates")
...
f"- 분류 신뢰도: {conf}\n"
f"- 건강일 추정 확률 is_healthy (0~1): {model_utils.format_is_healthy_for_prompt(ihp)}\n"
f"- 분류 상위 후보(최대 3): {model_utils.format_top_candidates_for_prompt(tc)}\n"
f"- 질병/비질병 힌트(1위): {state.get('disease_name')}\n"
```

**권장: generate_node 함수 본체 한 줄도 손대지 않는다.**
- `confidence`가 `None`이면 f-string은 `"분류 신뢰도: None"` 출력 → 프롬프트에 그대로 들어감. GPT-4o-mini는 "None"을 "정보 없음"으로 해석할 가능성이 높음. 다만 v8 베이스라인의 GPT 패턴 변화를 확인할 자리가 없으니 측정 후 판단.
- `format_is_healthy_for_prompt`·`format_top_candidates_for_prompt`는 이미 None/[] 안전.
- `disease_name`이 None일 때 f-string은 `"질병/비질병 힌트(1위): None"`. 위와 동일.

**더 깔끔한 옵션 — `state.get('disease_name')` 부분만 빈 값 처리하는 1줄 수정**
`f"- 질병/비질병 힌트(1위): {state.get('disease_name') or '없음'}\n"` / `f"- 분류 신뢰도: {conf if conf is not None else '없음'}\n"`. 다만 generate에 손을 대는 순간 [1-5] 변수 격리가 깨짐. **하지 않는다.** 작업 후 측정에서 "None" 문자열 노출이 GPT 응답에 영향을 주는지 확인 → 영향 있으면 [1-7]에서 일괄 정리.

---

## 결정 영역 5 — main.py L211-224 응답 매핑

```python
pid = PlantIdentificationResult(
    plant_name=out.get("plant_name"),
    disease_name=out.get("disease_name"),
    confidence=out.get("confidence"),
    is_healthy_prob=out.get("is_healthy_prob"),
    top_candidates=_cand,
)
```

**권장: 한 줄도 안 건드림.**
- 모든 필드가 `Optional[...]`이라 `None`/`[]` 그대로 통과 → 프론트 `types/diagnosis.ts`의 `null` 허용과 일치.
- `plant_name`은 analyze가 채워주니 학명이 나옴 (PlantIdResult 호환).
- `confidence`는 float `0.0~1.0` 자리에 `None` → 프론트 표시 처리 의존(ResultView가 null 처리하는지 [1-9]에서 확인).
- 6개 신규 필드(plant_name_korean·plant_confidence·alt_candidates·visual_description·observed_symptoms)는 [1-5]에서 응답에 노출하지 않음 → state에는 있지만 DiagnosisResponse에 매핑 안 함. **[1-9]에서 schemas.py + types/diagnosis.ts + ResultView 동시 변경으로 노출**.

**위험**: plant_name_korean이 이미 analyze에 있는데 응답에 안 박으면 프론트가 PLANT_NAME_KO_MAP에 의존해야 함 → 사용자 입장에서 "Dracaena reflexa"가 표시될 수도. v8 baseline은 어차피 PLANT_NAME_KO_MAP 변환에 의존했으니 회귀는 없음. [1-9] 머지 시점에 자연스럽게 개선됨.

---

## 결정 영역 6 — mime_type 동기화

main.py는 PIL로 모든 업로드를 JPEG로 재인코딩한 뒤 graph에 `image_bytes`만 넘긴다(`process_image()` 함수). `validate_magic_number`로 jpeg/png 구분은 하지만 그래프 입력 시점에는 이미 JPEG.

**권장: state에 mime_type 키를 추가하지 않고, analyze_node 내부에서 `VisionInput(image_bytes=..., mime_type="image/jpeg")` 하드코딩.**
- 현재 main.py가 어차피 JPEG로 재인코딩 → 그래프 입력은 100% JPEG.
- mime_type을 state로 흘리는 건 미래 확장(원본 보존)에 대비한 추상화인데, [1-4]에서 만든 `VisionInput`이 이미 mime_type을 받으므로 noop 인자 하나 박으면 됨.
- analyze_node closure 안에서 `VisionInput(image_bytes=state["image_bytes"], mime_type="image/jpeg")` 한 줄.
- 만약 추후 png 원본 보존이 필요하면 state에 `image_mime_type` 키 추가하는 작업을 별도로.

**위험**: 없음. 외부 영향 0.

---

## 결정 영역 7 — GeminiProvider 인스턴스 위치 ⚠️ 중요

`GeminiProvider`는 `genai.Client`를 생성자에서 보관(`[1-2]` 핵심 설계 결정). client 생성은 가벼우니 매 요청마다 만들어도 동작은 하지만 다음 두 가지가 걸린다.
- ANALYZE_SYSTEM 프롬프트(1459자)를 생성자에 박는 패턴([1-3] 확정) → 매 요청마다 prompt 객체 재생성은 낭비.
- httpx.AsyncClient는 이미 FastAPI lifespan에서 만들어 `init_graph(client)`에 주입 중. 같은 패턴이 자연.

**옵션 A — FastAPI lifespan에서 생성, `init_graph(client, vision_provider)`로 주입, `build_diagnosis_graph(client, vision_provider)`로 시그니처 확장**
- 일관성 best. httpx와 GeminiProvider 둘 다 lifespan 관리.
- 시그니처 변경 → `scripts/run_eval.py` / `scripts/eval_rag.py`도 호출부 수정 필요.

**옵션 B — `build_diagnosis_graph` 내부에서 매번 생성**
- 시그니처 무변경이라 호출부 안전.
- 매 빌드마다 Client + system_prompt 인스턴스화 → 비효율.
- 단일 빌드 후 `_compiled_graph` 캐시되므로 사실상 1회만 생성. 비용 무시 가능.

**옵션 C — 모듈 싱글톤 (app/vision/gemini.py 또는 graph.py 모듈 변수)**
- import 시점 부작용(키 없으면 RuntimeError) → 테스트 빡셈.
- 비추천.

**권장: 옵션 A.**
근거 — 시그니처 변경 비용(run_eval.py 1줄, eval_rag.py 1줄 추정)이 작고, 일관성·테스트 용이성·미래 second provider 추가 시 확장성이 우월. `build_diagnosis_graph(client, vision_provider)` 두 인자.

**부수 변경** — `scripts/run_eval.py`의 `build_diagnosis_graph(client)` 호출 + `_initial_state` 둘 다 [1-5] 작업 범위. 회귀 측정 스크립트가 작동하지 않으면 게이트 통과 자체 불가.

---

## 결정 영역 8 — 회귀 측정 방법

decision #5 회귀 임계: plant_korean / status / is_diseased / action_keywords 모두 baseline 대비 -5%p 이내. JSON 파싱 실패율은 +5%p 이내.

**v8 baseline (eval/baseline.json)**:
- 식물명 정확도: 90.0% (matchable 30장, correct 27)
- is_healthy precision 23.1% / recall 60% (FP 10건)
- status 분포: 건강 20·병해 10·과습 2·영양 1
- JSON 파싱: 100%
- latency 평균 21.1s

**측정 산출물**: `eval/after_phase1_wiring.json` (decision #5 명시 파일명).

**측정 워크플로**:
1. [1-5] 작업 완료 → 커밋 전 측정
2. `.env`에서 `PLANT_ID_API_KEY` 일시 주석 처리 (analyze 경로만 타게) — 또는 analyze_node가 이미 PLANT_ID_API_KEY 무시하면 그대로
3. `python scripts/run_eval.py` → `eval/after_phase1_wiring.json` 생성
4. v8 baseline과 4개 지표 비교
5. -5%p 이내면 통과 → 커밋·push. 초과면 롤백 또는 [1-7]/[1-9] 순서 변경 결정.

**예상 결과 — 가설**:
- 식물명: [1-2] 통합 검증대로 Gemini 2.5 Pro가 Dracaena 종 구분에서 우위 → 90% → 92~95% 기대 (단, 33장 중 8장은 [1-3] 검증에서 본 케이스, 25장은 미검증이라 상승 폭 보장 없음).
- is_healthy: 미지. Plant.id `is_healthy_prob` 신호가 사라지면서 generate의 패턴이 흔들릴 가능성 큼. FP 감소(precision 상승) 가능 / "건강" 디폴트 상승(recall 하락) 가능 — 둘 중 어느 쪽인지 측정 전엔 모름.
- latency: 외부 호출 7회 → 4회 (Plant.id 1회 + GPT-4o-mini 묘사 1회 제거 + Gemini analyze 1회 추가 = 순 -1회). 21s → 17~19s 기대.
- JSON 파싱: 100% 유지 기대 (`response_schema=AnalyzeResult` 보장).

---

## 권장 작업 분할 — 단일 커밋

**권장: [1-5] 전체를 단일 커밋으로 처리.**

근거 — 그래프 와이어링은 "절반만 분리" 불가능. analyze가 끼워지면 identify/describe는 죽어야 하고, build_diagnosis_graph 시그니처 변경은 main.py·scripts 동시 변경이 강제됨. 중간 단계 커밋은 동작 불가 상태.

**커밋 메시지 (권장)**: `feat: analyze 경로로 graph 와이어링, identify/describe 제거 ([1-5])`

**작업 묶음**:
1. `app/graph.py`
   - DiagnosisState에 6개 신규 키 추가 (plant_name_korean·plant_confidence·alt_candidates·visual_description·observed_symptoms).
   - `build_diagnosis_graph(client, vision_provider)` 시그니처 확장.
   - `identify_node`·`describe_node` 정의 제거.
   - `make_analyze_node(vision_provider)` import 후 그래프 첫 노드로 등록.
   - 노드 wrapping: analyze 결과(6필드)를 받아 `description = visual_description` 브리지 + 기존 키 빈 값 채우기 dict 반환.
   - `set_entry_point("analyze")` + edge `analyze → keyword → retrieve → generate → END`.
2. `app/main.py`
   - lifespan에 `GeminiProvider` 생성 (`get_gemini_api_key()` 사용, `system_prompt=prompts.ANALYZE_SYSTEM`).
   - `init_graph(client, vision_provider)`로 변경.
   - L211-224 응답 매핑 무변경.
   - `process_image()` 무변경 (JPEG 재인코딩 유지).
3. `scripts/run_eval.py`
   - `build_diagnosis_graph(client, vision_provider)` 호출부 수정.
   - `GeminiProvider` 생성 1줄 추가.
   - `_initial_state`에 6개 신규 키 default 추가(빈 값).
4. `scripts/eval_rag.py`
   - 위와 동일한 호출부 수정 (작업 프롬프트의 사전 확인 항목).
5. 측정
   - `python scripts/run_eval.py` → `eval/after_phase1_wiring.json` 생성.
   - decision #5 비교표 작성 (콘솔 출력 + json).
6. 검증 통과 시 커밋·push.

**총 라인 변경 추정**: 100~150줄. 신규 임포트 + state 키 + analyze wrapping closure + identify/describe 삭제 + main lifespan 1줄 + scripts 2개 호출부.

---

## 롤백 전략

회귀 -5%p 초과 시:
1. **즉시 `git revert HEAD`** — 단일 커밋이라 revert 1회로 v8 상태 완전 복원.
2. 회귀 원인 진단 — `eval/after_phase1_wiring.json` 케이스별 비교로 어느 지표·어느 케이스에서 깨졌는지 식별.
3. 분기:
   - **is_healthy 회귀** → [1-7] generate 프롬프트 재설계를 [1-6]/[1-8]보다 우선 처리. generate가 `is_healthy_prob`/`top_candidates`/`disease_name` 없이도 정상 작동하도록 프롬프트 변경 후 [1-5] 재진입.
   - **식물명 회귀** → [1-3] 프롬프트 v4 또는 temperature 튜닝(decision #6) 선행 후 [1-5] 재진입.
   - **JSON 파싱 회귀** → `response_schema` 호환성 문제 → AnalyzeResult Pydantic 모델 점검.
4. 재측정 → 통과 시 다시 커밋.

**커밋 분리 전략 검토 후 채택 안 함**: "analyze 추가 + identify 유지 → identify 제거"의 2단 분리도 고민했으나, 두 노드가 동시에 plant_name을 채우는 경합 + state 키 충돌이 발생해 더 복잡해짐. **단일 커밋 + revert**가 가장 단순한 안전망.

---

## 다음 단계 연계 ([1-6]~[1-10])

[1-5] 통과 후 진입 가능:
- **[1-6] keyword_node 축소**: 영문 번역 전용으로 (decision #2). `observed_symptoms` 입력으로 활용 시작. `build_rag_search_query_with_gpt` 호출 제거 또는 단순화.
- **[1-7] generate_node 정비**: "Plant.id 팩트" 섹션 제거, `visual_description` + `observed_symptoms` 입력으로 재설계. STRUCTURED_DIAGNOSIS_JSON_SYSTEM 프롬프트 수정.
- **[1-8] retrieve_node 정비**: keyword 변경에 따른 후속 정리.
- **[1-9] state/schema 슬림화 + 프론트 동시**: 죽은 키 일괄 제거 (is_healthy_prob·top_candidates·disease_name·confidence + DiagnosisResponse의 PlantIdentificationResult + types/diagnosis.ts + ResultView L57). **두 번째 회귀 게이트 -5%p**.
- **[1-10]**: Plant.id 완전 제거 (`identify_plant_disease_api` 함수·`PLANT_ID_API_KEY` reader 삭제) + 死코드 정리 + `eval/after_phase1.json` 측정 + temperature A/B/C 튜닝.

---

## 사용자 확정 대기 항목

작업 프롬프트(`1-5_graph_와이어링_프롬프트.md`)를 만들기 전 확인:

1. **결정 영역 1 권장 (옵션 A 브리지)** 동의?
2. **결정 영역 4 권장 (generate_node 무변경)** 동의? 또는 `state.get('disease_name') or '없음'` 1줄 수정도 [1-5]에 포함할지?
3. **결정 영역 7 권장 (옵션 A — `build_diagnosis_graph(client, vision_provider)` 시그니처 확장)** 동의?
4. **단일 커밋 전략** 동의?
5. **temperature 인자** — [1-2]에서 `GeminiProvider(temperature=None)`로 기본값 미설정. [1-5]에서도 None 유지 → decision #6 따라 [1-10] 후 A/B/C 튜닝. 동의?
6. **PLANT_ID_API_KEY 처리** — `.env`에서 일시 주석 처리 후 측정 vs analyze_node가 `identify_node` 대체했으니 그대로 둬도 됨. 후자 권장(코드 정합성).
7. **두 번째 워킹트리 임시 파일** — [1-4]의 `_validate_analyze_prompt_v2.py` 같은 검증 스크립트가 [1-5]에도 필요한가? 권장: 불필요. `scripts/run_eval.py`가 정식 회귀 측정 도구.

위 7개에 답을 박아주면 작업 프롬프트 md 작성으로 넘어감.

---

## 부록 — [1-5] 작업 후 자동 점검 항목

작업 프롬프트에 박을 검증 명령어들:

```bash
# 1. 단위 테스트 회귀 없음
pytest tests/ -v -m "not integration"
# 기대: 기존 23개 모두 passed

# 2. import 정합성
python -c "from app.graph import build_diagnosis_graph; from app.main import app; print('ok')"

# 3. graph 빌드 가능 (GeminiProvider 정상 인스턴스화)
python -c "from app.main import lifespan; print('lifespan ok')"

# 4. 회귀 측정
python scripts/run_eval.py
# 기대: eval/after_phase1_wiring.json 생성, v8 -5%p 이내

# 5. 라이브 호출 1회 (수동, GEMINI_API_KEY 필요)
# self_haengun_001.jpg 업로드 → /diagnose 호출 → DiagnosisResponse 정상 응답
```
