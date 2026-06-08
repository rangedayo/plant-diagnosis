# docs/work_history/ 정리 제안서 (read-only 인벤토리)

> 생성: 2026-06-09 · 브랜치 main · tip `348aca4` · 작업트리 clean
> 이 문서는 **read-only 인벤토리 + 정리 권고**입니다. 변경물은 이 파일 1개뿐. 실제 회고 작성·`git mv`·아카이브 이동은 **후속 별도 task** (본 라운드 범위 밖).
> 근거: 파일명 규칙 + `git log` 최종수정 커밋/날짜 + `MEMORY.md` 라운드별 핵심 수치. memory가 다루지 않는 초기 파일(Phase 1 일부)은 파일명 기반 추정임을 명시.

---

## Phase A — 시리즈별 인벤토리

전체 **84개 / 약 14,900 라인**. 시리즈 분류:

| 시리즈 | 파일 수 | 누적 라인(약) | 상태 | tip 기준 위치 |
|---|---:|---:|---|---|
| **Phase 1 파이프라인** (`1-N`) | 15 | 4,728 | 완료·푸시 | 가장 오래됨 (05-30 ~ 06-01) |
| **ACC 트랙** (`ACC-R1~R10`, fix, fix2, 위생) | 13 | 1,774 | 완료·푸시 | 06-05 ~ 06-06 |
| **R12 트랙** (`R12_0/a/b/c1/c1a/d1`) | 15 | 1,976 | **활성 라인** | 06-07 ~ 06-09 (tip) |
| **generate 정밀화 분석** (FP15, relabel, overcall, antifab, escalation, json_parse) | 10 | 801 | **활성·미커밋/재측정 대기** | 06-08 (bcfebd9·17b040e) |
| **B 트랙** (b_dataset RAG) | 7 | 2,495 | 완료·푸시 | 06-03 |
| **프론트 리디자인** (`R0~R6`) | 8 | 1,018 | 완료·푸시 | 06-04 |
| **시계열 기능** (`cc_timeline_*`) | 6 | 1,230 | 완료·푸시 | 06-04 ~ 06-05 |
| **L0 측정 정비** (`L0_*`) | 2 | 101 | 완료·푸시 | 06-04 |
| **한글명 보조** (run_eval, status_guard×2, 기능b, 드라세나, 맵보강, 정리파악, 정합라운드) | 8 | 770 | 완료·푸시 | 05-30 ~ 06-04 |
| **합계** | **84** | **~14,893** | | |

> 주: `ACC-R5`/`ACC-R8`은 사용자 측정 라운드라 task `.md` 없음(혼동표/측정만, memory에 기록). 프론트·시계열 트랙은 task 명세에 미열거됐으나 명확한 응집 그룹이라 별도 시리즈로 식별.

---

## Phase B — 파일별 요약

### Phase 1 파이프라인 (`1-N`) — 15개 · 완료
Vision→keyword→retrieve→generate 5단계 파이프라인 구축. 전부 푸시 완료. 핵심 산출은 코드에 반영됨(diagnosis/프롬프트는 이력).
- `1-1` vision provider protocol · `1-2`/`1-2.5` Gemini provider + Vertex ADC 전환(진단+프롬프트) · `1-3`(초안 v1)+`1-3_v4`(보강 진단) analyze 프롬프트 · `1-4` analyze node · `1-5` graph 와이어링 진단 · `1-6` keyword 축소 진단 · `1-7`/`1-7.5` generate 재설계+status 경로 · `1-8` retrieve 정비 · `1-9` state/schema 슬림화(51594d2) · `1-10a` RAG_FAILED 폐기·Plant.id sweep(ad4d1e1) · `1-10b` temperature 튜닝 최종측정.

### ACC 트랙 — 13개 · 완료
5-status 라벨 스키마 확립 + 평가셋 39건 구축 + 건조/영양부족 변별 시도.
- `ACC-R1` true_status 스키마 마이그레이션 · `ACC-R2` 행운목 "건조" 입력 · `ACC-R3`(epipremnum 6장 편입 v3)+`-labels`(33→39)+`-followup`(명명통일) **R3 trio** · `ACC-R4` run_eval 혼동표+plantvillage 사전매핑 · `ACC-R6` 건조 미발화 진단 · `ACC-R7` 건조·과습 트리거(순효과 0) · `ACC-R9` 변별실패 병목=analyze 상류 확정 · `ACC-R10` analyze 4축+generate 충돌룰(R12d-1에서 빼기 대상으로 입증) · `ACC-fix` baseline 원복 · `ACC-fix2` RAG transient 실패 진단 · `데이터위생` wikimedia 폐기.

