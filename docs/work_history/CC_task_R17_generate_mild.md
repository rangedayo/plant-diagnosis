# CC Task — R17: generate가 "경미"를 출력하도록 (스키마 길의 본 트랙)

> 시점: 2026-06-10. R16 baseline에서 이진 FP 10 = 경미 5 + 건강 5로 분해됨. 이번 = generate가 **"경미"를 낼 수 있게** 해서, 그 경미 5건이 비건강→경미로 옮겨 FP가 주는지 측정.
> **변수 = "모델이 경미 출력 가능"** (generate 프롬프트 + status enum + 경미 is_healthy 매핑). 가드·analyze·GT·채점 로직 무변경.
> R14와 차이: R14는 cosmetic을 "건강"으로 밀어 recall 깨짐. 이번엔 "경미"(안전한 중간)로 → recall 방어. 라운드 번호 R17 잠정.

## 1. 안전 제약 (필독)
- **🔴 cardinal_miss=0 / recall 사수.** 진짜 비건강을 "건강"이라 하면 안 됨(하드 게이트). "경미"로 깎는 것(soft_miss)도 최소화 — 활성 병변 신호가 recall 방어선.
- prompts.py는 **별 세션 안 건드림 확인됨**(사용자 컨펌). 이번에 prompts.py + model_utils만 손댐.
- 가드(`apply_status_guard`)·analyze·GT(labels.json)·채점 로직(run_eval/rescore) **무변경**. (가드-경미 상호작용은 CC가 짚은 보조 트랙 → 다음.)
- `default_structured_fallback`의 안전 폴백("병해 의심") **유지**(파싱 실패 시 점검 유도).
- 측정(과금)은 **사용자 PowerShell 직접**(Phase 2). CC는 코드까지.
- 커밋까지. **푸시 보류.**

