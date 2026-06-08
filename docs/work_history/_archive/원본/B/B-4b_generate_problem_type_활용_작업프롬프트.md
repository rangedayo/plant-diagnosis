# [B-4b] generate problem_type 메타 활용 + "건강" 회복 — Claude Code 작업 프롬프트

> 목적: [B-4a]에서 데이터로 정밀화된 FP 본질 직격. **"generate가 RAG의 problem_type 분포를 무시하고 '병해 의심'으로 기본 escalate"** 기전을 (1) problem_type 분포를 generate에 노출 + (2) cosmetic abiotic 패턴에 "건강" 회복 가이드 + (3) plant_confidence='low' 보수성 강화로 해소.
>
> 사전 진단: 본 대화 inline. 사용자 8개 결정 영역 전체 동의 (C-B-A-A-A-B-고정-C).
>
> 단계: [B-4b] (B-4 워크플로우 옵션 C — 진단 측정 / 본 작업 2단 분리, 본 작업)
> 선행: [B-4a] 완료 (FP 17/17 "병해 의심", empty=0, top_3 problem_type abiotic/env/general 우세 14/17, disease 우세 2~3건)
> 후행: 잔존 FP 측정 후 [B-4c]([1-3] v5 analyze 임계) 또는 단계 B'(농진청 종 메타) 결정

---

## 확정된 결정 (변경 금지)

1. **변경 범위**: 3개 파일
   - `app/graph.py` — retrieve_node 메타 노출 + generate_node의 context_summary 재조립 + 가중 다수결 헬퍼 인라인
   - `app/prompts.py` — STRUCTURED_DIAGNOSIS_JSON_SYSTEM 가이드 재설계
   - `app/model_utils.py` — 무변경 (가중 다수결은 graph.py 내 인라인)
   
2. **결정 영역 채택 (사용자 확정 전체)**:
   - **1C**: problem_type을 context_summary 평문 + 카드 본문 prefix 둘 다 노출
   - **2B**: 강한 가이드 — top_3 가중 다수결이 abiotic/env면 "병해 의심" 선택 금지
   - **3A**: 가중 sim 다수결 (sim 값으로 가중)
   - **4A**: enum 그대로 유지 + "non-cosmetic 증상 1개 이상이면 건강 금지"로 룰 좁히기 → cosmetic 패턴이고 RAG abiotic 우세면 "건강" 허용
   - **5A**: plant_confidence='low' + cosmetic + abiotic 우세 → "건강" 우선
   - **6B**: analyze 무변경 ([1-3] v4 실패 거울, 후순위)
   - **7**: 게이트 — FP 17→12 이하 + recall ≥ 60% + 회귀 5%p 이내
   - **8C**: prompts + graph만 (model_utils 무변경)

3. **측정 2회 평균** ([B-3]·[B-4a] 패턴): run1·run2 + 평균 파일 3개. `fp_analysis` 섹션 [B-4a]와 동일 형식으로 자동 출력 ([B-4a] run_eval.py 보강분 그대로 활용).

4. **frontend 무변경**: status enum 5개 유지(`건강·과습·건조·병해 의심·영양 부족`) → `types/diagnosis.ts`·`ResultView` 손대지 마라.

5. **단일 atomic 커밋** (1단계·[B-2]·[B-3]·[B-4a] 패턴).

---

## 사전 확인 — 작업 시작 전 모두 실행

각 항목 결과를 보고에 명시.

### A. 현재 코드·환경 상태
```bash
git status
# 기대: clean (B-4a 커밋·푸시 후)

git log -1 --oneline
# 기대: [B-4a] FP 17건 본질 진단 측정 커밋
```

### B. retrieve_node 현재 출력 키 (메타 노출 자리 확인)

```bash
grep -n "def retrieve_node\|state\[\|return {" app/graph.py
```

