# [B-4a] FP 본질 진단 측정 — Claude Code 작업 프롬프트

> 목적: e2e 측정에서 FP=17 본질을 데이터로 가르기. 각 FP 케이스의 `(observed_symptoms, top_3 카드 problem_type, pred_status)`를 박아 시나리오 ①(analyze over-report) vs ②(generate가 visual_description/RAG로 끌어내는 경로) 판정. **본 [B-4b] 작업 방향 결정의 데이터 근거**가 됨.
>
> **read-only 측정** — 본 진단·라벨링 로직 무변경. `app/graph.py`·`app/prompts.py`·`app/model_utils.py` 본체 미변경. `scripts/run_eval.py`에 측정 데이터 박기만.
>
> 사전 진단: 본 대화 inline. 사용자 8개 결정 영역 전체 동의.
>
> 단계: [B-4a] (B-4 워크플로우 옵션 C — 진단 측정 / 본 작업 2단 분리)
> 선행: [B-3] 완료 (07c25a3, golden_set retrieval Hit@10=1.0, e2e FP=17 불변)
> 후행: [B-4b] (본 작업 — [B-4a] 판정 결과 따라 generate 또는 analyze 또는 둘 다 방향 결정)

---

## 확정된 결정 (변경 금지)

1. **변경 범위**: `scripts/run_eval.py` 단일 파일에 측정 데이터 박기. 그래프·프롬프트·모델 유틸 본체 절대 손대지 마라.
2. **추가 박을 키 (per_case)**:
   - `observed_symptoms`: analyze 출력 그대로 (list[str])
   - `top_3_rag`: RAG retrieve 상위 3개 카드 메타 (list[dict])
     - 각 dict: `{card_id, problem_type, source, title, sim, rag_source}`
     - main_rag 문서엔 card_id 없으니 빈 문자열 허용
3. **추가 박을 메트릭 (전체 결과 dict)**: FP 케이스 분포 분석 3종 (아래 §보고에 박힘)
4. **측정 2회 평균** ([B-3] 패턴): run1·run2 + 평균 파일 3개
5. **graph.py 본체 무변경 원칙**: retrieve_node 출력 state 키 활용. state에 메타가 안 박혀 있으면 별도 retrieve 호출(`eval_retrieval.py`의 `_retrieve_top_n` 재사용) — graph.py에 메타 박는 변경 절대 금지
6. **본 e2e 진단·라벨링 로직 무변경**: `plant_match`·`healthy_match`·`json_ok`·`latency_sec` 계산 무변경. 키 추가만.
7. **FP 정의**: `gt_is_healthy=True` AND `pred_is_healthy=False` (기존 e2e 정의 그대로). 17건 추출은 per_case 박은 후 필터링.

---

## 사전 확인 — 작업 시작 전 모두 실행

각 항목 결과를 보고에 명시.

### A. 현재 코드·환경 상태
```bash
git status
# 기대: clean. 진행 중 변경 있으면 stash 또는 사용자에게 보고.

git log -1 --oneline
# 기대: 07c25a3 [B-3] golden_set retrieval·e2e 측정.
```

### B. retrieve_node 출력 state 키 확인 (핵심 — 방식 분기)

```bash
grep -n "rag_docs\|rag_metas\|rag_meta\|rag_sims" app/graph.py
```

확인할 것:
1. `state["rag_docs"]`에 텍스트 청크가 박힘 — 이미 확인됨 (generate_node의 `state.get("rag_docs")`)
2. `state["rag_metas"]` 또는 유사 키에 메타(card_id·problem_type·source·title·sim)가 박히는가?
3. retrieve_node 본체에서 `_chroma_query_sync` → `_triples_from_chroma` → `_merge_rag_triples` 결과 중 무엇이 state에 들어가는가

