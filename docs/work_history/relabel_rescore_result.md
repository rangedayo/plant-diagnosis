# 라벨 재검 + 재채점 — 새 비교 기준점 확정

> FP 15건 전수 재검 결과를 labels.json에 정정하고, 재측정 없이(`scripts/rescore_from_output.py`) 점수만 재계산.
> 워크시트: `FP15_relabel_worksheet.md` · 변별 진단: `R12c1a_discrimination_diagnosis.md`.

## 새 기준점 (이후 모든 라운드 비교 기준)

- **정본: `eval/after_acc_r12d1_relabeled.json`** — acc **62.86%**, 분모 **35**, **FP 13 · FN 0**(recall 1.0), precision 0.409.
- 정정 전(`after_acc_r12d1_remove_surface.json`, 원본 측정) = acc 58.33%, 분모 36, FP 15, FN 0 → **보존**(provenance).
- ⚠ **`eval/baseline.json`은 옛 라벨 기준이라 비교용 아님** — 보존만, 무접촉.

## 라벨 정정 2건 (나머지 13건 무변경 = 라벨 정확)

| case | 변경 | 비고 |
|---|---|---|
| inat_spathiphyllum_002 | 건강 → **비건강-원인미상** (is_healthy=false) | 아래잎 광범위 시듦. 원인 단정 불가 → 신설 enum. is_healthy엔 비건강 포함(TP), 5-status 혼동표는 중립 제외 |
| inat_monstera_deliciosa_001 | 건강 → **ambiguous** | halo 반점 병해 vs 환경/물리 손상 단정 불가 → 분모 제외. 모델 "병해 의심"은 정당한 의심 |

- 백업: `test_data/main_eval/labels.20260608_075206.bak.json` (정정 전 원본).
- 검증: `scripts/validate_main_eval.py` exit 0 (39건 valid).

## FP 13건 구성 (전부 GT 정확 = 진짜 모델 과민, 라벨로 못 줄임)

- **hard case 3 (드라세나, 종 인지 영역)**: self_dracaena_003·004·006 — 진짜 건조(행운목)와 증상 텍스트 동일, 종으로만 변별. 카드/프롬프트로 불가(`R12c1a` 결론 C).
- **개선 가능 10 (analyze 증상 추출 정밀화 타깃)**: haengun_001·004, chlorophytum_001·003, epipremnum_001, ficus_002, sansevieria_002, aglaonema_003, spathiphyllum_001·003 — 명백히 건강한 사진을 병해/영양/건조로 과민 판정.

## 도구 / 스키마

- `scripts/rescore_from_output.py`: 기존 측정 출력 + 현행 labels.json → `_build_result` 재사용해 **모델 호출 0**으로 재채점. labels 정정 후 baseline 갱신용 재사용 가능.
- `STATUS_UNKNOWN_CAUSE = "비건강-원인미상"` (labeling_vocab): is_healthy 비건강 포함 + 5-status 자동 skip. `ambiguous`(건강/비건강 자체 불명)와 구분.

## 알려진 측정 노트 (별도 후보, 이번 미반영)

`_build_fp_analysis`는 `gt_is_healthy`만 보고 ambiguous를 제외 안 해 monstera를 FP로 셈(진단 블록 14) — 헤드라인 `is_healthy_post_guard.fp`(13)와 1건 차이. 헤드라인 13이 정답. 진단 블록 ambiguous 제외 정렬은 변수 격리 위해 별도 라운드 후보.

## 다음 (범위 밖)

analyze(증상 추출) 정밀화 라운드 — 개선 가능 10건 타깃(정상 변이의 병징 과장 추출 억제), FN 0 사수. 드라세나 hard 3은 종 인지 별도.