확인할 것:
1. retrieve_node가 현재 state에 무엇을 박는가 (`rag_docs`·`rag_failed`·`rag_no_docs`·`rag_weak_evidence`·`rag_query` 등)
2. `_chroma_query_sync` → `_triples_from_chroma` → `_merge_rag_triples` 흐름에서 metas·sims가 함수 안에 있는가, state로 흘러나오는가
3. **새로 박을 키**: `rag_metas`(list[dict])·`rag_sims`(list[float])·`top_3_problem_type_weighted`(dict) — 명명은 클로드 코드 재량, 일관성만 유지

### C. 현재 STRUCTURED_DIAGNOSIS_JSON_SYSTEM 읽기

```bash
grep -n "STRUCTURED_DIAGNOSIS_JSON_SYSTEM" app/prompts.py
# view로 본문 전체 읽고 보고에 명시
```

확인할 것 (각각 라인 번호 박기):
1. "관찰된 증상이 1개 이상 보고되면 status='건강'을 선택하지 마세요" 줄 — **수정 대상** (결정 4A)
2. "검색된 참고 자료(RAG)는 cause·current_state 작성을 위한 보조 정보일 뿐입니다. status는 관찰된 증상이 결정합니다" 줄 — **수정 대상** (결정 2B)
3. plant_confidence='low' 활용 가이드 — **강화 대상** (결정 5A)
4. 다른 status 결정 관련 가이드 (충돌 점검)

### D. 기존 테스트 동작 확인
```bash
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 23 passed (현재 상태)
```

---

## 작업 묶음

### 1. `app/graph.py` — retrieve_node 메타 노출 + 가중 다수결 + generate_node context_summary 재조립

#### 1-1. retrieve_node 메타 노출

`_merge_rag_triples` 결과(docs·metas·raw_sims·merge_sims) 중 **metas와 raw_sims를 state에 박기**. 현재 docs(텍스트)만 흘려보내고 메타는 함수 내 변수로 소멸 — 이 자리가 [B-4a]에서 별도 retrieve 재호출이 필요했던 이유.

```python
# Before (예시 — 정확 라인은 view 후 확정)
async def retrieve_node(state: DiagnosisState) -> dict:
    ...
    docs, metas, raw_sims, _ = _merge_rag_triples(...)
    return {
        "rag_docs": docs,
        "rag_failed": ...,
        "rag_no_docs": ...,
        "rag_weak_evidence": ...,
    }

# After — metas·sims 박기 + 가중 다수결 계산
async def retrieve_node(state: DiagnosisState) -> dict:
    ...
    docs, metas, raw_sims, _ = _merge_rag_triples(...)
    
    # [B-4b] problem_type 가중 다수결 (top_3, sim 가중)
    top_3_pt_weighted = _weighted_problem_type_majority(metas[:3], raw_sims[:3])
    
    # [B-4b] 카드 본문에 [problem_type] prefix 박기 (결정 1C)
    docs_tagged = [
        _tag_doc_with_problem_type(doc, meta)
        for doc, meta in zip(docs, metas)
    ]
    
    return {
        "rag_docs": docs_tagged,            # prefix 박힌 텍스트
        "rag_metas": list(metas or []),     # 신규
        "rag_sims": list(raw_sims or []),   # 신규
        "top_3_problem_type_weighted": top_3_pt_weighted,  # 신규 — generate가 활용
        "rag_failed": ...,
        "rag_no_docs": ...,
        "rag_weak_evidence": ...,
    }
```

#### 1-2. 가중 다수결 헬퍼 (인라인, graph.py 내)

