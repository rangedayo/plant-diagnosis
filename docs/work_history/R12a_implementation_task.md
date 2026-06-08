# R12a 구현 task — 정합룰 롤백 + 가드 위치 veto + 측정

> 선행: R12a 사전 진단(read-only) 완료. 본 task는 그 진단 처방(PART D)을 실제 구현·측정하는 단계다.
> 진단 보고서 `docs/work_history/R12a_guard_location_veto_diagnosis.md`를 **먼저 읽고** 그 시뮬 로직과 구현이 일치하도록 한다.

---

## 0. 목적과 범위

- **목적**: recall 안정화 — `haengun_006` FN(건조→건강 over-correct) 재발 방지.
- **범위**: ① 진단 산출물 커밋 → ② 정합룰 롤백 → ③ 가드 위치 veto 구현 → ④ 3-run 측정 → ⑤ 게이트 판정 → ⑥ 결과 문서·보고.
- **측정 변수 = "가드 위치 veto" 단 하나.** 정합룰 롤백은 기준점 복귀(이전 라운드에서 is_healthy-neutral 확정)이지 새 변수가 아니다.

---

## 1. 절대 제약 (위반 시 즉시 중단·보고)

- `baseline.json` 수정·삭제 **절대 금지** (옛 라벨, 보존만).
- 앵커 `eval/after_acc_r12d1_relabeled.json` 수정·덮어쓰기 **절대 금지**. 이게 모든 비교의 기준점이다.
- 각 측정 출력은 `RUN_EVAL_OUT` 환경변수로 격리. 앵커·baseline 파일명에 절대 쓰지 않는다.
- `_symptom_is_cosmetic` 함수 본체 **불변**. veto는 반드시 **별도 함수**로 분리(lesion veto와 동형 layered).
- 한 번에 한 단계. 각 단계 끝나면 멈추고 결과 보고 후 다음으로.
- 푸시 금지(사용자 검토 후). 커밋까지만.

---

## 2. 사전 점검 (read-only — 먼저 실행하고 보고)

다음을 확인해 보고한다. 이상 있으면 **여기서 멈춘다.**

1. 현재 `HEAD`와 브랜치 상태 (origin/main 대비 ahead 수).
2. working tree에 `modified: app/prompts.py` **하나만** 있는지 (= 롤백 대상인 정합룰 add본). 그 외 잔재 있으면 보고.
3. 진단 산출물 존재 확인:
   - `docs/work_history/R12a_guard_location_veto_diagnosis.md`
   - `scripts/diagnostics/r12a_veto_sim.py`
4. 앵커 파일 존재 + 수치 확인: `eval/after_acc_r12d1_relabeled.json` → acc 62.86%, 분모 35, FP 13, FN 0.
5. `app/prompts.py`의 unstaged diff가 **정합룰(cause-status 정합 문장) 추가만**인지 확인. 다른 변경 섞여 있으면 보고하고 멈춤.

---

## 3. Step 1 — 진단 산출물 커밋 + 정합룰 롤백

### 3-1. 진단 산출물 커밋
이전 read-only 진단의 산출물을 먼저 이력으로 남긴다.

- 대상: `docs/work_history/R12a_guard_location_veto_diagnosis.md`, `scripts/diagnostics/r12a_veto_sim.py`
- 커밋 메시지: `docs(eval): R12a 가드 위치 veto 사전 진단 보고서 + 시뮬 스크립트`

### 3-2. 정합룰 롤백
`app/prompts.py`에서 generate cause-status 정합룰을 제거해 앵커 상태로 복귀시킨다.

