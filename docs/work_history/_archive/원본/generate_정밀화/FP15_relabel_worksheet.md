# FP 15건 라벨 재검 워크시트 (R12d-1 기준)

> 입력: `eval/after_acc_r12d1_remove_surface.json` (R12d-1 단일 run). FP = true_status=건강 ∧ pred=비건강.
> GT 라벨 파일(2단계 정정 대상): **`test_data/main_eval/labels.json`** (list 39건, 각 `ground_truth.is_healthy` + `ground_truth.true_status`). ⚠ 이 워크시트는 read-only — 라벨 무변경.
> 이미지: `test_data/main_eval/images/<case_id>.jpg` (15건 전부 존재 확인).

## 재검 rubric (합의 기준)

| 조건 | 판정 |
|---|---|
| `self_` + 전체 생장 안정 + 갈변이 말단(잎끝)·하부 국한 | **건강 유지** (hard case 인정) |
| `self_` + 광범위/진행성 손상(전체 시듦·줄기 손상) | **비건강 정정** |
| `inat_` + 광범위 시듦/명백한 이상 | **비건강 정정** |
| `inat_` + 경미·애매 | **ambiguous 제외** |
| 이진(건강/비건강) 판정이 본질적으로 모호 | **ambiguous 제외** |

⚠ 비건강 정정 시 **원인 status(건조/과습/병해/영양)는 별개 판단.** 이미지로 원인 불명확하면 "비건강·원인미상" 또는 ambiguous. 모델이 "건조"로 찍었다고 GT를 자동 "건조"로 정정 금지.

---

## 그룹 1 — pred=건조 (6건)

| case_id | 종 (gt / pred_sci) | 출처 | observed_symptoms | 현 GT | top_3 | 이미지 | 재검 판정 | 재검 status | 근거 |
|---|---|---|---|---|---|---|---|---|---|
| self_dracaena_003 | 드라세나 송 오브 인디아 / Cordyline fruticosa | **self** | 여러 잎의 잎끝 갈변 및 마름 | 건강 | aw·aw·abiotic | images/self_dracaena_003.jpg | **건강 유지** | 건강 | 사용자 실측: 생장 안정, 하부 자연 노화 |
| self_dracaena_004 | 드라세나 송 오브 인디아 / Dracaena deremensis | **self** | 여러 잎의 잎끝이 바삭하게 갈변 / 일부 잎의 황화 및 고사 | 건강 | aw·abiotic·"" | images/self_dracaena_004.jpg | **건강 유지** | 건강 | 사용자 실측: 생장 안정, 하부 자연 노화 |
| self_dracaena_006 | 드라세나 송 오브 인디아 / Dracaena reflexa 'Song of India' | **self** | 여러 잎의 잎끝 갈변 및 마름 / 일부 잎의 전체 고사 / 잎의 세로 말림 현상 | 건강 | aw·aw·abiotic | images/self_dracaena_006.jpg | **건강 유지** | 건강 | 사용자 실측: 생장 안정, 하부 자연 노화 |
| inat_spathiphyllum_002 | 스파티필름 / Spathiphyllum wallisii | inat | 다수의 아래잎 갈변 및 고사 | 건강 | aw·""·"" | images/inat_spathiphyllum_002.jpg | **비건강 정정** | 원인 미상 | 아래쪽 잎 광범위 시듦(사용자 판정) |
| inat_chlorophytum_comosum_003 | 접란 / Chlorophytum comosum | inat | 일부 잎끝 갈변 및 마름 | 건강 | aw·abiotic·"" | images/inat_chlorophytum_comosum_003.jpg |  |  |  |
| inat_spathiphyllum_001 | 스파티필름 / Spathiphyllum wallisii | inat | 잎끝 미세한 황화 / 잎 가장자리 갈변 및 마름 | 건강 | aw·aw·abiotic | images/inat_spathiphyllum_001.jpg |  |  |  |

## 그룹 2 — pred=병해 의심 (7건)