```python
def _weighted_problem_type_majority(
    metas: list[dict], sims: list[float]
) -> dict:
    """top_N의 problem_type을 sim으로 가중합 다수결.
    
    Returns:
        {
            "majority": "abiotic" | "disease" | "nutrient" | "env" | "pest" | "general" | "tie",
            "distribution": {"abiotic": 0.42, "disease": 0.18, ...},  # 가중합 정규화
            "top_problem_type": "abiotic" | "" (top_1의 problem_type),
        }
    """
    weights: dict[str, float] = {}
    for meta, sim in zip(metas or [], sims or []):
        pt = str((meta or {}).get("problem_type") or "").strip()
        if not pt:
            continue
        weights[pt] = weights.get(pt, 0.0) + max(float(sim), 0.0)
    
    if not weights:
        return {"majority": "tie", "distribution": {}, "top_problem_type": ""}
    
    total = sum(weights.values()) or 1.0
    distribution = {k: round(v / total, 4) for k, v in weights.items()}
    
    # 다수결 — 1위와 2위의 가중합 차이가 5% 미만이면 tie
    sorted_weights = sorted(weights.items(), key=lambda x: -x[1])
    if len(sorted_weights) == 1:
        majority = sorted_weights[0][0]
    elif sorted_weights[0][1] - sorted_weights[1][1] < 0.05 * total:
        majority = "tie"
    else:
        majority = sorted_weights[0][0]
    
    top_pt = str((metas[0] or {}).get("problem_type") or "") if metas else ""
    return {
        "majority": majority,
        "distribution": distribution,
        "top_problem_type": top_pt,
    }


def _tag_doc_with_problem_type(doc: str, meta: dict | None) -> str:
    """카드 본문에 [problem_type] prefix 박기 (결정 1C)."""
    pt = str((meta or {}).get("problem_type") or "").strip()
    if not pt:
        return doc
    if doc.startswith(f"[{pt}]"):
        return doc  # 중복 방지
    return f"[{pt}] {doc}"
```

#### 1-3. generate_node의 context_summary 재조립

```python
# Before (현재 — 봤음)
context_summary = (
    f"묘사:\n{visual_description}\n\n"
    f"[관찰 정보]\n"
    f"- 식물명(학명 1위): {plant_name}\n"
    f"- 식물명(통명): {plant_name_korean}\n"
    f"- 식별 신뢰도: {plant_confidence}\n"
    f"- 대안 후보: {alt_str}\n"
    f"- 관찰된 증상: {symptoms_str}\n"
)

# After — RAG problem_type 분포 박기 (결정 1C)
top_3_pt = state.get("top_3_problem_type_weighted") or {}
majority = str(top_3_pt.get("majority") or "tie")
dist = top_3_pt.get("distribution") or {}
top_pt = str(top_3_pt.get("top_problem_type") or "")

dist_str = ", ".join(f"{k} {v:.2f}" for k, v in sorted(dist.items(), key=lambda x: -x[1])) or "없음"

context_summary = (
    f"묘사:\n{visual_description}\n\n"
    f"[관찰 정보]\n"
    f"- 식물명(학명 1위): {plant_name}\n"
    f"- 식물명(통명): {plant_name_korean}\n"
    f"- 식별 신뢰도: {plant_confidence}\n"
    f"- 대안 후보: {alt_str}\n"
    f"- 관찰된 증상: {symptoms_str}\n\n"
    f"[검색된 자료의 타입 분포 (top_3 sim 가중)]\n"
    f"- 우세 타입: {majority}\n"
    f"- 1위 카드 타입: {top_pt}\n"
    f"- 분포: {dist_str}\n"
)
```

`rag_chunks`는 그대로 사용 — 단 retrieve_node 1-1에서 docs에 이미 `[problem_type]` prefix 박혀있어 자연스럽게 노출됨.

### 2. `app/prompts.py` — STRUCTURED_DIAGNOSIS_JSON_SYSTEM 가이드 재설계

기존 줄을 다음 방향으로 갱신. **의미·강도는 박힌 대로**, 표현 자연스럽게 다듬는 건 OK.

#### 2-1. (결정 4A) "1개 이상이면 건강 금지" 룰 좁히기

**기존 줄** (현재 박혀 있음):
> "관찰된 증상이 1개 이상 보고되면 status='건강'을 선택하지 마세요. 증상 양상에 따라 '병해 의심'·'과습'·'건조'·'영양 부족' 중 가장 적절한 것을 선택하세요."

**변경 후**:
> "관찰된 증상이 1개 이상 보고되면 원칙적으로 status='건강'을 선택하지 마세요. **단, 다음 두 조건을 모두 만족하면 예외적으로 'status=건강'을 선택할 수 있습니다**: (1) 보고된 증상이 모두 cosmetic 패턴(잎끝·잎 가장자리에 국한된 경미한 갈변, 단일 잎의 국소 변색, 좌우 대칭 무늬 등 종 고유 특성·자연 노화로 보이는 범위)이고, (2) 검색된 자료의 우세 타입이 'abiotic' 또는 'env' 또는 'general'이며 'disease'가 아닐 때. 두 조건 중 하나라도 어긋나면 '건강' 선택 금지."

