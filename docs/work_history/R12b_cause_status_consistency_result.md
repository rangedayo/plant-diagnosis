# R12b — cause–status 정합 제약 측정 결과 보고서

> 변경: `app/prompts.py` STRUCTURED_DIAGNOSIS_JSON_SYSTEM에 cause–status 정합 self-check 룰 1블록(commit 210b254).
> 측정: `eval/after_acc_r12b_cause_status.json` (사용자 run_eval --aux, Gemini 과금).
> 앵커 R8 `after_acc_r7_dry_guard.json` · 비교 R11 `after_acc_r10_v2_rag_ok.json`.
> **종합 판정: PASS (게이트 5/6 충족 + latency ⚠️는 단일 outlier 아티팩트로 무효).**

## 1. 게이트 5종 + latency 통과/실패 표

| 지표 | R11 | R12b | 기준 | 판정 |
|---|---|---|---|---|
| 🔴 `post_guard.fn` | 1 | **0** | = 0 (절대 사수) | ✅ PASS — recall 1.0 복구 |
| `post_guard.fp` | 14 | **14** | ≤ 14 | ✅ PASS — 악화 없음 |
| 건조 발화 (`pred="건조"`) | 0 | **1** (haengun_005) | > 0 | ✅ PASS — **사상 첫 건조 발화** |
| 건강행 `pred="건조"` | 0 | **0** | = 0 | ✅ PASS — 새 건조 FP 없음 |
| `pred_status` 분포 | 3종 | **5종** | 균형 점검 | ✅ PASS — {건강15·병해18·건조1·영양4·과습1} |
| `latency.mean` | 20.234s | 32.795s | R11 ±10% | ⚠️ 표면상 FAIL → **무효(아래)** |

**파생 지표**: precision 0.333→**0.364**, recall 0.875→**1.0**, accuracy 0.583→**0.611**.
pre_guard는 R11·R12b 동일(tp8/fn0/fp17) — generate 자체는 비건강 GT를 "건강"이라 부른 적 없음.
guard_caught_fp = 3 (양쪽 동일).

### latency ⚠️ 분해 — 단일 outlier 아티팩트
- per_case: min 13.691 / **median 19.327** / mean 32.795 / **max 506.266** / p90 26.65 (n=39).
- **outlier 1건**: `inat_epipremnum_aureum_009` = **506.266s** (~8.4분). 나머지 38건 최대는 정상권.
- **sans-outlier mean = 20.335s = R11 20.234s 대비 +0.5%** (±10% 이내). median 19.327s는 R11 mean보다도 낮음.
- retry 흔적: `json_parse_success_rate = 1.0`, `json_parse_failed_ids = []` → JSON 파싱 재시도 0건.
  506s 단독 스파이크는 프롬프트 길이 효과가 아니라 **해당 1건의 transient Gemini/네트워크 stall**
  (analyze 비전 호출 SDK backoff 추정). 재현 신호 아님.
- **결론**: 프롬프트 +1블록의 latency 순효과는 사실상 0. 게이트 latency 실패는 측정 노이즈로 무효.

## 2. 5-status 혼동표 (R12b)

행=GT true_status, 열=pred_status. (과습·영양 부족은 독립 GT 표본 0 → unmeasured, ambiguous 3건 제외)

| GT＼pred | 건강 | 과습 | 건조 | 병해 의심 | 영양 부족 | 표본 |
|---|---|---|---|---|---|---|
| 건강 | 14 | 0 | 0 | 12 | 2 | 28 |
| 건조 | 0 | 0 | **1** | 4 | 1 | 6 |
| 병해 의심 | 0 | 0 | 0 | 1 | 1 | 2 |
| (ambiguous, 제외) | 1 | 1 | 0 | 1 | 0 | 3 |

- **건조 행**: 6건 중 1 정답(건조)·4→병해 의심·1→영양 부족. **건조 대각선에 처음으로 값(1)이 찍힘**
  (R8·R11은 건조 열 전부 0). 다만 여전히 4/6은 병해 의심으로 과escalate.
- **건강 행**: 28건 중 14 정답 / 12→병해 의심 / 2→영양 부족 (= FP 14, guard 미포착분).
- 건강 열에 **건조 0** → 건조 FP 없음(게이트 충족 재확인).

## 3. 건조 6건 case별 변화 추적 (R11 → R12b)

> ⚠️ analyze(Gemini)는 비결정 — 동일 이미지라도 observed_symptoms가 run마다 변동.
> 005만 R11·R12b symptoms 완전 동일 → 순수 generate(프롬프트) 효과 격리 가능.

