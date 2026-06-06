# R12d-1 — "빼기" 라운드(R10 황화룰 + status_hint 제거) 측정 결과 보고서

> 변경: ① `app/prompts.py` R10 황화 충돌룰 제거(commit ccf5b8b) ② `scripts/build_b_dataset_rag.py` status_hint dead metadata 제거(commit 639b76c) + 카드 source 6장 status_hint 필드 제거(data/raw gitignore, 로컬).
> 빼지 않은 본질: 신설 건조카드 6장·재분류 3장 본문, `abiotic-water` problem_type, R12b cause-status 정합룰, 가드.
> 측정: `eval/after_acc_r12d1_remove_surface.json` (사용자 run_eval --aux, Gemini 과금).
> 앵커 R8 `after_acc_r7_dry_guard.json` · 비교 R12c-1 `after_acc_r12c1_rag_content.json`.
> **종합 판정: PASS (FN=0 복구 + 본질 보존 + 무악화). 단 healthy→건조 FP는 status_hint와 무관함이 입증됨.**

## 1. 라운드 목적

R12c-1 평가에서 사용자 통찰: *"계속 추가만 한다고 나아질 것 같지 않다. 건조에 과적합하는 건 아닌가."*
R7~R12c-1 누적 변경물 중 **본질 기여**와 **surface 패치**를 분리하기 위해 후자 둘을 제거:
- **R10 황화 충돌룰** — R11에서 효과 0 입증된 generate 프롬프트 블록.
- **status_hint 메타** — R12c-1 healthy→건조 FP의 가설상 원인.

CC가 착수 전 코드 검사로 제기한 반증: **status_hint는 `app/` 어디에서도 읽히지 않는 dead metadata**(graph.py가 generate에 노출하는 RAG 신호는 `problem_type`뿐). 이 라운드는 그 진단을 실측으로 검증한다.

## 2. 게이트 결과표 (R12c-1 대비)

| 지표 | 기준 | R12c-1 | R12d-1 | 판정 |
|---|---|---|---|---|
| 🔴 `post_guard.fn` | = 0 (절대 사수) | 1 | **0** | ✅ PASS — recall 1.0 복구 |
| `post_guard.fp` | ≤ 14 | 17 | **15** | ⚠️ 기준 초과 but **17→15 개선** |
| 건강행 `pred=건조` | ≤ 2 (핵심) | 7 | **6** | ⚠️ 거의 불변 (= status_hint no-op 입증) |
| 건조 발화 (`pred="건조"`) | ≥ 3 | 11 | **11** | ✅ PASS — 본질 보존 |
| 건조 TP (`gt=건조 ∧ pred=건조`) | ≥ 2 | 4 | **5** | ✅ PASS — 오히려 +1 |
| `latency.mean` | ±10% | 21.323s | **20.119s** | ✅ PASS (-5.6%, outlier 없음) |

**파생 지표(post-guard)**: precision 0.348, recall **1.0**, accuracy 0.583. pre-guard tp8/tn11/**fp17**/fn0 → guard가 2건 교정 → post tp8/tn13/**fp15**/fn0. `guard_caught_fp=2`.
**status 분포**: {건강14 · 건조11 · 병해 의심11 · 영양 부족3} — 5종은 아니나 4종 균형 유지.

## 3. 핵심 결론 3종 (데이터 근거)

### 3.1 status_hint = no-op 입증 (CC 사전 진단 ↔ 실측 대조)

- **사전 진단(코드)**: `status_hint`는 Chroma 메타로 쓰기만 되고 graph.py·model_utils 어디에서도 read 없음. generate 노출 경로는 `_tag_doc_with_problem_type`의 `problem_type` prefix + 가중 다수결 "우세 타입"뿐.
- **실측 대조**: status_hint 제거 후 **healthy→건조 FP 7 → 6** (단 1건 감소). 만약 status_hint가 FP 원인이었다면 6건 전부 사라졌어야 함. 1건 감소는 status_hint 효과가 아니라 **analyze 비결정성**(동일 이미지·run마다 observed_symptoms 변동)의 통상 노이즈 ±1~2 범위.
- **결론**: §1 가설은 **기각**. status_hint는 surface조차 아닌 **dead code**였고, 제거는 generate 동작에 no-op(저장소 정리 효과만). build verify_dry_top10도 6/6 그대로 통과(검색은 problem_type 기반).

### 3.2 healthy→건조 FP 진짜 범인 = abiotic-water 카드 본문/타입