#### 2-2. (결정 2B) RAG 위계 — 강한 가이드

**기존 줄**:
> "검색된 참고 자료(RAG)는 cause·current_state 작성을 위한 보조 정보일 뿐입니다. status는 관찰된 증상이 결정합니다."

**변경 후 (강한 가이드, "병해 의심" 금지 추가)**:
> "검색된 참고 자료(RAG)의 타입 분포(우세 타입)는 status 결정의 핵심 신호입니다. **우세 타입이 'abiotic'·'env'·'nutrient'이면 status='병해 의심' 선택 금지** — 증상이 어떻게 보고되었든 우세 타입에 부합하는 status('과습'·'건조'·'영양 부족') 또는 cosmetic 예외 시 '건강'을 선택하세요. 우세 타입이 'disease'이거나 'pest'일 때만 'status=병해 의심' 진입이 정당합니다. 우세 타입이 'tie'·'general'이면 관찰된 증상의 명확성에 따라 보수적으로 판단하세요."

#### 2-3. (결정 5A) plant_confidence='low' 활용 강화

**기존 줄**:
> "식별 신뢰도(plant_confidence)가 'low'이면 cause·action_plan에서 종 단정을 피하고 일반적 환경 점검 톤으로 작성하세요."

**변경 후 — status 결정 영역도 포함**:
> "식별 신뢰도(plant_confidence)가 'low'이면 종 식별이 흔들리는 상태로, 종 고유 무늬·자연 변이가 증상으로 잘못 보고되었을 가능성이 있습니다. cause·action_plan에서 종 단정을 피하고 일반적 환경 점검 톤으로 작성하세요. **plant_confidence='low' + 보고 증상이 cosmetic 패턴 + RAG 우세 타입이 abiotic/env/general이면 'status=건강'을 우선 고려**하세요."

#### 2-4. 충돌 가이드 정리

위 변경 후 기존 가이드와 의미 중복·충돌 발생하면:
- 영양 부족 진입 조건 줄 — 유지 ([1-7.5] 강한 가이드 본질 그대로)
- "관찰된 증상이 비어 있으면 반드시 '건강'" 줄 — 유지
- "묘사에 변색·반점 언급되어도 그것만으로는 status 결정 금지" 줄 — 유지
- "경미·국소 변색만으로는 '영양 부족'·'병해 의심' 단정 금지" 줄 — 위 2-1 변경과 의미 중첩 → 통합하거나 위 2-1로 흡수

순서 — 신규/강화된 5개 가이드를 "규칙:" 섹션 내에서 논리적 순서로:
1. status 결정 일반 원칙 (관찰된 증상이 근거, 묘사·RAG는 보조)
2. observed_symptoms 비어 있음 → 반드시 "건강"
3. observed_symptoms 1개 이상 → 원칙 "건강" 금지, 예외 조건 (2-1)
4. RAG 우세 타입과 status 매핑 (2-2)
5. plant_confidence='low' 활용 (2-3)
6. 영양 부족 진입 조건 (기존 유지)
7. cosmetic 패턴·종 고유 무늬 판단 가이드

### 3. cosmetic 패턴 정의 — 프롬프트에 명시

generate가 "cosmetic 패턴"을 알 수 있도록 명시적 정의 박기 (1단계 [1-3] v4 부위·대칭성·진행 3축의 generate 측 거울):

> "**cosmetic 패턴이란**: (1) 부위 기반 — 잎의 가장자리·끝에 국한된 경미한 변색, 잎 면 중앙은 정상. (2) 범위 기반 — 단일 잎 또는 소수의 잎에만 국한, 여러 잎으로 확산되지 않음. (3) 대칭성 기반 — 좌우·축 대칭으로 균일한 무늬·줄무늬는 종 고유 패턴 가능성. (4) 자연 노화 — 식물 아래쪽 오래된 잎에만 국한된 변색은 자연 범위. 이 중 어느 하나에 해당하면 cosmetic 신호로 봅니다. **반대로**: 비대칭·확산·잎 중앙부 변색·여러 잎 동시 진행은 cosmetic이 아닌 병변 신호."

