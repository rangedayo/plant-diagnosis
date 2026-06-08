# [ACC-R10] analyze 4축 변별 추출 + generate 황화 충돌 룰

> **목적**: R9 진단(병목 = analyze 상류 정보 손실 확정)과 외부 검토 보강에 따라, ① `analyze`가 황화·마름을 **4개 변별 축**(시작 부위·분포·질감·동반 신호)으로 추출하게 하고, ② `generate`에 **황화 충돌 분기 룰**을 추가한다. analyze가 변별 정보를 만들고(a), generate가 그 정보로 건조/영양/과습/병해를 가르도록(c) **두 변경을 함께** 적용한다 — a 없는 c는 무용, c 없는 a는 RAG prior에 끌려가므로.
>
> **성격**: 코드 수정 라운드 (`app/prompts.py` 두 블록). 측정 게이트 있음. 실측정은 R11(사용자 PowerShell).
>
> **선행**: R9 진단(`docs` 커밋) + 외부 검토. **후행**: R11 사용자 측정 → 남는 오류에서 RAG 점검(R12 후보).

---

## 1. 확정 배경 (R9 진단 + 외부 검토 5보강)

### 1-1. R9 진단 결론

- 병목 = **analyze 상류 정보 손실**(주원인 a). `observed_symptoms` 추출 지시(prompts.py L25-28)가 "간결한 명사구"만 요구 → 황화 양상·질감을 누락 → generate가 건조/영양 구별 불가.
- generate prior(b)는 약함 — "아래잎 황화"는 질소결핍 교과서 신호이기도 해, 빈약한 텍스트에 대한 합리적 추론이었음.
- 트리거 황화 겹침(c)은 보조 — 충돌 우선순위·prior 방어 룰 부재(L77-79).

### 1-2. 외부 검토 보강 (이번 라운드 반영)

1. **변별자는 질감 하나가 아니라 4축** — 시작 부위 / 분포 / 질감 / 동반 신호(병반 형태 포함).
2. **추정 금지 제약** — 촉감·토양 수분은 사진으로 불명확 → "시각적으로 판단 가능한 경우만". (§9 데이터 범위 원칙 정합)
3. **a + c 동반** — analyze만 고치면 RAG가 nutrient/disease 카드를 끌어와 generate를 밀 수 있음 → 충돌 룰 같이 필요.
4. **RAG는 측정 후** — top_3_problem_type_weighted가 generate에 노출돼 강한 보조 신호임이 확인됨(haengun_003 nutrient 0.872, haengun_005 disease 0.873). 단 지금 RAG 랭킹을 바꾸면 원인 분리 불가 → R11 측정 후 점검.
5. **검증 보조 — 텍스트 선확인** — 건조 6건 새 `observed_symptoms`에 변별 단서가 실제로 들어왔는지 먼저 확인(analyze가 먹혔는지). 안 들어왔으면 status 안 변해도 당연.

---

## 2. 작업

### Step 0 — read-only 선결 게이트 (불일치 시 중단·질의)

1. `git status` clean (R9 진단 커밋 후 전제). R8 결과 `eval/after_acc_r7_dry_guard.json` 존재 확인 (R11 비교 앵커).
2. **`ANALYZE_SYSTEM`(prompts.py:9 근방)의 `observed_symptoms` 설명(L25-28) 원문** 인용. `visual_description`(L22-24)과 분리돼 있음을 재확인.
3. **`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`(prompts.py:57 근방)의 status 결정 룰(L73-79)** 원문 인용. 영양 부족(L77)·건조(L78) 트리거 현재 문구.
4. `ALLOWED_STRUCT_STATUS` enum 원문 — status 문자열 일치 확인.

### Step 1 — analyze: 4축 변별 추출 + 추정 금지

`ANALYZE_SYSTEM`의 `observed_symptoms` 추출 지시(L25-28)를 보강. **`visual_description`은 건드리지 마라** (status 채널이 아님).

추가 방향 — 황화·갈변·마름이 보이면 **가능한 경우** 다음 4축을 함께 명사구에 담게:

- **시작 부위**: 잎끝 / 가장자리 / 아래(오래된)잎 / 잎맥 사이 / 잎 중앙
- **분포**: 단일 잎 / 여러 잎 / 균일 / 불규칙 / 국소 / 확산
- **질감·조직감**: 바삭한 마름 / 종이처럼 마른 / 물기 있는 무름 / 축 처짐
- **동반 신호**: 잎 말림·주름 / 고사 / 반점·괴사 / 줄기 밑동 이상

⚠ **추정 금지 (필수)**: "사진에서 시각적으로 확인 가능한 경우에만 적고, 확인되지 않는 촉감·토양 수분은 추정하지 말라"는 제약을 **반드시 함께** 명시. (§9 정합 — 가짜 정보 금지)

제약:
- 정량값·가짜 숫자 금지(§9). 정성 서술만.
- **over-fitting 금지**: 행운목 문자열("아래잎 황화 및 고사")만 겨냥한 문구 금지. 일반 속성 조합으로.
- 예시 문구는 일반형으로: "아래잎 황화·고사와 잎끝 바삭한 마름", "잎맥 사이 황화(잎맥 녹색 유지)", "물기 있는 무름 동반 처짐" 등.

### Step 2 — generate: 황화 충돌 분기 룰 (a 동반)

`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`의 status 결정 룰(L73-79 근방)에 황화 충돌 분기를 추가:

- **황화가 단독으로만 있으면 영양 부족으로 단정하지 말 것** (prior 방어).
- **마름·바삭함·잎끝/가장자리 시작·고사 동반 황화 → 건조 우선**
- **균일한 황화·잎맥 사이 황화·잎맥 녹색 유지 → 영양 부족 우선**
- **물기 있는 무름·줄기 밑동 무름·수침상 → 과습 우선**
- **불규칙 반점·잎 중앙부 괴사·확산성 병반 → 병해 의심**

⚠ 이 룰은 **"건조를 억지로 늘리는 룰"이 아니라 "황화 충돌 시 관찰 속성 기반 분기 룰"**이어야 한다. analyze가 변별 속성을 주지 않으면(빈약 텍스트) 기존대로 합리적 추론에 맡긴다 — 없는 단서를 지어내 건조로 보내면 안 됨.

status 문자열은 `ALLOWED_STRUCT_STATUS` enum과 정확히 일치.

### Step 3 — 검증 (합성·코드 sanity, Gemini 호출 금지)

⚠ **eval 풀런·Gemini 실호출 금지.** analyze 실제 추출 변화는 비전 호출이 필요하므로 **R11 측정에서** 확인. 여기선 문법·구조 + generate 충돌 룰만 합성 검증.

1. **import·문법**: `.venv\Scripts\python.exe -c "from app.main import app; print('ok')"`
2. **enum 일치**: 두 프롬프트의 status 문자열이 `ALLOWED_STRUCT_STATUS`와 일치.
3. **generate 충돌 룰 합성 단위 테스트** (가짜 observed_symptoms dict 주입, Gemini 불필요):
   - 마름·바삭 동반 황화 → **건조** ✓
   - 균일 황화·잎맥 사이 → **영양 부족** ✓
   - 물기 무름·줄기밑동 → **과습** ✓
   - 불규칙 반점·중앙 괴사 → **병해 의심** ✓
   - **황화 단독(변별 단서 없음) → 영양 부족 단정 안 함**(기존 합리 추론 유지, 건조로 억지 분류 안 함) ✓
   - 🔴 **경미한 잎끝 갈변만(건강 케이스) → 건강 유지**(건조로 끌어올리지 않음) ✓ — 건강→건조 FP 방지
   - 🔴 **심한 비건강 → 건강으로 안 감**(recall 사수) ✓
4. **pytest 회귀**: `.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"` — 모두 passed.

### Step 4 — atomic 커밋 (푸시 보류)