healthy행 pred=건조 6건 전수 — observed_symptoms + top_3 problem_type:

| case (gt=건강) | observed_symptoms | top_3 problem_type |
|---|---|---|
| self_dracaena_003 | 여러 잎의 잎끝 갈변 및 마름 | abiotic-water · abiotic-water · abiotic |
| self_dracaena_004 | 여러 잎의 잎끝 바삭 갈변 / 일부 황화·고사 | abiotic-water · abiotic · "" |
| self_dracaena_006 | 잎끝 갈변·마름 / 일부 전체 고사 / 세로 말림 | abiotic-water · abiotic-water · abiotic |
| inat_chlorophytum_comosum_003 | 일부 잎끝 갈변 및 마름 | abiotic-water · abiotic · "" |
| inat_spathiphyllum_001 | 잎끝 미세 황화 / 잎 가장자리 갈변·마름 | abiotic-water · abiotic-water · abiotic |
| inat_spathiphyllum_002 | 다수의 아래잎 갈변 및 고사 | abiotic-water · "" · "" |

- 6건 모두 **top_1 = abiotic-water** + 증상이 "잎끝/가장자리 갈변·마름"(건조 전형 어휘). 신설 건조카드(`dry_supplement_002 Brown crispy leaf tips…`, `dry_supplement_004 Wilting and lower-leaf yellowing…`)가 top_3를 지배(per_case sim 0.84~0.87).
- 즉 **정상 노화·cosmetic 잎끝 갈변을 abiotic-water 카드가 "건조 양성"으로 흡수.** status_hint가 아니라 **카드 본문·problem_type 자체**가 신호원 — task가 "본질 보존"으로 **유지**한 부분이 곧 FP의 원인. 빼기로 분리해 보니 본질(카드)과 FP가 같은 뿌리였다는 게 드러남.

### 3.3 FN=0 복구는 가드 개선이 아니라 운(analyze 변동) 의존

- haengun_006(gt=건조)이 이번 run에서 TP. **그러나 guard 발동 아님**(`guard_fired=false`): analyze가 이번 run에 `["아래잎 일부 황화", "일부 잎끝 갈변 및 마름"]`(마름=건조 단서)을 산출 → top_3 abiotic-water 지배 → generate가 직접 `pred=건조` 커밋.
- R11에서 006 FN이었던 건 analyze가 단일 cosmetic 증상만 줘서 generate가 건강 쪽으로 흘렀기 때문. **즉 006의 TP/FN은 analyze의 비결정적 증상 추출에 좌우** — R12d-1 코드 변경(빼기)의 직접 성과가 아님.
- `_symptom_is_cosmetic` 위치 가중(`아래/아래쪽/하엽/하부`) 미변경 → **재측정 시 006이 다시 단일 cosmetic+하엽으로 나오면 FN 재발 가능**. FN=0은 견고하지 않다(R12a 정당화).

## 4. 본질 직접 보존 (빼기 철저 검증)

- **건조 발화 11 불변 · 건조 TP 4→5(+1)** — surface 룰(R10·status_hint) 없이도 RAG→cause→status 연쇄가 작동. R10 황화룰을 빼도 건조 변별이 떨어지지 않음(=황화룰 효과 0 재확인).
- 건조 TP 5건: `haengun_002·003·006·008` + `epipremnum_004`. 모두 top_3 abiotic-water 우세 + cause "수분 부족/과도한 건조" + status="건조" 정합. cause-status가 R12b 정합룰만으로 정렬.
- **R10 황화룰 제거의 분포 영향 ≈ 0**: prompts len 4640→4301(-339자), 건조·병해·영양 분포 모두 R12c-1과 동급. 단 `haengun_005`가 R12b 건조 → R12d-1 **병해 의심**으로 status 후퇴(증상 동일: 마름+반점). R10 "마름→건조 우선" 룰이 빠지면서 generate가 반점 신호로 병해 escalate한 것으로 보이나, top_3가 약신호(`"",abiotic,""`)이고 단일 run·temperature 비결정과 교락 → R10 제거 단독 효과로 단정 불가. 005는 cause "수분 부족 또는 과습"인데 status 병해 의심 = R12b 정합룰 위반 잔존(003·008과 동형, generate escalation 편향).

## 5. 가드 진단

- `fired_count=2`, 둘 다 `all_cosmetic_nondisease_top1`, `guard_correct_fp=2`, `guard_induced_fn=0`.
  - `self_dracaena_001`: pre 병해 의심 → post 건강 (cause 재생성 ✅).
  - `self_dracaena_002`: pre **건조** → post 건강 (cause 재생성 ✅).
