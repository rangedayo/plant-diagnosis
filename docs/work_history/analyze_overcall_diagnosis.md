# analyze 정밀화 사전 — 과민 책임 단계 진단 (read-only)

**기준 출력**: `eval/after_acc_r12d1_remove_surface.json` (raw 추출용)
**새 앵커**: `eval/after_acc_r12d1_relabeled.json` (acc 62.86% · 분모 35 · FP 13 · FN 0)
**대상**: FP 13 중 개선 가능 10건 (드라세나 hard 3 = 종 인지 영역, 제외)
**성격**: read-only. 코드·프롬프트·평가셋 무변경, 측정 없음.

---

## 핵심 결론 (먼저)

**과민 책임은 analyze가 1순위, generate가 2순위 — 둘 다 손봐야 한다.**

- **(가) analyze 과장 5건** — 실제 이미지엔 없는 **병반·반점·괴사**를 지어내거나(spots/necrosis), "매우 건강"한 잎에 갈변·마름을 부착. **입력부터 오염**.
- **(나) generate 비약 3건** — analyze가 실제 정상 변이(하부 노화·말단 약간 마름)를 **충실히** 추출했는데 generate가 비건강으로 escalate.
- **(다) 혼합 2건** — analyze 경미 과장 + generate escalation 동반.

→ **1순위 타깃 = analyze**. 단 "정밀화"는 두 갈래여야 한다:
1. **병반·반점·괴사 날조 금지** (가 5건 직접 해소)
2. **정상 변이(하부 노화·말단 갈변·자연 흠집)를 증상으로 보고하지 않기** (나 3건의 입력을 비우면 generate가 escalate할 거리가 사라짐)
→ analyze 프롬프트 한 곳에서 대부분 커버 가능. **FN 0 사수가 제약** — "정상 변이 비보고"가 진짜 병징까지 삼키지 않도록 변별 지시 필요.

**보조 발견 (generate escalation 편향)**: 병해 의심 판정 4건(haengun_001·004, chlorophytum_001, +epipremnum_001 일부)의 `cause` 텍스트가 정작 **"수분 부족 또는 과습/환경"**이라 disease를 안 가리킨다. generate가 **자기 cause 추론보다 status를 과상향**한다는 증거 → generate cosmetic 관용도 보조 레버로 유효(R12b·R12c 계열과 연결).

**가드는 레버 아님**: 10건 전부 `guard_fired=false`. 가드는 cosmetic→건강 단방향뿐이라 이 FP들을 못 잡음(증상이 cosmetic으로 판정 안 됨). 문제는 상류.

---

## PART A — 10건 풀 파이프라인

| # | case_id | 종 | observed_symptoms (analyze) | top_3 problem_type | pred_status | cause (generate) | guard |
|---|---|---|---|---|---|---|---|
| 1 | chlorophytum_comosum_003 | 접란 | 일부 잎끝 갈변 및 마름 | abiotic-water, abiotic, — | 건조 | 수분 부족일 수 있습니다 | 미발동 |
| 2 | spathiphyllum_001 | 스파티필름 | 잎끝 미세한 황화 / 잎 가장자리 갈변 및 마름 | abiotic-water, abiotic-water, abiotic | 건조 | 수분 부족 또는 물 부족 | 미발동 |
| 3 | haengun_001 | 행운목 | 잎끝 갈변 및 마름 / **일부 잎의 미세한 노란 반점** | frame, disease, — | 병해 의심 | 환경적 요인으로 인한 수분 부족 또는 과습 | 미발동 |
| 4 | haengun_004 | 행운목 | 새잎 끝부분 갈변 및 마름 | abiotic, —, env | 병해 의심 | 수분 부족 또는 과습 | 미발동 |
| 5 | chlorophytum_comosum_001 | 접란 | 일부 잎끝의 갈색 마름 / 잎 가장자리의 국소적 갈변 | abiotic, —, abiotic-water | 병해 의심 | 수분 부족 또는 과습 | 미발동 |
| 6 | epipremnum_aureum_001 | 스킨답서스 | 여러 잎 가장자리의 불규칙한 갈변 및 마름 / **일부 잎의 갈색 괴사 반점** | general, frame, general | 병해 의심 | 환경적 요인이나 수분 부족 | 미발동 |
| 7 | ficus_elastica_002 | 고무나무 | **일부 잎의 작은 갈색 반점** / 일부 잎 가장자리 찢어짐 | —, pest, general | 병해 의심 | 해충의 피해 또는 환경적 요인 | 미발동 |
| 8 | sansevieria_trifasciata_002 | 산세베리아 | **일부 잎에 작은 갈색 마른 반점** | —, pest, disease | 병해 의심 | 해충 감염 또는 환경적 요인 | 미발동 |
| 9 | aglaonema_003 | 아글라오네마 | 아래잎 황화 | —, abiotic-water, abiotic | 영양 부족 | 수분 부족 또는 영양 부족 | 미발동 |
| 10 | spathiphyllum_003 | 스파티필름 | 잎 가장자리 갈변 / 아래잎 황화 | nutrient, abiotic-water, abiotic-water | 영양 부족 | 영양 부족 또는 수분 부족 | 미발동 |

