# generate R1 사후 — JSON 파싱 실패 6건 원인 진단 (read-only)

**측정 출력**: `eval/after_acc_generate_escalation.json` (정합룰 적용)
**대조 기준점**: `eval/after_acc_r12d1_remove_surface.json` (정합룰 적용 전, 파싱 100%)
**성격**: read-only. 측정·재호출(Gemini) 없음, 코드·프롬프트·baseline 무변경.

---

## 핵심 결론 (먼저)

**6건의 "파싱 실패"는 JSON 파싱 실패가 아니라 Gemini Vision API의 `429 RESOURCE_EXHAUSTED`(쿼터/레이트리밋) 이다. 정합룰은 범인이 아니다.**

- 6건 전부 `error = "VisionRetryableError: 429 RESOURCE_EXHAUSTED"`, `latency_sec = None`, `pred_status = None`, `observed_symptoms = []`.
- 즉 **analyze(Vision) 단계가 아예 반환을 못 함** → 그 하류인 generate(정합룰이 있는 곳)는 **실행조차 안 됨**. 정합룰이 응답을 길게/깨지게 만들었을 인과 경로가 성립 불가.
- truncation·형식 오류·빈 JSON 전부 **아님**(generate가 출력을 낸 흔적 자체가 없음).
- `json_parse_success_rate` 메트릭이 오해를 부른 것: run_eval은 파이프라인 **전체 예외(429 포함)**도 `json_ok=False`로 기록한다([scripts/run_eval.py:598-621](scripts/run_eval.py#L598-L621)의 광범위 `except`). 진짜 JSON 파싱 판정(`_struct_json_ok`, [run_eval.py:626](scripts/run_eval.py#L626))은 generate가 출력을 냈을 때만 도달하는데, 이 6건은 거기까지 못 감.

**→ 이번 측정값(FP 13→8, acc 72.4%)은 무효.** gt=건강 6건이 429로 탈락 → 분모에서 건강 케이스가 빠지니 FP가 기계적으로 줄어든 착시. 정합룰의 진짜 효과는 **이 run으로 알 수 없음**. 깨끗한 재측정 필요.

---

## PART A — 파싱 실패 6건 raw 확인

run_eval은 케이스 실패 시 **raw 응답 본문은 저장하지 않지만 `error` 필드(예외 타입+메시지)는 저장**한다([run_eval.py:618](scripts/run_eval.py#L618)). 6건 모두 error가 명확해 재호출 없이 진단 가능.

| case | gt | latency | pred_status | error |
|---|---|---|---|---|
| self_dracaena_004 | 건강 | None | None | VisionRetryableError: 429 RESOURCE_EXHAUSTED |
| self_haengun_004 | 건강 | None | None | 〃 |
| inat_chlorophytum_comosum_003 | 건강 | None | None | 〃 |
| inat_sansevieria_trifasciata_002 | 건강 | None | None | 〃 |
| inat_sansevieria_trifasciata_003 | 건강 | None | None | 〃 |
| inat_spathiphyllum_001 | 건강 | None | None | 〃 |

**latency 대조**: 실패 6건은 latency=None(측정 자체가 안 됨). max 101초·91초·87초의 긴 latency는 **성공한** 케이스들 — 429 backoff(60초) 재시도를 거쳐 끝내 성공한 케이스라 길어진 것. **긴 latency ≠ 긴 응답(truncation)** 이며, 실패 6건과 겹치지 않는다.

---

## PART B — 원인 분류

6건 전부 **단일 원인: API 429 (rate_limit / 쿼터 소진)**. truncation·형식 오류·빈 응답·비결정성 전부 해당 없음.

재시도 메커니즘 확인([app/nodes/analyze.py:22-41](app/nodes/analyze.py#L22-L41)): `_with_retry(max_attempts=2)` = 최초 + 재시도 1회, 429 backoff 기본 60초. 6건은 **재시도 1회도 429** → 시도 소진 → 예외 전파 → run_eval이 기록. run 도중 쿼터가 지속 소진된 구간에 걸린 것.

**max_tokens(truncation) 점검**: 무관함이 확정. truncation이려면 generate가 출력을 시작해 중간에 잘려야 하는데, 6건은 analyze에서 멈춰 generate 출력이 0. status=None·symptoms=[]가 그 증거.

---

## PART C — 정합룰 인과 확인 (핵심)

- **기준점 대조**: `after_acc_r12d1_remove_surface.json`(정합룰 전)에서 동일 6건은 **전부 `json_ok=True`**, latency 15~28초 정상, error 없음.
- 그러나 이는 **정합룰을 범인으로 만들지 않는다.** 차이는 프롬프트가 아니라 **그 run의 일시적 429 버스트**다. 정합룰은 generate(하류)에 있는데 6건은 analyze(상류)에서 죽었으므로 룰이 개입할 지점이 없었다.
- **응답 길이 영향 가설 기각**: 정합룰이 추론을 길게 만들어 truncation을 유발했다 → generate 출력이 0인 이상 성립 불가. latency 상승은 **429 backoff 재시도**(60초 sleep)가 성공 케이스들에 누적된 것이지 추론 길이가 아니다.
- **6건이 전부 gt=건강인 이유 = 우연**. 429는 호출 순서·쿼터 소진 타이밍에 걸리는 것이지 정답 라벨(건강/비건강)과 인과 없음. analyze 단계 실패는 식물 건강 여부를 알기도 전에 일어남.

---

## PART D — 처방 옵션 (사용자 결정)

이번 라운드의 진짜 문제는 **측정 인프라(쿼터)** 이지 프롬프트가 아니다. 따라서:

### 권고: 정합룰은 롤백 불필요 — 깨끗한 재측정으로 판정
정합룰은 이 실패에 무관하므로 이 사유로 되돌릴 이유 없음. 단, 429로 6건이 빠진 현 결과는 비교 불가 → **재측정**이 본질 처방.

재측정을 견고하게 만드는 보조 옵션(택1 이상):
1. **재시도 예산 상향** — `_with_retry(max_attempts=2 → 3~4)` + backoff 유지. 일시적 429를 흡수해 케이스 탈락 방지. (최소 변경, 권장)
2. **호출 페이싱** — eval 루프는 이미 순차([run_eval.py:596] for-loop)지만, 케이스 간 짧은 sleep 또는 분당 쿼터 회복 대기를 넣어 분당 한도 초과 회피.
3. **쿼터 여유 시간대 재실행** — 코드 무변경, 가장 단순. 429가 분 단위 회복이면 잠시 후 재시도로 39건 완주 가능.

### 처방에서 제외(부적합)
- ~~max_tokens 상향~~ — truncation 아님(generate 출력 0). 무효.
- ~~정합룰 간결화 / 출력 형식 강제 강화~~ — 파싱 실패가 형식 문제가 아니므로 무관.
- ~~롤백 + 모델 교체~~ — 정합룰·모델 둘 다 이 실패의 원인이 아님. 성급한 결론.

### 측정 위생(별도, 선택)
`json_parse_success_rate`가 **API 예외(429)와 진짜 JSON 파싱 실패를 한데 묶어** `json_ok=False`로 집계 → 오진을 부름. 향후 run_eval에서 `error`성 실패(429·5xx·image_not_found)와 구조 파싱 실패를 분리 집계하면 이런 혼동 방지. (이번 룰 평가와 무관한 도구 개선이라 별도 라운드 후보.)

---

## 다음 단계 (참고 — 범위 X)
재측정으로 39건 완주 → 정합룰의 진짜 FP/5-status 효과 판정. 그 전엔 `after_acc_generate_escalation.json`을 앵커로 쓰지 말 것(429 탈락 6건으로 왜곡).

---

*read-only 진단. 커밋·푸시 보류 (task 지시).*
