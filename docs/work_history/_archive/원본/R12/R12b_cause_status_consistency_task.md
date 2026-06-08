# R12b — generate cause–status 정합 제약 추가

## 0. 라운드 목적

R12-0 §C.4에서 확정된 사실:
- `self_haengun_003` — `pred_cause`에 "**수분 부족** 또는 환경적 요인으로 인한 스트레스"라고 명시했는데 `pred_status = 병해 의심`
- `self_haengun_008` — `pred_cause`에 "**과도한 건조**, 영양 부족 또는 과비 가능성"이라고 명시했는데 `pred_status = 영양 부족`

generate는 자유서술(cause)에서 건조를 인지하고도 enum 커밋에서 다른 카테고리로 빠진다. R9의 "analyze 상류 단독 병목" 결론이 §C.4로 부분 수정됐고, 하류(generate)가 충분한 단서를 받고도 enum-prose 정합에 실패하는 케이스가 실재함이 확정됐다.

**이 라운드 목표**: STRUCTURED_DIAGNOSIS_JSON_SYSTEM에 **cause–status 정합 제약**을 추가해, generate가 이미 prose로 말하고 있는 정답을 enum에서도 일관되게 고르도록 한다. 보고서 §추천: "R12b가 가장 저비용·고확률 … recall 위험 낮음(비건강→비건강 이동)".

## 1. 절대 제약 (변수 격리)

이 라운드에서 **단 한 가지 변수만** 변경한다. 다음은 전부 동결:

- `apply_status_guard()`, `_symptom_is_cosmetic()`, STATUS_GUARD_* 토큰 리스트 → **그대로** (R12a에서 다룸)
- `keyword_node`, `retrieve_node`, `generate_english_keywords` → **그대로** (R12c에서 다룸)
- `b_dataset_rag` Chroma 컬렉션, 카드 파일, `build_b_dataset_rag.py` → **그대로** (R12c에서 다룸)
- R10에서 추가된 **황화 충돌룰은 유지**. 효과 없다는 게 R11에서 확인됐지만 같은 라운드에서 제거하면 변수 둘이 됨 → R12b 측정 후 효과 분석에 따라 R12b-2로 별도 처리
- `ANALYZE_SYSTEM` (analyze 프롬프트) → **그대로**. observed_symptoms 4축은 유지

**유일한 변경 대상**: `app/prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 한 곳에 cause–status 정합 제약 룰 추가.

## 2. 변경 명세

### 2.1 추가할 룰의 의도

generate가 cause 자유서술에 어떤 원인을 적었다면, 그 원인이 status enum 5종 중 어디에 해당하는지 결정적으로 매핑되어야 한다. enum과 cause가 명백히 모순되는 출력은 invalid로 간주.

### 2.2 권장 룰 텍스트 (CC가 prompts.py에 자연스러운 한국어로 통합)

핵심 매핑 가이드를 generate 프롬프트에 다음 형식으로 추가:

> **cause–status 정합 제약**:
> - `cause`에 적는 주된 원인은 `status` enum과 직결되어야 한다. 다음 매핑을 따른다:
>   - cause 주원인이 "수분 부족 / 물 부족 / 과도한 건조 / 건조 스트레스 / 토양 건조 / underwatering / water stress" → `status = "건조"`
>   - cause 주원인이 "과습 / 물 과다 / 물주기 과다 / 뿌리 부패 (과습 맥락) / overwatering" → `status = "과습"`
>   - cause 주원인이 "영양 부족 / 비료 부족 / 결핍 / nutrient deficiency / nitrogen deficiency" → `status = "영양 부족"`
>   - cause 주원인이 "곰팡이 / 세균 / 바이러스 / 해충 / 진균 감염 / 흰가루 / 잎점무늬 / disease / pest" → `status = "병해 의심"`
> - cause에 **여러 원인을 나열**한 경우, **가장 먼저 명시한 원인** 또는 **가장 신뢰도 높게 단정한 원인**을 status에 매핑한다 ("A 또는 B"보다 "A이 유력하며 B도 가능"이면 A 우선).
> - cause와 status가 모순되는 출력은 금지. 자신 없으면 cause를 **단일 원인으로 좁혀** 쓰고 그것을 status에 매핑하라.
> - 단, cause가 "환경적 요인 / 스트레스 / 자연스러운 현상" 같은 **불특정 표현**만 있을 때는 이 매핑이 강제되지 않으며, 기존 status 결정 룰을 따른다.

문장은 CC가 prompts.py의 기존 톤·문체에 맞게 조정해도 됨. 핵심은 **다섯 가지**:
1. 매핑 표 (4개 원인 클러스터 → 4개 enum)
2. 다중 원인 시 우선순위 명시 (선행/신뢰도)
3. 모순 금지 (자신 없으면 cause를 좁혀라)
4. 불특정 cause는 매핑 강제 없음 (escape hatch)
5. 기존 룰(R10 황화 충돌룰, status 결정 룰)과 충돌하지 않게 배치 — **추가**이지 **대체**가 아님

### 2.3 룰 배치 위치

`STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에서 기존 status 결정 룰(보고서 §A.4의 :73-79 부근, 건조 룰 L78 인접)과 가까운 곳에 새 섹션으로 배치. 정합 제약은 status 결정 직후의 self-check 단계로 읽히게 구성하면 의도 전달이 명확.

## 3. 합성 검증

