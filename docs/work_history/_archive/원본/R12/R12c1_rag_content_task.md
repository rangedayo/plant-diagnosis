# R12c-1 — RAG 콘텐츠 묶음 (건조 카드 신설 + problem_type 확장 + 기존 카드 재분류)

## 0. 라운드 목적

R12-0 §C.3 진단: 건조 6건의 RAG 실패는 **층위 A(카드 빈약) + 층위 B(검색에서 밀림) + 층위 C(problem_type broad)**의 복합. R12b는 정합룰만 추가해 cause-status 모순은 잡았지만, **carrier(cause)에 "수분 부족"이 적혀야 정합룰이 발동**하는 의존성이 드러남(6건 중 1건만 교정).

이 라운드 목적: **콘텐츠 단위 변경 한 번**으로 RAG가 건조 신호를 실제 generate에 전달할 수 있게 한다.
- 건조 전용 카드 5~8장 신설 (사실상 "Too dry" 1장뿐인 현실 해소)
- problem_type 택소노미에 `abiotic-water` 신설 (또는 `status_hint` metadata 필드 추가)
- 기존 부분 매칭 카드 재분류
- Chroma 재적재 + 검증 강화 (6 건조 case 모두 top_10에 건조 카드 1장 이상 진입 확인)

검색 부스트(④)는 **이 라운드에 포함 안 함** — R12c-2로 분리. 콘텐츠만으로 효과 충분하면 R12c-2 생략, 부족하면 부스트 추가.

## 1. 절대 제약 (변수 격리)

이 라운드에서 변경 가능한 영역만 명시. 그 외 전부 동결:

**변경 가능**:
- `data/cards/` 또는 b_dataset 카드 source 파일들 (신규 카드 텍스트 + 기존 카드 메타 수정)
- `scripts/build_b_dataset_rag.py` (problem_type 신설 처리 + status_hint metadata 필드 추가 + verify 검증 강화)
- Chroma `b_dataset_rag` 컬렉션 (재적재 — 사용자 PowerShell 실행, 임베딩 과금)

**동결** (이번 라운드 변경 0):
- `app/prompts.py` 전체 (R12b 정합룰 유지)
- `app/graph.py` 전체 (retrieve_node, keyword_node, merge 로직 — R12c-2 영역)
- `apply_status_guard()`, STATUS_GUARD_* 토큰 (R12a 영역)
- `app/model_utils.py` `generate_english_keywords` (R12c-3-α 영역)
- `a_dataset_rag` 컬렉션 (메인 변수는 b만)

prompts.py가 카드 본문을 직접 받는 구조라 (R12-0 §A.4: `rag_chunks = prefix 박은 카드 본문 join`), 카드만 늘려도 generate 입력이 자동으로 풍부해짐. graph.py 변경 없이 효과 도달 가능.

## 2. 변경 명세

### 2.1 신설 카드 5~8장

**커버할 핵심 어휘** (R12-0 §C.1 0건 카드들):

| 어휘 클러스터 | 카드 1장 | 비고 |
|---|---|---|
| **Underwatering / Drought stress** | 1장 (필수) | 핵심 카드. 짧은 본문도 OK, title 명시 |
| **Water stress** | 1장 | 변형 표현 |
| **Leaf scorch (water-related)** | 1장 | Chemical scorch와 명시적 구분 |
| **Crispy brown leaf edges (water)** | 1장 | "Brown leaf tips • Chemical"과 임베딩 경쟁용 — 핵심 |
| **Low humidity damage** | 1장 (선택) | 실내 식물 맥락 |
| **Wilting from drought** | 1장 (선택) | 진행성 표현 |
| **Dehydration / Tissue dryness** | 1장 (선택) | 의학 표현 |
| **Brown crispy leaf tips (water-related)** | 1장 (선택) | Chemical 카드와 직접 경쟁 — title 거의 같지만 problem_type 다름 |

**최소 5장** (필수 4 + 선택 1)으로 시작, source 라이선스 사정에 따라 8장까지 확장.

### 2.2 카드 source 후보 (license-clean 우선)

**기존 사용 source 우선** (라이선스 검증 완료, 톤·형식 일관):
- `mobot_indoor` (Missouri Botanical Garden Plant Finder) — 권장
- `psu_ucanr` (Penn State Extension + UC IPM) — 권장
- `mu_trinklein` (Univ of Missouri Extension) — 권장

**확장 후보** (라이선스 확인 후 추가):
- UF/IFAS (University of Florida Extension) — public domain 또는 CC-BY
- NC State Extension — university extension
- AgriLife (Texas A&M) — public domain
- Other land-grant extension services

**비추천** (라이선스 또는 톤 문제):
- RHS (Royal Horticultural Society) — copyright 제한
- 일반 블로그·SNS — 출처 신뢰도 낮음

**라이선스 처리 — 매 신설 카드에 다음 필수 명시**:
```
source: <source 키>
source_url: <원문 URL>
license: "CC-BY 4.0" (또는 정확한 라이선스 명, **표기 통일** — v25 백로그 "CC-BY 4.0 ↔ CC BY 4.0" 같이 처리)
```

