# [B-4c] tie+cosmetic "건강" 룰 + TP 안전장치 측정 — Claude Code 작업 프롬프트

> 목적: [B-4b]에서 데이터로 입증된 **"cosmetic 증상은 problem_type이 tie로 분산되어 '병해 금지' 룰이 미발동"** 본질 해소. (1) generate 프롬프트에 **"RAG 우세 타입이 tie이고 관찰 증상이 모두 cosmetic이면 status='건강' 우선"** 룰 추가 + (2) **top_1 problem_type 보조 신호** 활용 + (3) **TP(진짜 아픈) 케이스 분포 측정**으로 룰이 recall을 깎지 않는지 검증.
>
> 사전 진단: 본 대화 inline. 사용자 위임 ("측정·분석 방향은 네 판단대로") + 명시 요구 1건 (**보고에 observed_symptoms 증상 문장 3~4개 직접 명시**).
>
> 단계: [B-4c] (B-4 본질 직격 3차 — 룰 추가 + TP 안전장치)
> 선행: [B-4b] 완료 (FP 17.5 불변, tie 지배 11~12건이 원인, problem_type 노출 인프라·헬퍼 구축됨)
> 후행: 잔존 FP·recall 결과 따라 [1-3] v5(analyze) 또는 단계 B'(농진청 종 메타) 결정

---

## 핵심 본질 (왜 이 룰인가)

[B-4b] 측정으로 입증된 기전:
- cosmetic 증상(잎끝/가장자리 갈변)은 묘사가 일반적 → top_3 카드가 abiotic/frame/nutrient/env로 sim 근소 분산 → 5% 임계로 **majority=tie**
- [B-4b]의 "병해 금지" 룰은 **명확한 단일 우세(abiotic/env/nutrient)에서만 발동** → tie 케이스(FP의 11~12건)에서 미발동 → generate가 "병해 의심" 기본 escalate

[B-4c] 가설:
- **tie = "여러 원인 가능한 경계 신호" = 대체로 경미·비특이적 증상의 표지**
- 반대로 **명확한 병해(흰 가루 막·검게 무른 조직·고사)는 묘사가 특이적 → 특정 disease 카드로 쏠림 → tie 아님** (top_1=disease)
- 따라서 **"tie + cosmetic → 건강"** 룰은 진짜 병해(disease 쏠림)를 안 건드리고 cosmetic FP만 회복 → recall 보존 기대

**검증 필수**: 위 가설이 성립하려면 "tie인데 사실 진짜 아픈" TP 케이스가 거의 없어야 함. 평가셋 TP는 5장뿐(표본 작음) → 본 측정에서 TP 케이스 분포를 박아 직접 확인. 이게 recall 게이트의 데이터 근거.

---

## 확정된 결정 (변경 금지)

1. **변경 범위**: 2개 파일
   - `app/prompts.py` — STRUCTURED_DIAGNOSIS_JSON_SYSTEM에 tie+cosmetic 룰 + top_1 보조 신호 가이드 추가
   - `scripts/run_eval.py` — tp_analysis 섹션 추가 + observed_symptoms 샘플 콘솔/JSON 출력 (read-only 측정 보강, 본 라벨링 무변경)
   - `app/graph.py` — **무변경** ([B-4b]에서 `top_3_problem_type_weighted`에 `majority`·`top_problem_type` 이미 노출, context_summary에 "우세 타입"·"1위 카드 타입" 이미 박힘)

2. **prompts.py 룰 설계 (본질)**:
   - (b) tie+cosmetic→건강: "RAG 우세 타입(majority)이 'tie'이고 관찰된 증상이 **모두 cosmetic 패턴**이면 status='건강'을 우선 고려" — cosmetic 정의는 [B-4b]에서 이미 프롬프트에 박혀 있음(재활용, 재정의 금지)
   - (a) top_1 보조: "단, 1위 카드 타입(top_problem_type)이 'disease' 또는 'pest'이면 tie여도 건강 회복 금지 — 병해 의심 진입 정당" — 명확한 병해 쏠림 보호
   - 기존 [B-4b] 룰(명확한 abiotic/env/nutrient 우세 → 병해 금지)은 **유지** (충돌 아님, tie 케이스를 추가 흡수)

3. **run_eval.py tp_analysis (안전장치 측정)**:
   - TP 정의: `gt_is_healthy=False` AND `pred_is_healthy=False` (진짜 아픈데 아프다고 맞춘 것)
   - FN도 함께: `gt_is_healthy=False` AND `pred_is_healthy=True` (진짜 아픈데 건강이라 놓침 — recall 직격)
   - 박을 키: status 분포·top_3 majority 분포·observed_symptoms 전수 dump (TP+FN 합쳐 5건이라 전수 가능)

