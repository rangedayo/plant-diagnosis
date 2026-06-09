# CC Task — R14: generate 개체-전체 판단 + 겸손 프레이밍 (FP 한계 검증 / 정성 프레이밍)

> 시점: 2026-06-09. R13 Arm C 채택 + GT 정정(FP 14→10) 완료. 이번 = **§6/§7 다음 레버 = generate 보정** 한 라운드.
> **이번 변수 = generate 시스템 프롬프트 1개(`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`)에 블록 1개 추가.** 그 외 일절 무변경.
> 라운드 번호(R14)는 잠정 — CLAUDE.md 넘버링에 맞춰 조정 가능.

## 0. 한 줄 요약
generate가 잎별 증상만 나열하고 개체 전체를 판정하지 않는 갭(§6)을 메우기 위해, `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에 **개체 전체 활력 판단 + 활성 병변 형태 변별(=recall 방어) + 겸손 프레이밍** 블록을 surgical하게 추가. relabeled 앵커 대비 **recall 1.0 하드 게이트** 하에 FP를 측정하고, per_case 출력을 정성 평가용으로 보존한다.

## 1. 안전 제약 (필독)
- **🔴 FN=0 절대 사수.** 이번 변경은 recall을 깎을 위험이 가장 큰 종류다(과거 [1-7] v2가 정확히 이 지점에서 recall 100→80% 실패). **측정에서 FN이 0이 아니면 즉시 멈추고 롤백 후 보고.** 채택 금지.
- **과금(Gemini) 측정 금지.** 이번 변수는 generate(gpt-4o-mini)뿐이므로 **analyze 재호출 불필요** — §3 read-only 게이트로 무과금 재생 경로를 먼저 확인한다. 무과금 경로가 없으면 측정은 사용자 PowerShell 직접(§5).
- **편집은 `app/prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 한 군데, 아래 §4 블록 추가만.** 다른 프롬프트·키·스키마·후처리 무접촉.
- `eval/baseline.json`, `eval/after_acc_armC_3p5flash_relabeled.json`(활성 앵커), `eval/after_acc_armC_3p5flash.json`(정정 전), old 앵커 — **읽기 OK, 수정·덮어쓰기 금지.**
- 측정 출력은 반드시 `RUN_EVAL_OUT`로 새 경로 지정(앵커·baseline 덮어쓰기 방지, CLAUDE.md §1).
- 커밋까지만. **푸시 보류**(사용자 검토 후).

## 2. 이번 변수 & 동결 영역 (변수 격리 보증)
- **변수(1개)**: `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에 개체-전체 판단 + 프레이밍 블록 추가.
- **동결(무변경)**: `analyze`(gemini.py·ANALYZE 프롬프트), RAG·Chroma·키워드, `apply_status_guard`(veto 포함), `regenerate_healthy_cause`, `normalize_structured_result`·`default_structured_fallback`, status enum, `run_eval.py`·`rescore_from_output.py`·`validate_main_eval.py` 로직, GT(`labels.json`), **스키마 확장((b) 보류 유지 — 새 JSON 키 추가 금지).**

## 3. Phase 0 — read-only 선결 게이트 (과금 0, 끝나면 보고·HOLD)
편집 전에 다음만 조사·보고하고 **사용자 OK 전까지 멈춘다.**

### 3.1 무과금 재생 타당성
- `eval/after_acc_armC_3p5flash.json`(또는 relabeled)의 `per_case`에 generate **입력**을 재구성할 재료가 있는지 확인: `observed_symptoms`, `visual_description`, `plant_confidence`, `alt_candidates`, 그리고 RAG 결과(검색 청크 또는 우세 타입/top_problem_type). 어느 필드가 있고 어느 게 없는지 명시.
- analyze 출력(=Gemini 산출)을 **재호출 없이 재사용**해 RAG(로컬 Chroma)+generate(gpt-4o-mini)+guard만 다시 돌려 35장을 재채점하는 경로가 존재/구성 가능한지 판단. 참고: `scripts/diagnostics/r12b_synthetic_check.py`가 Gemini 0건으로 generate를 돌리는 선례.
- 결론 보고: (A) 무과금 재생 가능(명령/스크립트 제안 + 예상 비용: gpt-4o-mini 토큰 + 임베딩만, Gemini 0), 또는 (B) 불가 → 사용자 PowerShell 풀 eval 필요(analyze 3.5-flash/global 과금).
  - 보너스 메모: 무과금 재생이 가능하면 analyze 출력 고정이라 **generate 단일 변수 격리가 풀 eval보다 더 깨끗**함(analyze run-to-run 노이즈 0).

### 3.2 편집 대상 확정
- `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에서 §4의 삽입 기준점(아래 "cosmetic 패턴이란…" 불릿과 "대안 후보(alt_candidates)…" 불릿)이 **현재 파일에 그대로 존재**하는지 확인하고, 그 두 불릿 사이가 삽입 위치임을 보고. (문구가 다르면 멈추고 실제 문구 보고.)