1. `feat(prompt): analyze observed_symptoms 4축 변별 추출 + 추정 금지 제약` — ANALYZE_SYSTEM
2. `feat(prompt): generate 황화 충돌 분기 룰 (마름→건조·균일→영양·무름→과습)` — STRUCTURED_DIAGNOSIS_JSON_SYSTEM
3. `docs(work_history): ACC-R10 프롬프트 보존` — 본 .md 복사

푸시는 사용자 검토 후.

### Step 5 — R11 측정 안내 (사용자 PowerShell)

⚠ **`RUN_EVAL_OUT` 반드시 먼저 설정** (baseline.json 덮어쓰기 재발 방지):

```powershell
$env:RUN_EVAL_OUT="after_acc_r10_analyze_generate.json"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

- 비교 앵커: `eval/after_acc_r7_dry_guard.json` (R8)
- **1차 검증 (텍스트 선확인)**: 건조 6건의 새 `observed_symptoms`에 "마름/바삭/잎끝·가장자리/무름 없음/잎맥 사이" 같은 **변별 단서가 실제로 들어왔는지** 먼저 확인. → analyze 보강이 먹혔는지. 안 들어왔으면 status 안 변해도 당연 (analyze 프롬프트 추가 보강 필요).
- **2차 감시 (status 변화)**:
  1. **건조 발화 > 0** — status_distribution에 건조 등장 + 혼동표 true 건조 행 pred 건조 칸 ≥ 1 (R8은 0)
  2. 🔴 **recall 100% / FN 0 사수** — 깨지면 즉시 revert
  3. **FP ≤ 8** (1차 목표), 허용선 10 (현 R8 = 8)
  4. **병해 의심 ≤ 12** — analyze가 풍부해지며 병반 단어 늘면 재증가 가능, 감시
  5. **건강 행 pred 건조 = 0** — 잎끝 갈변만 있는 건강 케이스가 건조로 이동하면 위험 신호
- **RAG 점검은 R12로** — 위 측정 후, 건조가 여전히 영양/병해로 가고 해당 케이스 RAG 1위가 nutrient/disease면 검색어·카드 타입 점검 (지금은 손대지 않음).

---

## 3. 게이트

- 🔴 **recall 100% / FN 0** — 절대 사수. 못 지키면 즉시 revert.
- **건조 발화 > 0** (R8은 0) — R10 1차 목표.
- **FP ≤ 8 (허용 10)** — 증상 풍부화로 경미 케이스가 증상有로 끌려올라 FP 증가할 수 있음. 10 초과 시 analyze 추출 범위 재검토.
- **병해 의심 ≤ 12** — 재증가 안 함.
- **건강 행 pred 건조 = 0** — 새 건조 FP 없음.

---

## 4. 제약 (불변)

- **변경 파일**: `app/prompts.py`의 `ANALYZE_SYSTEM`(observed_symptoms만) + `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`(status 결정 룰). 그 외 무변경.
- `visual_description`·status guard·RAG·`test_data/*`·`eval/*.json` 무변경.
- **[B-2] `main_rag` 명명 변경 보류** — 손대지 말 것.
- §9 데이터 범위: 정량값·가짜 숫자 금지, **추정 금지**, 일반 속성 조합(특정 케이스 암기 금지).
- 파일 인코딩 BOM 없는 UTF-8, Python 3.12.

---

## 5. 보고 형식

1. **Step 0 게이트** — observed_symptoms 설명 원문 / status 결정 룰 원문 / enum 확인.
2. **Step 1** — analyze 4축 추출 + 추정 금지 추가 문구 (over-fitting 회피·일반형 확인).
3. **Step 2** — generate 황화 충돌 분기 룰 추가 diff (건조 억지 분류 아님 확인).
4. **Step 3** — 4개 검증 결과 (특히 합성: 마름→건조 / 황화단독→영양유지 / 건강 잎끝갈변→건강유지 / 심한 비건강→건강 안감).
5. 커밋 해시 3건.
6. R11 측정 명령 (RUN_EVAL_OUT 강조) + 텍스트 선확인 + 감시 5포인트.
