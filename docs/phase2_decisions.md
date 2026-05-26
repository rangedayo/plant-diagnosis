# Phase 2 결정사항 요약

> Phase 2(리팩토링 설계) 종료 시점의 누적 결정 10개를 1쪽으로 정리. 평가셋 라벨링 작업(1~2주 예상) 중 컨텍스트가 흩어지거나 새 대화창에서 [1-0]을 시작할 때 회복용으로 사용.
>
> 작성일: 2026-05-26 / Phase 2 산출물: `phase2_refactoring_plan.md` 응답 전체 (2-A ~ 2-F)
>
> 후속 작업 진입점: **[1-0] 평가셋 라벨링 + baseline 측정 스크립트**

---

## 1. analyze JSON 8필드 → 6필드 ((c) 결정)

`is_healthy: bool`과 `health_notes: str`를 제거. analyze는 **관찰**(plant_name / plant_name_korean / plant_confidence / alt_candidates / visual_description / observed_symptoms), generate는 **진단**(status enum)으로 책임 분리.

**근거**: is_healthy(analyze)와 status(generate) 모순은 RAG가 analyze가 못 본 정보를 가져오는 정상 동작이므로 프롬프트 강제로 누르면 RAG 의미가 깎임. 스키마 설계로 모순 표면 원천 차단이 가장 단순.

## 2. keyword_node 유지 — 영문 번역 전용으로 축소

analyze가 한국어 observed_symptoms를 출력 → keyword_node는 영문 번역 1콜만 담당. 3단계(다국어 임베딩) 진입 시 제거 재검토.

**근거**: main_rag 컬렉션이 현재 영문. observed_symptoms를 그대로 영문 임베딩에 넣으면 검색 품질 저하 위험. 3단계까지의 안전 경로.

## 3. STRUCTURED_DIAGNOSIS_RAG_FAILED 분기 폐기

RAG 시스템 오류 시 가짜 답변 생성 폐기. 빈 dict 반환 + 프론트가 "진단 정보를 가져오지 못했습니다" 에러 UI 표시.

**근거**: 시스템 오류 시 LLM 호출은 비용 낭비 + 정직성 훼손. 정직한 에러 노출이 사용자 신뢰에 더 유리.

## 4. SDK 사전 조사 [1-1.5] 별도 task 분리

`google-genai` vs `google-generativeai`, APIError import 경로, 재시도 속성명, `genai.Client` thread-safety, async 메소드 지원 여부, Literal 타입 SDK 호환성 — 6항목을 30~60분 별도 task로 사전 검증.

**근거**: [1-2 GeminiProvider 구현]의 (추정) 항목 4곳을 사전 분리하면 1-2가 구현만으로 2~3시간에 마무리 가능. 빡빡한 작업 단위 회피.

## 5. 회귀 임계 -5%p (강화)

plant_korean / status / is_diseased / action_keywords 일치율 모두 baseline 대비 -5%p 이내. JSON 파싱 실패율은 +5%p 이내. [1-5](graph 와이어링 전환)와 [1-9](스키마 슬림화) 머지 게이트.

**근거**: 초기 -10%p는 관대. 평가셋 20~30장에서 -10%p는 2~3건 회귀 = 실질적 품질 저하. action_keywords는 baseline 절대값이 30% 미만이면 라벨 품질 점검 후속 task 분리.

## 6. temperature / load_history N 튜닝 위치

- **temperature**: 1단계 완료 직후 0.0 / 0.2 / 0.5 A/B/C, 평가셋으로 최적값 채택
- **load_history N**: 4단계 진입 시 N=2 / 3 / 5 A/B/C (Phase 3 영역, 메모만)

**근거**: 둘 다 직관 초기값으로 시작하면 회귀 시 원인 분리 어려움. 단계 완료점에서 격리 튜닝하면 baseline 대비 영향 정량화 가능.

## 7. 이미지 중복 검사 — (image_hash, plant_handle) UNIQUE + cached 플래그

진단 1건당 sha256 hash 계산 → `(image_hash, plant_handle)` 조회 → 히트 시 graph 스킵, 기존 레코드 반환 + `"cached": true` 플래그. 같은 이미지를 다른 plant_handle에 올리면 새 진단(의도된 동작).