→ **세 가지 경우의 수**:
- **경우 1 (rag_metas 박힘)**: run_eval.py에서 `out.get("rag_metas")` 첫 3개 슬라이스 — 가장 깔끔
- **경우 2 (rag_docs만 박힘, 메타 누락)**: run_eval.py에서 `eval_retrieval.py`의 `_retrieve_top_n` 호출로 메타 별도 획득 — 그래프 무변경 유지, 측정 비용만 약간 추가
- **경우 3 (다른 형태)**: 사용자에게 보고 후 결정

**기본 선택: 경우 2 (eval_retrieval.py 함수 재사용)**. 경우 1이 발견되면 더 효율적이라 그쪽으로 전환. 어떤 경우든 graph.py 본체 무변경.

### C. 기존 테스트 동작 확인
```bash
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 모두 passed (현재 코드 검증).
```

### D. eval_retrieval.py 의존 확인
```bash
grep -n "_retrieve_top_n\|_chroma_query_sync\|_merge_rag_triples" scripts/eval_retrieval.py
# 기대: 함수 정의 + import 경로 확인. run_eval.py에서 재사용 가능한지 확인.
```

---

## 작업 묶음 — `scripts/run_eval.py` 1개 파일

### 1. per_case dict 키 추가

기존 per_case dict에 두 키 추가. 본 e2e 라벨링 계산 무변경.

```python
# Before (예시 — 정확 라인은 view 후 확정)
case_result = {
    "image_id": image_id,
    "gt_plant": gt_plant,
    "pred_plant_scientific": ...,
    "pred_plant_ko": ...,
    "plant_match": ...,
    "gt_is_healthy": gt_is_healthy,
    "pred_status": pred_status,
    "pred_is_healthy": pred_is_healthy,
    "healthy_match": healthy_match,
    "latency_sec": latency,
    "json_ok": json_ok,
}

# After — 두 키 추가
case_result = {
    "image_id": image_id,
    "gt_plant": gt_plant,
    "pred_plant_scientific": ...,
    "pred_plant_ko": ...,
    "plant_match": ...,
    "gt_is_healthy": gt_is_healthy,
    "pred_status": pred_status,
    "pred_is_healthy": pred_is_healthy,
    "healthy_match": healthy_match,
    "latency_sec": latency,
    "json_ok": json_ok,
    # [B-4a] 진단 측정 신규 키
    "observed_symptoms": list(out.get("observed_symptoms") or []),
    "top_3_rag": _build_top_3_rag(...),  # 아래 §2 참조
}
```

### 2. `_build_top_3_rag` 헬퍼 함수

경우 1 또는 경우 2 분기:

**경우 1 — state에 rag_metas 박힘 (사전 확인 B에서 확정 시)**:
```python
def _build_top_3_rag(out: dict) -> list[dict]:
    metas = (out.get("rag_metas") or [])[:3]
    sims = (out.get("rag_sims") or [])[:3]
    rag_sources = (out.get("rag_sources") or [])[:3]
    result = []
    for i, m in enumerate(metas):
        m = m or {}
        result.append({
            "card_id": str(m.get("card_id") or ""),
            "problem_type": str(m.get("problem_type") or ""),
            "source": str(m.get("source") or ""),
            "title": str(m.get("title") or "")[:80],
            "sim": round(float(sims[i]) if i < len(sims) else 0.0, 4),
            "rag_source": str(rag_sources[i] if i < len(rag_sources) else (m.get("_rag_source") or "")),
        })
    return result
```

**경우 2 — eval_retrieval.py `_retrieve_top_n` 재사용 (기본)**:
```python
# scripts/run_eval.py 상단 import
from eval_retrieval import _retrieve_top_n  # 또는 동등한 경로

def _build_top_3_rag(query_en: str, db_path: str) -> list[dict]:
    """eval_retrieval._retrieve_top_n 결과 상위 3개를 그대로 사용 (TOP_N=10 → [:3])"""
    if not query_en:
        return []
    top_10 = _retrieve_top_n(query_en, db_path)
    return [
        {
            "card_id": item.get("card_id") or "",
            "problem_type": item.get("problem_type") or "",
            "source": item.get("source") or "",
            "title": item.get("title") or "",
            "sim": item.get("sim", 0.0),
            "rag_source": item.get("source") or "",  # eval_retrieval은 source 키로 통합
        }
        for item in top_10[:3]
    ]
```