- 대상: `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 내 정합 문장 제거.
- 사전 점검 §2-5에서 unstaged diff가 정합룰 추가만임을 확인했으므로, HEAD 버전으로 복원하면 된다(`git restore app/prompts.py` 등). 복원 후 diff가 비었는지 확인.
- 커밋 메시지: `chore(prompts): generate cause-status 정합룰 롤백 (is_healthy-neutral 확인 완료)`

→ **여기서 멈추고** working tree clean 상태와 두 커밋 해시 보고.

---

## 4. Step 2 — 가드 위치 veto 구현

진단 보고서의 시뮬 로직과 **동일하게** 구현한다(구현≠시뮬 괴리 방지).

- **신규 함수** (예: `_has_progressive_location_marker(symptoms)`): 하부 위치 토큰 검출.
- **토큰 셋 (확정)**: `"아래쪽"`, `"하엽"`, `"하부"`, `"하단"`
  - 매칭 방식(부분 일치 vs 단어 경계)은 진단 보고서가 가정한 방식과 동일하게 맞춘다. 시뮬과 다르면 결과가 어긋난다 — 어느 방식인지 보고에 명시.
- **배치**: `_symptom_is_cosmetic`은 불변. veto는 가드 **규칙 3 직전**에 별도 layer로 삽입(기존 lesion veto와 동형 구조).
- **동작**: 증상에 하부 위치 토큰이 있으면 "진행성 신호"로 보고 cosmetic 건강 교정을 **차단(veto)** 한다.

→ **여기서 멈추고** 변경 파일·함수명·매칭 방식·삽입 위치를 diff와 함께 보고. 측정은 다음 단계.

- 커밋 메시지: `feat(guard): R12a 가드 위치 veto (하부 위치 토큰=진행성 신호)`

---

## 5. Step 3 — 측정 (3 run)

비결정 analyze를 평탄화하기 위해 **3회** 측정한다.

- 각 run:
  - `RUN_EVAL_OUT=eval/after_acc_r12a_veto_run1.json` (run2, run3 동일 패턴)
  - `scripts/run_eval.py` 실행.
- **측정 위생 (수치 신뢰 전 필수)**: 각 run 결과에서 `error` 필드를 확인해 **429·JSON 파싱 실패가 섞였는지** 검사. 오염된 run은 무효 처리하고 재측정. (1차 정합룰 측정 때 429를 "파싱 실패"로 오진한 전례 방지.)
- **각 run 보고 항목**:
  - acc, 분모
  - FP: 건수 + 사진 id 전체 리스트
  - FN: 건수 + 사진 id 전체 리스트
  - `haengun_006`의 최종 판정(건조 유지 / 건강 뒤집힘)과 그때 analyze가 추출한 증상 텍스트

---

## 6. Step 4 — 게이트 판정

앵커: FP 13 / FN 0. 허용 임계: **FP ≤ 14**.

- 🟢 **PASS**: 3 run 각각 **FP ≤ 14** AND `haengun_006`이 위치 토큰을 추출한 run에서 **FN 복구(건조 유지)**.
- 🟡 **부분 통과**: veto는 정상 작동(위치 토큰 있을 때 차단 성공)하나, 일부 run에서 analyze가 위치 토큰 **없는** 텍스트를 내 FN이 잔존 → veto는 유지하고, 남은 불안정은 ②(모델 교체) 사안으로 넘김.
- 🔴 **FAIL**: 어느 run이든 **FP > 14** OR 위치 토큰이 추출됐는데도 veto가 미작동 → veto 롤백 후 원인 분석 보고.

→ FN이 일부 run에서 ≠0이면, **analyze가 위치 토큰 없는 텍스트를 낸 것인지** vs **veto 로직 갭인지** 반드시 구분해 보고(이게 🟡과 🔴을 가른다).

---

## 7. Step 5 — 결과 문서 + 보고

- `docs/work_history/R12a_result.md` 작성:
  - 가설 / 변경사항(롤백+veto) / 3-run 측정 테이블(run별 acc·FP·FN·haengun_006 판정) / 게이트 결과(🟢🟡🔴) / 결론 / 다음 라운드 노트.
- eval JSON 3건 커밋:
  - 커밋 메시지: `docs(eval): R12a veto 측정 결과 + R12a_result.md`
- **푸시 보류** — 사용자 검토 후. 여기서 보고만 하고 멈춘다.

---

## 8. 커밋 계획 요약 (제안)

1. `docs(eval): R12a 가드 위치 veto 사전 진단 보고서 + 시뮬 스크립트`
2. `chore(prompts): generate cause-status 정합룰 롤백 (is_healthy-neutral 확인 완료)`
3. `feat(guard): R12a 가드 위치 veto (하부 위치 토큰=진행성 신호)`
4. `docs(eval): R12a veto 측정 결과 + R12a_result.md`

각 단계 끝에 멈추고 보고 → 사용자 확인 후 다음. 게이트 🔴이면 4번 전에 멈추고 롤백 판단을 사용자에게 넘긴다.