### R12 트랙 — 15개 · **활성 라인**
현 활성 앵커 `after_acc_r12d1_relabeled.json`(acc 62.86%/FP13/FN0)로 수렴한 라인.
- `R12_0` readonly 진단(task+diagnosis 2개) · `R12a` 가드 위치 veto = **직전 라운드, tip 348aca4** (diagnosis_task + diagnosis + implementation_task + result + run3_hygiene_check_task + run3_hygiene_check = **6개**) · `R12b` cause-status 정합룰(task+result, 실측 PASS) · `R12c1` RAG 콘텐츠 건조카드(task) · `R12c1a` 변별 진단(task+diagnosis) · `R12d1` 빼기 라운드(task+result, surface 분리).

### generate 정밀화 분석 — 10개 · **활성·미커밋/재측정 대기**
`MEMORY.md`: "전부 미커밋, tip 17b040e/bcfebd9". generate escalation 측정 결과 대기 중.
- `FP15` relabel(inventory_task+worksheet) · `relabel_rescore`(task+result) = **새 앵커 정의 문서** · `analyze_overcall`(task+diagnosis, FP10 책임분해) · `analyze_antifab`(task, antifab 실패→롤백) · `generate_escalation`(task, 정합룰 강화+retry 상향, **재측정 대기**) · `json_parse_failure`(task+diagnosis, 429 RESOURCE_EXHAUSTED 진단).

### B 트랙 — 7개 · 완료
b_dataset RAG 수집→임베딩→측정. FP는 generate 본질임을 확증한 라인.
- `B-1` 수집 · `B-2` 청크/임베딩/적재(791d469) · `B-3` 골든셋 측정(Hit@10=1.0) · `B-4a` FP 본질 진단 · `B-4b` problem_type 활용(순효과 0) · `B-4c` tie+cosmetic 룰(순효과 0) · `B-prime` 종메타 정상화(순효과 0).

### 프론트 리디자인 (`R0~R6`) — 8개 · 완료
Plantia 4화면 Next.js 이식. 전부 푸시(9ef8729~4da149f).
- `R0` gate · `R1` tokens/types · `R2` ResultView · `R3` CareGuideView · `R4` home+upload(+hotfix illustration/timeout) · `R5` UI polish 브랜딩 · `R6` careguide layout.

### 시계열 기능 (`cc_timeline_*`) — 6개 · 완료
Firebase 인증→영속화→비교. 기능 완전 종료(d931d80).
- `step1` firebase auth(+followup auth hygiene) · `step2a` 쓰기 · `step2b` 읽기 UI · `step3` compare(+followup 버튼 스타일).

### L0 측정 정비 — 2개 · 완료
- `L0_eval_baseline_readonly_survey` · `L0_impl_guard_fp_legibility`(가드 전/후 FP 가독성, L1 앵커).

### 한글명 보조 — 8개 · 완료
- `run_eval_작성` · `status_guard_설명정합`+`status_guard_전략2`(FP 17.5→7.5 성공 라운드) · `기능b_케어가이드` · `드라세나_라벨정정` · `맵보강_재측정` · `정리파악_docs커밋` · `정합라운드_임베딩확인`.

---

## Phase C — 분류 권고

### 🟢 ACTIVE 유지 (그대로, 합치지 않음) — 약 12개
현 활성 앵커 비교에 직접 연결되거나 미커밋/재측정 대기인 핫 파일.

| 파일 | 근거 |
|---|---|
| `R12a_*` (6개) | tip 348aca4 = 직전 라운드. veto 효과 미입증·안전핀 유지 중 |
| `relabel_rescore_result.md` | 현 활성 앵커(after_acc_r12d1_relabeled.json) **정의 문서** |
| `generate_escalation_task.md` | **재측정 대기** (escalation v2, 쿼터 여유 시) |
| `analyze_antifab_task.md` / `analyze_overcall_diagnosis(.md/_task.md)` | generate 정밀화 진행 라인, 미커밋 |
| `json_parse_failure_diagnosis(.md/_task.md)` | 429 진단, run_eval 예외처리 개선 미완 |

