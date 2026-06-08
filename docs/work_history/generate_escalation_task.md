# [generate 정밀화 R1] escalation 편향 교정 — 롤백 + cause-status 정합 — 작업 프롬프트

## 0. 맥락

- analyze 날조 억제(antifab) 라운드 **실패** (FP 13→16, acc 62.86→54.3, latency +24%). 환각은 프롬프트 훈계로 안 잡힘 → **롤백**.
- 이번 변수 = **generate escalation 편향 교정**: generate가 cause(자기 분석)는 "수분/과습/환경"이라 비-disease를 가리키면서 status만 "병해 의심"으로 부풀리는 자기모순(진단 발견 2).
- **변수 격리**: 롤백은 기준점 복귀(변수 아님), generate 수정이 이번 변수. analyze는 기준점 상태로 둠.

비교 기준점: `eval/after_acc_r12d1_relabeled.json` (acc 62.86%, FP 13, FN 0).

---

## PART A — 롤백 (기준점 복귀)

- `app/prompts.py`의 antifab 변경(`ANALYZE_SYSTEM`에 추가했던 "관찰 충실성" 한 줄) **제거**.
- analyze가 relabeled 기준점 상태와 동일한지 `git diff`로 확인 (analyze 무변경 상태 복귀).

---

## PART B — generate escalation 진단 (수정 전 확인, 무과금)

성급한 수정 방지(날조 억제 실패 교훈). 먼저 모순 케이스를 정확히 식별:
- `eval/after_acc_r12d1_remove_surface.json`에서 **cause는 비-disease(수분/과습/환경)를 가리키는데 status만 "병해 의심"** 인 케이스 추출 (진단 발견 2의 4건).
- 각: case_id, cause 텍스트, status, top_3 — cause와 status가 어긋난 지점 명시.
- 기존 **R12b cause-status 정합룰**이 prompts.py 어디 있는지 확인 (있는데 LLM이 위반 중인 상태). 강화할지 보완할지 판단 근거 보고.

---

## PART C — generate 프롬프트 수정 (한 변수)

원칙(일반 규칙, surface 패치 금지):
- "status는 너 자신의 분석(cause)과 일치해야 한다. cause가 수분/환경/관리 요인을 가리키면 status도 그에 맞춰라 — 병해로 비약하지 마라."
- "병해(병해 의심)는 cause에서 실제 병징(반점 확산·괴사·수침상 병반 등)을 지목할 때만 선택하라."

⚠ **FN 0 사수**: status를 무조건 낮추는 게 아니라 **cause와 정합**시키는 것. cause가 실제 병징을 가리키면 병해 유지. 진짜 환자(epipremnum_005의 "검은 반점 확산" 등)는 비건강으로 남아야 함.
⚠ **surface 패치 금지**: 종/케이스/특정 증상 목록 박지 말 것. 일반 정합 원칙만.
⚠ 기존 R12b 정합룰과 **중복·충돌 점검**: 이미 있으면 강화(왜 LLM이 위반하는지 고려해 표현 보강), 없으면 추가. analyze·가드·RAG 무변경.

---

## PART D — 합성 검증 (측정 전, 무과금)

- import OK, 변경은 generate 블록 한정 (analyze 롤백 + generate 수정 외 무변경)
- pytest 회귀 없음
- grep: 롤백 확인(antifab 문구 0) + generate 정합 원칙 추가 확인 + 증상 유형 목록 아님 자가 점검

---

## PART E — 측정 (사용자 PowerShell, Gemini 과금)

재적재 불필요(프롬프트만). 바로:
```powershell
$env:RUN_EVAL_OUT="after_acc_generate_escalation.json"
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```
⚠ `RUN_EVAL_OUT` 설정 확인 — baseline.json 덮어쓰기 방지.

---

## PART F — 보고 (chat)

비교: `after_acc_r12d1_relabeled.json`(62.86%) 대비.

게이트:
- 🔴 **post.fn = 0** (절대 사수)
- post.fp ≤ 12 (현 13에서 감소 기대)
- latency ±10%

검증 포인트:
1. **cause-status 모순 4건이 정합됐나** — cause가 환경/수분인 케이스의 status가 병해에서 환경계열(건조/과습/건강)로 내려왔나
2. **진짜 병해 보존(FN 점검)** — cause가 실제 병징을 가리키는 케이스(예: epipremnum_005 "검은 반점 확산")는 병해/비건강 유지됐나
3. 새 accuracy (62.86% → ?)
4. 결과 JSON 경로

---

## 주의사항

- ⚠ `eval/baseline.json` 무접촉, `RUN_EVAL_OUT` 필수.
- ⚠ **롤백 + generate 정합 수정만** — analyze 추가 변경·정상변이 비보고 금지.
- Bash로 `$env:` 금지 → PowerShell.
- 커밋·푸시 보류 (측정 결과 검토 후).

---

## 다음 단계 (참고 — 범위 X)

generate escalation 효과 확인 후 → 효과 있으면 다음 항목(정상 변이 비보고 등) 한 항목씩. 효과 없으면 다른 레버 재고. 한 항목씩 효과 확인하며 진행.