4. **측정 2회 평균** ([B-3]·[B-4a]·[B-4b] 패턴): run1·run2 + 평균 파일 3개

5. **본 e2e 라벨링 무변경**: `plant_match`·`healthy_match`·`json_ok`·`latency_sec` 무변경. fp_analysis([B-4a] 박은 것) 유지.

6. **단일 atomic 커밋** (1단계·[B-2]·[B-3]·[B-4a]·[B-4b] 패턴).

7. **frontend·status enum 무변경**: 5개 유지.

---

## 사전 확인 — 작업 시작 전 모두 실행

각 항목 결과를 보고에 명시.

### A. 현재 코드·환경 상태
```bash
git status
# 기대: clean (B-4b 커밋·푸시 후)
git log -1 --oneline
# 기대: [B-4b] generate problem_type 가중 다수결 커밋
```

### B. [B-4b] 박은 state 키·context_summary 확인 (graph.py 무변경 근거)

```bash
grep -n "top_3_problem_type_weighted\|top_problem_type\|majority\|우세 타입\|1위 카드 타입" app/graph.py
```

확인할 것:
1. `top_3_problem_type_weighted` dict에 `majority`·`top_problem_type` 키 있는지 ([B-4b] `_weighted_problem_type_majority` 반환값)
2. generate_node context_summary에 "우세 타입: {majority}"·"1위 카드 타입: {top_pt}" 이미 박혀 있는지
3. → **둘 다 확인되면 graph.py 무변경**. generate는 이미 majority·top_pt 정보를 프롬프트로 받고 있으므로, prompts.py에서 활용 가이드만 추가하면 됨
4. 만약 context_summary에 둘 중 하나라도 누락이면 → 보고 후 graph.py 최소 변경 (해당 줄만)

### C. 현재 STRUCTURED_DIAGNOSIS_JSON_SYSTEM 읽기 ([B-4b] 갱신 후 상태)

```bash
grep -n "STRUCTURED_DIAGNOSIS_JSON_SYSTEM" app/prompts.py
# view로 본문 전체 읽기
```

확인할 것 (라인 번호 박기):
1. [B-4b]에서 박은 "RAG 우세 타입이 abiotic/env/nutrient이면 병해 의심 금지" 줄 — **본 룰 삽입 위치 기준점**
2. [B-4b]에서 박은 cosmetic 패턴 정의 줄 — **재활용 (수정 금지, 참조만)**
3. [B-4b]에서 박은 "tie/general/frame이면 보수적 판단" 줄 — **본 룰로 구체화 대상** (현재 "보수적 판단"이 모호해서 generate가 병해 의심으로 해석한 게 [B-4b] 실패 원인)
4. cosmetic 예외 "건강" 조건 줄 — 본 tie 룰과 정합 점검

### D. run_eval.py fp_analysis 구조 확인 (tp_analysis 거울 작성용)

```bash
grep -n "_build_fp_analysis\|fp_analysis\|_count_top3_majority\|fp_observed_symptoms_samples" scripts/run_eval.py
```

확인할 것: [B-4a]에서 박은 `_build_fp_analysis`·`_count_top3_majority`·`_count_by_key`·`_majority_problem_type` 헬퍼 — tp_analysis가 이들 재사용 가능한지.

### E. 기존 테스트
```bash
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 23 passed
```

---

## 작업 묶음

### 1. `app/prompts.py` — tie+cosmetic 룰 + top_1 보조 신호

[B-4b]에서 박은 "tie/general/frame → 보수적 판단"의 모호함이 실패 원인이었음. 이를 **구체적 룰로 대체·보강**.

**삽입 위치**: [B-4b] "RAG 우세 타입이 abiotic/env/nutrient이면 병해 의심 금지" 룰 **직후**.

**추가할 룰 (의미·강도 박힌 대로, 표현은 자연스럽게)**:

> "**우세 타입(majority)이 'tie'인 경우의 판단**: tie는 관찰된 증상이 비특이적이어서 여러 원인(건조·과비·염류·자연 노화 등)에 고르게 매칭됐다는 신호입니다. 이때는 다음 순서로 판단하세요:
> (1) **1위 카드 타입(top_problem_type)이 'disease' 또는 'pest'이면** — 가장 가까운 자료가 병해/해충이므로 'status=병해 의심' 진입이 정당합니다.
> (2) **1위 카드 타입이 'disease'·'pest'가 아니고(abiotic/env/nutrient/general/frame 등), 관찰된 증상이 모두 cosmetic 패턴이면** — 'status=건강'을 우선 선택하세요. 비특이적 경미 증상 + 병해로 쏠리지 않는 자료 분포는 종 고유 특성·자연 노화 범위일 가능성이 높습니다.
> (3) **1위 카드 타입이 'disease'·'pest'가 아니지만 증상이 cosmetic이 아니면(비대칭·확산·잎 중앙부 변색 등 병변 신호)** — 'status=병해 의심'은 피하되 증상 양상에 맞는 '과습'·'건조'·'영양 부족' 중 선택하세요."

