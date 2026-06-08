# R12d-1 — Surface-level 빼기 (R10 황화룰 + status_hint 메타 제거)

## 0. 라운드 목적

R12c-1 결과 평가에서 사용자가 짚은 통찰: **"계속 추가만 한다고 나아질 거 같지 않다. 우리가 건조에 과적합하고 있는 건 아닌가."**

R7 ~ R12c-1을 거치며 시스템에 쌓인 변경물들 중, **본질적 기여**와 **surface-level 패치**를 구분해서 후자를 제거. 빼기는 두 가지 목적:

1. **각 변경물의 진짜 기여도 분리 측정** — 지금은 R7 트리거·R10 룰·R12b 정합룰·R12c-1 카드·status_hint 다섯이 얽혀서 어느 게 효과 내는지 분리 불가
2. **확장성 회복** — 새 식물·새 증상 추가 시 룰을 또 추가하는 패턴에서 벗어남. 본질적 기여(카드)와 LLM 강제 매핑(메타)의 효과를 분리해 향후 방향 결정

이번 라운드에서 빼는 둘:
- **R10 황화 충돌룰** (prompts.py) — R11에서 효과 0 입증, 안전한 빼기
- **status_hint 메타 필드** (build_b_dataset_rag.py + Chroma 재적재) — R12c-1 healthy→건조 FP 7건의 유력한 원인

빼지 않는 것 (본질 보존):
- 새 건조 카드 6장 (`dry_supplement_001~006`) + 재분류 3장 (mobot_indoor_001·002, psu_ucanr_019)
- `abiotic-water` problem_type 라벨
- R12b cause-status 정합룰
- 가드 (사용자 결정 — 위치 veto 추가도 보류, 현 상태 그대로)

## 1. 절대 제약 (변수 격리)

**변경 가능**:
- `app/prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM`에서 R10 황화 충돌룰 블록만 제거 (R12b 정합룰 유지)
- `scripts/build_b_dataset_rag.py`에서 status_hint metadata 처리 코드 제거
- 카드 source 파일 (status_hint 필드 제거)
- Chroma `b_dataset_rag` 컬렉션 재적재 (사용자 PowerShell)

**동결**:
- `app/graph.py` 전체 (retrieve_node, keyword_node, merge 로직, status_guard 토큰 — 가드는 사용자 결정으로 보류)
- `app/model_utils.py` 전체
- abiotic-water problem_type — **유지** (status_hint와 별개, 카드 분류의 의미 있는 부분)
- 신설 카드 6장 본문 — **유지** (status_hint 필드만 빼고 본문은 그대로)
- 재분류 3장의 problem_type — **유지** (abiotic-water 그대로)
- R12b 정합룰 — **유지** (003·008 해결한 본질적 진전)
- `a_dataset_rag` 컬렉션

## 2. 변경 명세

### 2.1 R10 황화 충돌룰 제거

위치: `app/prompts.py`의 `STRUCTURED_DIAGNOSIS_JSON_SYSTEM` 안 (R12-0 §A.4 인용에 따르면 :87 부근, R12b 정합룰 직전).

처리: **블록 완전 제거**. 효과 0 입증됐고 generate 프롬프트 단순화 효과도 있음.

R12b 정합룰은 그대로 유지 — cause-status 매핑 4종(건조·과습·영양 부족·병해 의심) 블록은 보존.

### 2.2 status_hint 메타 필드 제거

위치: `scripts/build_b_dataset_rag.py` + 카드 source.

처리:
- 카드별 `status_hint` 필드 정의 제거 (신설 6장 + 재분류 3장 모두)
- build_b_dataset_rag.py의 status_hint 처리 로직 제거 (override 처리 등)
- 메타 키 목록에서 status_hint 제거
- problem_type, license, source_url 같은 다른 메타는 유지

**유지되는 메타 필드** (재확인):
- title, card_id, problem_type, source, source_id, section
- license, source_url (R12c-1에서 추가, 유지)

### 2.3 verify_b_dataset_query 조정

`verify_dry_top10_entry` 검증은 **유지**. 단 status_hint 제거 후에도 abiotic-water 카드가 top_10에 진입하는지 확인 — 검색 자체는 problem_type 기반이라 영향 없을 것으로 예상하지만 측정으로 확인.

기준 그대로: 6 건조 case 모두 top_10에 `problem_type=abiotic-water` 카드 ≥ 1장 진입. 실패 시 exit 2.

### 2.4 EXPECTED_TOTAL 검증

R12c-1에서 EXPECTED_TOTAL 88로 동적화됨. status_hint 제거는 카드 수 영향 없음 — 88 그대로 유지.

## 3. Chroma 재적재 (사용자 PowerShell)

```powershell
.venv\Scripts\python.exe scripts\build_b_dataset_rag.py
```

- 임베딩 과금 발생 (status_hint 메타만 빠진 거라 본문 동일 → 캐시 활용 가능하면 비용 미미)
- verify_dry_top10_entry 통과 후 컬렉션 commit
- 통과 못 하면 status_hint 빠진 것이 검색에 영향 줬다는 신호 → 진단 라운드 분기

## 4. 합성 검증 (CC 수행)

### 4.1 build 단계 검증
- import OK
- pytest 기존 25건 회귀 없음
- build_b_dataset_rag.py dry-run (Chroma 쓰기 없이 카드 로드·메타 검증) — status_hint 필드 부재 확인

### 4.2 콘텐츠 검증
- 신설 카드 6장 본문 그대로 유지 확인 (status_hint 필드만 제거)
- 재분류 3장 problem_type 그대로 유지 확인 (abiotic-water 유지)
- prompts.py에서 R10 황화룰 블록 완전 제거 확인 + R12b 정합룰 보존 확인

