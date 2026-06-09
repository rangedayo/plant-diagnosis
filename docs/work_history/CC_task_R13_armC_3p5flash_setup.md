# CC Task — ② 모델 교체 A/B: Arm C (3.5 Flash plain) 셋업 + 스모크 절차

> 시점: 2026-06-09. OPEN DECISION 확정됨 = **Arm C = `gemini-3.5-flash` plain (모델만 교체)**.
> 이 task는 코드 셋업 + 스모크/eval 절차 산출까지. **실제 과금 측정은 사용자 PowerShell**.

## 0. 한 줄 요약
analyze 모델을 env(`ANALYZE_MODEL`)로 파라미터화한다. 기본값은 **현재 하드코딩된 2.5 Pro 모델 문자열 그대로** → baseline 코드 byte-identical. 코드 변경은 이것 하나뿐. CC는 Gemini 과금 호출을 절대 실행하지 않는다.

## 1. 안전 제약 (필독)
- **변수 격리**: 이 라운드 변수는 **모델 하나**. `ANALYZE_SYSTEM` 프롬프트·RAG(b_dataset_rag)·generate·status guard(R12a veto 포함) 전부 불변.
- **앵커·baseline 불변**: `eval/after_acc_r12d1_relabeled.json`(앵커)·`baseline.json` 읽어서 덮어쓰기 금지. 비교 기준일 뿐 건드리지 않는다.
- **`RUN_EVAL_OUT` 격리**: 스모크/Arm C 출력은 신규 파일로. 기존 eval 산출물 덮어쓰기 금지.
- **CC는 Gemini 과금 호출 실행 금지** — 스모크·풀 eval 포함. 과금 측정은 사용자가 PowerShell로 직접 한다.
- **자동 커밋 금지**. 변경 구현 + diff 제시 후 대기. (ACC-fix 덮어쓰기 사고 재발 방지 + 멀티세션 커밋 동기화.)

## 2. 변경 사항 (코드, 비측정)

### 2-1. analyze 모델 env 파라미터화 (유일한 코드 변경)
- 위치: `app/nodes/analyze.py` (또는 Gemini 모델 인스턴스화 지점). 현재 2.5 Pro 모델명이 하드코딩된 곳을 찾는다.
- 변경: 모델명을 `os.environ.get("ANALYZE_MODEL", "<현재 하드코딩된 문자열 그대로>")`로 교체.
  - 기본값은 **지금 코드에 박힌 문자열을 글자 그대로** 복사할 것. 추측·정규화 금지(예: 임의로 `gemini-2.5-pro`로 바꾸지 말 것 — 실제 박혀 있는 값 그대로).
- analyze 진입 시 해석된 모델명을 1줄 로그/print 출력. 예:
  - `[analyze] model=<default값> (default)`
  - `[analyze] model=gemini-3.5-flash (env)`
  - → 스모크에서 어느 모델이 실제로 쓰였는지 눈으로 확인하기 위함.
- `_with_retry`(max_attempts=3) 및 `ANALYZE_SYSTEM` 프롬프트는 불변.

### 2-2. (읽기 전용) 측정 위생 보고 — `run_eval.py` 에러 필드
- `scripts/run_eval.py` L836 부근에서, 각 이미지의 `error` 필드가 **429(rate limit)** 와 **진짜 파싱 실패**를 구분하는지 코드를 읽고 **보고만** 한다.
- **수정하지 말 것.** 구분이 안 되면 보고서에 현재 동작 + 최소 패치 제안만 적는다. 적용 여부는 별도 결정.
- 이유: R12a run3에서 429를 파싱실패로 오분류한 전례 → A/B 신뢰성을 위해 측정 전에 현재 상태를 알아야 함. (단, 코드 변경은 이번 라운드 변수에 포함하지 않음.)

## 3. 비측정 로컬 검증 (CC가 실행해도 됨 — 과금 없음)
- python import / 구문 통과.
- env 미설정 시: 해석된 모델명 == 기존 하드코딩 문자열인지 assert/print로 증명 (baseline 불변 증명).
- `ANALYZE_MODEL=gemini-3.5-flash` 설정 시: 해석된 모델명이 그대로 바뀌는지 확인 (**실제 API 호출 X**, 해석된 문자열만 출력).

## 4. 산출물: PowerShell 명령 (사용자가 실행)
- 먼저 **앵커(`after_acc_r12d1_relabeled.json`)를 생성한 실제 run_eval 호출/플래그**를 run history·`docs/work_history`·`run_eval.py` 기본값에서 확인한다.
- Arm C eval은 그 호출을 **동일하게 미러링**한다 — eval set·플래그 전부 동일, **`ANALYZE_MODEL`만 다름**. (eval set을 임의로 재정의하지 말 것. 앵커와 같은 조건이어야 비교가 성립.)
- 제공할 명령 2개:
  - **(a) 1-이미지 스모크**: `ANALYZE_MODEL=gemini-3.5-flash`, `RUN_EVAL_OUT=eval/smoke_armC_3p5flash.json`, 단일 이미지로.
    - 1-이미지로 제한하는 방법(플래그/limit/소형 subset)은 run_eval.py 실제 인터페이스에 맞춰 명시.
    - 목적: env override가 실제로 반영되는지(로그에 `model=gemini-3.5-flash` 확인) + 파이프라인 무파손(파싱 OK) 확인. **풀 eval 전 돈 낭비 방지.**
  - **(b) 풀 Arm C eval** (스모크 통과 후): `ANALYZE_MODEL=gemini-3.5-flash`, `RUN_EVAL_OUT=eval/after_acc_armC_3p5flash.json`, 앵커와 동일 set/flags.
- 두 명령 모두 `baseline.json`·앵커 파일에 접근/덮어쓰기하지 않음을 확인.

## 5. 보고 형식 (CC → 웹)
1. 변경 diff (`analyze.py`).
2. 비측정 검증 결과 (default == 기존 문자열 / env override 반영).
3. `run_eval.py` 에러 필드 현재 동작 + (구분 안 될 시) 최소 패치 제안.
4. 확정된 PowerShell 스모크/eval 명령 + 앵커 미러링 근거(어느 호출을 복제했는지).
5. 제안 커밋 메시지 (커밋은 대기).

## 6. 금지 사항
- 과금 측정 실행 (스모크·eval 포함).
- 자동 커밋.
- `baseline.json`·앵커 접근/수정.
- `ANALYZE_SYSTEM`·RAG·generate·status guard(veto) 변경.
- eval set 재정의.
- `run_eval.py` 에러필드 로직 변경 (이번 라운드 한정).