호출 시점 — 케이스별 진단 후, `query_en`은 `out.get("rag_query") or state.get("symptom_en") or " ".join(out.get("observed_symptoms") or [])` 중 graph가 실제 사용한 쿼리. 사전 확인 B에서 graph가 어떤 쿼리로 retrieve하는지 확인 후 동일 쿼리 박기.

### 3. 추가 메트릭 — FP 분포 분석 3종

per_case 박은 후, 전체 결과 dict의 `meta` 또는 신규 `fp_analysis` 섹션에 박기:

```python
# FP 케이스 추출
fp_cases = [c for c in per_case if c["gt_is_healthy"] and not c["pred_is_healthy"]]

fp_analysis = {
    "fp_count": len(fp_cases),
    "fp_status_distribution": _count_by_key(fp_cases, "pred_status"),
    # 기대 키: {"병해 의심": N, "영양 부족": N, "과습": N, "건조": N}
    "fp_observed_symptoms_buckets": {
        "empty": sum(1 for c in fp_cases if not c["observed_symptoms"]),
        "non_empty": sum(1 for c in fp_cases if c["observed_symptoms"]),
    },
    "fp_top3_problem_type_majority": _count_top3_majority(fp_cases),
    # 각 FP 케이스의 top_3 problem_type 중 최다 타입 다수결 → 분포 집계
    # 기대 키: {"disease": N, "abiotic": N, "nutrient": N, "env": N, "pest": N, "tie": N}
    "fp_observed_symptoms_samples": [
        {
            "image_id": c["image_id"],
            "gt_plant": c["gt_plant"],
            "pred_status": c["pred_status"],
            "observed_symptoms": c["observed_symptoms"],
            "top_3_problem_types": [t["problem_type"] for t in c["top_3_rag"]],
        }
        for c in fp_cases
    ],
}
```

**핵심**: `fp_observed_symptoms_samples`는 17건 전수 dump. [B-4b] 진단의 본질 데이터.

### 4. 출력 파일

기존 환경변수 `RUN_EVAL_OUT` 그대로 사용 ([1-5]에서 추가됨):

- `eval/after_phase_b4a_run1.json` (run1)
- `eval/after_phase_b4a_run2.json` (run2)
- `eval/after_phase_b4a.json` (2회 평균 — [B-3] `after_phase_b3_e2e.json` 형식 거울)

### 5. 변경 추정 라인

`scripts/run_eval.py`만:
- import 추가: ~3줄
- `_build_top_3_rag` 헬퍼: ~20~30줄
- per_case dict 키 추가: ~5줄
- `fp_analysis` 섹션 추가: ~30줄
- 헬퍼 함수 2~3개 (`_count_by_key`, `_count_top3_majority`): ~30줄

**총 ~90~120줄 추가**. 기존 라인 삭제 없음 (read-only 추가만).

---

## 제약

- **변경 가능 파일**: `scripts/run_eval.py` 단 하나
- **절대 수정 금지**:
  - `app/graph.py`, `app/prompts.py`, `app/model_utils.py`, `app/vision/*`, `app/nodes/*`, `app/schemas.py`, `app/main.py`
  - `tests/*`, `.env`, README
  - `eval/golden_set.json`, `scripts/eval_retrieval.py` ([B-3] 결과물 — 호출만, 수정 금지)
  - `data/vector_db/*` (Chroma 컬렉션)
- **본 e2e 라벨링 계산 무변경**: `plant_match`·`healthy_match`·`json_ok`·`latency_sec` 코드 줄 한 글자도 손대지 마라
- **graph.py 메타 노출 금지**: 경우 2(eval_retrieval.py 재사용)가 기본. 만약 경우 1이라도 graph.py에서 메타 키 추가 변경 절대 금지 (이미 박혀 있으면 그대로 활용만)
- 파일 인코딩 BOM 없는 UTF-8. Python 3.12 호환.