(top_3에서 `—` = 빈 problem_type, HOUSEPLANT 출처 일반 카드)

---

## PART B — 과장 패턴 (정상 변이 → 둔갑한 증상 문장)

각 케이스의 **실제 이미지 소견(웹 확인) vs analyze 추출** 대조:

| case | 실제 이미지 소견 | analyze 추출 | 정상 변이 유형 | 과장 여부 |
|---|---|---|---|---|
| chlorophytum_003 | 잎 녹색 살아있음, 마른 꽃대 일부 | 일부 잎끝 갈변 및 마름 | 접란 말단 갈변(정상 빈발) / 마른 꽃대 오귀속 | 경미 과장 (실제는 녹색 강조, 꽃대를 잎 마름으로?) |
| spathiphyllum_001 | **진녹색 윤기 — 매우 건강** | 잎끝 미세 황화 + 가장자리 갈변·마름 | 윤기·건강을 갈변으로 | **날조** (실제 소견에 갈변 없음) |
| haengun_001 | 본체 진녹색, 잎끝만 미세 갈변 | 잎끝 갈변(충실) + **미세한 노란 반점** | 경미 말단 갈변(실재) + **반점 날조** | **반점 날조** |
| haengun_004 | 새순 녹색, 끝부분만 약간 마름 | 새잎 끝부분 갈변 및 마름 | 경미 말단 마름(실재) | 충실 (과장 아님) |
| chlorophytum_001 | 싱싱·무늬 양호, 끝 약간 갈변 | 잎끝 갈색 마름 + 가장자리 국소 갈변 | 경미 말단 갈변(실재) | 대체로 충실 |
| epipremnum_001 | 무늬 좋음, **자연 흠집·구멍** | 가장자리 갈변·마름 + **갈색 괴사 반점** | 자연 흠집·구멍을 **괴사 반점**으로 | **괴사 날조** |
| ficus_002 | **진녹색 윤기 — 거의 완벽** | **작은 갈색 반점** + 가장자리 찢어짐 | 거의 완벽을 반점으로 / 물리적 찢김을 병징처럼 | **반점 날조** |
| sansevieria_002 | **개화 꽃대 여러 개, 잎 건강** | **작은 갈색 마른 반점** | 개화·건강을 반점으로 | **반점 날조** |
| aglaonema_003 | 은녹 무늬, **하부 잎 일부 노화** | 아래잎 황화 | 하부 노화(자연 senescence) = 황화 | 충실 (노화를 황화로 정확 기술) |
| spathiphyllum_003 | **꽃 3개 개화, 잎 진녹색** | 가장자리 갈변 + 아래잎 황화 | 개화·진녹색을 갈변·황화로 | 경미 과장 (하부 황화 약간 실재 가능) |

**핵심 둔갑 유형**:
- **자연 흠집·구멍·꽃대 → "괴사 반점/병반"** (epipremnum_001, ficus_002 일부)
- **"매우 건강/거의 완벽"한 잎 → 갈변·반점 부착** (spathiphyllum_001, ficus_002, sansevieria_002)
- **하부 노화(senescence) → "황화"로 정확 기술** (aglaonema_003, spathiphyllum_003) — 이건 과장이 아니라, 정상 변이를 *증상으로 보고한 것 자체*가 문제

---

## PART C — 책임 단계 분포

기준: observed_symptoms가 실제보다 과장/날조 → **(가)**. 충실·경미한데 status가 비건강으로 튐 → **(나)**. 둘 다 → **(다)**.