## 2. Phase 0 — read-only (먼저 보고·HOLD)
1. `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 현재 status enum 줄 + cosmetic 관련 규칙 불릿들(증상≥1→건강 금지 예외 / RAG 우세 타입 / tie·general / plant_confidence low) 위치 보고.
2. `app/model_utils.py` `ALLOWED_STRUCT_STATUS`(5종) + `normalize_structured_result`의 status 처리 + **pred_is_healthy를 status에서 파생하는 위치** 확인 보고.
3. §3 편집안(아래)이 현재 텍스트와 맞는지, **기존 "cosmetic→건강" 불릿을 "→경미"로 재라우팅할 때 모순 없는 최소 diff**를 제안해 보고.
4. → 보고 후 HOLD. 제안 diff 검토 OK 받고 Phase 1.

## 3. 편집안 (Phase 0에서 정확한 최소 diff 확정)

### 3.1 status enum (prompts.py + model_utils)
- `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` status 줄에 **"경미" 추가**: `"건강", "경미", "과습", "건조", "병해 의심", "영양 부족"`.
- `ALLOWED_STRUCT_STATUS`에 `"경미"` 추가(없으면 normalize가 경미를 "병해 의심"으로 강등시킴).

### 3.2 경미 판정 규칙 (prompts.py에 추가 + 기존 cosmetic→건강 재라우팅)
다음 블록을 status 규칙부에 추가하고, **기존 "cosmetic이면 건강" 경로들을 모두 "경미"로 재라우팅**(모순 제거 — Phase 0에서 정확 위치 제안):

```
- 경미(mild) 판정 — 우선 규칙: 관찰된 증상이 1개 이상 있으나 (1) 모두 cosmetic 패턴(잎끝·가장자리 국소 변색·마름 등, 아래 정의), (2) 단일 잎 또는 소수 잎에만 국한, (3) 활성 병변 신호(비대칭·확산성 병반, 잎 중앙부 변색, 조직 무름·물러짐, 곰팡이, 여러 잎 동시 진행)가 전혀 없음 — 을 모두 만족하면 status="경미"를 선택하세요. 미용적 손상은 있으나 개체 전체는 건강한 중간 상태입니다.
- 이때 검색 자료(RAG) 우세 타입이 disease/pest로 나왔더라도(cosmetic 증상이 병해 카드와 겹쳐 검색됐을 수 있음), 활성 병변 신호가 없는 한 "경미"를 우선합니다. (RAG 우세 타입 조건은 경미 판정에 요구하지 않음.)
- ⚠ recall 사수: 활성 병변 신호가 하나라도 있거나 증상이 다수 잎으로 확산됐으면 "경미"를 쓰지 말고 아래 규칙대로 비건강 원인(과습/건조/병해 의심/영양 부족)을 선택하세요. 실제 병징을 "경미"로 깎는 것은 금지입니다.
- 관찰된 증상이 전혀 없으면(빈 목록) 종전대로 "건강".
- status="경미"일 때 cause는 특정 원인을 단정하지 말고 "이 종에서 흔히 나타날 수 있는 경미한 잎끝 손상으로 보이며 반드시 병을 의미하지는 않습니다" 같은 신중·종맥락 톤으로 쓰세요. action_plan은 관찰·일반 관리 위주. (cause–status 정합 점검은 경미에 특정 원인을 강제하지 않음.)
```

### 3.3 pred_is_healthy 매핑
- 모델이 status="경미"를 내면 **pred_is_healthy = true**로 파생(GT 컨벤션과 동일 — 경미는 is_healthy 측면에서 건강 쪽). → 이진 지표에서 경미 예측이 FP를 깎는 방향. (3단 채점은 R16에서 이미 경미→경미 tier 매핑.)

## 4. Phase 1 — 코드 적용 (Phase 0 OK 후)
- §3 편집 적용. 기존 cosmetic→건강 불릿 재라우팅으로 모순 제거.
- `pytest -m "not integration"` 통과 확인(과금 0). normalize가 "경미"를 살려 보내는지 단위 점검 추가 권장.
- 커밋: `feat: generate 경미 출력 — status enum + 경미 판정 규칙 (R17)` (prompts.py·model_utils + tests). 푸시 보류.

## 5. Phase 2 — 측정 (사용자 PowerShell 직접, 과금)
```powershell
$env:RUN_EVAL_OUT="after_acc_r17_generate_mild.json"
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```
- 베어 파일명(eval/ 접두 금지). analyze=3.5-flash/global(현 기본).
- 비교 앵커 = `eval/after_acc_r16_3tier_baseline.json` (exact 27/39 · cardinal_miss 0 · FP 10 = 경미5+건강5).

## 6. 게이트 & 읽기
- 🔴 **cardinal_miss = 0** (비건강→건강). 깨지면 즉시 멈추고 롤백.
- **soft_miss(비건강→경미)** 추적 — 작으면 허용, 크면(모델이 경미 남발해 진짜 병징 깎음) 재검토.
- 성공 시그널: 경미 GT 5건이 비건강→**경미(exact)**로 이동, over_call→비건강 감소, **이진 FP 10→~5 이하**, exact_match 27/39↑.
- 결과 해석: R14처럼 analyze run-to-run 노이즈 교락이 있으니, 받으면 **per_case의 observed_symptoms를 baseline과 대조**(증상 같은데 status만 비건강→경미로 바뀜=프롬프트 효과 / 증상 자체가 다름=노이즈)로 분리. per_case 보존 필수.

## 7. 보고 형식 (CC → 웹)
1. Phase 0: 프롬프트 enum·cosmetic 불릿 위치 + ALLOWED_STRUCT_STATUS·pred_is_healthy 위치 + 재라우팅 최소 diff안. → HOLD.
2. (코드 후) prompts.py·model_utils diff 요지 + `not integration` 결과 + 커밋 해시.
3. (측정 후, 사용자 실행) 3×3 혼동표 + cardinal_miss(🔴)·soft_miss·over_call·exact + 이진(FP·recall) — baseline 대비 델타.

## 8. 금지 사항
- 과금 측정 임의 실행(Phase 2는 사용자).
- 가드·analyze·GT·채점 로직 변경.
- default 안전 폴백("병해 의심") 변경.
- 활성 병변 케이스를 경미로 깎는 규칙(=recall 위협) — 금지.
- 자동 푸시.