| case | R11 status | R12b status | symptoms 동일? | 핵심 변화 |
|---|---|---|---|---|
| haengun_002 | 병해 의심 | 병해 의심 | 변동 | cause "환경적 요인/해충"→"환경적 요인이나 **수분 부족**" (status 불변) |
| haengun_003 | 병해 의심 | 병해 의심 | 변동(고사·바삭 탈락) | cause "수분 부족 또는 과습"(수분 우선) **인데 status=병해 의심** → 룰 위반 |
| **haengun_005** | 병해 의심 | **건조** ✅ | **완전 동일** | **순수 룰 효과**: cause "수분 부족…"→status=건조 |
| haengun_006 | 건강(FN) | 영양 부족 | 변동(마름 유입) | analyze가 "마름" 산출 → guard veto → 비건강 유지(FN→TP) |
| haengun_008 | 영양 부족 | 병해 의심 | 변동(고사·주름 탈락) | cause "수분 부족 또는 과습"(수분 우선) **인데 status=병해 의심** → 룰 위반 |
| epipremnum_004 | 병해 의심 | 병해 의심 | 변동 | cause "병해 또는 환경적 요인"(병해로 회귀) → status=병해 정합 |

### 3.1 005가 건조로 간 이유 (성공 격리)
- symptoms R11=R12b 완전 동일: `['잎끝 갈변 및 바삭한 마름', '잎 표면의 불규칙한 작은 황색 반점']`.
- R11: cause=`"과습 또는 영양 부족일 수 있습니다."` → status=**병해 의심** (cause에 병해 언급조차 없는 모순).
- R12b: cause=`"수분 부족 또는 환경적 요인일 수 있습니다."` → status=**건조**.
- **'바삭한 마름' 단서 + cause-status 룰이 generate를 건조로 락(lock).** 입력이 동일하므로 이 전환은
  100% 프롬프트(R12b) 효과. 반점(병해 신호)과 마름(건조 신호) 충돌에서 룰이 건조로 정렬시킴.

### 3.2 003·008이 건조로 안 간 이유 (룰 위반 잔존)
- **003** R12b: cause=`"수분 부족 또는 과습일 수 있습니다."` — 수분 부족을 **먼저** 명시.
  룰대로면 "가장 먼저 명시한 원인"=수분 부족 → status="건조"여야 함. **그런데 status=병해 의심.**
  cause에 병해·감염·곰팡이 언급이 **전혀 없는데** status만 병해 의심 → **명백한 cause-status 모순(룰 위반)**.
- **008** R12b: cause=`"수분 부족 또는 과습일 수 있습니다."` — 동일하게 수분 우선인데 status=병해 의심.
  R11(영양 부족)에서 다른 오답(병해 의심)으로 이동했을 뿐 건조 도달 실패. 역시 cause에 없는 status.
- **진단**: generate는 cause를 R11보다 깔끔하게 "수분 부족 우선"으로 좁혔으나(룰의 cause측 효과는 발현),
  **status enum 커밋에서 여전히 병해 의심으로 과escalate**. 정합 룰을 LLM이 단일 호출에서 준수하지 못함
  (005는 준수, 003·008은 위반 — temperature 비결정). RAG 우세 타입 룰(general→비병해)도 함께 무시.
  즉 **generate의 병해 의심 escalation 편향이 cause-status 룰보다 강한 케이스가 남아 있다.**

## 4. cause–status 정합 위반 잔존 여부

- **교정 성공**: 005 (cause 수분 부족 → status 건조). 합성 4/4에서 예측한 동작이 실측에서도 1건 발현.
- **위반 잔존**: 003·008 (cause 수분 부족 우선인데 status 병해 의심). **status가 cause에 등장하지 않는
  순수 모순** 형태로 남음. 추가로 FP 다수도 cause에 "수분 부족"을 적고 status=병해 의심
  (예: epipremnum_001 "환경적 요인이나 수분 부족"→병해 의심; chlorophytum_001 "과습 또는 수분 부족"→병해 의심).
- **요약**: 룰은 generate의 **cause 텍스트를 건조 쪽으로 좁히는 데는 광범위하게 성공**했으나,
  그 cause를 **status enum으로 옮기는 최종 커밋은 일부만(005) 성공**. 병해 의심 escalation 편향이
  남은 위반의 공통 원인.

## 5. 부수효과 분석 (다른 케이스 영향 / FP 분해)

- **FP 14건 불변(=R11)**, 그러나 **건조 FP 0** — 정합 룰이 건강 케이스를 건조로 끌어내리지 않음.
  우려했던 "non-cosmetic 건강 over-report → 건조 FP"는 이번 run에서 **미발생**. FP는 전부 병해 의심(12)·
  영양 부족(2)로, R11과 동일 성격(생물 피해 과진단).
- **과습 1건 신규**(epipremnum_009, gt=ambiguous 제외 대상) — 정합 룰이 과습 enum도 활성화시킴(분포 다양화).
- **recall 복구(fn 1→0)의 실제 기전 주의**: 006이 FN을 벗어난 것은 **cause-status 룰 때문이 아니라**
  analyze가 이번 run에서 "마름"(병변 토큰)을 산출 → `apply_status_guard` 병변 veto로 건강 교정이
  차단됐기 때문. R11에선 analyze가 단일 cosmetic 증상만 줘서 guard가 건강으로 over-correct → FN이었음.
  **즉 recall=1.0은 R12b 룰의 직접 성과가 아니라 006의 analyze 변동에 의존** → 재측정 시 006이 다시
  단일 cosmetic으로 나오면 FN 재발 가능. **이 복구는 견고하지 않다(R12a 정당화).**