### 🟡 회고 합치기 (산재된 같은 라운드 → 1 회고) — 약 49개 → 9 회고
같은 라운드의 task+result+diagnosis가 흩어진 묶음. 1 회고로 흡수 후 원본 아카이브.

| 회고 신설(제안명) | 흡수 원본 | 비고 |
|---|---|---|
| `R12_트랙_회고.md` | R12_0(2) + R12b(2) + R12c1(1) + R12c1a(2) + R12d1(2) = **9** | R12a는 ACTIVE 유지(별도) |
| `Phase1_파이프라인_회고.md` | `1-N` 15개 | 코드 반영 완료, 깊은 회고 불필요 |
| `ACC_트랙_회고.md` | ACC 13개 (R3 trio 포함) | R7/R9/R10 교훈은 §7에 이미 |
| `B_트랙_회고.md` | B 7개 | "순효과 0" 3연속 핵심 |
| `프론트_리디자인_회고.md` | R0~R6 8개 | UI, 진단 무관 |
| `시계열_기능_회고.md` | cc_timeline 6개 | 기능 종료 |
| `generate_정밀화_회고.md` | FP15(2) + relabel_rescore_task(1) | analyze_overcall은 ACTIVE라 제외, relabel result도 ACTIVE |
| `status_guard_회고.md` | status_guard×2 + 기능b + run_eval | FP 17.5→7.5 성공 라운드 보존 |
| `잡_보조_회고.md` | 드라세나·맵보강·정리파악·정합라운드·L0×2 | 얕게 |

### 🔴 아카이브 직접 이동 (회고 불요, 교훈 §7에 이미) — 0~소수
CLAUDE.md §7에 이미 반영된 실패 전례(antifab·status_hint·R10 황화룰·"추가만")는 회고 없이 원본만 `_archive/원본/<라운드>/`로 옮겨도 됨. 단 본 제안은 **회고 흡수 후 일괄 아카이브**를 기본으로 하므로, 🟡의 원본들이 아카이브 대상이 됨(중복 분류 아님 — 🟡=회고 작성, 그 결과 원본 이동).

### ❓ 판단 필요 — 3개
| 파일 | 쟁점 |
|---|---|
| `analyze_overcall_*` (2) | generate 정밀화 라인이나 antifab으로 이미 결론(롤백). ACTIVE vs 회고 흡수 경계 |
| `relabel_rescore_task.md` | result는 ACTIVE(앵커정의)인데 task는 회고로? 분리 보관 여부 |

---

## Phase D — 제안 요약

- **전체 84개 → 정리 후 가시 ~21개** (ACTIVE 12 + 회고 신설 9), 원본 ~63개는 `_archive/원본/<라운드>/`로 이동. **가시 파일 75% 감축.**
- **그룹화**: 9개 트랙 회고가 각 트랙 원본을 흡수 (위 🟡 표).

### active 경계선 권고
> **R12d-1(relabel) 이후만 active.** 즉 `relabel_rescore_result` + `R12a` + `generate 정밀화(미커밋)`만 ACTIVE. 그 이전(Phase1·프론트·시계열·B·ACC-R1~R10·status_guard·L0) **전부 closed → 회고 후 아카이브.**
> 이유: 현 활성 앵커가 r12d1_relabeled이고, 그 이전 라운드의 교훈은 이미 CLAUDE.md §7과 MEMORY.md에 압축돼 원본 상시 노출 불필요.

### 회고 깊이 권고
> **트랙당 중간(~30줄) 회고** 기본. 단 **R12 트랙·generate 정밀화는 깊은(~60줄)** — 활성 인접·미해결 변수 보존 필요. **Phase1·프론트·시계열은 얕은(~10줄)** — 코드/기능에 이미 반영, 포인터만.

### 산출 감소율
- 파일 수: **84 → ~21 가시** (-75%)
- 라인: ~14,900 → 회고 ~400줄 + ACTIVE ~1,200줄 = 가시 ~1,600줄 (-89%), 원본은 아카이브 보존(무손실).

---

## 다음 단계 (후속 별도 task — 본 라운드 범위 밖)

1. 사용자가 이 제안서 검토 → 경계선/그룹/깊이 조정
2. 트랙별 회고 `.md` 작성 (9개)
3. `git mv` 원본 → `_archive/원본/<라운드>/` (무손실 이동)
4. 그룹별 atomic 커밋 (`refactor:` 또는 `docs:`)
5. 푸시 보류 (사용자 검토 후)
