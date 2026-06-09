# CC Task — R13 Arm C: 앵커 비교 가능성 확인 (read-only) + 커밋 + 인시던트 로그

> 시점: 2026-06-09. 직전 task에서 `app/vision/gemini.py` ANALYZE_MODEL 파라미터화 구현·비측정 검증 완료.
> 이 task는 **전부 read-only + 커밋/문서 작업 — 과금 측정 없음.** 풀 eval은 이 task 보고 검토 후 사용자 PowerShell.

## 0. 한 줄 요약
① 앵커가 거친 후처리를 확인해, Arm C raw 출력을 앵커와 **비교 가능하게 만드는 정확한 절차**를 확정(read-only). ③ 검증 완료된 `gemini.py` 변경을 isolated 커밋. ④ 직전 과금 사고를 CLAUDE.md 인시던트 이력에 기록. ② error_kind 패치는 **적용 금지(보류)**.

## 1. 안전 제약 (필독)
- **과금 호출 절대 금지.** 이 task에 측정 단계 없음. 혹시 회귀 점검을 돌린다면 반드시 `-m "not integration"`.
- `baseline.json`·앵커(`after_acc_r12d1_relabeled.json`) **읽기 OK, 수정·덮어쓰기 금지.**
- `ANALYZE_SYSTEM`·RAG·generate·status guard(R12a veto)·`run_eval.py` 채점 로직 **전부 무변경.**
- **error_kind 패치 적용 금지** (별도 결정으로 보류).

## 2. ① 앵커 비교 가능성 확인 (read-only, 최우선·게이트)
**배경**: 앵커 `after_acc_r12d1_relabeled.json`은 raw 측정이 아니라 **후처리본**이다 (raw → `after_acc_r12d1_remove_surface.json`(remove_surface) → relabel via `rescore_from_output.py`). 그런데 Arm C는 `run_eval.py --aux`로 **raw**를 생성한다. 따라서 raw(Arm C) vs 후처리본(앵커) 비교가 성립하는지 측정 전에 확정해야 한다.
- 숫자 단서: 앵커 acc 62.86% = **22/35** → 분모 35. 그런데 set은 39장. **약 4건이 어딘가에서 빠진다** — 이 갭의 정체를 반드시 규명.

**확인 항목**:
- **2-1 relabel**: `rescore_from_output.py`가 한 일이 GT 라벨 교정이라면, 그 교정 라벨이 **현재 `test_data/main_eval/labels.json`에 이미 반영**돼 있는가? (반영돼 있으면 raw 채점 = relabel 채점.)
- **2-2 remove_surface (분모 39→35의 정체)**: 이 제외가
  - **(a) GT/케이스ID 기반** (결정적, arm 무관) 인지, 아니면
  - **(b) 모델 출력 기반** (예: 모델이 surface-only로 판단한 케이스를 제외 → arm마다 빠지는 케이스가 달라짐) 인지.
  - → **(b)이면 Arm A와 Arm C의 분모가 달라져 비교가 교락된다.** 반드시 (a)/(b) 판정.
- **2-3 무과금 재현 테스트**: 디스크에 있는 **기존 raw Arm-A 출력 파일**을 현재 채점 경로 / 현재 `labels.json`으로 다시 채점(`rescore_from_output.py` 등, **측정 아님**)했을 때 앵커 게이트 수치(FP13 / FN0 / acc62.86 / 분모35)가 **재현되는가?**

**산출 결론 (둘 중 하나로 명확히)**:
- **Case A**: "추가 후처리 불필요 — 현재 `labels.json` = relabel GT이고 remove_surface는 [근거]. raw Arm C 수치가 앵커와 **직접 비교 가능**."
- **Case B**: "Arm C raw 출력에 **[정확한 후처리 레시피: remove_surface 단계 + `rescore_from_output.py` 인자]**를 똑같이 적용해야 비교 가능." + 그 레시피가 **결정적(arm 무관, 2-2가 (a))** 임을 확인. (만약 2-2가 (b)로 판명되면 → 단순 미러링으로 비교 불가, 별도 설계 필요하다고 플래그.)

## 3. ③ `gemini.py` 커밋
- 직전 task에서 구현·비측정 검증 완료된 `app/vision/gemini.py` 변경(ANALYZE_MODEL env 파라미터화)을 **이 파일 하나만** isolated 커밋.
- `prompts.py` 등 다른 파일 동시 커밋 금지 (조율 중인 별도 세션과 충돌 방지).
- 제안 커밋 메시지 (그대로 또는 동등):
  ```
  feat: analyze 모델 ANALYZE_MODEL env 파라미터화 (R13 Arm C 셋업)

  GeminiProvider 모델명을 env(ANALYZE_MODEL)로 파라미터화. 기본값은
  기존 하드코딩 "gemini-2.5-pro" 그대로 → env 미설정 시 동작 byte-identical.
  해석된 모델명을 생성 시 1줄 출력([analyze] model=... (default|env|arg)).
  모델 교체 A/B(Arm C=gemini-3.5-flash plain) 측정용 셋업.

  - app/vision/gemini.py: model 기본 None→본문 해석(import-time 평가 회피)
  - ANALYZE_SYSTEM·RAG·generate·status guard 전부 불변 (변수 격리)
  ```
- 커밋 후 해시·`git log -1 --oneline` 보고.

## 4. ④ 인시던트 로그 (CLAUDE.md)
- 직전 과금 사고를 CLAUDE.md 인시던트 이력에 **한 줄 추가** (기존 ACC-fix·antifab·status_hint 옆):
  - 요지: `tests/vision/`는 `model_utils.py` 모듈 레벨 `load_dotenv()`로 .env 키가 pytest에 주입돼 integration 테스트의 skipif가 무력화 → 실 Gemini 호출 발생. **회귀 점검 시 `-m "not integration"`(또는 `-k`) 필수.**
- 이 변경은 `gemini.py` 커밋과 **별도 커밋** (docs/incident). 메시지 예: `docs: CLAUDE.md 인시던트 — pytest integration 실 API 호출 + 회귀 점검 -m "not integration" 룰`.
- 커밋 후 해시 보고.

## 5. ② error_kind 패치 — 적용 금지
- 측정 전 적용하지 않음. 결과 분석 시 per-case `error` 문자열(VisionRetryableError=429 / VisionPermanentError=스키마) + `error` 키 부재(json_ok=False=진짜 파싱실패)로 **수동 분류**한다. 패치는 향후 단독 단계 후보.

## 6. 보고 형식 (CC → 웹)
1. **① 결론**: Case A or B + 근거. (B면) Arm C 비교 절차 레시피. **2-2 (a)/(b) 판정 명시.** 2-3 재현 결과.
2. ③ `gemini.py` 커밋 해시 + oneline.
3. ④ CLAUDE.md 커밋 해시.
4. (있으면) 추가로 눈에 띈 위생 이슈.

## 7. 금지 사항
- 과금 측정 (스모크·eval 포함).
- error_kind 패치 적용.
- `baseline.json`·앵커 수정.
- `prompts.py` 동시 커밋.
- 측정 하네스(`run_eval.py`) 채점 로직 변경.
