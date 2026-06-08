# [1-3] v4 analyze 프롬프트 보강 진단

> 목적: [1-7] 후 잔존 FP 14건의 근본 원인인 analyze `observed_symptoms` over-reporting 억제. v3 프롬프트의 "종 고유 무늬·형태는 증상 아님" 가이드를 일반 원칙으로 강화 — **종 이름 박지 않고 일반화 의도**.
>
> 작성일: 2026-05-30
> 단계: [1-3]의 두 번째 갱신 (v3 → v4)
> 선행: [1-5]/[1-7]/[1-6] 완료, push 완료. 폴더 정리 + README/log 정리 완료.

---

## [1-3] v4의 성격 — 왜 분리된 단계인가

[1-7] v2 실험이 데이터로 입증했다:

| 가이드 표현 | recall | FP |
|---|---|---|
| v1 ("증상 1개 이상이면 건강 금지") | 100% | 14 |
| v2 ("경미한 단일 증상은 건강 허용") | 80% | 14 |

generate 가이드를 정반대로 바꿔도 FP 동일. → **FP 14건의 원인은 generate가 아니라 analyze 입력**. 평가셋 healthy 28장 중 절반이 over-report되고 있어서 generate가 받는 입력 자체가 깨져 있음. analyze에서 잡아야 한다.

[1-9] 2차 회귀 게이트(`is_diseased` -5%p 이내) 진입 전 accuracy 회복 필수. v4는 게이트 대상 아니지만 사실상 필수 선행.

---

## 결정 영역 1 — 가이드 방향 (핵심: overfit 회피)

이 결정이 v4의 본질. 사용자 우려대로 **특정 종 이름 박기는 overfit 위험** — 평가셋 33장만 통과, 페페로미아·아글라오네마·새 종 들어오면 같은 over-report 재발.

**옵션 A — 일반 원칙 강화 (권장)**
- 평가셋 over-report 패턴에서 *일반 규칙*만 추출
- 프롬프트에 식물 종 이름 0개
- 모든 종에 적용 가능

**옵션 B — 종별 화이트리스트 (비추)**
- "접란은 잎끝 변색 정상" 식. 평가셋만 통과. 면접에서 "평가셋 튜닝 아니냐" 질문 직격.

권장 = 옵션 A. 면접 답변으로도 더 강력 — "평가셋 점수가 아니라 일반화를 의도했다"는 메타 인식 시그널.

---

## 결정 영역 2 — 일반 원칙의 3축

평가셋 over-report 케이스(접란·드라세나·산세베리아·ficus·sansevieria)에서 종 이름을 빼고 *어떤 패턴이 종 특성 vs 진짜 병징인가*를 일반 규칙으로 추출:

**부위 기반**: 잎 가장자리·끝에 국한된 경미한 변색은 종 특성·노화 가능성이 더 높다. 잎 면 중앙·줄기·뿌리에 나타나는 변색이 진짜 병징 신호에 더 가깝다.

**대칭성 기반**: 좌우·축 대칭으로 균일하게 나타나는 무늬·줄무늬·반점은 종 고유 패턴일 가능성이 높다. 비대칭·국소 집중 패턴이 병변 신호.

**진행 기반**: 식물 일부 잎(특히 아래쪽 오래된 잎)에만 국한된 변색은 자연 노화. 여러 잎으로 확산·진행 중인 변색이 병징.

이 3축은 식물 종 무관 적용 가능. v3의 "종 고유 무늬·형태는 증상 아님"보다 구체적·실행 가능.

---

## 결정 영역 3 — `visual_description` vs `observed_symptoms` 분리 명시

현재 v3 프롬프트에 두 필드의 책임 차이가 암묵적. 모델이 visual_description에 묘사한 내용을 그대로 observed_symptoms에도 넣는 경향. 이게 over-report의 한 메커니즘.

**v4 명시 — 두 필드 책임 분리**:
- `visual_description`: 이미지에 보이는 모든 시각적 정보를 묘사 (관찰 단계의 ground truth)
- `observed_symptoms`: 그 묘사 중 **병변이라 확신할 수 있는 증거**만 추출 (보고 단계의 임계값 적용)

즉 "잎끝이 약간 갈색"은 visual_description에 묘사하되, 결정 영역 2의 3축으로 봤을 때 종 특성 가능성이 높으면 observed_symptoms엔 넣지 않음.

이게 generate에 들어가는 입력의 보수성을 보장. visual_description의 풍부함은 유지(RAG 의미 보존).

---

## 결정 영역 4 — 좋은 예 / 나쁜 예 패턴 (종 이름 없이)