---

## 제약

- **변경 가능 파일**: `app/graph.py`, `app/prompts.py` 단 두 개
- **절대 수정 금지**:
  - `app/model_utils.py` (가중 다수결은 graph.py 인라인)
  - `app/vision/*`, `app/nodes/*`, `app/schemas.py`, `app/main.py`
  - `app/prompts.py`의 `ANALYZE_SYSTEM`·`ENGLISH_KEYWORD_*`·`STRUCTURED_DIAGNOSIS_JSON_USER_TEMPLATE`·`STRUCTURED_DIAGNOSIS_NO_RAG_DOCS_BLOCK` 상수 (STRUCTURED_DIAGNOSIS_JSON_SYSTEM 하나만 수정)
  - `tests/*`, `scripts/*` (run_eval.py 포함 — [B-4a] 보강분 그대로 활용)
  - `types/diagnosis.ts`, `components/ResultView.tsx` (status enum 무변경)
  - `.env`, README, `data/vector_db/*`
- **status enum 무변경**: 5개 유지
- **frontend 무변경**: 본 작업의 본 본질이 백엔드 generate 본체. 프론트 파급 없도록.
- 파일 인코딩 BOM 없는 UTF-8. Python 3.12 호환.

---

## 검증 — 측정 전 단계별 확인

```bash
# 1. import·문법 확인
.venv\Scripts\python.exe -c "from app.graph import build_diagnosis_graph; print('ok')"
.venv\Scripts\python.exe -c "from app.prompts import STRUCTURED_DIAGNOSIS_JSON_SYSTEM; print(len(STRUCTURED_DIAGNOSIS_JSON_SYSTEM))"
# 기대: 'ok' + 정수 (기존 길이 +300~500자 예상)

# 2. 단위 테스트 (영향 없어야)
.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"
# 기대: 23 passed

# 3. graph 빌드 확인
.venv\Scripts\python.exe -c "from app.main import app; print('ok')"
# 기대: 'ok'

# 4. dry-run 1~2장 — 신규 state 키 + prefix 박힌 docs + context_summary 분포 박힘 확인
# (run_eval.py에 --limit 옵션 활용)
```

4개 통과 후 본 측정.

---

## 측정 — 2회 측정 평균 ([B-3]·[B-4a] 패턴)

```bash
# 1회차
$env:RUN_EVAL_OUT="eval/after_phase_b4b_run1.json"
.venv\Scripts\python.exe scripts\run_eval.py

# 2회차
$env:RUN_EVAL_OUT="eval/after_phase_b4b_run2.json"
.venv\Scripts\python.exe scripts\run_eval.py

# 평균 — eval/after_phase_b4b.json (B-3·B-4a 형식 거울)
```

**비교 baseline**: `eval/after_phase_b3_e2e.json` (2회 평균) + `eval/after_phase_b4a.json` (2회 평균, FP 본질 데이터)

**중요**: [B-4a] run_eval.py 보강분에 `fp_analysis` 섹션 자동 출력 — [B-4b] 측정 결과에도 동일 형식으로 박힘. [B-4a] vs [B-4b] 직접 비교 가능.

---

## 게이트

**2회 평균 기준**:
- **FP 17 → 12 이하** (절대 수치 — 본 [B-4]의 본 게이트)
- **recall ≥ 60%** (절대 임계 — 진짜 아픈 식물 놓치면 안 됨)
- **회귀 5%p 이내** (plant_korean·accuracy·json·latency)
- **fp_status_distribution 변화**: "병해 의심" 17 → 10 이하 + "건강" 회복분 + (선택) 다른 enum으로 정상 분산

회복(precision 35%+ 또는 accuracy 55%+)은 보너스. 게이트 판정에 안 씀.

