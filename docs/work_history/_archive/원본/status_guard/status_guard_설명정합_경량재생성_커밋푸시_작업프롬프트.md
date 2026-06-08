# [status guard 마무리] 교정분 설명 경량 재생성 정합 + 재측정 + 커밋·푸시 — 작업 프롬프트

## 0. 맥락 (먼저 읽을 것)

status guard 측정 **성공**: FP 17.5→7.5(목표 ≤12 ✅), FN 0/recall 1.0 사수, healthy_acc +30pp. 입력 설득 3회(B-4b·c·B') 실패를 **출력 후처리 우회**로 돌파.

**남은 1건**: guard가 status를 건강으로 교정해도 `cause`(설명문)는 generate가 쓴 "병해 의심" 텍스트 그대로 → **status=건강 / cause=병해 의심 모순**. 측정(status 기준)엔 안 보이지만 **제품으론 치명적**(사용자가 cause를 읽음). main 올리기 전 정합 필수.

**결정된 방식**: guard 교정 케이스만 **cause 경량 재생성**(코드 템플릿 아님). status는 guard 확정값으로 고정, cause 텍스트만 건강 전제로 재생성.

**작업 구성**: PART A(경량 재생성 정합) → PART B(재측정 — 정합이 status/FP/FN에 영향 없는지 검증) → PART C(커밋 + 푸시) → PART D(보고).

⚠ **이번엔 커밋·푸시까지 간다.** PART A 2커밋(495b01f·aca3736, 이미 로컬 존재) + status guard 새 커밋을 **함께 origin/main 푸시**.

---

## PART A — 교정분 cause 경량 재생성

### A-1. 동작

`apply_status_guard()`가 status를 **비건강→건강으로 교정한 케이스만** cause 재생성 트리거. 미교정 케이스는 generate 원본 cause 그대로(불필요한 호출·비결정 방지).

- **재생성 입력**: 식물종, `observed_symptoms`(해당 cosmetic 증상), "이 증상은 종 정상 범위/경미한 cosmetic으로 판정되어 건강 처리됨" 컨텍스트.
- **재생성 출력**: 건강 전제의 cause 텍스트 (한국어, 기존 형식 유지). 예 방향: 관찰된 증상이 해당 종에서 흔한 경미한 변색이며 건강 이상 신호가 아니라는 취지 + 간단한 케어 코멘트.
- **temp=0** (비결정 최소화).

### A-2. status 고정 — 핵심 (재생성이 status를 다시 흔들면 안 됨)

⚠ 재생성은 **cause만** 건드린다. status enum은 **guard 확정값(건강) 불변**.
- 재생성 LLM 프롬프트에 **status 재판정 금지** 명시("이미 건강으로 확정됨, 그에 맞는 설명만 작성").
- 코드에서 **status는 guard 값으로 강제** — 재생성 응답에 status 필드가 와도 무시하고 guard 확정값 유지. (재생성이 status에 새는 경로를 코드로 원천 차단)
- 강제 3개 원칙 형식(JSON·enum·한국어) 유지 — 재생성도 enum·한국어 규격 안에서.

### A-3. 비용

교정 건수만큼 추가 LLM 호출 (~8~10건/run, 짧은 프롬프트). 미미하나 보고에 대략 명시.

---

## PART B — 재측정 (정합 검증)

### B-1. e2e 2회 평균

`eval/after_phase_status_guard_{run1,run2,avg}.json` **재생성**(정합 후 최종본으로 갱신).

### B-2. 검증 포인트 (status only 대비 — 정합은 cause만 건드리니 status 결과 불변이어야 정상)

- **FP 7.5 불변** — status 기준. 정합이 cause만 건드렸으면 같아야 함.
- **FN 0 불변** / recall 1.0.
- ⚠ **FP/FN이 변하면 → 재생성이 status에 샌 것** (A-2 status 강제 고정 버그) → 잡고 재측정. 정합은 status를 절대 안 바꿔야 한다.
- **설명 품질 (per_case 샘플)**: guard 교정 케이스의 cause를 **정합 전(병해 의심) vs 정합 후(건강 전제)** 나란히 — 모순 해소됐는지, status=건강과 정합하는지, 한국어 자연스러운지.
- `plant_korean` 등 텍스트 품질 지표 — cause가 바뀌니 약간 흔들릴 수 있음. 노이즈 범위(±3%p)인지 확인.

---

## PART C — 커밋 + 푸시

### C-1. status guard 커밋 (코어 + 정합 + eval 한 묶음)

- 포함: `app/graph.py`(apply_status_guard + 경량 재생성), `scripts/run_eval.py`(guard 진단), `eval/after_phase_status_guard_{run1,run2,avg}.json`(정합 후 최종).
- ⚠ 커밋 전 `git status` — `eval/baseline.json` **안 떠야 정상**. 뜨면 중단·보고.
- 메시지:
  ```
  feat: [status guard] generate 출력 후 cosmetic over-escalate 교정 (FP 17.5→7.5, FN 0) + 교정분 cause 경량 재생성 정합
  ```

### C-2. 푸시 (PART A 2커밋 함께)

- 로컬 미푸시 커밋 3개 → `origin/main` 한 번에 push:
  - `495b01f` feat: [B'] 종 메타 주입 + 측정
  - `aca3736` revert: [B'] 종 주입 제거
  - (C-1의 status guard 커밋)
- 푸시 후 `git status` clean + unpushed 0 확인.

---

## PART D — 보고

1. **경량 재생성 구현** — 위치(교정 케이스만 트리거), status 고정 처리(A-2), 비용.
2. **재측정** — FP/FN이 status only(7.5/0) 대비 **불변 확인**, plant_korean 노이즈 범위.
3. **설명 품질** — 교정 케이스 cause 정합 전/후 샘플 1~2건 (모순 해소 확인).
4. **커밋·푸시** — status guard 커밋 해시 + 3커밋 push 결과, baseline 무접촉, clean 확인.
5. **판정** — 정합 완료·전 게이트 통과 시 status guard 라운드 종료 선언.

---

## 환경 주의사항 (반드시 준수)

- `$env:RUN_EVAL_OUT`에 **`eval/` 접두 금지** (코드가 prepend → `eval/eval/` 이중경로).
- **Bash 툴로 `$env:` 금지** (구문 깨져 baseline 덮어쓰는 사고 전례) → 측정은 **PowerShell 툴**.
- ⚠ **`eval/baseline.json` 절대 덮어쓰기 금지** (커밋 기준).
- run_eval 콘솔 **cp949 한글 깨짐** → 값 확인은 **JSON UTF-8 읽기**.
- **2회 평균 패턴** (run1/run2 + 평균). analyze 비결정성 FP ±1.
- GateGuard 훅: Bash/Edit/Write 전 "사실 명시" 요구.

---

## 산출물 요약

- `app/graph.py` — apply_status_guard + 교정분 cause 경량 재생성 (status 고정)
- `eval/after_phase_status_guard_{run1,run2,avg}.json` — 정합 후 최종
- status guard 커밋 1개 + PART A 2커밋 → origin/main 푸시
- PART D 보고 (chat)
