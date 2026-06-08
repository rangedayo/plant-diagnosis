# 프로젝트 전체 정리 제안서 — eval/ + 기타 (read-only)

> 생성: 2026-06-09 · 브랜치 main · tip `348aca4` · 작업트리 clean
> 보충 라운드: `docs/work_history/` 정리는 [_cleanup_proposal.md](work_history/_cleanup_proposal.md)에서 완료. 이 문서는 **work_history 제외** 전체 폴더 인벤토리 + sync 용량 대책.
> 변경물은 이 파일 1개뿐. 실제 sync 해제·`git mv`·`.gitignore` 갱신은 **후속 별도 task**.
> 근거: `du`, `git ls-files`, `.gitignore`, `MEMORY.md`. 측정 없음(read-only).

---

## Phase A — 폴더별 인벤토리 (work_history 제외)

| 폴더 | 디스크 | git 추적 | 비고 | sync 영향 |
|---|---:|---:|---|---|
| **`eval/`** | 4.2M | **65 JSON** | 측정 출력 누적 (`*.log` 2개는 gitignore) | **🔴 64% (주범)** |
| **`docs/`** (work_history 제외) | 1.2M | ~12 | design 7 + context_dumps 3 + root 4 | 🟡 16% |
| `test_data/` | 234M | **9** | 이미지 전부 gitignore, metadata/labels만 추적 | 🟢 무시 |
| `data/` | 31M | **0** | 전부 gitignore (`data/` 90행) | 🟢 무시 |
| `scripts/` | 492K | 30 | Python (재사용 vs 1회용 혼재) | 🟢 소 |
| `app/` | 276K | 28 | 백엔드 코드 | 🟢 유지 |
| `components/` | 124K | 10 | 프론트 | 🟢 유지 |
| `tests/` | 116K | 16 | pytest | 🟢 유지 |
| `lib/`·`pages/`·`types/`·`styles/` | ~61K | 11 | 프론트 | 🟢 유지 |

**결론: sync 89% 중 eval/이 64%p. 코드 폴더·test_data·data는 무관(gitignore 또는 소형). 대책은 eval/에 집중.**

---

## Phase B — `eval/` 집중 분석 (65 추적 JSON, 4.1M)

### 크기 구조
- **대용량 ~200-222KB × 13개 = ~2.8MB** — full `--aux` per-case 덤프 (sync 주범의 주범)
- 중형 ~50-90KB × ~12개
- 소형 ~13KB × ~30개 — Phase1/vertex/초기 요약본 (rescore 불가, 순수 이력)

### 🟢 유지 필수 (sync 유지) — 8개
| 파일 | KB | 근거 |
|---|---:|---|
| `baseline.json` | 14 | CLAUDE.md §1 절대 불변 (보존만) |
| `after_acc_r12d1_relabeled.json` | 88 | **현 활성 앵커** (acc 62.86%/FP13/FN0) |
| `after_acc_r12a_veto_run1/2/3.json` | 219/210/211 | **직전 라운드** R12a 3-run 측정 |
| `after_acc_r12b_cause_status.json` | 219 | R12 트랙 비교 측정 (PASS) |
| `after_acc_r12c1_rag_content.json` | 219 | R12 트랙 비교 측정 |
| `after_acc_r12d1_remove_surface.json` | 220 | R12d1 빼기 측정 (앵커 직전 단계) |

### 🟡 보존 가치 (sync 해제 가능, repo 보존) — 5개
| 파일 | KB | 근거 |
|---|---:|---|
| `after_acc_generate_escalation_v2.json` | 222 | **재측정 대기** 라인 (escalation v2) |
| `after_acc_analyze_antifab.json` | 221 | antifab 실패 측정 (§7.2 전례 원본) |
| `golden_set.json` | 11 | B-3 retrieval 골든셋 = **재사용 fixture** (측정 아님) |
| `baseline_current_postguard_run1/2.json` + `_avg` | 74/74/1 | L0/L1 앵커 (가드 전후 FP 가독성) |

> 🟡는 rescore/재측정 재실행 시 필요할 수 있으나 sync 상시 노출은 불필요 → **repo 유지 + sync 해제** 권장.

### 🔴 archive 후보 (이미 후속 라운드로 대체·무효) — 약 50개
| 그룹 | 파일 (개수) | 근거 |
|---|---|---|
| Phase1 era | `after_phase1_*` (~17), `after_vertex_baseline*` (2) | 파이프라인 구축기, 코드 반영 완료 |
| B 트랙 | `after_phase_b2/b3*/b4a/b4b/b4c*` (~11), `after_phase_b_prime*` (3) | "순효과 0" 확정, 대체됨 |
| 단발 라운드 | `after_phase_care_guide*` (3), `after_phase_status_guard*` (3), `after_phase_rename*` (3) | 완료·푸시 |
| **무효 측정** | `after_acc_r10_v2_rag_ok.json` (223), `after_acc_generate_escalation.json` (204) | MEMORY: **앵커 금지·무효** (R11 RAG전멸 / 429) |
| 대체된 ACC | `after_acc_r7_dry_guard.json` (222), `after_acc_r3r4_L0prime.json` (220), `baseline_before_mapfix.json` (14) | R8/R12로 대체 |

> 🔴 대용량(r10_v2·escalation·r7 = ~650KB)이 sync 해제 1순위. **무효 측정인데 ~220KB씩 sync 점유 중.**

---

## Phase C — 기타 폴더 권고