**기존 "tie/general/frame → 보수적 판단" 줄**: 위 룰로 흡수·대체 (모호 표현 제거).

**충돌 점검**: cosmetic 정의 줄·cosmetic 예외 "건강" 조건 줄은 유지. 본 tie 룰이 그 정의를 참조하는 구조라 정합.

### 2. `scripts/run_eval.py` — tp_analysis 섹션 + observed_symptoms 출력

#### 2-1. `_build_tp_analysis` 헬퍼 ([B-4a] `_build_fp_analysis` 거울)

```python
def _build_tp_analysis(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    """TP(진짜 아픈데 맞춤) + FN(진짜 아픈데 놓침) 분포 — [B-4c] recall 안전장치.

    TP: gt_is_healthy=False AND pred_is_healthy is False
    FN: gt_is_healthy=False AND pred_is_healthy is True  ← recall 직격, 0이어야 정상
    """
    sick_cases = [
        c for c in per_case
        if c.get("gt_is_healthy") is False and c.get("pred_is_healthy") is not None
    ]
    tp_cases = [c for c in sick_cases if c.get("pred_is_healthy") is False]
    fn_cases = [c for c in sick_cases if c.get("pred_is_healthy") is True]

    def _dump(cases: list[dict]) -> list[dict]:
        return [
            {
                "image_id": c["image_id"],
                "gt_plant": c["gt_plant"],
                "pred_status": c["pred_status"],
                "observed_symptoms": c.get("observed_symptoms") or [],
                "top_3_problem_types": [
                    str(t.get("problem_type") or "") for t in (c.get("top_3_rag") or [])
                ],
                "top_3_majority": _majority_problem_type(c.get("top_3_rag")),
            }
            for c in cases
        ]

    return {
        "tp_count": len(tp_cases),
        "fn_count": len(fn_cases),
        "tp_status_distribution": _count_by_key(tp_cases, "pred_status"),
        "tp_top3_majority": _count_top3_majority(tp_cases),
        "fn_top3_majority": _count_top3_majority(fn_cases),
        # 전수 dump (TP+FN 합쳐 ~5건)
        "tp_samples": _dump(tp_cases),
        "fn_samples": _dump(fn_cases),  # ← 비어 있어야 recall 100%
    }
```

#### 2-2. 결과 dict에 tp_analysis 추가

```python
# [B-4a]에서 박은 fp_analysis 옆에 추가
result = {
    ...
    "fp_analysis": _build_fp_analysis(per_case),   # [B-4a] 유지
    "tp_analysis": _build_tp_analysis(per_case),   # [B-4c] 신규
    "per_case": per_case,
}
```

#### 2-3. 콘솔 출력 — observed_symptoms 직접 보이게 (사용자 요구)

[B-4a] FP 분석 콘솔 출력 블록 직후에 추가:

```python
tpa = result["tp_analysis"]
print("\n[TP/FN 분석] ([B-4c] recall 안전장치)")
print(f"  TP={tpa['tp_count']}  FN={tpa['fn_count']} (FN>0이면 recall 깎임)")
print(f"  TP status: {tpa['tp_status_distribution']}")
print(f"  TP top_3 majority: {tpa['tp_top3_majority']}")
print(f"  FN top_3 majority: {tpa['fn_top3_majority']}")

print("\n[관찰 증상 문장 — TP 케이스 (진짜 아픈 식물)]")
for s in tpa["tp_samples"]:
    print(f"  · {s['image_id']} [{s['pred_status']}] majority={s['top_3_majority']}")
    print(f"    증상: {s['observed_symptoms']}")
if tpa["fn_samples"]:
    print("\n[⚠ 관찰 증상 문장 — FN 케이스 (놓친 아픈 식물)]")
    for s in tpa["fn_samples"]:
        print(f"  · {s['image_id']} [{s['pred_status']}] majority={s['top_3_majority']}")
        print(f"    증상: {s['observed_symptoms']}")

# FP 케이스 증상 문장도 일부 출력 (회복 검증용 — 사용자 요구)
fpa = result["fp_analysis"]
print("\n[관찰 증상 문장 — FP 케이스 일부 (오진 유지분, 최대 8건)]")
for s in fpa.get("fp_observed_symptoms_samples", [])[:8]:
    print(f"  · {s['image_id']} [{s['pred_status']}]")
    print(f"    증상: {s.get('observed_symptoms', [])}  타입: {s.get('top_3_problem_types', [])}")
```

