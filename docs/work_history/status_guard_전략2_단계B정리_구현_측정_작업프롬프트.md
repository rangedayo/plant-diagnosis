# [전략 2 / status guard] 단계 B' 정리 + status guard 구현·측정 — 작업 프롬프트

## 0. 맥락 (먼저 읽을 것)

**generate 설득 3회 연속 실패 확정**: B-4b(프롬프트 강화) → B-4c(tie/cosmetic 룰) → B'(RAG 종 사실) 전부 커버-종 FP 순효과 0. generate의 "증상 보고 시 병해 escalate" 본질은 **입력 신호(룰·분포·종 사실)로는 안 풀린다**가 측정으로 확정.

**전환 논리**: status guard는 generate를 **설득**하는 게 아니라, generate 출력 뒤에서 **코드가 status를 직접 교정** = generate 성향을 **우회**한다. 설득 경로(3회 실패)와 구조적으로 다르므로 풀릴 가능성이 높다.

**철학 전환 근거**: "강제 3개 원칙(LLM이 status 확정)"과 충돌하나, 사용자 승인("결과 안 나오면 철학 바꿀 수 있다") + 3회 실패로 조건 충족. **이진 게이트(건강↔비건강)라 "모든 질환을 룰로"가 아니라 cosmetic 키워드 한 묶음만** 정의하면 됨. 강제 3개 원칙(JSON·enum·한국어) 형식 자체는 유지 — guard는 status enum **값만** 교정, 형식 안 깸.