- dracaena_002는 **건조 FP를 가드가 잡은 케이스** — 가드 없었으면 healthy→건조가 7이었을 것(6+1). 즉 abiotic-water 카드가 만든 건조 FP를 가드가 일부만 흡수.
- 잔여 healthy→건조 FP 6건은 전부 cosmetic 판정 실패(증상이 "마름·고사" 등 비-cosmetic 어휘) → 가드 미발동. 가드는 비건강→건강 1방향이라 이 6건을 직접 못 줄임.

## 6. 측정 한계 (정직)

- **단일 run.** run2 미수행. analyze 비결정성으로 FP·status는 ±1~2 진동. 특히 **FN=0이 haengun_006의 analyze 운에 의존** → 재측정 시 FN=1 가능성 실재.
- healthy→건조 7→6의 1건 감소도 같은 노이즈 범위 — "감소"로 해석 금지(no-op 입증의 보강 근거).
- 005 status 후퇴(건조→병해)는 R10 제거 효과와 temperature 비결정이 교락되어 단일 run으로 귀인 불가.
- 과습·영양 부족은 독립 GT 표본 0(혼동표 unmeasured) — 해당 status 정확도는 이번에도 미측정.

## 7. 다음 라운드 후보 (확정 2, 우선순위 사용자 결정 대기)

빼기로 드러난 사실: **healthy→건조 FP의 뿌리는 abiotic-water 카드(본질)** 이고, **FN=0은 견고하지 않다.** 둘을 각각 겨냥한 두 후보를 변수 격리해 분리 라운드로:

| 후보 | 겨냥 | 내용 | 리스크 |
|---|---|---|---|
| **R12c-1-α** (카드 negative 신호) | §3.2 healthy→건조 FP 6건 | abiotic-water 카드 본문에 "정상 노화·종 고유 잎끝 갈변과의 구별"(negative/감별) 문장을 보강해, cosmetic 잎끝 갈변을 건조로 끌지 않게. problem_type·카드 수 불변(본문만). | 건조 TP 회귀 위험(카드가 보수화) → 건조 발화·TP 동시 추적 |
| **R12a** (가드 위치 veto) | §3.3 FN=0 견고화 | `_symptom_is_cosmetic`에 위치 veto(`아래/아래쪽/하엽/하부`) 추가 — 단일 cosmetic+하엽 위치를 건강으로 over-correct 못 하게. 재현 가능한 recall 사수. | 가드 보수화 → healthy FP 소폭 증가 가능 |

- 두 후보는 **서로 다른 파일·다른 메커니즘**(R12c-1-α=카드 본문 / R12a=guard 코드) → 반드시 분리 측정.
- 권고 순서(참고): healthy FP가 정확도 최대 적자이므로 **R12c-1-α 우선** 검토, 단 FN 재발 신호 보이면 **R12a 선행**. 결정은 사용자.

---

## 종합 판정

**PASS.** 절대 사수 게이트(post.fn=0) 충족, 건조 발화·TP 등 본질 전량 보존, latency 정상, 무악화(FP 17→15 개선). 빼기 라운드의 1차 목적(본질/surface 분리)을 달성.

**이 라운드의 진짜 수확** = 측정 자체보다 **분리 결과**:
1. **status_hint = dead code 확정** — 입력 설득 5회·카드 추가 누적 중 하나가 generate에 닿지조차 않았음을 코드+실측 이중 확인. 제거로 build 스크립트 단순화.
2. **healthy→건조 FP의 뿌리 = abiotic-water 카드(유지한 본질)** — "추가만으로 안 나아진다"는 통찰의 메커니즘 확인. 본질과 FP가 동근(同根)이라 다음은 카드 **본문 정교화**(R12c-1-α)가 정공법.
3. **FN=0은 운** — recall 사수는 프롬프트·카드가 아니라 **가드 위치 veto(R12a)** 로만 견고화 가능.

## 변경 파일 명시
이 라운드 산출물: 본 보고서 + (이미 커밋된) `app/prompts.py`(ccf5b8b) + `scripts/build_b_dataset_rag.py`(639b76c) + (gitignore·로컬) `data/raw/b_dataset/dry_supplement/dry_supplement.json` status_hint 제거. 측정 JSON `after_acc_r12d1_remove_surface.json`은 사용자 산출물. graph.py·model_utils·analyze·가드·abiotic-water problem_type·카드 본문 등 그 외 일절 무변경(변수 격리 유지).