**게이트 실패 시**:
- recall <60% → 즉시 revert. cosmetic 예외 조건이 너무 관대해서 진짜 병해를 놓침.
- FP > 12 → revert 하지 말고 §보고에 잔존 FP 분석 + [B-4c] 또는 단계 B' 결정 자리로.

---

## 보고 형식

### 1. 사전 확인 결과
- git status·git log
- retrieve_node 현재 출력 키 dump + 신규 박을 키 명세
- 현재 STRUCTURED_DIAGNOSIS_JSON_SYSTEM 라인 번호 (1·2·3번 줄 위치)
- pytest 결과

### 2. 변경 파일·라인
- `app/graph.py`: +N -M
- `app/prompts.py`: +N -M
- 신규 헬퍼 목록 (`_weighted_problem_type_majority`, `_tag_doc_with_problem_type`)

### 3. 검증 결과
- 4개 단계 결과
- dry-run 1~2장 신규 키 dump + context_summary 분포 박힘 확인

### 4. 측정 결과 (2회 평균)

| 메트릭 | run1 | run2 | 평균 | B-3 | Δpp |
|---|---|---|---|---|---|
| plant_korean | ? | ? | ? | 0.8833 | ? |
| precision | ? | ? | ? | 0.2273 | ? |
| recall | ? | ? | ? | 1.0 | ? |
| accuracy | ? | ? | ? | 0.4848 | ? |
| FP | ? | ? | ? | 17 | ? |
| json | ? | ? | ? | 1.0 | ? |

게이트 판정 — 박기.

### 5. fp_analysis 변화 ([B-4a] vs [B-4b])

[B-4a]에서 박힌 동일 형식으로 자동 출력. 핵심 변화:

| 항목 | B-4a | B-4b | 변화 |
|---|---|---|---|
| FP 총건수 | 17.5 | ? | ? |
| status: 병해 의심 | 17 | ? | ? |
| status: 건강 (FP 자체에 없지만 회복분으로) | — | — | — |
| observed_symptoms empty | 0 | ? | (예상: 변동 미미, analyze 무변경) |
| top_3 다수결 abiotic 우세 FP | 1 | ? | (예상: 감소 — 그쪽이 "건강"으로 회복) |
| top_3 다수결 disease 우세 FP | 2~3 | ? | (예상: 잔존) |
| top_3 다수결 tie | 11~12 | ? | (예상: 가중 다수결로 감소) |

### 6. 잔존 FP 분석 (게이트 통과 여부와 무관 박기)

FP 7~12건 잔존 예상. 다음 분해:
- status별 분해
- top_3 problem_type별 분해 — 어느 problem_type이 잔존 FP 우세인가
- observed_symptoms 패턴별 분해

→ [B-4c] 또는 단계 B' 방향 신호.

### 7. 위험·미해결
- analyze 비결정성 ([1단계 7건] + [B-4a] FP 17↔18) — 2회 평균 본질
- cosmetic 패턴 정의가 모델 자율 해석 자리 — 보수성·관대성 어느 쪽으로도 흔들릴 가능성. dry-run에서 1~2건 직접 확인 권장
- 가중 다수결 tie 임계(5%)가 적절한가 — 잔존 FP 분석에서 신호 보고
- frontend 무변경 확인 (status enum 5개 유지)

---

## 커밋 — 작업 완료 후 사용자 검토 대기

게이트 통과해도 **사용자 검토 → 커밋 → push** 순서. 자동 커밋·push 금지.

권장 커밋 메시지:
```
feat: [B-4b] generate에 RAG problem_type 가중 다수결 + cosmetic "건강" 회복 가이드
```

수정 파일: `app/graph.py`, `app/prompts.py`  
신규 파일: `eval/after_phase_b4b_run1.json`, `after_phase_b4b_run2.json`, `after_phase_b4b.json`

---

## 작업 완료 후 즉시 진행 금지

[B-4c] 또는 단계 B'는 [B-4b] 보고의 §6 잔존 FP 분석 결과를 사용자가 검토한 뒤 별도 작업 프롬프트로 박는다. **자동으로 다음 단계 진행 금지**.