**이번 작업 구성**: PART A(단계 B' 정리, 2커밋) → PART B(status guard 구현) → PART C(측정) → PART D(보고). **커밋은 PART A의 2개만 명시 지점. PART B·C 변경은 측정·보고 후 사용자 결정(커밋 금지).**

---

## PART A — 단계 B' 정리 (status guard 착수 전 선행)

### A-1. 단계 B' 기록 커밋

generate 설득 3회째 실패를 히스토리에 박는다(B-4b·c 패턴 계승, 재현 가능 + status guard 근거 보존).

- 포함: `app/graph.py`(종 주입), `scripts/run_eval.py`(per_case 카드 분해), `scripts/build_species_normal_rag.py`(신규), `eval/after_phase_b_prime{,_run1,_run2}.json`, 메모리(`phase-b-prime-species-meta-null-effect.md`, `MEMORY.md`)
- ⚠ 커밋 전 `git status` — `eval/baseline.json` 변경 목록에 **안 떠야 정상**. 뜨면 중단·보고.
- 메시지:
  ```
  feat: [B'] 종 메타 (a) 정상화 RAG 주입 + FP 측정 (순효과 0 + FN 리스크 — generate 설득 3회째 실패)
  ```

### A-2. 종 주입 revert 커밋

종 메타 generate 주입은 FP 이득 0 + FN 유발이라 main에 켜두면 해롭다. 제거해 B-4c 동등 상태로 복원.

- `app/graph.py`에서 **species_normal_rag retrieve 호출 + generate context의 종 메타 섹션 제거** → graph diff로 **B-4c 시점과 동등** 확인(retrieve/generate 로직이 B-4c와 같은지).
- ⚠ **보존 (삭제 금지)**: `species_normal_rag` 컬렉션, `build_species_normal_rag.py`, 종명 매핑 json. (b) 케어 가이드 미래 용도 자산. graph.py의 **주입 코드만** 제거.
- (a) 4청크 컬렉션 자체는 진단 경로 끊기면 당장 안 쓰임 — 두든 지우든 무해하니 **보존**(나중 (b)는 케어 필드로 새로 적재). 지금은 손대지 않는다.
- 메시지:
  ```
  revert: [B'] 종 메타 generate 주입 제거 (FP 0 + FN 리스크) — species_normal_rag·스크립트·매핑은 (b) 케어용 보존
  ```

⚠ **푸시 여부는 사용자 자리** — A-1·A-2 커밋만 만들고 푸시는 보류, 보고에서 푸시할지 물을 것. (status guard 측정까지 보고 한 번에 푸시할 수도 있음)

---

## PART B — status guard 구현

### B-1. 동작 설계

generate 출력(status + 설명) 뒤에 `apply_status_guard()` 후처리를 둔다. **핵심 동작은 over-escalate 교정** — generate가 비건강(병해 의심 등)이라 했는데 실제론 cosmetic뿐이면 **건강으로 내린다**.

- **입력**: `observed_symptoms`, `top_3_problem_type_weighted`, `rag_metas`, `rag_sims`, `plant_confidence`
- **이진 게이트 재판정 규칙 (초안)**:
  - 증상 empty → 건강 (generate가 이미 하지만 guard에서도 보장)
  - **모든 증상이 cosmetic + 비-disease top_1 → 건강으로 교정** ← 핵심
  - disease·pest top_1 → 유지(비건강, 교정 안 함)
  - **병변 단어 1개라도 있으면 → 유지(비건강)** ← FN 0의 안전판
  - **애매하면 LLM status 유지** (보수적 — 1차는 FN 0 사수 우선)

### B-2. cosmetic 키워드 묶음 — 추측 금지, 데이터에서 도출

⚠ **키워드를 머리로 추측해 짜지 말 것.** B-4 교훈(튜닝 부담)을 그대로 밟는다. **먼저 잔존 FP 데이터를 읽고** cosmetic/병변 키워드를 도출한다:
- 단계 B' 커버 4종 **FP 11건의 `observed_symptoms` 패턴** (eval/after_phase_b_prime per_case)
- **B-4c §6 분해** (tie 우세 / disease 우세 / 비-disease top_1)
- **B-4a fp_analysis** (FP 17건 observed_symptoms·top_3)

도출 방향 (확정은 데이터 보고 결정):
- **cosmetic(건강쪽 신호)**: 가장자리·끝에 국한, 단일·소수 잎의 변색/마름 — 예: "잎끝 갈변", "가장자리 변색", "잎끝 마름".
- **병변(비건강 사수)**: "고사", "전체 마름", "확산", "황화 및 고사", "처짐", "줄기 건조", "부패", "반점".

⚠ **B-4c §5 교훈 (FN 0의 핵심)**: cosmetic 정의는 **"가장자리·끝 국한 + 단일·소수 잎"**. 병변 신호가 하나라도 섞이면 cosmetic 아님 → 건강 교정 금지. tie인 TP 7건이 전부 "아래잎 고사/전체 마름/황화" 동반이라 cosmetic 정의 밖이었고, 그래서 "tie→건강"에도 FN 0이었음. 이 분리선을 키워드로 정확히 재현해야 한다.

### B-3. 구현 위치

- `model_utils.py`의 `normalize_structured_result`(형식만 정규화, 라벨 의미검증 없음 — v17에서 status guard 자리로 지목됨) **뒤**, 또는 `graph.py` generate_node 직후에 `apply_status_guard()`.
- guard는 **status enum 값만** 교정. JSON 구조·enum 집합(건강·과습·건조·병해 의심·영양 부족)·한국어 설명은 그대로 — 강제 3개 원칙 형식 불변.
- 교정 시 설명문과의 정합: status를 건강으로 내릴 때 설명문이 "병해 의심"을 말하면 모순 → 교정된 케이스는 설명문도 정합 처리(간단히: guard 교정 사유를 설명에 반영하거나, 설명 재생성은 비용이니 1차는 status만 교정하고 정합은 보고에서 판단).

---

## PART C — 측정

### C-1. e2e 2회 평균

- **메트릭/게이트**: FP(목표 **≤12**), recall/FN(**FN 0 유지 필수** — guard가 진짜 아픈 식물 깎으면 실패), 회귀 ≤5pp, plant_korean.
- 기준: B-4c(FP 17.5) 대비. A-2 revert로 B-4c 동등 복원했으므로 baseline 재사용.

### C-2. 측정 진단 분해 (필수)

- **guard 발동 건수** — 몇 건을 비건강→건강으로 교정했나.
- **교정 정확도 (per_case)** — 교정된 케이스가 진짜 FP였나(건강해야 할 게 건강 됐나).
- ⚠ **FN 점검 (per_case)** — guard가 건강으로 내린 것 중 **진짜 아픈 식물(TP)이 섞였나**. 1건이라도 있으면 키워드가 너무 넓음 → 병변 키워드 보강·cosmetic 범위 축소.
- **cosmetic/병변 키워드 hit/miss** per_case.

### C-3. 산출물

`eval/after_phase_status_guard_{run1,run2,avg}.json`

---

## PART D — 보고 (PART B·C는 커밋 전, 변경 보존)

1. **PART A 결과** — A-1·A-2 2커밋 해시, graph가 B-4c와 동등한지 확인, baseline.json 무접촉.
2. **status guard 규칙 + cosmetic/병변 키워드** — **어느 데이터(B'/B-4c/B-4a)에서 도출했는지** 근거와 함께.
3. **guard 발동 내역** — 건수 + 교정된 케이스 샘플.
4. **FP 측정** — 2회 평균, B-4c(17.5) 대비, 목표 ≤12 달성 여부.
5. **FN 점검** — guard가 깎은 것 중 TP 유무 (있으면 키워드 조정 필요).
6. **판정 + 권고** — 목표 달성 & FN 0 → 성공(커밋·푸시 결정 요청) / FN 발생 or 효과 부족 → 키워드 조정 재측정 / 그 외 방향.

---

## 환경 주의사항 (반드시 준수)

- `$env:RUN_EVAL_OUT`에 **`eval/` 접두 금지** (코드가 prepend → `eval/eval/` 이중경로).
- **Bash 툴로 `$env:` 금지** (구문 깨져 baseline 덮어쓰는 사고 전례) → 측정은 **PowerShell 툴**.
- ⚠ **`eval/baseline.json` 절대 덮어쓰기 금지** (커밋 기준).
- run_eval 콘솔 **cp949 한글 깨짐** → 값 확인은 **JSON UTF-8 읽기** (콘솔 숫자 신뢰 금지).
- **2회 평균 패턴** (run1/run2 + 평균). analyze 비결정성 FP ±1.
- GateGuard 훅: Bash/Edit/Write 전 "사실 명시" 요구.
- **커밋은 PART A 2개만.** status guard 구현·측정(B·C) 변경은 보존 상태로 두고 사용자 결정 대기.

---

## 산출물 요약

- PART A: 2커밋 (B' 기록 + 종 주입 revert), species_normal_rag·스크립트·매핑 보존
- PART B: `apply_status_guard()` (model_utils 또는 graph) — 코드 변경, 미커밋
- PART C: `eval/after_phase_status_guard_{run1,run2,avg}.json` — 미커밋
- PART D: 위 6항목 보고 (chat)