few-shot 박지 않고, 원칙 적용의 패턴만 명시. 종 이름 0개:

```
나쁜 예 (over-report):
  관찰: 잎 한 장의 끝부분만 약간 갈색, 다른 잎은 깨끗
  → observed_symptoms: ["잎끝 갈변"]  ❌ (부위 국한 + 한 잎 = 종 특성/노화)

좋은 예 (정상 처리):
  관찰: 잎 한 장의 끝부분만 약간 갈색, 다른 잎은 깨끗
  → visual_description에 "한 잎 끝부분 미세 갈변" 묘사
  → observed_symptoms: []  ✅

좋은 예 (병변 보고):
  관찰: 여러 잎에 비대칭 흑갈색 반점이 확산, 잎 중앙부에도 나타남
  → observed_symptoms: ["잎 비대칭 흑반점", "잎 중앙부 변색"]  ✅
```

이 패턴이 모델에게 결정 영역 2/3의 원칙을 어떻게 적용할지 보여줌. 종 이름이 아니라 *상황 묘사*로 표현.

---

## 결정 영역 5 — 평가셋 overfit 회피 명시

진단 md·refactoring_log·면접 답변에 일관되게 박을 입장:

> v4는 평가셋 33장에 맞춰 튜닝한 것이 아니다. 평가셋에서 관찰된 over-report 패턴(자연 변색·종 특성 무늬)에서 *일반 원칙*을 추출해 프롬프트에 반영했다. 식물 종 이름은 프롬프트에 0개.

**한계도 정직하게 명시**: 평가셋 33장으로 측정하면 같은 평가셋에 대한 성능만 검증 가능. 진짜 일반화 효과는 Phase 3(데이터셋 확대)에서 추가 검증 영역.

이 한계는 진단 md + refactoring_log + 작업 후 보고에 일관되게 박음.

---

## 결정 영역 6 — 측정 방법 + 위험 (recall 깎이는 트레이드오프)

**산출**: `eval/after_phase1_analyze_v4.json`

**목표**:
- FP 14 → 6~8 회복 (healthy 28장 중 절반 → 4분의 1 수준)
- accuracy 57.6% → 65~70% (v8 baseline 63.6% 회복·초과)
- recall 100% 유지가 이상적이나 80~90%로 깎일 가능성 있음 (트레이드오프)
- plant_korean 89.3~92.6% 유지 (식별 영역은 손 안 댐)
- JSON 100% 유지

**핵심 트레이드오프 위험**: v4가 너무 보수적이면 진짜 병징도 over-report 억제 가이드에 걸려서 observed_symptoms에 안 들어감 → generate가 "증상 없음" 신호로 받음 → 진짜 unhealthy 식물을 "건강"으로 → recall 깎임.

**판정 기준**:
- 이상적: precision↑ + recall 유지 → accuracy↑ → [1-9] 안전 진입
- 허용: precision↑ + recall 80~90% (FN 1~2건) → accuracy↑ → [1-9] 진입 가능
- 실패: recall <60% → v8 회복 게이트 깨짐 → v4 revert 또는 임계 재논의

표본 5장 노이즈는 여전. recall 1장 = 20%p 흔들림.

---

## 결정 영역 7 — 작업 분할

영향 파일 1개: `app/prompts.py`의 `ANALYZE_SYSTEM` 재작성.

**단일 커밋** — `feat: analyze 프롬프트 v4, observed_symptoms over-reporting 억제 ([1-3] v4)`

라인 변경 추정: +50~70줄 (현 ANALYZE_SYSTEM 1459자 → 2200자 안팎). 결정 영역 2/3/4의 가이드 추가가 핵심.

다른 코드는 한 줄도 안 건드림. 측정 1회로 판정.

---

## 롤백 전략

회귀 게이트 대상 아니지만 다음 케이스에서 revert:
- recall <60% (v8 회복 게이트 깨짐): 가이드 강도 조정 후 재측정
- plant_korean -5%p 초과 (예상 외 영향): 매우 드물 것. 발생 시 원인 분석

단일 커밋이라 `git reset --soft HEAD~1`로 즉시 복원.

---

## 다음 단계 연계

v4 통과 후:
- **[1-8] retrieve_node 정비**: `fallback_plant_name` 참조 제거, RAG 가중치 조정
- **[1-9] state/schema 슬림화** 🔴 2차 회귀 게이트: 죽은 키 일괄 제거 + 프론트 동시
- **[1-10]**: Plant.id 완전 제거 + `eval/after_phase1.json` 측정 + temperature A/B/C 튜닝

v4가 효과 없으면 (예: FP 12 이상 유지) decision #5 임계 재논의 — [1-9] 한정 -5%p → -10%p로 완화하거나, 평가셋 확대(Phase 3)를 [1-9] 전에 진행.