## 6. R12a 설계 입력 (R12b 후 잔존 패턴)

1. **006 FN의 견고한 해결은 R12b로 불가** — guard 미변경이라 analyze 운에 좌우. R12-0 §B.4 진단대로
   `_symptom_is_cosmetic` 위치 veto(`아래/아래쪽/하엽/하부`) 필요. 단일 cosmetic+하엽 위치를 건강으로
   교정하지 않게 막아야 재현 가능한 recall 사수.
2. **003·008 = guard 영역 아님** — 이들은 generate가 비건강(병해 의심)으로 이미 판정, guard 발동 안 함.
   잔존 오답(건조 대신 병해)은 **generate enum 편향** 문제 → R12b-2(황화 충돌룰·정합룰 강화) 또는
   R12c(건조 카드 보강으로 우세 타입을 건조로) 영역.
3. **FP 14의 주성분 = generate 병해 의심 과진단**(12/14). cause엔 수분/환경을 적고 status만 병해로 올림.
   R12a guard는 비건강→건강 1방향뿐이라 이 FP를 직접 못 줄임(병변 토큰 동반 시 veto). FP 감축은
   R12b-2/R12c 또는 generate 단순화 라운드 필요.

---

## 추가 분석 A — latency 분포 (사용자 요청)

| 통계 | 값 |
|---|---|
| n | 39 |
| min | 13.691s |
| **median** | **19.327s** |
| mean | 32.795s (outlier 포함) |
| **sans-outlier mean (>60s 제외, n=38)** | **20.335s (R11 20.234s 대비 +0.5%)** |
| p90 | 26.65s |
| max | **506.266s** |
| outlier(>60s) | **1건: `inat_epipremnum_aureum_009` = 506.266s** |
| JSON 파싱 재시도 | 0건 (success_rate 1.0, failed_ids 빈 배열) |

- outlier 1건 제거 시 평균은 R11과 사실상 동일 → **프롬프트 증가의 latency 순효과 ≈ 0**.
- 506s는 retry 흔적(JSON 파싱 실패) 없이 단발 → analyze(Gemini 비전) 단계 네트워크/SDK stall 추정.
  결과 자체는 정상 산출(pred=과습, json_ok). 재현성 없는 측정 노이즈.

## 추가 분석 B — 건조 6건 cause 텍스트 인용 (사용자 요청)

| case | R12b status | R12b cause (원문) |
|---|---|---|
| 002 | 병해 의심 | "환경적 요인이나 수분 부족이 원인일 수 있습니다." |
| 003 | 병해 의심 | "수분 부족 또는 과습일 수 있습니다." ← 수분 우선인데 status 병해(위반) |
| **005** | **건조** | "수분 부족 또는 환경적 요인일 수 있습니다." ← 정합 성공 |
| 006 | 영양 부족 | "수분 부족 또는 영양 부족일 수 있습니다." |
| 008 | 병해 의심 | "수분 부족 또는 과습일 수 있습니다." ← 수분 우선인데 status 병해(위반) |
| epipremnum_004 | 병해 의심 | "병해 또는 환경적 요인으로 인한 증상일 수 있습니다." |

- 6건 중 **5건 cause가 "수분 부족"을 언급**(002·003·005·006·008) — 정합 룰이 cause를 건조 쪽으로
  광범위하게 이동시킴. 그러나 status까지 건조로 커밋된 것은 005뿐. **cause는 설득됐고 enum은 부분 설득.**

---

## 종합 판정

**PASS.** 절대 사수 게이트(post_guard.fn=0) 복구, 건조 발화 첫 성공, FP 불변·건조 FP 0,
latency는 단일 outlier 무효. R12b는 **방향이 옳음이 실측으로 확인**됨(cause→건조 광범위 이동, 005 정합 성공).

**한계(정직)**: ① recall 복구는 006 analyze 변동 의존 — 견고하지 않음. ② 003·008은 cause를 좁혔으나
status는 병해로 위반 잔존 — generate escalation 편향이 룰을 일부 이김. ③ 건조 정답은 6건 중 1건뿐.

**다음 우선순위 권고**: **R12a(guard 위치 veto)로 006 FN을 견고화** → 그 다음 R12c(건조 카드 보강으로
003·008·기타의 우세 타입을 건조로 끌어 generate enum 편향을 입력에서 교정). R12b 룰은 유지(순효과 양성).

## 변경 파일 명시
이 라운드 측정·분석 산출물: 본 보고서 + (이미 커밋된) `app/prompts.py` 룰(210b254) +
`scripts/diagnostics/r12b_synthetic_check.py`. 측정 JSON `after_acc_r12b_cause_status.json`은 사용자 산출물.
guard·RAG·analyze·황화룰 등 그 외 일절 무변경(변수 격리 유지).
