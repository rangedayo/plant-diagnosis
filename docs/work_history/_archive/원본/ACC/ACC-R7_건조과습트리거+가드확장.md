# [ACC-R7] prompts.py 건조·과습 트리거 신설 + status guard 비건강 전체 확장

> **목적**: R6 진단(가설 a 확정)에 따라 generate가 "건조"·"과습"을 발화하도록 `prompts.py`에 양성 트리거를 신설한다. **동시에** status guard의 발동 대상을 "병해 의심" 전용에서 **비건강 status 전체**로 확장해, 트리거 추가로 새로 생길 수 있는 "건조 FP"를 막는다. 두 변경을 함께 가야 R7 전제("비건강 내부 재분류라 recall 안전")가 precision까지 성립한다.
>
> **성격**: 코드 수정 라운드 (`app/prompts.py` + status guard). 측정 게이트 있음. 실측정은 R8(사용자 PowerShell).
>
> **선행**: ACC-fix(baseline 원복 + R5 보존) 완료, R6 진단(`a2a998d`). **후행**: R8 사용자 측정.

---

## 1. 확정 배경 (R6 진단 결과 + 사용자 통찰)

### 1-1. R6 진단 — 가설 a 확정

- `prompts.py`에 **건강·영양 부족(L77)만 양성 트리거**가 있고 **건조·과습은 트리거 없음** → 0발화.
- 트리거 있는 status만 발화(건강 19·영양 부족 3), 없는 것은 0건 — "거의 통제실험".
- 가드(c): →건조 reroute 없으나, 건조 6건 전부 `guard_fired=False`라 가드 단독은 수정처 아님. b(RAG)는 기각.

### 1-2. 사용자 통찰 — 프롬프트만 고치면 가드 우회 위험

프롬프트만 고치면 이런 경로가 생긴다:

```
건강한 식물(잎끝 갈변 살짝) → generate "병해 의심" → 가드 발동 → "건강" 교정 ✓  (현재)
건강한 식물(잎끝 갈변 살짝) → generate "건조"     → 가드 미발동(건조는 대상 아님) → "건조" 확정 ✗  (R7 후 위험)
```

→ 지금 가드가 잡는 7건 중 일부가 R7 후 "건조"로 분류되며 **가드를 우회 → 새 FP**. 그래서 가드도 비건강 전체로 확장해야 함.

---

## 2. 작업

### Step 0 — read-only 선결 게이트 (불일치 시 중단·질의)

1. `git status` clean 확인 (ACC-fix 라운드 완료 전제). R5 결과 `eval/after_acc_r3r4_L0prime.json` 존재 확인 (R8 비교 앵커).
2. **`prompts.py` 영양 부족 트리거(L77 근방) 원문 인용** — 건조·과습 트리거를 이 **대칭 구조**로 신설할 본보기. status 정의 블록 전체 구조 보고.
3. **status guard 본체 위치·발동 조건 원문** (R6에서 파악된 `all_cosmetic_nondisease_top1` 룰) — 현재 어떤 status일 때 발동하는지, 도착 status가 "건강" 단방향인지 코드 인용.
4. `app/model_utils.py` `ALLOWED_STRUCT_STATUS` 원문 — 트리거 신설이 enum과 일치하는지 확인.
5. R5 디버그 기준 건조 6건 + 가드 7건 발동 케이스 재확인 (Step 2 합성 테스트 설계용).

### Step 1 — prompts.py 건조·과습 양성 트리거 신설

영양 부족(L77) 트리거와 **대칭 구조**로 건조·과습 트리거 추가:

- **건조**: 잎끝 갈변, 잎 가장자리 마름, 잎 전체 마름·황화, 아래잎 고사, 줄기 마름 등 **수분 부족 전형 신호**가 보이면 "건조"로 판단하라는 지시.
- **과습**: 잎 전체 처짐·물러짐, 잎 황화 동반 무름, 줄기·뿌리 무름, 곰팡이·물러진 반점 등 **과습 전형 신호**가 보이면 "과습"으로 판단하라는 지시.

제약·주의:
- ⚠ **과습은 평가셋 표본 0** — 트리거는 대칭으로 넣되 R8에서 측정 불가. "건조"만 검증 가능. 보고에 명시.
- ⚠ **over-fitting 금지**: R5 행운목 증상 문자열에만 맞추지 마라. 일반 식물 건조·과습 증상으로 작성 (특정 케이스 암기 아님).
- ⚠ **§9 데이터 범위 원칙**: 토양습도%·정량값·가짜 숫자 금지. 증상 **정성 서술만**.
- status 문자열은 `ALLOWED_STRUCT_STATUS` enum과 **정확히 일치** ("건조"·"과습").
- 5개 status 설명의 **비대칭 해소**가 목표 — 병해 의심이 디폴트로 빨아들이지 않도록 건조·과습도 동등한 무게의 트리거.

### Step 2 — status guard 비건강 전체 확장

현재 가드(`all_cosmetic_nondisease_top1`)를 다음과 같이 확장:

- **발동 status 필터 확장**: "병해 의심일 때만" → **비건강 status 전체**(병해 의심·건조·과습·영양 부족)일 때 발동 검토.
- **발동 조건은 그대로**: 증상이 전부 경미한 cosmetic + RAG top1이 nondisease → "건강"으로 교정. 이 핵심 조건(경미함 판정)은 **건드리지 마라.** status 필터만 넓힌다.
- 즉 "어떤 비건강 status든, 증상이 경미한 cosmetic뿐이면 건강으로 reroute".

⚠ **recall 사수 (절대 조건)**:
- 가드는 **경미한 cosmetic일 때만** 건강으로 보낸다. 진짜 아픈 식물(심한 증상)을 건강으로 보내면 FN 발생 → recall 깨짐.
- 발동 조건(경미함 판정 로직)을 **느슨하게 만들지 마라.** status 필터 확장만 한다.
- R5 가드 7건은 전부 올바른 FP 교정(induced_fn=0)이었음 — 이 동작이 깨지면 안 됨.

### Step 3 — 검증 (합성·코드 sanity, Gemini 호출 금지)

⚠ **eval 풀런·Gemini 실호출 금지.** 실측정은 R8(사용자).

1. **import·문법**: `.venv\Scripts\python.exe -c "from app.main import app; print('ok')"`
2. **enum 일치**: prompts.py 트리거 status 문자열이 `ALLOWED_STRUCT_STATUS`와 정확히 일치하는지.
3. **가드 합성 단위 테스트** (Gemini 불필요, 합성 케이스 dict):
   - 건조 + 경미한 cosmetic(잎끝 갈변뿐) + RAG nondisease → **건강으로 교정**되는지
   - 건조 + 심한 증상(잎 전체 마름·줄기 마름) → **건조 유지**(가드 미발동, FN 방지)되는지
   - 병해 의심 + 경미 → 기존대로 건강 교정 (회귀 없음)
   - 영양 부족 + 경미 → 건강 교정 (신규 대상)
4. **pytest 회귀**: `.venv\Scripts\python.exe -m pytest tests/ -v -m "not integration"` — 모두 passed.

### Step 4 — atomic 커밋 (푸시 보류)

1. `feat(prompt): prompts.py 건조·과습 양성 트리거 신설 (5-status 비대칭 해소)` — prompts.py
2. `feat(guard): status guard 발동 대상 비건강 status 전체로 확장 (건조 FP 방지)` — guard 파일
3. `docs(work_history): ACC-R7 프롬프트 보존` — 본 .md를 `docs/work_history/`로 복사

푸시는 사용자 검토 후.

### Step 5 — R8 측정 안내 (사용자 PowerShell)

⚠ **`RUN_EVAL_OUT` 반드시 먼저 설정** (안 그러면 baseline.json 또 덮어씀 — ACC-fix 재발 방지):

```powershell
$env:RUN_EVAL_OUT="after_acc_r7_dry_guard.json"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

- 비교 앵커: `eval/after_acc_r3r4_L0prime.json` (R5)
- **감시 포인트**:
  1. **건조 열이 차는가** — 5-status 혼동표 true=건조 행에서 pred 건조 칸 > 0 (R5는 0)
  2. **병해 의심 열이 줄었는가** — 건조가 병해 의심에서 빠져나왔는지
  3. **FN = 0 유지** (절대 사수) — recall 100% 유지
  4. **FP가 R5(10) 대비 증가하지 않음** — 가드 확장이 새 건조 FP를 막았는지 (핵심 검증)

---

## 3. 게이트

- 🔴 **recall 100% / FN 0** — 절대 사수. 못 지키면 즉시 revert.
- **건조 발화 > 0** (R5는 0) — R7 목표 달성 여부.
- **FP ≤ R5(10)** — 가드 확장이 건조 FP 증가를 막았는지. 증가하면 가드 필터/조건 재검토.
- recall 깨지면 가드 조건이 너무 느슨한 것 → Step 2 경미함 판정 로직 점검.

---

## 4. 제약 (불변)

- **변경 파일**: `app/prompts.py` + status guard 파일(R6에서 특정된 곳, graph.py 등). 그 외 무변경.
- `test_data/*`·`labels*.json`·`eval/*.json`·`scripts/*` 무변경.
- **[B-2] `main_rag` 명명 변경 보류** — 손대지 말 것.
- §9 데이터 범위: 정량값·가짜 숫자 금지, 증상 정성 서술만.
- 파일 인코딩 BOM 없는 UTF-8, Python 3.12.

---

## 5. 보고 형식

1. Step 0 게이트 — prompts.py 영양 부족 트리거 원문 / 가드 발동 조건 원문 / enum 확인.
2. Step 1 — 건조·과습 트리거 추가 원문 (대칭 구조 확인). 과습 측정 불가 명시.
3. Step 2 — 가드 status 필터 확장 diff. 경미함 판정 로직 무변경 확인.
4. Step 3 — 4개 검증 결과 (특히 합성 테스트: 건조+경미→건강, 건조+심함→건조 유지).
5. 커밋 해시 3건.
6. R8 측정 명령 (RUN_EVAL_OUT 강조) + 감시 4포인트.