---

## 사용자 확정 대기 항목

작업 프롬프트(`1-3_v4_analyze_프롬프트_작업.md`) 작성 전 확인:

1. **결정 영역 1 (옵션 A — 일반 원칙, 종 이름 0개)** 동의?
2. **결정 영역 2 (부위·대칭성·진행 3축)** 이 추출 방향 OK? 다른 축 추가 또는 빼기?
3. **결정 영역 3 (`visual_description` vs `observed_symptoms` 책임 분리 명시)** 동의?
4. **결정 영역 4 (좋은/나쁜 예 종 이름 없이)** 패턴 표현 OK?
5. **결정 영역 5 (overfit 회피 + 한계 명시)** 진단 md·log·보고 다 같은 입장 박기 동의?
6. **결정 영역 6 (recall 트레이드오프 허용 범위 — 80~90%까지 OK)** 동의?
7. **결정 영역 7 (단일 커밋)** 동의?

7개에 답 박아주면 작업 프롬프트 md 작성으로 넘어감.

---

## 측정 결과 — v4 실패 + 근본 원인 재진단 (2026-05-30)

사용자 확정: 결정 1~7 모두 권장안 채택(3축 그대로, recall 80~90% 허용). v4 프롬프트 작성 →
`eval/after_phase1_analyze_v4.json` 1회 측정. **결과: 자체 판정 기준으로 실패, working tree revert.**

### 측정 비교 (baseline = `after_phase1_generate.json`, generate v1)

| 지표 | baseline | v4 | 목표 | 판정 |
|---|---|---|---|---|
| accuracy | 57.6% | 54.5% | 65~70% | ❌ 하락 |
| precision | 26.3% | 18.8% | ↑ | ❌ 하락 |
| recall | 100% | 60% | 80~90% 허용 | ❌ 실패 경계 |
| FP | 14 | 13 | 6~8 | ❌ 사실상 무변화 |
| FN | 0 | 2 | — | ❌ 신규 |
| plant_acc | 89.3% | 88.9% | 유지 | ✅ (노이즈 내) |
| JSON | 100% | 100% | 유지 | ✅ |

### 케이스별 flip (5건, 전부 경계 케이스)

- ✅ FP 고침: `inat_chlorophytum_comosum_003`(접란), `self_haengun_004`(행운목) — 진짜 over-report 2건
- ❌ 신규 FN: `self_haengun_003`·`self_haengun_006` — 진짜 병든 행운목인데 증상까지 억제돼 "건강" (recall 트레이드오프 현실화)
- ❌ 신규 FP: `inat_sansevieria_trifasciata_001` — 건강한 산세베리아가 "병해 의심"으로 (노이즈 추정, 반대 방향)

### 근본 원인 재진단 (★ 핵심 발견)

**FP 14건은 observed_symptoms over-report 때문이 아니었다.** v4가 observed_symptoms를 비워도
FP는 14→13으로 거의 안 줄었다. v4 FP 13건의 status 분해: **영양 부족 8 + 병해 의심 5**.

→ generate가 빈 observed_symptoms에도 `visual_description`(잎 변색 묘사)과 RAG 청크로부터
"영양 부족"을 8건이나 호출한다. **실제 FP 주범은 analyze observed_symptoms가 아니라
generate가 visual_description/RAG에서 '영양 부족'·'병해 의심'을 끌어내는 경로**다.
오히려 v4의 "경미한 변색도 visual_description에 빠짐없이 적어라" 지시가 영양 부족 과진단
연료를 더 줬을 가능성이 있다.

[1-7]의 진단("FP 원인 = analyze 입력")은 부분적으로만 맞았다. observed_symptoms를 통한 경로는
~2건만 설명하고, 나머지 ~12건은 generate의 visual_description/RAG 해석 경로다.

### 다음 타겟 (재설정)

generate의 '영양 부족'/'병해 의심' 과호출 억제로 방향 전환:
- 후보 A: generate 프롬프트에 "visual_description의 경미·국소 변색만으로는 영양 부족/병해 단정 금지,
  결정적 증거(observed_symptoms) 없으면 건강 우선" 가이드 추가.
- 후보 B: '영양 부족' status 자체의 진입 임계를 높임 (RAG 근거 필수 등).
- 측정은 동일 평가셋 1회. 표본 5장(unhealthy) recall 노이즈는 여전 — FP(healthy 28장) 변화가
  더 신뢰할 신호.

증거 파일 보존: `eval/after_phase1_analyze_v4.json` (revert 후에도 측정 기록으로 유지).
