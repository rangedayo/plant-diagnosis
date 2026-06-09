# R16 결과 — 3단 채점 코드 + 무과금 baseline 재채점

> 시점: 2026-06-10. R15에서 GT가 3단(tier)으로 마이그레이션된 뒤, 채점 로직에 3단 + 비대칭 게이트를 추가하고 현 생산 모델 출력을 새 3단 GT로 **무과금 재채점**해 3단 출발선(baseline)을 확정.
> 변수 = **채점 코드(run_eval/rescore)뿐**. 모델(generate/analyze)·가드·GT·프롬프트 무변경. 측정 Gemini **0**.

## 0. 한 줄 결론
모델 5종 status를 3단 tier로 매핑(건강→건강 / 경미→경미(미래) / 과습·건조·병해 의심·영양 부족→비건강)하고 3×3 혼동표 + 비대칭 게이트 지표를 추가. `after_acc_armC_3p5flash.json`(현 생산 모델 raw 출력)을 R15 3단 GT로 재채점 → **`eval/after_acc_r16_3tier_baseline.json`** 생성, 새 활성 3단 앵커로 지정.

## 1. 추가 코드 (add-only, 기존 이진/5-status 지표 무변경)
- `scripts/run_eval.py`
  - `_status_to_tier(status)`: `None→None`(skip/error 제외), `건강→건강`, `경미→경미`(현 모델 미출력, 미래 대비), `과습·건조·병해 의심·영양 부족·비건강-원인미상→비건강`, 미지원→`비건강`(안전 측=과대)+stderr 로그.
  - `build_tier_diagnosis(per_case)`: 3×3 혼동표(행=gt_tier, 열=pred_tier) + `exact_match`·`cardinal_miss`·`soft_miss`·`minor_undercall`·`over_call{to_mild,to_unhealthy,total}` + `scored`/`skipped`/`skipped_ids`.
  - `_measure_labels` per_case에 `gt_tier`·`pred_tier`, `_build_result`에 `tier_diagnosis` 키, `_report_console`에 3×3 콘솔 출력.
- `scripts/rescore_from_output.py`: `gt_tier` 재병합 + 보존된 `pred_status`에서 `pred_tier` 계산(무과금 재채점 대응) + CLI tier 요약 출력.
- `tests/test_run_eval_tier.py`: 단위 테스트 11건(매핑 6 + 코너 5: scored/skipped·3×3·비대칭 지표·경미 미출력·빈 입력).
- 회귀: `pytest -m "not integration"` → **34 passed**(기존 23 + 신규 11), 2 integration deselected.

## 2. 3단 baseline 핵심 — `eval/after_acc_r16_3tier_baseline.json`
**현 생산 모델(3.5-flash/global, R14 롤백 프롬프트) 출력을 R15 3단 GT로 무과금 재채점한 0점(출발선).** 모델이 경미를 못 내는 상태.

### 3×3 tier 혼동표 (행=정답 gt_tier, 열=예측 pred_tier; scored 39, skipped 0)

| gt＼pred | 건강 | 경미 | 비건강 |
|---|---|---|---|
| **건강** (16) | 11 | 0 | **5** |
| **경미** (7) | **2** | 0 | **5** |
| **비건강** (16) | **0** | 0 | 16 |

### 비대칭 게이트 지표

| 지표 | 값 | 의미 |
|---|---|---|
| `exact_match` | **27/39 (69.2%)** | 대각합 |
| 🔴 `cardinal_miss` | **0** | gt비건강→pred건강. 하드 게이트 사수 (옛 FN 0의 3단판) |
| `soft_miss` | **0** | gt비건강→pred경미. 모델 경미 미출력이라 0 정상 |
| `minor_undercall` | **2** | gt경미→pred건강. 허용(저위험) |
| `over_call` | **10** | →경미 **0** / →비건강 **10** |

### 이진 동치
TP 16 · TN 13 · FP 10 · FN 0 · **recall 1.0** · acc **74.36%**(29/39).

## 3. 읽기 (측정, 게이트 판정 아님)
- 모델이 **비건강 16건 전수**를 비건강으로 잡음 → `cardinal_miss 0`, recall 1.0이 3단에서도 유지.
- **이진 FP 10 = `over_call→비건강` 10과 동일 집합 = 경미 5 + 건강 5.**
  - 건강 GT → 비건강 5건: 진짜 over-call(미용 vs 병리 임계값 영역).
  - 경미 GT → 비건강 5건: 3단 관점에선 "한 칸 과대"이지 순수 오진 아님 → 모델이 경미를 낼 수 있으면 분리 가능.
- 경미 7건은 모델이 건강 2 / 비건강 5로 쪼갬(경미 열 전부 0 = 현 모델 한계, 예상대로).
- → **3단 스키마의 가치 = FP의 절반(경미 5)이 "과대 한 칸"으로 재해석됨**. 다음 트랙(generate 경미 출력)의 직접 근거.

## 4. 변수 격리 보증
모델(generate/analyze)·`apply_status_guard`·GT(`labels.json`)·프롬프트·기존 이진/5-status 지표 **일절 무변경**. 측정 Gemini **0회**(rescore 무과금, `rescore_note: no model calls`, remerged 14건). 입력 `after_acc_armC_3p5flash.json`·old 앵커 읽기만, 출력은 새 파일명(앵커 클로버 방지).

## 5. 측정 한계 (정직)
- 단일 raw 출력 재채점(analyze 비결정성 고정분 1 run). 경미 채점은 **모델이 경미를 못 내는 현 상태의 0점**이라 exact 27/39는 상한이 아니라 출발선.
- 표본 39(경미 7) 작음 → noise.

## 6. 커밋
- `8b41ab1` `feat:` — run_eval/rescore 3단 채점 + 테스트
- `3f96dd4` `data:` — baseline json + CLAUDE.md §2 앵커 갱신
- (본 보고서) `docs:` — task md + R16_result.md provenance

## 7. 다음 라운드 후보
1. **generate 경미 출력** (메인 트랙) — STRUCTURED status enum에 경미 추가 + generate가 경미를 낼 조건. 측정 시 `over_call→비건강`의 경미 5건이 `→경미`(soft side)로 이동하는지 = 이진 FP 감소 여부. **FN 0 / cardinal_miss 0 사수 게이트.**
2. (보조) 경미 판정을 status guard가 어떻게 다룰지.
