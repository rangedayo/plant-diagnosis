# CC Task — R16: 3단 채점 코드 + 무과금 baseline 재채점

> 시점: 2026-06-10. R15에서 GT가 3단(tier)으로 마이그레이션됨. 이번 = **채점 로직에 3단 + 비대칭 게이트 추가**하고, 기존 모델 출력을 새 3단 GT로 **무과금 재채점**해 3단 출발선(baseline) 확정.
> **변수 = 채점 코드(run_eval/_build_result·rescore)뿐.** 모델(generate/analyze)·가드·GT·프롬프트 무변경. 측정(Gemini) 0.
> 라운드 번호 R16 잠정.

## 0. 한 줄 요약
모델 5종 status를 tier로 매핑(건강→건강 / 경미→경미(미래) / 과습·건조·병해 의심·영양 부족→비건강)하고, 3×3 tier 혼동표 + 비대칭 게이트 지표를 `_build_result`에 추가. 그 코드로 `eval/after_acc_armC_3p5flash.json`(현 생산 모델 출력)을 새 3단 GT로 재채점해 `eval/after_acc_r16_3tier_baseline.json` 생성. 새 3단 활성 앵커로 지정.

## 1. 안전 제약 (필독)
- **과금 측정 금지.** 무과금 재채점(`rescore_from_output.py`, 모델 호출 0). 회귀 `-m "not integration"`.
- 기존 이진(is_healthy)·5-status 지표 **그대로 유지**(추가만, 제거·변경 금지). 연속성.
- 모델 출력(generate/analyze), `apply_status_guard`, GT(labels.json) **무변경**.
- 재채점 입력 `after_acc_armC_3p5flash.json`·`baseline.json`·old 앵커 **읽기만**(수정·덮어쓰기 금지). 출력은 **새 파일명**(앵커 클로버 방지).
- 커밋까지. **푸시 보류.**

## 2. Phase 0 — read-only (먼저 보고·HOLD)
1. `_build_result`(run_eval.py)의 현재 구조 + `build_status_confusion_matrix` 위치/시그니처 + per_case가 담는 필드 확인 보고.
2. `rescore_from_output.py` CLI 시그니처(입력/출력 인자, RUN_EVAL_OUT 사용 여부) 확인.
3. `eval/after_acc_armC_3p5flash.json`의 per_case가 **39장 전부**(과거 ambiguous 4장 포함) `pred_status`를 담고 있는지 확인(재채점 가능 전제).
4. labels.json의 새 `tier` 필드를 rescore가 어떻게 읽어 per_case의 gt에 넣을지 + §3 삽입 최소안 제안.
5. → **보고 후 HOLD.** OK 받고 Phase 1.

## 3. Phase 1 — 채점 로직 추가 (Phase 0 OK 후)

### 3.1 status → tier 매핑 (헬퍼)
- `"건강"` → `건강`
- `"경미"` → `경미` (현 모델은 안 내지만 미래 대비 통과)
- `"과습"`·`"건조"`·`"병해 의심"`·`"영양 부족"` → `비건강`
- 그 외/미상 → `비건강`(안전 측 = 과대로 처리)으로 매핑하되 로그.

per_case에 `gt_tier`(labels.json tier), `pred_tier`(위 매핑) 추가.

### 3.2 3×3 tier 혼동표 + 비대칭 지표 (`_build_result`에 새 블록, 예: `tier_diagnosis`)
심각도 순서 건강(0) < 경미(1) < 비건강(2). 분모 = scored 39 (ambiguous 0이라 전부 포함).
- **3×3 혼동표**: 행=gt_tier, 열=pred_tier, 카운트.
- 파생 지표:
  - `exact_match` = 대각합/총.
  - 🔴 `cardinal_miss` = count(gt=비건강 & pred=건강) — **하드 게이트(목표 0)**. 옛 FN의 3단판.
  - `soft_miss` = count(gt=비건강 & pred=경미) — 추적(현 모델은 0).
  - `minor_undercall` = count(gt=경미 & pred=건강) — 허용(경미를 건강이라 함, 저위험).
  - `over_call` = pred가 gt보다 심각(건강→경미·건강→비건강·경미→비건강). 가능하면 분해: `→경미`(건강→경미) / `→비건강`(건강→비건강 + 경미→비건강). 최소화 목표(안전).