사용자(랑) 라이선스·source 검토 필요. CC가 카드 신설 완료 후 source URL 목록 + 라이선스 명세 + 카드 본문 요약을 사용자에게 보고하고 검토 통과 후 임베딩 진행.

### 2.3 problem_type 택소노미 확장

**현재 분포** (R12-0 §C.1): pest 28 · general 18 · disease 14 · abiotic 10 · env 8 · frame 2 · nutrient 2.

**신설 옵션 (3가지 비교)**:

| 옵션 | 내용 | 장점 | 단점 |
|---|---|---|---|
| (A) `abiotic-water` 신설 | abiotic 하위 카테고리화 | problem_type 기반 부스트(R12c-2) 용이 | 기존 코드의 problem_type 처리에 새 값 인식 필요 |
| (B) metadata `status_hint` 필드 신설 | 카드별로 enum 매핑 ("건조","병해 의심" 등) | generate가 enum 직결 매핑 가능, 코드 변경 최소 | problem_type은 그대로라 검색 부스트 단계에서 활용 어려움 |
| (C) 둘 다 (A + B) | problem_type=abiotic-water + status_hint=건조 | 검색·매핑 둘 다 강화 | 메타 키 2개 늘어남, build_b_dataset_rag.py 수정 늘어남 |

**권장: (C) 둘 다**. 너 "본질 우선" 정신과 부합. 비용 (메타 키 2개 추가)은 작고, 후속 R12c-2 검색 부스트와 generate enum 매핑 둘 다 활용 가능.

### 2.4 기존 카드 재분류

R12-0 §C.1에서 부분 매칭으로 잡힌 카드들 검토:

| card_id | 현재 problem_type | 본문 키워드 | 재분류 결정 (CC가 본문 확인 후 판정) |
|---|---|---|---|
| `mobot_indoor_001` "Too dry" | env | drought | → `abiotic-water` + `status_hint="건조"` (확정) |
| `mu_trinklein_012` | general | dry soil 부분 매칭 | 본문 확인 후 판정 |
| `mobot_indoor_006` | ? | drought 부분 매칭 | 본문 확인 후 판정 |
| `mobot_indoor_009` | ? | drying 부분 매칭 | 본문 확인 후 판정 |
| `psu_ucanr_015` | ? | scorch 부분 매칭 | 본문이 chemical scorch면 그대로, water scorch면 재분류 |

재분류 결과는 보고서에 카드별로 판정 근거와 함께 기록.

### 2.5 build_b_dataset_rag.py 수정

- problem_type 신값 `abiotic-water` 인식 + 빌드 처리
- 메타 키 `status_hint` 추가 (값: "건강" / "과습" / "건조" / "병해 의심" / "영양 부족" / 또는 null)
- **verify_b_dataset_query 검증 강화**:
  - 기존: 컬렉션 정상 적재 + sample query
  - 추가: 6 건조 case (`self_haengun_002/003/005/006/008`, `inat_epipremnum_aureum_004`)의 observed_symptoms (R11/R12b JSON에서 채취) 각각으로 영문 쿼리 시뮬레이션 → **top_10에 `problem_type=abiotic-water` 카드 ≥ 1장 진입 확인**
  - 실패 시 exit 2로 빌드 중단

## 3. Chroma 재적재 (사용자 PowerShell)

```powershell
.venv\Scripts\python.exe scripts\build_b_dataset_rag.py
```

- 임베딩 과금 발생 (ada-002, ~$0.01 미만으로 추산)
- verify_b_dataset_query 통과 후 컬렉션 commit
- 통과 못 하면 카드 추가/재분류가 실효 없는 거니 빌드 중단 → 카드 본문 또는 어휘 재검토 라운드 (R12c-1-α)

## 4. 합성 검증 (CC 수행)

### 4.1 build 단계 검증
- import OK
- pytest 기존 25건 회귀 없음
- build_b_dataset_rag.py local dry-run (Chroma 쓰기 없이 카드 로드·메타 검증만)

### 4.2 콘텐츠 검증
- 신설 카드 5~8장 본문 확인 — license-clean, 어휘 커버, 길이 적정
- 메타 필드 전수 확인 — title, card_id, problem_type, source, source_id, section, license, status_hint
- 기존 카드 재분류 결과 — 카드별 판정 근거 명시

### 4.3 한계 명시 (보고서에 기록)
- 합성 검증은 카드 콘텐츠와 메타 무결성만 확인.
- **임베딩 유사도는 실제 ada-002 호출 후에만 측정 가능** — verify_b_dataset_query가 그 역할.
- 빌드 자체 통과해도 실측에서 효과 보장 안 됨 — generate가 새 카드 본문을 어떻게 해석할지는 LLM 결정.

## 5. 게이트 (실측 시)

R12b 통과 게이트 유지 + R12c-1 특수 게이트 추가:

| 지표 | 기준 | 근거 |
|---|---|---|
| 🔴 `post_guard.fn` | **= 0** (절대 사수) | recall 게이트 |
| `post_guard.fp` | ≤ 14 | R11/R12b 비교점, 악화 금지 |
| 건조 발화 (`pred_status="건조"` 카운트) | **≥ 3** ⬆️ | R12b=1에서 진전 명시. 6건 중 절반 이상 |
| 건강행 `pred="건조"` | **≤ 2** | R12b=0에서 약간 완화. 건조 카드 풍부해지면 healthy→건조 위험 있음. 너무 엄격하면 R12c-1 자체가 위반 |
| **top_10 진입률** (build verify) | **6/6 case 모두 abiotic-water 카드 ≥ 1장 진입** | R12c-1의 RAG 측 실효 검증. build 단계에서 강제 |
| latency mean | ±10% from R11 baseline (18.2~22.3s) | R12b에서 outlier로 ⚠️였음. R12c-1 정상으로 복귀 기대 |

앵커: R8 `after_acc_r7_dry_guard.json`
비교: R12b `after_acc_r12b_cause_status.json`

## 6. 측정 절차 (사용자 PowerShell)

```powershell
$env:RUN_EVAL_OUT="after_acc_r12c1_rag_content.json"
.venv\Scripts\python.exe scripts\run_eval.py --aux
```

- 측정 전 build_b_dataset_rag.py가 완료된 상태 확인 (자가점검에 abiotic-water top_10 진입 확인 포함).
- 자가점검 실패 시 exit 2로 측정 중단, Gemini 호출 0건 보장.

## 7. 결과 보고서 위치 (CC가 실측 후 작성)

- `docs/work_history/R12c1_rag_content_result.md`
- 보고서 구조:
  1. 게이트 6종 통과/실패 표
  2. 5-status 혼동표 + R12b 대비 delta
  3. 건조 6건 case별 변화 (R12b → R12c-1): observed_symptoms·pred_status·pred_cause·top_3 RAG 카드
  4. 신설 카드의 검색 등장 빈도 (어떤 카드가 자주 잡혔는가)
  5. healthy→건조 부작용 분석 (≤ 2 게이트 점검)
  6. **R12c-2 진행 여부 판정**: 건조 발화 ≥ 3 + 6건 중 ≥ 3건 건조 분류 통과면 R12c-2 생략 가능. 아니면 검색 부스트로 다음 라운드.
  7. 라이선스 표기 정합 처리 결과 (v25 백로그 종결 가능 여부)

## 8. 커밋 컨벤션

3~4 커밋 권장:

1. `feat(rag): add 5~8 underwatering/drought cards to b_dataset (R12c-1)`
2. `feat(rag): introduce abiotic-water problem_type + status_hint metadata (R12c-1)`
3. `chore(rag): reclassify existing dry-adjacent cards to abiotic-water (R12c-1)`
4. `feat(build): extend verify_b_dataset_query with dry top_10 entry check (R12c-1)`

또는 4건이 너무 잘게면 2건으로 묶기:
- `feat(rag): add dry cards + abiotic-water taxonomy + status_hint (R12c-1)`
- `feat(build): extend verify with dry top_10 entry check + reclassify existing (R12c-1)`

라이선스 표기 통일(v25 백로그)은 카드 신설 커밋에 동봉 가능 — 어차피 메타 표기 변경.

## 9. 시작 전 확인

CC가 작업 착수 전 다음 확인 보고:
- 현재 브랜치/tip — R12b 결과 보고서 + 푸시 완료 상태인지
- `data/cards/` 또는 카드 source 파일들 위치 확인 (b_dataset 카드 어디서 어떻게 정의되는가)
- `build_b_dataset_rag.py`의 verify_b_dataset_query 현 구현 확인 (확장 지점 파악)
- 기존 카드 라이선스 표기 형식 (CC-BY 4.0 vs CC BY 4.0 어느 쪽이 표준인지)

## 10. 사용자 검토 게이트 (필수)

CC가 카드 신설 완료 후, **사용자 검토 없이 build 진행 금지**. 신설 카드 5~8장 각각에 대해:
- source URL
- license 명세 (정확한 형식)
- 카드 본문 (title + body 요약)
- 사용 의도 (어떤 핵심 어휘 클러스터 커버)

이 4종 정보를 사용자에게 정리 보고 후 "OK"받은 다음 build_b_dataset_rag.py 실행. 라이선스 미흡한 카드는 사용자 지시에 따라 제외 또는 source 재선정.

## 11. 다음 단계 (참고용 — 이 라운드 범위 X)

- R12c-1 결과에 따라 분기:
  - **건조 발화 ≥ 3 + 게이트 전부 통과** → R12c-2(부스트) 생략. R12a(가드 위치 veto) 또는 R12c-3-α(번역 프롬프트) 우선순위 재정렬.
  - **건조 발화 부족 또는 healthy→건조 FP 폭증** → R12c-2 부스트 또는 R12c-1-α(카드 본문 어휘 조정).
- R12c-1으로 라이선스 표기 통일(v25 백로그) 종결 가능.
- R13 영어화 트랙은 R12c 완료 + 안정화 후 별도 트랙으로.
