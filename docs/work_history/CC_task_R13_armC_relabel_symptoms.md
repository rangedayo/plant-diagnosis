# CC Task 보충 — R13 Arm C 정정: symptoms 확정 (validate 게이트 해제)

> 직전 task `CC_task_R13_armC_relabel_rescore.md`의 §2(정정표)를 **아래 완성본으로 대체.** symptoms가 채워져 `labeling_vocab.py:75`("비건강이면 symptoms≥1") 규칙을 충족 → validate 통과 가능. **나머지 절차·예상수치·커밋 계획은 직전 task 그대로.**

## 1. 완성된 정정표 (4건 — 사용자 결정, enum 키 글자 그대로 §8.1)

`test_data/main_eval/labels.json`의 `ground_truth`:

| image_id | `is_healthy` | `true_status` | `symptoms` |
|---|---|---|---|
| `self_haengun_001` | `true`→**`false`** | `"건강"`→**`"건조"`** | **변경 없음** (이미 `["leaf_edge_dry"]`, 통과) |
| `inat_spathiphyllum_003` | `true`→**`false`** | `"건강"`→**`"과습"`** | `[]`→**`["leaf_edge_dry", "leaf_spots"]`** |
| `inat_spathiphyllum_001` | `true`→**`false`** | `"건강"`→**`"과습"`** | `[]`→**`["leaf_edge_dry"]`** |
| `inat_epipremnum_aureum_001` | `true`→**`false`** | `"건강"`→**`"병해의심"`** | `[]`→**`["leaf_browning"]`** |

- symptoms 값은 사용자가 SYMPTOM_VOCAB enum에서 직접 선택한 것 — **추가·변경 금지, 글자 그대로**.
- `true_status` 표기(예: "병해의심" vs "병해 의심")는 labels.json 기존 컨벤션에 맞출 것.
- 10건(건강 유지)은 무접촉.

## 2. validate 통과 확인
이제 비건강 4건 모두 symptoms≥1:
- haengun_001: `leaf_edge_dry`
- spathiphyllum_003: `leaf_edge_dry`, `leaf_spots`
- spathiphyllum_001: `leaf_edge_dry`
- epipremnum_001: `leaf_browning`

→ `labeling_vocab.py:75` 위반 해소 예상. `validate_main_eval.py`가 그래도 exit≠0이면 **멈추고 보고**(다른 규칙일 수 있음).

## 3. 이후 진행 (직전 task 그대로)
`CC_task_R13_armC_relabel_rescore.md`의:
- §3 §8.2 절차 (백업 → 정정 → validate → `rescore_from_output.py` → `eval/after_acc_armC_3p5flash_relabeled.json`)
- §4 예상수치 (**FP 14→10, acc 60.0→71.4%, FN 0, recall 100% 유지** — symptoms는 채점에 안 쓰이므로 이 수치 불변). 예상과 다르면 멈추고 보고.
- §5 워크리스트 갱신 (결정 칸 채우기) — **symptoms도 함께 적어두면 추적 깔끔**: epipremnum_001=leaf_browning, spathiphyllum_001=leaf_edge_dry, spathiphyllum_003=leaf_edge_dry+leaf_spots, haengun_001=leaf_edge_dry.
- §6 CLAUDE.md §2 활성 앵커 갱신
- §7 커밋 2건 (`fix:` 정정+재채점 / `docs:` 워크리스트+CLAUDE.md), 푸시 보류
- §8 보고 / §9 금지

## 4. 보고 시 추가 확인
- 정정 4건 diff에 symptoms도 위 표대로 들어갔는지.
- validate exit 0.
- rescore 수치가 §4 예상과 일치(특히 **FN=0**).