### 3.1 검증 케이스 (R11 결과에서 직접 채취)

CC가 합성으로 새 프롬프트의 **문법/sanity**만 확인. 다음 입력을 generate에 주고 출력이 정합을 따르는지 합성 호출로 점검:

| case | observed_symptoms | top_3 RAG (R11 실측) | 기대 동작 |
|---|---|---|---|
| haengun_003 시뮬 | 아래잎 전체의 바삭한 마름 및 고사, 새순 끝부분 마름 | general(저온) / '' / abiotic(Chemical) | cause가 "수분 부족"을 주원인으로 명시 → status="건조" |
| haengun_008 시뮬 | 여러 잎의 잎끝 갈변 및 마름, 아래쪽 잎 고사, 전체적인 잎 처짐 및 주름 | general(저온) / '' / general | cause가 "과도한 건조"를 주원인으로 명시 → status="건조" |
| healthy 시뮬 (정합 확인) | 일부 잎끝 갈변 | abiotic / '' / env | cause가 "자연스러운 현상" 류 → 매핑 강제 없음, 기존 룰대로 |
| 모순 sanity | (인위 입력) cause="병해 가능성" + status="건조" 출력 강제 시도 | — | 룰 위반 회피 — cause나 status 중 하나로 정합되어야 함 |

### 3.2 한계 명시 (보고서에 기록)

- generate는 LLM 결정이라 합성으로 100% 보장 불가. 합성은 "프롬프트 문법 + 명백한 매핑 표 작동" 정도 검증.
- 진짜 효과 검증은 **사용자 PowerShell 실측** (Gemini 과금).
- 합성 4/4 통과가 실측 통과를 의미하지 않음 — R10 합성 4/4 통과 후 실측 실패한 전례 인지.

## 4. 게이트 (실측 시)

보고서 §추천 R12b 게이트를 그대로:

| 지표 | 기준 | 근거 |
|---|---|---|
| 🔴 `post_guard.fn` | **= 0** (절대 사수) | R11에서 깨진 게이트 — 깨지면 즉시 revert |
| `post_guard.fp` | ≤ 14 | R11 비교점 — 악화 금지 |
| 건조 발화 (`pred_status="건조"` 카운트) | **> 0** | 1차 목표. 합성으론 검증 불가, 실측에서만 확인 |
| 건강행 `pred="건조"` | = 0 | 새 건조 FP 위험 신호 |
| `pred_status` 분포 | 5종 균형 점검 | escalation 경향이 cause-status 정합으로 완화되는지 |
| latency_sec.mean | R11 20.234s 대비 ±10% | 프롬프트 길이 증가로 인한 지연 추적 |

앵커: `eval/after_acc_r7_dry_guard.json` (R8)
비교: `eval/after_acc_r10_v2_rag_ok.json` (R11)

## 5. 측정 절차 (사용자 PowerShell)

```powershell
$env:RUN_EVAL_OUT="after_acc_r12b_cause_status.json"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

- `RUN_EVAL_OUT` 설정 확인 필수 — 미설정 시 baseline.json 덮어쓰는 ACC-fix 사고 재발 방지.
- R12-0에서 추가된 자가점검 (`_probe_rag_collections`)이 b_dataset_rag 정상 적재 확인 후 측정 시작.
- 자가점검 실패 시 exit 2로 중단, Gemini 호출 0건 보장.

## 6. 결과 보고서 위치

- `docs/work_history/R12b_cause_status_consistency_result.md` (실측 후 사용자가 결과 받으면 CC가 분석 보고서 작성)
- 보고서 구조:
  1. 게이트 5종 통과/실패 표
  2. 5-status 혼동표
  3. 건조 6건 case별 변화 (pre R11 → post R12b)
  4. cause-status 정합 위반 사례 잔존 여부 (003·008이 진짜 교정됐는지)
  5. 부수효과 분석 (다른 케이스 영향, FP 변화 분해)
  6. R12a 설계 입력 (R12b 후에도 남은 FN/FP 패턴)

## 7. 커밋 컨벤션

- `feat: add cause-status consistency constraint to STRUCTURED_DIAGNOSIS_JSON_SYSTEM (R12b)`
- 합성 검증 결과는 같은 커밋에 포함하거나 docs 분리 커밋
- 푸시는 사용자 검토 + 실측 통과 후 일괄

## 8. 시작 전 확인

CC가 작업 착수 전 다음을 확인 보고:
- 현재 브랜치/tip — R12-0 푸시 후 상태인지 (`main` + R12-0 두 커밋 반영)
- `prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 현 상태 — R10 황화 충돌룰 위치 확인, 룰 추가할 자리 미리 식별
- R10 황화 충돌룰 변경 없음을 명시 (변수 격리 보증)

## 9. 보고서 후 다음 단계 (참고용 — 이 라운드 범위 X)

- **R12a**: guard hotfix — `_symptom_is_cosmetic`에 위치 veto (`아래/아래쪽/하엽/하부`). FN 케이스가 R12b로 해결되지 않은 경우 진행.
- **R12c**: RAG 보강 — 건조 카드 5~8장 신설 + `abiotic-water` problem_type 추가 + 검색 부스트 + Chroma 재적재. 사용자가 "시간/과금 들여도 본질적으로 RAG 튼튼하게"라고 명시했으므로 충실하게 설계.

R12b 측정 결과에 따라 다음 라운드 우선순위·범위 재조정.