---

## 검증 — 측정 전 단계별 확인

```bash
# 1. import·문법 확인
.venv\Scripts\python.exe -c "import scripts.run_eval; print('ok')"
# 기대: 'ok'.

# 2. 단위 테스트 (영향 없어야)
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 모두 passed.

# 3. graph 빌드 확인 (run_eval.py 보강이 graph.py에 영향 안 줬는지)
.venv\Scripts\python.exe -c "from app.main import app; print('ok')"
# 기대: 'ok'.

# 4. 빠른 dry-run — 1~2장만으로 신규 키 박혔는지 확인
# (run_eval.py에 --limit N 옵션 있으면 활용, 없으면 sample 1장 직접)
```

4개 통과 후 본 측정.

---

## 측정 — 2회 측정 평균 ([B-3] 패턴)

```bash
# 1회차
$env:RUN_EVAL_OUT="eval/after_phase_b4a_run1.json"
.venv\Scripts\python.exe scripts\run_eval.py

# 2회차 (1회차와 독립 실행)
$env:RUN_EVAL_OUT="eval/after_phase_b4a_run2.json"
.venv\Scripts\python.exe scripts\run_eval.py

# 평균 산출 — [B-3] after_phase_b3_e2e.json 형식 거울로 별도 스크립트 또는 수동 집계
# 평균 파일: eval/after_phase_b4a.json
```

**비교 baseline**: `eval/after_phase_b3_e2e.json` (2회 평균). [B-3] 대비 회귀 없는지 확인 (게이트는 [B-4b] 자리지만, [B-4a]가 측정 코드만 손이라 본 라벨링 결과는 [B-3]과 같아야 정상).

---

## 게이트 — [B-4a]는 측정 코드만 손이라 별도 게이트 없음

다음 두 조건만 확인:
1. **본 e2e 라벨링 무회귀**: precision·recall·accuracy·plant_korean·FP·json 5메트릭이 [B-3] 2회 평균과 ±2%p 이내 (run-to-run noise 허용). 회귀가 크면 측정 코드 버그.
2. **신규 키 박힘 확인**: per_case 33건 모두 `observed_symptoms`·`top_3_rag` 채워짐. `fp_analysis` 섹션 모든 키 채워짐.

본 [B-4] 게이트(FP 17→12 이하)는 [B-4b]의 자리.

---

## 보고 형식

작업 완료 후 다음을 명확히 박아 보고:

### 1. 사전 확인 결과
- git status·git log
- **retrieve_node 출력 state 키 확인 결과** (경우 1·2·3 중 어느 것 선택했는지 + 근거)
- pytest 결과
- eval_retrieval.py 함수 재사용 가능 여부

### 2. 변경 파일·라인 수
- `scripts/run_eval.py`: +N -0 (read-only 추가만)
- 헬퍼 함수 목록

### 3. 검증 결과
- 4개 검증 단계 결과
- dry-run 1~2장 신규 키 dump

### 4. 측정 결과 (2회 평균)
- 5메트릭 (precision·recall·accuracy·plant_korean·FP·json) — [B-3] 대비 변화 (회귀 없어야 정상)
- 평균 파일 경로 + run1·run2 파일 경로

### 5. **FP 17건 분포 분석 (본 [B-4a]의 핵심 산출물)**

**§5-1. FP status 분해 표**:
| status | 건수 | 비율 |
|---|---|---|
| 병해 의심 | ? | ? |
| 영양 부족 | ? | ? |
| 과습 | ? | ? |
| 건조 | ? | ? |

