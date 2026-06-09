# CC Task — R15: GT에 3단 스키마(건강/경미/비건강) 반영

> 시점: 2026-06-09. R14(generate 프롬프트 레버) 기각 후, 진짜 병목=이진 스키마 → 3단 도입 결정.
> **이번 = GT 데이터 + 받쳐주는 규칙 코드(vocab·validate)만.** 측정·채점 코드(run_eval)·모델 출력 변경 없음.
> 라벨은 전부 사람(랑) 확정값(§8.1). 라운드 번호 R15는 잠정.

## 0. 한 줄 요약
전체 39장에 3단 라벨(`tier` = 건강/경미/비건강)을 부여하고, `labeling_vocab.py`·`validate_main_eval.py`를 3단을 받도록 확장. 비건강은 원인(true_status)·증상 유지. ambiguous는 0이 됨(4장 전부 재분류). 백업 + validate exit 0 + 커밋(푸시 보류).

## 1. 안전 제약 (필독)
- **과금 측정 금지.** 무과금(파일·검증·git만). 회귀 점검 `-m "not integration"`.
- `test_data/main_eval/labels.json` **백업 필수**(`.bak`+타임스탬프) 후 편집.
- **라벨 자동 추정 금지(§8.1).** 증상이 없는 비건강 케이스는 **사람이 채울 자리** — 임의로 채우지 말고 **멈추고 보고**.
- 활성 앵커·`baseline.json`·old 앵커 **무접촉**(읽기만).
- `run_eval.py`·`rescore_from_output.py` **로직 변경 금지**(이번은 GT·vocab·validate만).
- 커밋까지. **푸시 보류.**

## 2. Phase 0 — read-only (먼저 보고·HOLD)
1. 현재 `labels.json` 한 entry 구조 출력(ground_truth 키 구성), 그리고 **아래 §4 비건강 16장 중 `symptoms`가 비어 있는 것**을 전수 확인해 목록 보고. 특히 ambiguous에서 옮긴 3장(`monstera_deliciosa_001`·`epipremnum_aureum_007`·`epipremnum_aureum_009`).
2. §3 스키마 반영안(아래)이 현재 코드와 맞는지 확인, 충돌 있으면 보고.
3. → **보고 후 HOLD.** 증상 결측이 있으면 사용자가 vocab에서 채워줄 때까지 대기. 결측 없으면 OK 받고 Phase 1.

## 3. 스키마 반영안 (Phase 0에서 확인·미세조정)
`labeling_vocab.py`:
- `TIER_VOCAB = ["건강", "경미", "비건강"]` 신설.
- `STATUS_VOCAB`에 `"경미"` 추가(또는 tier 전용으로 분리 — CC 판단, 단순한 쪽으로).

`validate_label` 갱신:
- required에 `tier` 추가, `tier ∈ TIER_VOCAB` 검증.
- **tier ↔ is_healthy 정합**: `tier="비건강"` ↔ `is_healthy=False`; `tier ∈ {건강, 경미}` ↔ `is_healthy=True`.
- **증상 규칙(유지)**: `is_healthy=False`(=비건강)이면 `symptoms ≥ 1`. 경미·건강은 요구 안 함(경미는 있어도 됨).
- 기존 `true_status` 규칙은 유지하되 경미 수용: `true_status="경미"` 허용(tier=경미일 때).

per-entry 표현(제안):
- `tier`: 건강 | 경미 | 비건강
- `is_healthy`: 건강·경미 → `true`, 비건강 → `false`
- `true_status`: 건강 → `"건강"`, 경미 → `"경미"`, 비건강 → 원인(`과습`/`건조`/`병해 의심`/`영양 부족`/`비건강-원인미상`)
- `symptoms`: 비건강은 기존 유지(없으면 사용자 입력). 경미·건강은 기존 그대로(건드리지 말 것).

> 주: 기존 `run_eval.py`는 이 변경 후에도 깨지지 않고 degrade — 경미는 is_healthy=true라 이진에선 건강 취급, 5-status 혼동표에선 STATUS_VOCAB 밖이면 자동 skip. 3단 채점은 다음 라운드(별도). **이번엔 run_eval 손대지 말 것.**

## 4. 39장 tier 라벨 (사람 확정값 — 글자 그대로)

