# CC Task — R13 Arm C: GT 정정 4건 + 무과금 재채점 (Relabel Pass)

> 시점: 2026-06-09. 사용자 GT 재검 완료(14/14 판정). 본 task는 **§8.2 절차: labels.json 정정 → validate → rescore_from_output**. **새 측정 없음 (Gemini 호출 0).**

## 0. 한 줄 요약
사용자 결정에 따라 4건의 GT를 정정(건강 → 비건강+status)하고, 기존 Arm C 출력을 그대로 재채점해 새 앵커를 생성. 워크리스트와 CLAUDE.md §2 갱신.

## 1. 안전 제약 (필독)
- **과금 호출 절대 금지.** 모든 단계 무과금(파일 편집 + 스크립트 재채점). 회귀 점검 시 `-m "not integration"`.
- **`labels.json` 백업 필수** (§1, §8.2): `.bak` + 타임스탬프. 백업 없이 편집 금지.
- **정정 대상은 정확히 아래 4건만.** 다른 케이스(10건 건강 유지 포함) 무접촉.
- **변경 필드는 `is_healthy` + `true_status` 두 개만.** `symptoms`·`diagnosis` 등 자유 텍스트 필드는 사용자가 별도로 결정할 영역(§8.1) — 자동 추정·수정 금지. validate가 그 일관성으로 실패하면 **수정하지 말고 보고**.
- 사용자가 준 값 **글자 그대로 박기**(§8.1, 표현 다듬기 금지).
- 기존 앵커 `eval/after_acc_armC_3p5flash.json`·`baseline.json`·old 앵커 **읽기 OK, 수정·삭제 금지** (보존).
- `prompts.py`·RAG·generate·status guard·`run_eval.py`·`rescore_from_output.py` 자체 로직 무변경.

## 2. ① GT 정정 (사용자 결정 — 글자 그대로)

`test_data/main_eval/labels.json`의 다음 4건만 정정:

| image_id | `ground_truth.is_healthy` | `ground_truth.true_status` |
|---|---|---|
| `self_haengun_001` | `true` → **`false`** | `"건강"` → **`"건조"`** |
| `inat_spathiphyllum_003` | `true` → **`false`** | `"건강"` → **`"과습"`** |
| `inat_spathiphyllum_001` | `true` → **`false`** | `"건강"` → **`"과습"`** |
| `inat_epipremnum_aureum_001` | `true` → **`false`** | `"건강"` → **`"병해의심"`** |

(true_status 표기는 labels.json의 기존 표기 컨벤션을 따를 것. "병해 의심" vs "병해의심" 등 띄어쓰기는 기존 파일에 맞춤.)

10건은 변경 없음 (참고용 — 손대지 말 것):
- 건강 유지: `self_dracaena_001/002/003/004/006`, `inat_aglaonema_001/002/003`, `inat_chlorophytum_comosum_001/003`

## 3. ② §8.2 절차

1. **백업**: `test_data/main_eval/labels.json` → `test_data/main_eval/labels.json.<YYYYMMDD-HHMMSS>.bak`.
2. **정정**: 위 §2 표 그대로 4건만 편집. 다른 entry 무접촉.
3. **검증**: `.venv\Scripts\python.exe scripts\validate_main_eval.py` exit 0 확인. **실패 시 — 수정하려 들지 말고 즉시 보고** (symptoms/diagnosis 일관성 등 미정 영역일 수 있음).
4. **재채점**: `.venv\Scripts\python.exe scripts\rescore_from_output.py` — 입력 = `eval/after_acc_armC_3p5flash.json`, 출력 = **`eval/after_acc_armC_3p5flash_relabeled.json`** (R12 컨벤션 따라 `_relabeled` suffix).
   - `aux_plantvillage_results`는 변경 없이 그대로 보존(PlantVillage 라벨은 정정 대상 아님).
   - 정확한 CLI 인자는 `rescore_from_output.py` 시그니처에 맞춰 결정. (이전 R12 재채점 호출 패턴을 참고해 미러링.)

## 4. ③ 예상 수치 (sanity check)

재채점 결과는 다음과 **정확히 일치**해야 함 (정정한 4건이 모두 기존 FP였고 model pred_is_healthy=False이므로 전부 FP→TP로 전환):

| 지표 | 정정 전 | 정정 후 (예상) |
|---|---|---|
| TP | 9 | **13** |
| TN | 12 | 12 |
| FP | 14 | **10** |
| FN | 0 | **0** (불변) |
| 분모 | 35 | 35 |
| accuracy | 60.0% | **71.4%** (25/35) |
| recall | 100% | **100% 유지** |
| precision | 39.1% | 56.5% |