**§5-2. FP observed_symptoms 빈/비빈 분해 표**:
| observed_symptoms | FP 건수 | 시나리오 매핑 |
|---|---|---|
| empty (비어 있음) | ? | 시나리오 ② (generate가 visual_description/RAG로 끌어냄) |
| non_empty (1개 이상) | ? | 시나리오 ① (analyze over-report) 또는 혼합 |

**§5-3. FP top_3 problem_type 다수결 분해 표**:
| 다수결 problem_type | FP 건수 | 의미 |
|---|---|---|
| disease | ? | retrieval이 병해 카드를 우세로 가져오는데 generate가 그대로 따름 |
| abiotic | ? | retrieval이 환경 카드 우세인데도 generate가 무시하고 병해/영양 판정 — 핵심 본질 |
| nutrient | ? | retrieval이 영양 카드 우세 — generate "영양 부족" 정당화 자리 |
| env | ? | retrieval이 환경(빛·온도) 카드 우세 |
| pest | ? | retrieval이 해충 카드 우세 |
| tie | ? | 동률 |

**§5-4. FP 17건 전수 dump 표**:
| image_id | gt_plant | pred_status | observed_symptoms | top_3 problem_types |
|---|---|---|---|---|
| ... | ... | ... | [...] | [..., ..., ...] |

### 6. **시나리오 판정 — [B-4b] 본 작업 방향 권장**

§5-2와 §5-3 데이터로 다음 셋 중 하나 박기:

- **시나리오 ① 우세** (empty FP < 5건, non_empty FP > 12건): analyze observed_symptoms over-report가 본질. [B-4b]는 analyze 프롬프트 재손([1-3] v5). 다만 [1-3] v4 실패의 거울이라 신중.
- **시나리오 ② 우세** (empty FP > 12건, non_empty FP < 5건): generate가 visual_description/RAG로 끌어내는 경로가 본질. [B-4b]는 generate 프롬프트 재손 — 결정 영역 3(RAG problem_type 메타 활용) + 결정 영역 5(plant_confidence='low' 활용 강화) 중심.
- **혼합 시나리오** (둘 다 5건 이상): analyze + generate 둘 다 손 자리. [B-4b]를 다시 분리할지 사용자 결정.

§5-3 추가 신호:
- abiotic/env/nutrient 다수결 FP가 많으면 → RAG는 정답 타입을 가져오는데 generate가 무시 → 결정 영역 3(problem_type 메타 활용) 본질 직격
- disease 다수결 FP가 많으면 → RAG도 병해 쪽이라 카드 문제 → 단계 B'(농진청 종 메타) 또는 카드 추가 자리

### 7. 위험·미해결
- 측정 비용 (33장 × 2회 ≈ 1단계 e2e와 동일 수준)
- analyze 비결정성 (1단계 7건 비결정 발견됨) — 2회 평균이 본질 흐릴 가능성. 보고에 언급
- 그래프 본체 변경이 필요한 상황 발견 시 (경우 3) 사용자 보고 후 결정 — 자동 진행 금지
- eval_retrieval.py 함수 재사용 시 import 경로 — `scripts/eval_retrieval.py` → `scripts/run_eval.py` 동일 디렉토리라 `from eval_retrieval import _retrieve_top_n` 또는 `sys.path` 처리. 표준 패턴 따르기.

---

## 커밋 — 작업 완료 후 사용자 검토 대기

게이트 통과해도 **사용자 검토 → 커밋 → push** 순서. 자동 커밋·push 금지.

권장 커밋 메시지:
```
feat: [B-4a] FP 17건 본질 진단 측정 (observed_symptoms + top_3 problem_type 박기)
```

신규 파일: `eval/after_phase_b4a_run1.json`, `after_phase_b4a_run2.json`, `after_phase_b4a.json`  
수정 파일: `scripts/run_eval.py`

---

## 작업 완료 후 즉시 진행 금지

[B-4b] 본 작업은 [B-4a] 보고의 §6 시나리오 판정 결과를 사용자가 검토한 뒤 별도 작업 프롬프트로 박는다. **자동으로 [B-4b] 진행 금지**.