### 3. 변경 추정 라인
- `app/prompts.py`: +12~18 −2~4 (tie 룰 추가, 모호 줄 대체)
- `scripts/run_eval.py`: +50~70 −0 (read-only 추가)
- `app/graph.py`: 0 (무변경 — 사전 확인 B에서 확정)

---

## 제약

- **변경 가능 파일**: `app/prompts.py`, `scripts/run_eval.py` 두 개 (graph.py는 사전 확인 B 통과 시 무변경)
- **절대 수정 금지**:
  - `app/model_utils.py`·`app/vision/*`·`app/nodes/*`·`app/schemas.py`·`app/main.py`
  - `app/prompts.py`의 cosmetic 패턴 정의 줄 ([B-4b] 박은 것 — 참조만, 재정의 금지), `ANALYZE_SYSTEM`·기타 상수
  - `tests/*`·`.env`·README·`data/vector_db/*`
  - `eval/golden_set.json`·`scripts/eval_retrieval.py`
  - `types/diagnosis.ts`·`components/ResultView.tsx` (status enum 무변경)
  - `scripts/run_eval.py`의 본 라벨링 계산 (`plant_match`·`healthy_match`·`json_ok`·`latency_sec`·`_build_fp_analysis`) — tp_analysis 추가만, 기존 무변경
- **analyze 무변경**: 본 [B-4c]는 generate 측 룰. analyze 임계는 [1-3] v5 자리(후순위)
- 파일 인코딩 BOM 없는 UTF-8. Python 3.12 호환.

---

## 검증 — 측정 전 단계별 확인

```bash
# 1. import·문법
.venv\Scripts\python.exe -c "from app.prompts import STRUCTURED_DIAGNOSIS_JSON_SYSTEM; print(len(STRUCTURED_DIAGNOSIS_JSON_SYSTEM))"
.venv\Scripts\python.exe -c "import scripts.run_eval; print('ok')"
# 기대: 정수(B-4b 길이 +150~300자) + 'ok'

# 2. 단위 테스트
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 23 passed

# 3. graph 빌드
.venv\Scripts\python.exe -c "from app.main import app; print('ok')"
# 기대: 'ok'

# 4. dry-run 2~3장 — tie 케이스 1장 포함되게(드라세나/스파티필름) → 룰 발동 확인
#    + tp_analysis·observed_symptoms 콘솔 출력 정상 박힘 확인
```

4개 통과 후 본 측정.

---

## 측정 — 2회 평균

```bash
$env:RUN_EVAL_OUT="eval/after_phase_b4c_run1.json"
.venv\Scripts\python.exe scripts\run_eval.py

$env:RUN_EVAL_OUT="eval/after_phase_b4c_run2.json"
.venv\Scripts\python.exe scripts\run_eval.py

# 평균 → eval/after_phase_b4c.json
```

**비교 baseline**: `eval/after_phase_b4b.json` (FP 17.5) + `eval/after_phase_b3_e2e.json` (회귀 기준).

---

## 게이트 (2회 평균)

| 게이트 | 조건 | 실패 시 |
|---|---|---|
| **recall (핵심 안전장치)** | **≥ 60% (FN ≤ 2)** | **FN 급증 시 즉시 revert** — 룰이 진짜 아픈 식물을 건강으로 잘못 분류 |
| FP (본 [B-4] 게이트) | 17 → 12 이하 | revert 금지, 잔존 FP 분석 후 [1-3] v5/단계 B' 결정 |
| 회귀 | plant_korean·accuracy·json 5%p 이내 | 큰 회귀 시 원인 분석 |

**recall 우선 원칙**: FP 개선과 recall 보존이 충돌하면 **recall 보존이 절대 우선**. 아픈 식물 놓치는 건 사용자 신뢰 본질(1단계에서 60→100% 끌어올린 핵심 성과)을 깎는 것. FN이 0→2 이상으로 늘면 룰이 과하게 관대한 것 → revert 후 재설계.

---

## 보고 형식

### 1. 사전 확인 결과
- git status·log
- **graph.py 무변경 근거** (top_3_problem_type_weighted majority·top_problem_type 키 + context_summary 노출 확인 결과)
- STRUCTURED_DIAGNOSIS_JSON_SYSTEM 라인 번호 (룰 삽입 위치)
- pytest 결과