**예상과 다르면 멈추고 보고.** (예: FN이 0이 아니면 어딘가 잘못된 것 — recall 게이트 §4.2 위반.)

5-status 혼동표는 status 정정에 따라 달라지므로 그대로 보고. (haengun_001: model pred 건조 = GT 건조 → status 정답화. spathiphyllum_003: model pred 병해의심 vs GT 과습 → status 불일치. spathiphyllum_001: model pred 건조 vs GT 과습 → status 불일치. epipremnum_001: model pred 건조 vs GT 병해의심 → status 불일치.)

## 5. ④ 워크리스트 갱신

`docs/work_history/GT_recheck_worklist_R13_armC_FP14.md`(untracked)의 결정 칸을 채워 넣을 것:

- Tier 1: dracaena_001/002/004 → **유지(건강)**, haengun_001 → **비건강 (건조)**, aglaonema_001 → **유지(건강)**, epipremnum_aureum_001 → **비건강 (병해의심)**, spathiphyllum_003 → **비건강 (과습)**
- Tier 2: aglaonema_003 → **유지(건강)**, spathiphyllum_001 → **비건강 (과습)**, dracaena_006 → **유지(건강)**
- Tier 3: dracaena_003 → **유지(건강)**, aglaonema_002 → **유지(건강)**, chlorophytum_comosum_001 → **유지(건강)**, chlorophytum_comosum_003 → **유지(건강)**

그리고 워크리스트 끝에 한 줄 요약 추가: *"결정 완료 2026-06-09. 정정 4건(건강→비건강+status), 유지 10건. 정정 기준 = (가) 개체 전체 건강 판단. 정정한 4건은 사진 근거로 활성 병변/심한 환경 스트레스가 식별된 케이스."*

## 6. ⑤ CLAUDE.md §2 갱신

활성 앵커 갱신:
- **현 활성 앵커** → `eval/after_acc_armC_3p5flash_relabeled.json` (R13 Arm C, **GT 정정 후**)
  - 수치: acc **71.4%**, 분모 35, FP **10**, FN 0, recall 1.0
- **참고(강등)**: `eval/after_acc_armC_3p5flash.json` (GT 정정 전 raw 측정, 보존). 그 위에 `after_acc_r12d1_relabeled.json`도 그대로 참고로 보존.
- footer 갱신: *"2026-06-09 — R13 Arm C GT 정정(4건) + 재채점. FP 14→10, acc 60.0→71.4%, recall 1.0 유지. 잔여 10 FP = 진짜 over-call 영역."*

## 7. 커밋 (제안 2개, 푸시 보류)

분리해서 atomic하게:

1. **`fix: R13 Arm C — GT 정정 4건 + 재채점 (FP 14→10, acc 60.0→71.4%, recall 1.0 유지)`**
   - `test_data/main_eval/labels.json` (4건 정정)
   - `eval/after_acc_armC_3p5flash_relabeled.json` (새 앵커, 추적 시작)
   - `.bak` 백업 파일은 일반적으로 gitignore 대상 — repo 컨벤션 따라 처리, 추적 안 함이면 보고만.

2. **`docs: R13 Arm C 워크리스트 결정 + CLAUDE.md 활성 앵커 갱신`**
   - `docs/work_history/GT_recheck_worklist_R13_armC_FP14.md` (결정 채워 추적 시작)
   - `CLAUDE.md` (§2 + footer)

푸시 보류, 사용자 검토 후.

## 8. 보고 형식 (CC → 웹)
1. labels.json 백업 파일명 + 정정 4건 diff (정확히 위 표대로인지).
2. validate_main_eval.py exit code (0 기대).
3. rescore 결과 핵심 수치 — §4 예상치와 일치 여부 (FP, TP, TN, FN, acc, recall). **불일치 시 멈추고 원인 보고.**
4. 새 앵커 파일 경로 + 핵심 수치.
5. 워크리스트 + CLAUDE.md 변경 요지.
6. 커밋 해시 2개 + `git status` (untracked 잔존 확인).

## 9. 금지 사항
- 과금 측정(스모크·풀 eval).
- 4건 외 GT 변경.
- `symptoms`·`diagnosis` 자동 추정/수정.
- `baseline.json`·`after_acc_armC_3p5flash.json`(정정 전 원본)·old 앵커 삭제 또는 덮어쓰기.
- `rescore_from_output.py`·`run_eval.py`·`validate_main_eval.py`·`prompts.py`·RAG·guard 로직 변경.
- 자동 푸시.