| case_id | 종 (gt / pred_sci) | 출처 | observed_symptoms | 현 GT | top_3 | 이미지 | 재검 판정 | 재검 status | 근거 |
|---|---|---|---|---|---|---|---|---|---|
| self_haengun_001 | 행운목 / Dracaena fragrans | **self** | 잎끝 갈변 및 마름 / 일부 잎의 미세한 노란 반점 | 건강 | frame·disease·"" | images/self_haengun_001.jpg |  |  |  |
| self_haengun_004 | 행운목 / Dracaena fragrans | **self** | 새잎 끝부분 갈변 및 마름 | 건강 | abiotic·""·env | images/self_haengun_004.jpg |  |  |  |
| inat_chlorophytum_comosum_001 | 접란 / Chlorophytum comosum | inat | 일부 잎끝의 갈색 마름 / 잎 가장자리의 국소적 갈변 | 건강 | abiotic·""·aw | images/inat_chlorophytum_comosum_001.jpg |  |  |  |
| inat_epipremnum_aureum_001 | 스킨답서스 / Epipremnum aureum | inat | 여러 잎 가장자리의 불규칙한 갈변 및 마름 / 일부 잎의 갈색 괴사 반점 | 건강 | general·frame·general | images/inat_epipremnum_aureum_001.jpg |  |  |  |
| inat_ficus_elastica_002 | 고무나무 / Ficus elastica | inat | 일부 잎의 작은 갈색 반점 / 일부 잎 가장자리 찢어짐 | 건강 | ""·pest·general | images/inat_ficus_elastica_002.jpg |  |  |  |
| inat_monstera_deliciosa_001 | 몬스테라 / Monstera deliciosa | inat | 여러 잎 황화 / 잎 가장자리 갈변 / 잎 중앙부 불규칙 갈색 반점 | 건강 | disease·""·disease | images/inat_monstera_deliciosa_001.jpg |  |  |  |
| inat_sansevieria_trifasciata_002 | 산세베리아 / Dracaena trifasciata | inat | 일부 잎에 작은 갈색 마른 반점 | 건강 | ""·pest·disease | images/inat_sansevieria_trifasciata_002.jpg |  |  |  |

## 그룹 3 — pred=영양 부족 (2건)

| case_id | 종 (gt / pred_sci) | 출처 | observed_symptoms | 현 GT | top_3 | 이미지 | 재검 판정 | 재검 status | 근거 |
|---|---|---|---|---|---|---|---|---|---|
| inat_aglaonema_003 | 아글라오네마 / Aglaonema commutatum | inat | 아래잎 황화 | 건강 | ""·aw·abiotic | images/inat_aglaonema_003.jpg |  |  |  |
| inat_spathiphyllum_003 | 스파티필름 / Spathiphyllum wallisii | inat | 잎 가장자리 갈변 / 아래잎 황화 | 건강 | nutrient·aw·aw | images/inat_spathiphyllum_003.jpg |  |  |  |

---

## 출처 분포 (웹 판정 우선순위)

- **self_ (사용자 실측 가능) = 5건**: dracaena_003·004·006(3건 사전 판정완료), haengun_001·004(미판정 2건).
- **inat_ (공개 데이터, 실측 불가) = 10건**: spathiphyllum_001·002·003, chlorophytum_001·003, epipremnum_001, ficus_002, monstera_001, sansevieria_002, aglaonema_003. (spathiphyllum_002 사전 판정완료)
- **사전 판정 4건**: 건강 유지 3(dracaena_003·004·006) + 비건강 정정 1(spathiphyllum_002).
- **미판정 11건**: self 2 + inat 9. → 웹 판정 시 self 2건 우선(실측 대조 가능), inat 9건은 이미지 단독 판정.

## 이미지 경로 (전 15건 존재)
`test_data/main_eval/images/<case_id>.jpg` — 누락 0건.

## GT 라벨 파일 위치 (2단계 정정 대상, 이번엔 무수정)
- **정본**: `test_data/main_eval/labels.json` (list 39건). 정정 필드 = 각 항목 `ground_truth.is_healthy`(bool) + `ground_truth.true_status`(건강/건조/과습/병해 의심/영양 부족/ambiguous).
- 백업 존재: `labels.20260605_201853.bak.json` 등(.bak). draft: `labels_draft.json`, `labels_inat_draft.json`.
- 검증 스크립트: `scripts/validate_main_eval.py` (정정 후 무결성 확인용).
- ⚠ `eval/baseline.json`은 GT 정본 아님 — 절대 미접촉.