### 4.3 한계 명시
- status_hint 제거의 효과는 LLM 결정에 달림. 합성으로 보장 불가.
- R12c-1과 동일한 분포 측정 결과를 기대하지 않음 — healthy→건조 FP 감소, 건조 TP도 약간 감소 가능

## 5. 게이트 (실측 시)

R12c-1 게이트 기준 그대로 + 두 가지 추적 지표 추가:

| 지표 | 기준 | R12c-1 | 비교 의미 |
|---|---|---|---|
| 🔴 `post_guard.fn` | **= 0** (절대 사수) | 1 | recall 게이트. 깨지면 즉시 R12a 분리 라운드로 |
| `post_guard.fp` | ≤ 14 | 17 | R11/R12b 비교점, 악화 시 빼기 효과 분석 |
| 건조 발화 | ≥ 3 | 11 | R12d-1로 폭증 완화 기대. ≥ 3 유지가 본질 진전 보존 신호 |
| **건강행 pred=건조** | **≤ 2** | 7 | **R12d-1의 핵심 검증 지표** — status_hint 제거가 healthy FP 줄이는지 |
| top_10 진입률 6/6 (build) | 6/6 | 6/6 | status_hint 빠져도 검색은 problem_type 기반이라 유지 기대 |
| latency mean | ±10% | 21.323s ✅ | 정상 범위 유지 |
| **TP 보존** (추가) | haengun_002·003·008·epipremnum_004 중 ≥ 2건 건조 유지 | 4건 | R12c-1의 본질 진전이 status_hint 없이도 유지되는지 |
| **R10 황화룰 영향** (추적) | — | — | 황화룰 제거 전후 분포 비교 (효과 0 재확인) |

앵커: R8 `after_acc_r7_dry_guard.json`
비교: R12c-1 `after_acc_r12c1_rag_content.json`

## 6. 측정 절차 (사용자 PowerShell)

```powershell
$env:RUN_EVAL_OUT="after_acc_r12d1_remove_surface.json"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

자가점검 (verify_dry_top10_entry) 통과 확인 후 측정 시작.

## 7. 결과 보고서 위치 (CC가 실측 후 작성)

- `docs/work_history/R12d1_remove_surface_result.md`
- 보고서 구조:
  1. 게이트 점검 표 (R12c-1 비교)
  2. 5-status 혼동표 + R12c-1 대비 delta
  3. **healthy→건조 FP 변화 추적** (R12c-1 7건 → R12d-1 몇 건? 어떤 케이스가 어디로 옮겨갔나)
  4. **TP 보존 추적** (haengun_002·003·008·epipremnum_004가 건조 유지하는지)
  5. R10 황화룰 제거의 직접 효과 (분포 변화 없음 확인)
  6. status_hint 제거의 직접 효과 (cause 텍스트 변화, status 매핑 변화)
  7. haengun_006 FN 재발 여부 (재발 시 다음 액션 R12a로)
  8. R12d-1의 본질 분리 측정 — 어느 변경(R12b 정합룰 vs status_hint vs 카드 본문)이 어떤 효과 냈는지 가능한 한 분리

## 8. 커밋 컨벤션

2 커밋 권장:

1. `refactor(prompts): remove R10 chlorosis conflict rule (effect=0, R11 verified)`
2. `refactor(rag): remove status_hint metadata (keep problem_type=abiotic-water)`

라이선스 표기는 R12c-1에서 처리 완료 — 추가 작업 없음.

## 9. 시작 전 확인

CC가 작업 착수 전 확인 보고:
- 현재 브랜치/tip — R12c-1 측정 후 상태인지 (`a7a835a` + R12c-1 결과 보고서 푸시 완료 여부)
- `prompts.py` R10 황화룰 블록의 정확한 시작·끝 라인 (제거 범위 명확화)
- 카드 source 파일에서 status_hint 정의 위치 (9장 카드 모두 필드 일관 제거)
- build_b_dataset_rag.py의 status_hint 처리 로직 분포 (override·메타 작성·verify 등)

## 10. FN 발생 시 처리 원칙

빼기 라운드라 "다시 추가"가 revert 방향임을 인지. 측정에서 post.fn=1 발생 시:

- **status_hint 다시 추가하지 않음** — 빼기 효과 검증이 본 라운드 목적
- 대신 **R12a 가드 위치 veto를 분리 라운드로 진행** — 사용자 결정대로 이번엔 가드 보류했지만, FN 재발 시 가드는 가장 정확한 안전망
- R12d-1과 R12a를 변수 격리해서 두 효과(빼기 + 가드)를 독립적으로 가늠

## 11. 다음 단계 (참고용 — 이 라운드 범위 X)

R12d-1 결과에 따라 분기:

| 결과 | 다음 액션 |
|---|---|
| 게이트 통과 (healthy FP 감소, TP 보존, FN 0) | **빼기 성공.** R12 트랙 종결 검토. 남은 surface-level(R12b 정합룰) 빼기 시도 가능 (R12d-2) |
| healthy FP 감소했지만 FN 재발 | **R12a 가드 위치 veto** 분리 라운드 |
| healthy FP 감소 없거나 TP 폭락 | status_hint 외 다른 원인 — read-only 진단 라운드 (R12d-0 후행) |
| 게이트 광범위 위반 | R12c-1 시점으로 부분 revert + 진단 |

## 12. 라운드 의의 — "본질 vs Surface" 분리

이 라운드는 단순한 빼기가 아님. **시스템에 어떤 변경이 본질이고 어떤 게 surface인지 분리하는 진단 라운드**. 결과로 향후 식물·증상·카드 추가 시 어떤 차원에서 접근해야 일반화되는지 학습. 결과가 어떻든 분리 측정 자체가 가치.