### 건강 (16)
self_dracaena_003 · inat_aglaonema_001 · inat_aglaonema_002 · inat_aglaonema_003 · inat_chlorophytum_comosum_001 · inat_chlorophytum_comosum_002 · inat_epipremnum_aureum_002 · inat_epipremnum_aureum_003 · inat_ficus_elastica_001 · inat_ficus_elastica_002 · inat_ficus_elastica_003 · inat_monstera_deliciosa_002 · inat_monstera_deliciosa_003 · inat_sansevieria_trifasciata_001 · inat_sansevieria_trifasciata_002 · inat_sansevieria_trifasciata_003

→ tier="건강", is_healthy=true, true_status="건강". (대부분 현재와 동일 — tier 필드만 추가.)

### 경미 (7)
self_dracaena_001 · self_dracaena_002 · self_dracaena_004 · self_dracaena_006 · self_haengun_004 · inat_chlorophytum_comosum_003 · inat_epipremnum_aureum_006

→ tier="경미", is_healthy=true, true_status="경미". (현재 건강이던 것 → tier만 경미로. is_healthy/symptoms 기존 유지.)

### 비건강 (16) — tier="비건강", is_healthy=false, true_status=원인
| image_id | true_status(원인) | symptoms |
|---|---|---|
| self_haengun_001 | 건조 | 기존 유지 |
| self_haengun_002 | 건조 | 기존 유지 |
| self_haengun_003 | 건조 | 기존 유지 |
| self_haengun_005 | 건조 | 기존 유지 |
| self_haengun_006 | 건조 | 기존 유지 |
| self_haengun_008 | 건조 | 기존 유지 |
| inat_epipremnum_aureum_004 | 건조 | 기존 유지 |
| inat_monstera_deliciosa_001 | 건조 | **확인 필요(결측 시 사용자 입력)** |
| inat_spathiphyllum_001 | 과습 | 기존 유지 |
| inat_spathiphyllum_003 | 과습 | 기존 유지 |
| inat_epipremnum_aureum_009 | 과습 | **확인 필요** |
| inat_epipremnum_aureum_001 | 병해 의심 | 기존 유지 |
| inat_epipremnum_aureum_005 | 병해 의심 | 기존 유지 |
| inat_epipremnum_aureum_008 | 병해 의심 | 기존 유지 |
| inat_epipremnum_aureum_007 | 병해 의심 | **확인 필요** |
| inat_spathiphyllum_002 | 비건강-원인미상 | 기존 유지 |

- "병해 의심" 표기는 STATUS_VOCAB(`"병해 의심"`, 띄어쓰기)에 맞추고, 기존 entry 표기와 일관 확인.
- **확인 필요 3장**: 현재 ambiguous라 symptoms 결측 가능 → Phase 0에서 확인, 결측이면 사용자가 SYMPTOM_VOCAB에서 ≥1 선택해 채움(여기 와서 반영).

## 5. Phase 1 — 적용 (Phase 0 OK + 필요 증상 확보 후)
1. `labels.json` `.bak` 백업.
2. `labeling_vocab.py`·`validate_main_eval.py` §3대로 갱신.
3. 39장에 §4 tier/is_healthy/true_status 반영. ambiguous 4장은 위 재분류대로(이제 ambiguous 0).
4. `scripts/validate_main_eval.py` exit 0 확인. **실패 시 멈추고 보고**(증상 결측 등이면 사용자 입력 대기).
5. tier 분포 보고: 건강 16 / 경미 7 / 비건강 16, ambiguous 0 (합 39).

## 6. 커밋 (atomic, 푸시 보류)
1. `feat: GT 3단 스키마(tier) + vocab/validate 확장 (R15)` — labeling_vocab.py·validate_main_eval.py.
2. `data: 39장 3단 라벨 반영 (건강16/경미7/비건강16, ambiguous→0)` — labels.json (+ .bak).
- 해시·`git status` 보고.

## 7. 보고 형식
1. Phase 0: entry 구조 + 비건강 증상 결측 목록 + 스키마안 확인. → HOLD.
2. (적용 후) vocab/validate diff 요지.
3. labels.json 39장 tier 반영 확인 + validate exit 0 + tier 분포.
4. 커밋 해시 + git status.

## 8. 금지 사항
- 과금 측정.
- 증상·라벨 자동 추정/임의 입력(§8.1) — 결측은 멈추고 보고.
- `run_eval.py`·`rescore_from_output.py` 로직, 모델 출력(generate/analyze), 앵커·baseline 변경.
- 자동 푸시.