### (가) analyze 과장 — 5건
실제 이미지엔 없는 병반·반점·괴사를 날조, 또는 "매우 건강"한 잎에 갈변 부착. 입력 오염.

| case | 근거 (symptom / cause) |
|---|---|
| spathiphyllum_001 | 실제 "매우 건강"인데 "잎끝 미세 황화 + 가장자리 갈변·마름" 부착 → cause "수분 부족" |
| haengun_001 | "미세한 노란 **반점**" 날조 (실제 잎끝만 미세 갈변) → cause는 수분/과습으로 hedge |
| epipremnum_001 | 자연 흠집·구멍을 "갈색 **괴사 반점**"으로 → cause "환경/수분" |
| ficus_002 | "거의 완벽"인데 "작은 갈색 **반점**" 날조 + 가장자리 찢어짐(물리적) → cause "해충/환경" |
| sansevieria_002 | 개화·건강한데 "작은 갈색 마른 **반점**" 날조 → cause "해충/환경" |

### (나) generate 비약 — 3건
analyze가 실제 정상 변이를 충실히 추출했는데 generate가 비건강으로 escalate.

| case | 근거 |
|---|---|
| haengun_004 | "새잎 끝부분 갈변·마름" = 실제 "끝부분만 약간 마름" 충실 → generate가 병해 의심 (cause는 수분/과습뿐, disease 미지목) |
| chlorophytum_001 | "잎끝 갈색 마름 + 가장자리 국소 갈변" = 실제 "끝 약간 갈변" 충실 → 병해 의심 (cause 수분/과습) |
| aglaonema_003 | "아래잎 황화" = 실제 "하부 잎 일부 노화"(자연 senescence) 정확 → generate가 영양 부족 |

### (다) 혼합 — 2건

| case | 근거 |
|---|---|
| chlorophytum_003 | analyze 경미 과장(실제 녹색 강조·마른 꽃대를 잎 마름으로?) + generate 건조 escalate |
| spathiphyllum_003 | analyze 경미 과장(개화·진녹색에 가장자리 갈변 부착) + 하부 황화 충실분 + generate 영양 부족 escalate |

**분포: 가 5 / 나 3 / 다 2.**

---

## PART D — 정밀화 타깃 결론

1. **1순위 = analyze 프롬프트.** 직접 책임(가 5 + 다 2 = 7/10). 두 갈래 정밀화:
   - **(a) 날조 억제**: 자연 흠집·구멍·꽃대·윤기를 "반점·괴사·병반"으로 추출 금지. 실제 병변(뚜렷한 동심원 반점·무름·곰팡이 등)만 반점/괴사 어휘 허용.
   - **(b) 정상 변이 비보고**: 하부 노화·말단 약간 갈변·경미 가장자리 갈변은 *정상 변이로 명시*하거나 observed_symptoms에서 제외 → generate가 escalate할 입력이 사라짐 (나 3건 해소).

2. **2순위 = generate cosmetic 관용 (보조).** 병해 의심 4건의 cause가 "수분/과습/환경"으로 disease를 안 가리키는데 status만 병해 의심 → generate가 자기 추론보다 status를 과상향. cause-status 정합(R12b 계열) + cosmetic→건강 관용 강화로 나·다 잔여 보강.

3. **🔴 FN 0 제약.** (b) "정상 변이 비보고"가 진짜 병징(드라세나 등 실제 비건강)까지 삼키면 recall 붕괴. analyze 정밀화는 **"정상 변이"와 "병변"의 변별 기준을 명시**해야 안전 (예: 말단 국소 갈변·하부 노화·자연 흠집 = 정상 / 확산성 반점·무름·곰팡이·전면 황화 = 병변).

4. **변수 격리**: 다음 라운드는 analyze 프롬프트 한 변수만. generate·가드는 후속.

### 다음 라운드 제안 (미구현)
- analyze observed_symptoms에 정상 변이 변별 가이드 추가 (날조 금지 + 정상 변이 비보고/명시), FN 0 사수 변별 기준 동반.
- 측정 앵커 = `after_acc_r12d1_relabeled.json` (62.86%, FP 13, FN 0). 감시: post.fn 0 유지 · post.fp ≤ 12 · 반점/괴사 날조 케이스(가 5건) 감소.

---

*read-only 진단. 커밋·푸시 보류 (task 지시).*
