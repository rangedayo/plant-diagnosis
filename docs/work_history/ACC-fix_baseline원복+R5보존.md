# [ACC-fix] baseline.json 원복 + R5 결과 보존 (미니 정정 라운드)

> **목적**: R5 측정을 `RUN_EVAL_OUT` 없이 돌려, `run_eval.py` 기본 출력 경로인 `eval/baseline.json`(v8 구스키마, 보존 대상 역사 산출물)이 R5 결과로 덮어써졌다. **원본을 git에서 복원**하고, **R5 결과를 정식 파일명으로 떼어내 보존**한다.
>
> **성격**: git 정정 + 파일 보존. R6 진단(`a2a998d`)과 함께 푸시. **코드·프롬프트·데이터 로직 무변경.**
>
> **선행**: R6 진단 완료(`a2a998d` docs 커밋). **후행**: ACC-R7(건조·과습 트리거 + 가드 확장).

---

## 1. 확정된 사실 (조사 근거)

### 1-1. baseline.json 원본 = v8 구스키마

git 마지막 커밋의 `eval/baseline.json`은 다음이어야 한다 (프로젝트 자료 확인):

```
measured_at: 2026-05-29T03:06:51
total: 33
is_healthy: recall=0.6, precision=0.231, fn=2  (구스키마 — 가드 전/후 구분 없음)
status_distribution: 건강 20, 병해 의심 10, 영양 부족 1, 과습 2
```

→ Plant.id + GPT-4o-mini 시절의 v8 baseline. 프로젝트 §7 "baseline.json(구스키마) 무변경" 보존 대상.

### 1-2. 현재 워킹트리 baseline.json = R5 결과로 덮임

- `git status`에 `M eval/baseline.json` (미스테이징)으로 떠 있음 (R6 보고에서 확인됨).
- 내용은 R5 결과: `total: 39` + `aux_plantvillage_results`(50건) 섹션 포함 + 5-status 혼동표 신스키마.
- 이게 **원래 `eval/after_acc_r3r4_L0prime.json`으로 갔어야 할 결과**.

---

## 2. 작업

### Step 0 — read-only 확인 (불일치 시 중단·질의)

1. `git status` — `M eval/baseline.json` 미스테이징 확인. 다른 의도치 않은 변경 없는지.
2. **원본 검증**: `git show HEAD:eval/baseline.json` 에서 `measured_at`이 `2026-05-29`, `total`이 `33`, `recall`이 `0.6`인지 확인. → §1-1과 일치하면 원본 보존 확인. 불일치 시 **중단·보고** (다른 커밋에서 이미 변형됐을 수 있음).
3. **R5 검증**: 현재 워킹트리 `eval/baseline.json`이 `total: 39` + aux 섹션(50건) + `status_confusion_matrix` 키를 가졌는지 확인. → R5 결과 맞는지 확정.
4. `eval/after_acc_r3r4_L0prime.json`이 아직 없는지 확인 (덮어쓰기 가드).

### Step 1 — R5 결과 떼어내기

- 현재 워킹트리 `eval/baseline.json`(=R5 결과)을 `eval/after_acc_r3r4_L0prime.json`으로 **복사**.
  - 단순 파일 복사 (내용 변형·재인코딩 금지). BOM 없는 UTF-8 유지.
- 복사본의 `total: 39` + aux 섹션 보존 확인.

### Step 2 — baseline.json 원복

- `git checkout eval/baseline.json` (또는 `git restore eval/baseline.json`) — 마지막 커밋의 v8 원본 복원.
- 복원 후 `eval/baseline.json`의 `measured_at`이 `2026-05-29`, `total`이 `33`으로 돌아왔는지 확인.

### Step 3 — atomic 커밋 (푸시는 사용자 검토 후)

- `eval/after_acc_r3r4_L0prime.json` 신규 추가 (R5 5-status 첫 측정 결과, ACC-R7 비교 앵커).
  - 커밋: `feat(eval): ACC-R5 5-status 첫 측정 결과 보존 (main 39 + aux 50, L0prime)`
- `eval/baseline.json`은 원복됐으므로 **커밋에 포함 안 됨** (변경 없음 = clean).
- R6 진단(`a2a998d`)이 아직 푸시 안 됐으면 이번에 함께 푸시 대상. push는 사용자 확인 후.

---

## 3. 제약

- **`baseline.json` 내용 변경 절대 금지.** 원복만. 커밋에 baseline.json이 변경분으로 들어가면 안 됨.
- **R5 결과 손실 금지.** Step 1 복사를 Step 2 원복보다 **반드시 먼저** 실행 (순서 어기면 R5 데이터 소실).
- 다른 파일 무변경.

---

## 4. 보고 형식

1. Step 0 확인 결과 — 원본 measured_at·total·recall / R5 total·aux 유무.
2. 복사·원복 실행 결과 — `after_acc_r3r4_L0prime.json` 생성 + `baseline.json` 2026-05-29 복원 확인.
3. `git status` 최종 (baseline.json clean, after_acc_r3r4_L0prime.json 신규).
4. 커밋 해시 + R6(`a2a998d`) 푸시 동반 여부.

---

## 5. 비고 — RUN_EVAL_OUT 재발 방지

ACC-R7 이후 측정 시 **반드시 `$env:RUN_EVAL_OUT` 먼저 설정**할 것. 안 그러면 또 baseline.json이 덮임. R7 프롬프트 측정 안내에 강조 포함됨.
