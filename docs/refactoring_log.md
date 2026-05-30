# 1단계 리팩토링 진행 로그

> 1단계 = Plant.id 제거 + Gemini 통합 + 강제 로직 일부 완화.
> 각 단계의 본질·결정·결과만 압축. 자세한 진단·옵션 비교는 `docs/work_history/1-N_*.md` 참조.

---

## 1단계 정의 + 게이트

**목표**: 7회 외부 호출 → 4회. analyze 6필드(관찰) + generate(진단) 책임 분리. 강제 규칙 3개(JSON·status enum·언어)로 축소.

**회귀 게이트 (decision #5, -5%p 이내)** — [1-5] graph 와이어링과 [1-9] state 슬림화 두 곳에서 발동:
- `plant_korean` 정확도
- `is_diseased` 일치율 (status → bool 변환)
- `action_keywords` 일치율 (run_eval 미측정, baseline 라벨 부재로 측정 갭)
- JSON 파싱 실패율 +5%p 이내

**v8 baseline (eval/baseline.json, 33장)**:
| 지표 | 값 |
|---|---|
| 식물명 정확도 | 90.0% (27/30 matchable) |
| is_healthy precision / recall | 23.1% / 60.0% (FP 10, FN 2) |
| status 분포 | 건강 20·병해 의심 10·과습 2·영양 부족 1 |
| JSON 파싱 | 100% |
| latency 평균 | 21.1s |
| 외부 호출 | 7회 (Plant.id 1 + OpenAI 6) |

---

## [1-1] VisionProvider Protocol

신규 `app/vision/` 디렉토리에 Protocol·AnalyzeResult Pydantic 모델·VisionInput·에러 계층(RetryableError·PermanentError + RetryHint)·MockVisionProvider 작성. 기존 코드 한 줄도 안 건드림.

**핵심 결정**: Protocol 기반 추상화. 추후 Claude·OpenAI Vision 등 교체 시 한 줄. `default_factory=list`가 Gemini SDK에서 거부될 가능성을 [1-2] 통합 테스트로 실증 후 결정. 결과: 거부 안 됨, default 유지.

**산출**: pytest 13/13. 모든 신규 파일.

## [1-2] GeminiProvider 구현

google-genai SDK 의존성 추가. `app/vision/gemini.py`에 GeminiProvider 클래스 작성 — system_prompt 생성자 주입, 429/5xx backoff 분리, `types.Part.from_text(text=...)` keyword-only 호출.

**SDK 실증 3건** (추정 → 검증 전환):
1. `types.Part.from_text(text=prompt)` keyword-only (위치 인자 TypeError)
2. APIError 실제 속성 `.code/.message/.status/.details/.response` — `response_json` 없음, Retry-After는 `e.response.headers["Retry-After"]` → `e.details` 재귀 → 60초 폴백
3. `ClientError(code, response_json, response=None)` 시그니처

**모델 결정 (decision #11)**: `gemini-2.5-flash` → `gemini-2.5-pro`. Pro의 reasoning 우위로 Dracaena 종 혼동 완화 기대. 단가는 거의 무관(33장 측정 1회 ≈ $0.15).

**산출**: pytest 18/18 + 통합 1/1. 통합 테스트로 `self_haengun_001` → Dracaena fragrans 정확 식별 (latency 9.8~12.4s).

## [1-3] analyze 프롬프트 v3

신규 `ANALYZE_SYSTEM`(1459자) + `ANALYZE_USER_TEMPLATE`. v1→v2→v3 진화:
- v1: 6필드 기본 정의
- v2: 통합 검증 8장으로 잡힌 over-reporting + 한국어 통명 보정
- v3: "종 고유의 무늬·형태, 물리적 흠집은 증상 아님" 가이드 추가 (접란·드라세나 자연 변색 케이스 대응 — [1-7] 후 측정에서 부분 효과 확인됨)

**강제 4항목**: JSON 6필드 / `plant_confidence` enum(low/med/high) / 한국어 / 출력 외 텍스트 금지. 나머지는 권장 톤. 통합 검증 2회 8장에서 강제 위반 0건, `is_healthy`/`health_notes` 누출 0건(책임 분리 충족).

**잔여 비결정성**: temperature None 상태에서 Dracaena conf med↔high 흔들림. [1-10] temperature A/B/C 튜닝 영역.

## [1-4] analyze_node factory

`app/nodes/` 신규 디렉토리. `make_analyze_node(provider)` factory 함수 + `_with_retry` helper inline(2번째 provider 추가 시 decorator로 승격, TODO 주석). graph 와이어링 X — [1-5]에서.

**핵심 결정 (decision #8)**: 재시도는 inline helper. YAGNI — Provider 1개일 때 decorator는 추상화 과잉. 2개째 등장 = 중복 코드 임계점.

**산출**: pytest 23/23. 모든 신규 파일.

---

## [1-5] graph 와이어링 🔴 1차 회귀 게이트 — 통과

`identify_node` + `describe_node` 제거하고 analyze_node가 그래프 첫 노드로 진입. `build_diagnosis_graph(client, vision_provider)` 시그니처 확장. DiagnosisState에 6신규 키 추가 + 기존 Plant.id 키는 빈 값으로 흘려보냄(브리지 패턴, [1-9]서 제거).

**게이트 결과**:
| 지표 | v8 | [1-5] | 델타 | 판정 |
|---|---|---|---|---|
| plant_korean | 90.0% | 89.3% | -0.7%p | ✅ |
| is_diseased | 63.6% | 63.6% | 0%p | ✅ |
| JSON 실패율 | 0% | 0% | 0%p | ✅ |
| latency | 21.1s | 32.4s | +11s | ⚠️ 게이트 외 |

**부작용 = 보수화**: TP 3→1, FN 2→4, precision 23.1→11.1%, recall 60→20%. Plant.id `is_healthy_prob` 신호 소멸 + `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`의 "건강에 가깝게" 가이드 + status fallback "건강"의 3 메커니즘 합. 진단 md 롤백 분기에 미리 박은 "is_healthy 회귀 → [1-7] 우선" 경로 발동.

latency +11s는 Gemini 2.5 Pro thinking 부담. [1-10] flash 검토 영역.

## [1-7] generate 재설계 (순서 변경: [1-6]보다 우선)

3 메커니즘 정면 대응:
1. **메커니즘 1 — Plant.id 신호 소멸**: `generate_node` context_summary에서 "Plant.id 팩트" 섹션 통째 제거 → analyze 6필드 [관찰 정보] 섹션으로 교체.
2. **메커니즘 2 — 보수 가이드**: `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`의 "건강에 가깝게" 줄 삭제. observed_symptoms 가이드로 교체 ("증상 1개 이상이면 status='건강' 금지").
3. **메커니즘 3 — status fallback**: `normalize_structured_result` + `default_structured_fallback`의 fallback "건강" → "병해 의심". 불확실 시 사용자 점검 행동 유도.

**v2 실험 폐기**: "경미한 단일 증상은 건강 허용" 표현으로 완화 시도 → recall 100→80%로 깎이고 precision은 그대로(FP 14 동일). 데이터로 입증: **FP 근본 원인은 generate 가이드가 아니라 analyze over-reporting**. [1-7] 범위 밖 확정. v1 채택.

**결과**:
| 지표 | v8 | [1-5] | [1-7] |
|---|---|---|---|
| precision | 23.1% | 11.1% | **26.3%** ✅ |
| recall | 60.0% | 20.0% | **100%** ✅ |
| FN | 2 | 4 | **0** (아픈 식물 0장 놓침) |
| FP | 10 | 8 | 14 (잔존 — [1-3] v4 영역) |

암묵적 회복 게이트(precision ≥23%, recall ≥60%) 통과. accuracy는 63.6→57.6%(-6%p)로 [1-9] 2차 게이트 차단 위험 누적.

**미룬 항목**: weak_evidence 강제·action_plan 패딩·미사용 상수(결정 6·7·10) → Phase 2. RAG_FAILED 분기 폐기(결정 8) → [1-9].

## [1-6] keyword_node 축소

decision #2 실행. `keyword_node` GPT 호출 2~3회 → 1회 축소. analyze가 만든 한국어 `observed_symptoms`를 RAG 키워드로 직접 채택(최대 5개), 영문 번역만 LLM 호출.

**死 코드 정리 (-312/+26줄)**: `build_rag_search_query_with_gpt`·`estimate_fallback_plant_with_gpt` + 연쇄 死 함수(`describe_image_with_gpt`, `extract_keywords_with_gpt`, `_image_bytes_to_jpeg_base64_sync`) + 미사용 프롬프트 상수 4쌍(RAG_QUERY_SYMPTOM_*, KEYWORD_*, FALLBACK_PLANT_*, DESCRIBE_IMAGE_*). 死 함수 동반 제거는 진단 md의 누락(상수만 제거 지시했었음)을 Claude Code가 정확히 보강함.

`format_*` 헬퍼는 레거시 state(`is_healthy_prob`·`top_candidates`) 처리용이라 [1-9]로 격리.

**결과**:
| 지표 | [1-7] | [1-6] | 변화 |
|---|---|---|---|
| recall | 100% | 100% | 유지 |
| precision | 26.3% | 23.8% | -2.5%p (FP 2장 추가) |
| plant_korean | 89.3% | 92.6% | +3.3%p (측정 노이즈) |
| JSON | 100% | 100% | 유지 |
| **latency** | 32.4s | **25.5s** | **-6.9s (-21%)** |

precision -2.5%p의 FP 2장(ficus_elastica·sansevieria 자연 변색)도 [1-3] v4 영역. RAG 영역 변경이 generate 결과에 미치는 영향은 작음(부수적).

---

## 게이트 통과 현황 종합

| 게이트 | 시점 | 결과 |
|---|---|---|
| 1차 회귀 게이트 (decision #5) | [1-5] graph 와이어링 | ✅ 통과 (4지표 중 측정 가능 3개 모두 -5%p 이내) |
| 1차 회귀 게이트의 부작용 회복 | [1-7] generate 재설계 | ✅ precision 23.1→26.3%, recall 60→100% |
| 2차 회귀 게이트 (decision #5) | [1-9] state 슬림화 | ⏳ 진입 전 [1-3] v4로 accuracy -6%p 회복 필요 |

## 미해결 잔존

1. **FP 14 / accuracy -6%p** — analyze observed_symptoms over-reporting이 근본 원인. [1-3] v4에서 접란·드라세나·산세베리아 자연 변색 케이스 직격 가이드 추가로 대응. v4가 효과 없으면 decision #5의 -5%p 임계를 [1-9] 한정으로 -10%p 재논의 또는 데이터셋 표본 확대(Phase 3).
2. **self_dracaena 종 혼동** — Pro 모델이 우리 reflexa 식물을 fragrans 변종·구학명·Cordyline 등으로 출력. [1-3] v4 또는 [1-10] temperature 튜닝 영역.
3. **latency +4.4s 누적 (21.1→25.5s)** — Gemini 2.5 Pro thinking. [1-10]에서 flash 검토.

## 다음 단계

**[1-3] v4** (다음 진입 후보 1): analyze 프롬프트에 종 고유 자연 변색 케이스를 더 강하게 박기. 접란 "잎 가장자리 자연 변색"·드라세나 "잎끝 마름은 종 특성"·산세베리아 "잎 측면 황색 무늬는 종 특성" 같은 예시 명시. 표본 작아 효과 측정에 한계 있을 수 있음.

**[1-8] retrieve_node 정비** (다음 진입 후보 2): `fallback_plant_name` 참조 제거, `_final_plant_name`·`_build_rag_query` 헬퍼 단순화. RAG 가중치(NCPMS 0.8·UC_IPM 0.85·플랜트명 매칭 보너스) 변경 검토.

**[1-9] state/schema 슬림화** 🔴 2차 게이트: 죽은 키 일괄 제거(`is_healthy_prob`·`top_candidates`·`disease_name`·`confidence`·`fallback_plant_name`) + `DiagnosisResponse`의 `PlantIdentificationResult` 제거 + `types/diagnosis.ts` + `ResultView` + RAG_FAILED 시 백엔드 502 + 프론트 에러 UI 동시.

**[1-10]**: Plant.id 함수·reader·env 완전 제거 + 死코드 정리 + `eval/after_phase1.json` 측정 + temperature A/B/C 튜닝.

---

## 운영 원칙

1. **변수 격리** — 한 번에 하나만 바꿔서 측정. 한 단계에 여러 영역 손대면 회귀 시 원인 분리 불가.
2. **gates는 가설이 아니다** — 측정으로만 판정. precision 회복 가이드라도 측정해서 데이터로 확인 후에야 채택.
3. **진단 md → 작업 프롬프트 md → 측정 → 보고** 순서. 위험 단계는 진단 먼저(v7 원칙).
4. **死 코드 정리는 자발적 청소가 아니라 결정의 결과** — 사용 안 되는 함수·상수는 발견 즉시 제거 (정직한 시스템).
5. **추정 → 실증 전환 기록** — SDK 시그니처, 모델 행동 등은 추정으로 시작하되 측정 후 확정 사항을 `phase2_decisions.md`에 갱신.