### 2. 변경 파일·라인
- `app/prompts.py`: +N −M (추가 룰 본문)
- `scripts/run_eval.py`: +N −0
- `app/graph.py`: 0 (무변경 확인)

### 3. 검증 결과
- 4개 단계
- **dry-run tie 케이스 1장의 판단 추적** — 증상이 cosmetic으로 인식됐는지, top_1이 비-disease인지, status가 건강으로 회복됐는지

### 4. 측정 결과 (2회 평균)

| 메트릭 | run1 | run2 | 평균 | B-4b | Δ |
|---|---|---|---|---|---|
| plant_korean | ? | ? | ? | 0.8688 | ? |
| precision | ? | ? | ? | 0.2223 | ? |
| recall | ? | ? | ? | 1.0 | ? |
| accuracy | ? | ? | ? | 0.4697 | ? |
| FP | ? | ? | ? | 17.5 | ? |
| FN | ? | ? | ? | 0 | ? |
| json | ? | ? | ? | 1.0 | ? |

게이트 판정 (recall·FP·회귀 3개) 박기.

### 5. ★ 관찰 증상 문장 직접 명시 (사용자 요구 — 필수)

**§5-1. TP 케이스 (진짜 아픈 식물) 증상 문장 전수**:
| image_id | gt_plant | pred_status | top_3 majority | observed_symptoms (문장 전수) |
|---|---|---|---|---|
| ... | ... | ... | ... | [...전체...] |

**§5-2. FN 케이스 (놓친 아픈 식물) 증상 문장 — 있으면 ⚠**:
| image_id | gt_plant | pred_status | top_3 majority | observed_symptoms |
|---|---|---|---|---|
| (비어 있어야 recall 보존) |

**§5-3. FP 케이스 (오진 유지분) 증상 문장 — 최대 8건**:
| image_id | pred_status | observed_symptoms (문장) | top_3 problem_types |
|---|---|---|---|

**§5-4. 회복 케이스 대조** — [B-4b]에선 FP였다가 [B-4c]에서 "건강"으로 회복된 케이스의 증상 문장:
| image_id | B-4b status | B-4c status | observed_symptoms | 회복 근거(tie+cosmetic+비-disease?) |
|---|---|---|---|---|

### 6. tp_analysis vs fp_analysis 종합

- **recall 직격**: FN top_3 majority 분포 — tie인 FN이 있나? (있으면 "tie→건강" 룰이 진짜 아픈 식물을 깎은 것 = 가설 반증)
- **FP 회복**: tie majority였던 FP가 몇 건 "건강"으로 회복됐나
- 잔존 FP: disease 우세 FP(retrieval/코퍼스 단, 단계 B') vs tie 잔존(룰 미발동분) 분해

### 7. 다음 단계 신호
- recall PASS + FP 개선 → [B-4] 본질 해소 자리. 잔존 FP가 disease 우세면 단계 B'
- recall FAIL → revert + tie 룰 재설계 (top_1 조건 강화 등)
- tie 잔존 FP가 많으면 → cosmetic 인식이 모델 자율 해석에서 막힌 것, analyze [1-3] v5 자리

### 8. 위험·미해결
- analyze 비결정성 (FP ±1, [1단계] 7건) — 2회 평균 본질
- TP 표본 5장으로 recall 검증 — 표본 작음. 본 측정은 신호일 뿐, 평가셋 확장 시 재검증 자리
- cosmetic 인식이 모델 자율 — dry-run에서 직접 확인
- top_1 problem_type이 빈 문자열("")인 케이스 처리 (main_rag 카드는 problem_type 없음) — 빈 값일 때 룰 동작 명시

---

## 커밋 — 작업 완료 후 사용자 검토 대기

게이트 통과해도 **사용자 검토 → 커밋 → push** 순서. 자동 커밋·push 금지.

권장 커밋 메시지:
```
feat: [B-4c] generate tie+cosmetic "건강" 룰 + top_1 보조 신호 + TP recall 안전장치 측정
```

수정: `app/prompts.py`, `scripts/run_eval.py`  
신규: `eval/after_phase_b4c_run1.json`·`run2.json`·`after_phase_b4c.json`

---

## 작업 완료 후 즉시 진행 금지

[1-3] v5(analyze) 또는 단계 B'는 [B-4c] 보고의 §6·§7 결과를 사용자가 검토한 뒤 별도 작업 프롬프트로 박는다. **자동 진행 금지**.