**근거**: 동일 이미지 재진단은 LLM 호출 0회로 비용 절감 + 사용자 경험("이전 진단 결과입니다 (날짜)") 자연스러움. 다른 식물 개체의 시계열에 같은 이미지 재사용 가능성도 보존.

## 8. 재시도 데코레이터 도입 트리거

당장은 analyze_node 안 `_with_retry` helper. **2번째 Vision Provider(OpenAI Vision / Claude Vision) 추가 시점**에 `RetryableProviderDecorator`로 승격. helper에 `# TODO: extract to decorator when 2nd provider added` 주석 표시.

**근거**: YAGNI. Provider 1개일 때 데코레이터는 추상화 과잉. 2개째 등장 = 중복 코드 임계점.

## 9. 429/5xx backoff 분리

`VisionRetryableError`에 `RetryHint(kind, backoff_seconds)` 첨부. **429**: 60초+ (서버 Retry-After 헤더 우선), **5xx**: 2초. analyze_node helper가 hint 보고 sleep.

**근거**: rate limit는 분 단위 회복, 서버 오류는 초 단위 회복. 같은 카테고리로 합치면 둘 다 비효율 (429에 2초 = 무한 실패, 5xx에 60초 = 사용자 이탈).

## 10. 3단계 진입 = 데이터셋 라이선스·인용 정책 작성 선행 조건

데이터셋 확정 직후 2개 task를 선행으로 박음:
- `docs/dataset_licenses.md`: 사용 데이터셋별 공식 라이선스 명시 위치, 라벨 `license` 필드 매핑
- `docs/citation_policy.md`: 데이터셋별 청크 수 한도, 청크 길이, UI 출처 표시 형식, 인용 사용처 명시 의무

**근거**: PlantVillage(CC-BY 계열)와 한국 책 인용(fair_use_quote)의 사용 한계가 다름. 라이선스 정리 안 된 데이터를 벡터 DB에 적재하면 응답 라이선스 추적 불가 + 책 출판사 클레임 위험. 적재 전에 못박아야 함.

---

## 진행 흐름 게이트 (한눈에)

```
[Phase 2 종료, 지금]
        │
        ▼
[1-0] 평가셋 20~30장 라벨링 + run_eval.py + baseline 측정 ← 다음 진입점
        │
        ▼ baseline 확보
[1-1] VisionProvider Protocol  +  [1-1.5] SDK 사전 조사 (병렬 가능)
        │
        ▼
[1-2] GeminiProvider 구현 → [1-3] 프롬프트 → [1-4] analyze_node (unwired)
        │
        ▼
[1-5] graph 와이어링 🔴 — 회귀 게이트 -5%p
        │
        ▼
[1-6 ~ 1-8] keyword/retrieve/generate 점진 정리
        │
        ▼
[1-9] state/schema 슬림화 + 프론트 동시 변경 — 회귀 게이트 -5%p
        │
        ▼
[1-10] Plant.id 완전 제거 + 1단계 baseline (eval/after_phase1.json)
        │
        ▼ temperature 튜닝 (0.0/0.2/0.5)
[2-1 ~ 2-7] 강제 로직 완화 → 2단계 baseline + 정성 평가
        │
        ▼
Phase 3 진입 (데이터셋 교체 — 선행: dataset_licenses.md, citation_policy.md)
```

## 컨텍스트 회복 체크리스트 (새 대화창에서 [1-0] 시작 시)

1. `phase2_refactoring_plan.md` 읽기 (요청 사항)
2. 이 파일(`docs/phase2_decisions.md`) 읽기 (결정 사항)
3. `app/graph.py`, `app/prompts.py`, `app/model_utils.py`, `app/schemas.py` 현재 상태 확인 (Phase 2는 코드 미수정 상태 가정)
4. `eval/` 디렉토리 존재 여부 확인 — 없으면 [1-0] 미시작 / 있으면 진행 단계 파악
5. `.env`의 `PLANT_ID_API_KEY` / `GEMINI_API_KEY` 상태 확인
