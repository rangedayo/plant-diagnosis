# CC Task — R13 Arm C: 스모크 404 대응 (Vertex 글로벌 엔드포인트)

> 시점: 2026-06-09. 스모크 결과 = 404 NOT_FOUND. `gemini-3.5-flash`가 Vertex **asia-northeast1 단일리전에 없음**(코드·모델 정상, 리전 문제). 신형 Gemini는 Vertex 글로벌 엔드포인트로 먼저 풀림.
> 이 task는 **read-only 진단 + (필요시) 최소 코드 변경 — 과금 측정 없음.** 스모크 재실행은 사용자 PowerShell.

## 0. 한 줄 요약
Vertex location을 `global`로 두면 `gemini-3.5-flash`가 해석됨. **먼저 location이 env 구동인지 하드코딩인지 읽고**, env면 코드 변경 0(사용자가 env만 추가), 하드코딩이면 baseline byte-identical 유지하며 최소 파라미터화. 글로벌 기준 스모크 명령 산출.

## 1. 안전 제약 (필독)
- **과금 호출 절대 금지.** 스모크 재실행은 사용자. 회귀 점검 시 `-m "not integration"`.
- **baseline byte-identical**: location 기본값은 **현재 값 그대로**(asia-northeast1) — env 미설정 시 동작 불변.
- 변수 격리: 이 변경은 "3.5-flash가 해석되게" 하는 인프라 한정. `ANALYZE_SYSTEM`·RAG·generate·status guard·`run_eval.py` 채점 로직 무변경.
- **error_kind 패치 여전히 보류**(적용 금지).

## 2. ① (read-only) Vertex 클라이언트 설정 파악 — 최우선
- `app/vision/gemini.py`·`app/model_utils.py`(또는 genai 클라이언트 생성 지점)에서 확인:
  - 클라이언트가 `genai.Client(vertexai=True, ...)`로 생성되는가?
  - **location(`asia-northeast1`)이 어디서 오는가** — env(예 `GOOGLE_CLOUD_LOCATION`)인가, 인자로 하드코딩인가, SDK 기본 자동탐지인가?
  - project(`energy-ts-forecast`)는 어디서 오는가? (참고용)
- 보고: location 결정 경로 1줄 + 관련 코드 라인.

## 3. ② 분기 처리
- **Case env**: location이 이미 env(`GOOGLE_CLOUD_LOCATION` 등) 구동 → **코드 변경 없음.** 사용자가 그 env를 `global`로 두면 됨. 정확한 env 변수명을 보고.
- **Case 하드코딩**: location이 코드에 박혀 있으면 → **최소 파라미터화.** env override 추가(예 `os.environ.get("GOOGLE_CLOUD_LOCATION", "<현재 값 그대로>")`), 기본값 = 현재 박힌 값 **글자 그대로** → baseline 불변. diff 제시. **커밋은 보류**(diff + 제안 메시지만).

## 4. ③ (read-only, 인지용) 3.5-flash temperature 캐비엇
- 참고: Google이 3.5 Flash에 `temperature`/`top_p`/`top_k`를 더는 권장하지 않음(아키텍처 변경). 현 코드는 `self._temperature is not None`이면 config에 temperature를 넣음.
- 보고만: analyze provider의 기본 temperature 값 + integration 테스트 provider가 temperature를 보내는지. **변경하지 말 것** — 글로벌 수정 후 스모크가 400(temperature 관련)으로 죽으면 그때 별도 결정. (현 404와는 무관.)

## 5. ④ 산출물: 글로벌 기준 스모크 명령 (사용자 실행)
- Case env 기준 예시(실제 변수명으로 교체):
  ```
  $env:GOOGLE_CLOUD_LOCATION="global"
  $env:ANALYZE_MODEL="gemini-3.5-flash"
  $env:PYTHONIOENCODING="utf-8"
  .venv\Scripts\python.exe -m pytest tests\vision\test_gemini_provider.py::test_integration_real_gemini_call -s
  # 확인: [analyze] model=gemini-3.5-flash (env) + PASS(스키마 OK)
  Remove-Item Env:\ANALYZE_MODEL
  Remove-Item Env:\GOOGLE_CLOUD_LOCATION
  ```
- 스모크 PASS 시 풀 eval도 동일하게 `GOOGLE_CLOUD_LOCATION=global` 추가 필요함을 명시(명령은 CC 1차 보고의 `run_eval.py --aux` + `RUN_EVAL_OUT=after_acc_armC_3p5flash.json`에 location env만 추가).

## 6. 보고 형식 (CC → 웹)
1. ① location/project 결정 경로 + 코드 라인.
2. ② Case env / Case 하드코딩 판정. (하드코딩이면) diff + 제안 커밋 메시지(커밋 보류).
3. ③ 기본 temperature 값 + 테스트의 temperature 전송 여부.
4. ④ 확정된 글로벌 스모크 PowerShell 명령 + 풀 eval에 추가할 env.

## 7. 금지 사항
- 과금 측정(스모크·eval).
- baseline 동작 변경(location 기본값은 현재 값 그대로).
- temperature 처리 변경.
- error_kind 패치 적용.
- `prompts.py` 동시 커밋, 채점 로직 변경, 앵커·baseline.json 수정.