→ **여기까지 하고 보고 후 HOLD.** 사용자 OK를 받으면 Phase 1·2 진행.

## 4. Phase 1 — generate 프롬프트 편집 (사용자 OK 후)
`app/prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 안, **"cosmetic 패턴이란…"으로 시작하는 불릿 바로 다음 줄**(즉 "대안 후보(alt_candidates)…" 불릿 바로 앞)에 아래 **두 불릿을 그대로 삽입**. 기존 텍스트는 한 글자도 수정·삭제하지 말 것(순수 추가).

```
- 개체 전체 판단(중요 — status 결정 전 한 단계): 보고된 증상이 개체 전체의 건강을 나타내는지, 아니면 소수 잎의 국소 현상인지 먼저 판단하세요. 보고된 증상이 (1) 모두 cosmetic 패턴이고, (2) 단일 잎 또는 소수의 잎에만 국한되며, (3) 활성 병변 신호(비대칭·확산성 병반, 잎 중앙부 변색, 조직의 무름·물러짐, 곰팡이, 여러 잎 동시 진행)가 전혀 없다면 — 이는 개체 전체가 아니라 개별 잎 수준의 현상일 가능성이 높습니다. 이 경우 RAG 우세 타입이 "disease"·"pest"로 검색되었더라도(cosmetic 증상 키워드가 병해 카드와 겹쳐 검색됐을 수 있음), 위 활성 병변 신호가 없는 한 status="건강"을 우선 고려하세요. ⚠ 그러나 위 활성 병변 신호가 하나라도 있거나 증상이 다수 잎으로 확산된 경우에는 이 개체-전체 관용을 적용하지 말고, 기존 룰에 따라 증상 양상에 맞는 비건강 status를 분명히 선택하세요. 실제 병징을 "건강"으로 놓치는 것은 절대 금지입니다(recall 사수).
- 프레이밍(말투): status가 건강이든 비건강이든 cause·summary·current_state는 과대 진단 톤을 피하고 신중하게 작성하세요. 특히 cosmetic 패턴이 관찰된 경우 "이 종에서는 흔히 나타날 수 있는", "반드시 병을 의미하지는 않으며" 같은 종 맥락·겸손 표현으로 묘사해 사용자가 불필요하게 불안해하지 않도록 하세요. 단, status가 "건강"이 아니면 cause는 그 status와 정합해야 하며(위 cause–status 정합 룰 유지), 활성 병변 신호가 있을 때는 신중하되 분명하게 전달하세요.
```

설계 의도(커밋 메시지·보고용):
- 첫 불릿 = §6 "개체 전체 vs 잎-하나" 갭 + RAG가 cosmetic 키워드로 disease 카드를 끌어와 예외가 막히던 경로를 **활성 병변 신호 부재**라는 안전 게이트와 함께 우회. **활성 병변 변별이 [1-7] v2와의 결정적 차이**(무딘 완화 → 정밀 변별).
- 둘째 불릿 = §6 reframe(진짜 제품 지표 = 프레이밍). 이진 status가 안 움직여도 정성 개선을 얻을 수 있는 레버.

## 5. Phase 2 — 측정
- **무과금 재생 가능시(§3.1 A)**: 제안된 경로로 35장 재채점, 출력 `eval/after_acc_r14_generate_wholeplant.json`(또는 합의 경로). Gemini 0건 확인.
- **불가시(§3.1 B)**: 사용자 PowerShell 직접 (CLAUDE.md §3.2):
  ```powershell
  $env:RUN_EVAL_OUT="eval/after_acc_r14_generate_wholeplant.json"
  $env:PYTHONIOENCODING="utf-8"
  # analyze = 3.5-flash/global (현 기본값) 그대로
  .venv\Scripts\python.exe scripts\run_eval.py --aux
  ```
  CC는 명령 제안·자가점검만, **실행은 사용자.**
- 비교 앵커 = `eval/after_acc_armC_3p5flash_relabeled.json` (FP 10·FN 0·acc 71.4%).

## 6. 게이트 & 정지 조건
| 결과 | FN | FP | 판정 |
|---|---|---|---|
| A | 0 유지 | < 10 | 렌즈가 바닥 깸 → 채택 후보(정성 점검 동반) |
| B | 0 유지 | ≈ 10 | 이진 바닥 확정 → 정성 프레이밍 개선 여부로 채택/롤백 결정 |
| C | **> 0** | — | **즉시 멈추고 롤백**([1-7] 재현). 채택 금지, 정성 전환 신호 |
- 어느 경우든 **FN=0 깨지면 그 자리에서 정지·보고.** 자동 진행 금지.

## 7. per_case 보존 (정성 평가용)
- 측정 결과 json의 `per_case`(케이스별 status·cause·summary·current_state·observed_symptoms)를 보존. 정성 루브릭(묘사 정확성 / 과대진단 vs 보정 / 종 맥락 / 톤)은 **Claude(웹)가 결과 받아 워크리스트로 구조화**할 예정이므로 CC는 가공하지 말 것.
- 특히 **TP 케이스의 cause/summary 톤**도 같이 보존(겸손 프레이밍이 진짜 양성의 명료함을 흐리지 않았는지 점검용).

## 8. 커밋 (atomic, 푸시 보류)
1. `feat: generate 개체-전체 판단 + 겸손 프레이밍 블록 추가 (R14)` — `app/prompts.py`만.
2. (측정 후) `eval/` 결과 json + 결과 요약 문서는 측정·판정 확정 후 별도 커밋. 판정 C(롤백)면 1번 커밋도 revert.
- `git status`·해시 보고. 푸시 X.

## 9. 보고 형식 (CC → 웹)
1. **Phase 0**: §3.1 재생 타당성(A/B + 명령/비용) + §3.2 삽입 위치 확인. → HOLD.
2. (OK 후) prompts.py diff(추가된 두 불릿만, 순수 add 확인).
3. 측정 핵심 수치: **FN(최우선)**, FP, TP, TN, acc, recall, precision — 앵커 대비 델타.
4. §6 표 어느 결과(A/B/C)인지 + 판정.
5. cause–status 모순 0 확인(정합 룰 유지 점검), JSON 파싱율.
6. per_case 보존 경로 + 커밋 해시/`git status`.

## 10. 금지 사항
- FN>0 무시·자동 진행. (즉시 정지·롤백)
- 과금(Gemini) 측정 임의 실행.
- prompts.py의 다른 부분·기존 문구 수정/삭제(순수 add만).
- analyze·RAG·guard·normalize·fallback·스키마(JSON 키)·GT 변경.
- 앵커·baseline 접근/덮어쓰기.
- 자동 푸시.