- 콘솔에도 3×3 표 + 위 지표 출력.

### 3.3 기존 지표 유지
- is_healthy 이진(TP/TN/FP/FN·precision/recall)·5-status 혼동표·fp/tp_analysis 등 **그대로**. (경미는 is_healthy=true라 이진에선 건강 취급, 5-status 혼동표에선 STATUS_VOCAB 밖 자동 skip — R15 설계대로.)

### 3.4 테스트
- 위 매핑·3×3·비대칭 지표에 대한 **단위 테스트 추가**(합성 per_case로 각 코너: cardinal_miss, soft_miss, over_call, exact). 측정 코드를 바꿨으니 회귀 테스트도 같이 보강(과금 0).
- `pytest -m "not integration"` 통과 확인.

## 4. Phase 2 — 무과금 재채점 (baseline 확정)
- `rescore_from_output.py`로 입력=`eval/after_acc_armC_3p5flash.json`(현 생산 모델 출력 = 되돌린 프롬프트 + 3.5-flash), 출력=**`eval/after_acc_r16_3tier_baseline.json`**. 모델 호출 0 확인.
  - (RUN_EVAL_OUT 쓰는 구조면 **베어 파일명**, `eval/` 접두 금지 — R14 경로 사고 주의.)
- 새 GT(3단)로 채점된 결과의 **3×3 혼동표 + cardinal_miss/soft_miss/over_call/exact** + 기존 이진 수치 보고.
- 주의: 이번은 **모델이 경미를 못 내는 현 상태의 출발선**. cardinal_miss가 0이 아닐 수 있음(새 GT에 ex-ambiguous 3장 + monstera_001 병해가 비건강으로 들어옴 — 현 모델이 그걸 건강이라 했으면 잡힘). **게이트 판정이 아니라 측정**이니 0 아니어도 멈추지 말고 그대로 보고.

## 5. 앵커 갱신 (CLAUDE.md §2)
- `eval/after_acc_r16_3tier_baseline.json` = **새 활성 3단 baseline 앵커**(현 모델 기준 0점). 수치(3×3·cardinal_miss·over_call·이진 동치) 기입.
- 이진 앵커는 계속 역사적 참고(R15에서 강등됨).
- footer: "2026-06-10 R16: 3단 채점 + baseline 재채점. 다음=모델 경미 출력(generate) + 재측정."

## 6. 커밋 (atomic, 푸시 보류)
1. `feat: run_eval 3단 채점 — tier 매핑·3×3 혼동표·비대칭 게이트 지표 (+테스트) (R16)` — run_eval.py(+rescore 필요 시)·tests.
2. `data: R16 3단 baseline 재채점 + CLAUDE.md 앵커 갱신` — eval/after_acc_r16_3tier_baseline.json·CLAUDE.md.
- 해시·`git status` 보고.

## 7. 보고 형식
1. Phase 0: _build_result/rescore 구조 + after_acc_armC_3p5flash.json per_case 39장 확인 + 삽입안. → HOLD.
2. (구현 후) 추가 코드 요지 + `not integration` 결과.
3. **3단 baseline 핵심**: 3×3 혼동표, cardinal_miss(🔴)·soft_miss·minor_undercall·over_call·exact_match, + 기존 이진(TP/TN/FP/FN·recall).
4. 커밋 해시 + git status.

## 8. 금지 사항
- 과금 측정(Gemini).
- 모델 출력(generate/analyze)·가드·GT·프롬프트 변경.
- 기존 이진·5-status 지표 제거/변경(추가만).
- 앵커·baseline 접근 시 입력 파일 수정/출력 클로버.
- 자동 푸시.