### scripts/ (30개)
| 분류 | 파일 | 권고 |
|---|---|---|
| **재사용 (유지)** | `run_eval.py`, `rescore_from_output.py`, `validate_main_eval.py`, `validate_plantvillage_50.py`, `eval_avg.py`, `build_b_dataset_rag.py`, `build_care_guide.py`, `eval_rag/retrieval.py` | 🟢 유지 |
| **1회용 마이그레이션** | `migrate_labels_add_status.py`, `migrate_plantvillage_add_status.py`, `prepare_plantvillage.py` | 🔴 `scripts/_archive/migrations/` |
| **1회용 probe** | `_probe_ncpms.py`, `_probe_svc42_response.py`, `_probe_svc_codes.py` | 🔴 archive |
| **1회용 수집** | `collect_*.py` (6: inaturalist/mobot/mu_trinklein/psu_indoor/psu_ucanr/wikimedia) | 🔴 archive (특히 `collect_wikimedia`=폐기 데이터) |
| **대체된 build** | `build_main_rag.py`, `build_rag_db.py`, `build_species_normal_rag.py` | ❓ 대체 여부 사용자 확인 (species_normal=순효과0) |
| **라운드별 진단** | `diagnostics/*` (4: r12_0/r12a×2/r12b) | 🟡 라운드 종료 후 archive |

### test_data/ (이미지 gitignore, metadata 9 추적)
| 폴더 | 권고 |
|---|---|
| `main_eval`, `plantvillage_50`, `self_captured`, `inaturalist_candidates` | 🟢 사용 중 유지 |
| `wikimedia_candidates` | 🔴 **deprecated** (MEMORY: wikimedia 폐기, images gitignore됨, SOURCE 잔재 확인) |
| `moneyplant_candidates` | ❓ 보관자리 (SOURCE만 추적) — 편입 여부 미정 |

### docs/ 기타
| 항목 | 권고 |
|---|---|
| `docs/context_dumps/` (3: README + generate_input 2) | 🔴 sync 해제 + `_archive/` (구 컨텍스트 덤프) |
| `docs/design/` (7) | 🟢 유지 (설계 정본) |
| `docs/phase2_decisions.md`, `phase2_refactoring_plan.md`, `refactoring_log.md` | 🟡 Phase2 완료 → archive 후보 |
| `docs/eval_collection_spec.md` | 🟢 유지 |

---

## Phase D — 두 액션 제안

### Action 1 (즉시·리스크 0): Project Knowledge sync 제외

GitHub 동기화 UI에서 **체크 해제 권장** (CC 권한 밖, 사용자 직접):

| 해제 대상 | 이유 | 절감 |
|---|---|---|
| **`eval/` 전체** (단, `baseline.json` + `after_acc_r12d1_relabeled.json`만 유지 가능하면 유지) | 측정 출력은 AI 컨텍스트 불요, 대용량 | **~64%p** |
| `docs/context_dumps/` | 구 컨텍스트 덤프, 현 작업 무관 | ~소 |

> **예상 sync 용량: 89% → ~25%** (eval 64%p 제거 시). eval에서 활성 앵커 2개만 유지하면 ~26%.
> 가장 큰 비효율: **무효 측정**(`after_acc_r10_v2_rag_ok` 223KB·`after_acc_generate_escalation` 204KB)이 sync 점유 중 — 1순위 해제.

### Action 2 (정식 cleanup·별도 task): repo 정리

권장 신규 구조:
```
eval/_archive/phase1/        ← after_phase1_*, vertex
eval/_archive/b_track/       ← after_phase_b*
eval/_archive/single_rounds/ ← care_guide, status_guard, rename
eval/_archive/invalid/       ← r10_v2_rag_ok, generate_escalation (무효)
eval/_archive/superseded/    ← r7_dry_guard, r3r4_L0prime, baseline_before_mapfix
docs/context_dumps/_archive/
scripts/_archive/migrations/ ← migrate_*, prepare_plantvillage
scripts/_archive/probes/     ← _probe_*, collect_*
```
우선순위(높음→낮음): ① eval/ 무효·Phase1 archive → ② scripts 1회용 archive → ③ docs phase2 archive.
`.gitignore` 갱신: eval/ 측정 출력 신규분 패턴 추가 검토(단 활성 앵커는 추적 유지).

---

## 전체 정리 그림 (work_history 제안 통합)

| 영역 | 현재 | 정리 후 (가시/sync) |
|---|---:|---:|
| `docs/work_history/` (지난 task) | 84 파일 | ~21 가시 (회고 9 + ACTIVE 12) |
| `eval/` | 65 JSON / 4.1M | ~13 활성 유지, ~50 archive, sync ~64%→~1% |
| `scripts/` | 30 | ~14 유지, ~16 archive |
| **sync 용량** | **89%** | **~25%** (Action 1만으로) |

> 두 라운드 합산 시: **work_history 가시 -75% + eval sync -64%p → Project Knowledge 89%→~25%, repo 가시 파일 대폭 축소.** 무손실(전부 `_archive/` 보존, gitignore 미적용).

---

## 다음 단계 (후속·범위 밖)

1. 사용자 검토 → 경계/그룹 조정
2. **Action 1 즉시**: GitHub sync UI에서 `eval/`·`context_dumps/` 해제 (사용자 직접)
3. **Action 2 별도 task**: `_archive/` 이동 + `git mv` + atomic 커밋 + `.gitignore` 갱신 — work_history 정리와 병합 또는 분리는 사용자 결정
