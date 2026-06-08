# R12a run3 측정 위생 확인 (read-only·무과금)

> R12a 3-run 측정 중 run3에서 JSON 파싱 실패 3건 발생(표적 `self_haengun_006` 포함).
> 429(쿼터/레이트리밋) vs 진짜 파싱 실패 판별. 핸드오프 §8 교훈("429를 파싱 실패로 오진") 대응.
> **새 인퍼런스 0건** — 기존 run3 산출물의 `error` 필드만 분석.

---

## 1. run1·run2·run3 실제 저장 경로 (커밋 #4 대비)

3개 run **전부 중첩 `eval/eval/` 폴더**에 저장됨 (task §3-1이 지적한 이중 eval 폴더 — run2만이 아니라 3개 모두):

```
eval/eval/after_acc_r12a_veto_run1.json
eval/eval/after_acc_r12a_veto_run2.json
eval/eval/after_acc_r12a_veto_run3.json
```

원인: `RUN_EVAL_OUT="eval/after_acc_r12a_veto_run1.json"`로 설정했으나 `run_eval`이 출력 경로에
`eval/`를 prepend → `eval/eval/...`. **커밋 #4 전에 `eval/`로 이동 권고** (앵커·baseline과 같은
디렉터리에 모이도록). 파일명 자체는 앵커·baseline과 겹치지 않음(덮어쓰기 사고 아님).

---

## 2. 3건 분류 — **전부 429 (RESOURCE_EXHAUSTED), 진짜 파싱 실패 아님**

| run | json_parse_success_rate | failed_ids |
|---|---|---|
| run1 | **1.0** | [] (clean) |
| run2 | **1.0** | [] (clean) |
| run3 | **0.923** | self_haengun_006, inat_chlorophytum_comosum_002, inat_sansevieria_trifasciata_002 |

run3 3건 per-case 레코드 (전부 동일 패턴):

```
json_ok: False
pred_status: None        observed_symptoms: []        latency_sec: None
error: "VisionRetryableError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429,
        'message': 'Resource exhausted. Please try again later. ...',
        'status': 'RESOURCE_EXHAUSTED'}}"
```

**분류 근거**:
- 세 건 모두 `error` 필드에 **`429 RESOURCE_EXHAUSTED`(Vertex AI 쿼터)** 원문. 모델이 깨진 JSON을
  반환한 게 아니라 **analyze 단계가 `_with_retry`(max_attempts=3) 소진 후 `VisionRetryableError`를
  던져** `run_eval`의 case-level except(run_eval.py L598-621)에 잡힌 것.
- `observed_symptoms=[]`·`pred_status=None`·`latency_sec=None` → analyze가 반환을 못 했고
  **generate는 아예 실행 안 됨** → 파싱할 JSON 자체가 생성되지 않음. "JSON 파싱 실패"는 오분류.
- **타임아웃/기타 아님**: 메시지가 명시적 429. (단 latency 상승 추세 29s→44s→58s, max~168s는 동일
  쿼터 압박의 방증 — run3에서 한계 초과.)

---

## 3. 분류 → 게이트 처리 권고

**429로 판명 → run3 부분 오염.** 권고:

- **게이트 판정은 clean한 run1·run2 기준** (둘 다 `json_parse_success_rate=1.0`, 39/39 완주).
- run3는 **"API 스로틀로 3건 미측정 — 표적 `haengun_006` 포함"**으로 기록. run3의 FP/is_healthy
  수치는 3건(pred_is_healthy=None → healthy_match=None) 분모 탈락으로 run1·run2·앵커와 **직접
  비교 불가** → 게이트 분모로 쓰지 않음.
- **⚠ 중요**: 표적 `haengun_006`이 run3에서 **429로 드롭** → run3는 veto의 FN 복구를 **확인도
  반증도 못 함**(케이스가 실행 안 됨). FN 복구 판정은 run1·run2에서 `haengun_006`이 위치 토큰을
  추출했는지로 본다.
- **② 모델 교체 근거 아님**: 현 모델이 valid JSON을 못 낸 사례가 **0건**. 실패는 전부 인프라(쿼터)
  사유 → 모델 교체로 안 풀림. 쿼터 여유 시간대 run3 **재측정**이 올바른 대응.

---

## 4. run_eval의 429/파싱 집계 구조 (측정 위생 개선 후보)

- **분리 신호는 존재**: 429 예외 케이스는 case-level except에서 `json_ok=False` + **별도 `error`
  필드**(`VisionRetryableError: 429...`)로 기록됨(run_eval.py L600-620). 진짜 파싱 실패는 케이스가
  정상 반환했으나 `_struct_json_ok(sr)=False`인 경우로 **error 필드 없음**(L626).
- **그러나 집계가 합쳐짐**: `json_parse_failed_ids = [c for c in per_case if not c["json_ok"]]`
  (run_eval.py L836) — 429와 진짜 파싱 실패를 **한 통에** 넣음. 그래서 run3의
  `json_parse_success_rate=0.923`은 실제로 "API 스로틀 + 파싱" 혼합 실패율이며 **파싱 품질로
  오독될 수 있음**(핸드오프 §8 오진 재발 위험).
- **개선 후보(별도 위생 라운드)**: `error`에 `429`/`RESOURCE_EXHAUSTED` 포함 여부로 실패를
  `api_throttle_ids` vs `json_parse_failed_ids`로 **분리 집계**. 이 task 범위 밖 — 메모만.

---

## 결론

run3 파싱 실패 3건 = **전부 429 쿼터 소진**(진짜 파싱 실패 0). 게이트는 **run1·run2(clean)** 기준,
run3는 부분 오염으로 기록 + 쿼터 여유 시 재측정. 모델 교체 근거 아님. 측정 파일은 `eval/eval/`에
잘못 저장됨 → 커밋 #4 전 `eval/`로 이동 권고.

*진단 스크립트: `scripts/diagnostics/r12a_run3_hygiene.py` (read-only). 이 task는 커밋 없음 —
산출물은 R12a 매듭(result.md + 커밋 #4)에서 함께 정리.*
