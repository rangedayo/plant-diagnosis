# R12-0 — Read-Only 진단 라운드 (RAG 호출 + Guard 조건 + b_dataset 카드 존재)

## 0. 라운드 목적

R11 측정 결과 `recall=0.875` (FN=1), `FP=14`, 건조 발화 0 — R10은 게이트 5개 중 4개 위반으로 실패 판정됨. R12 본 라운드(R12a guard hotfix → R12b generate 단순화 → R12c RAG 보강) 설계 전, **세 영역 동시 read-only 진단**을 수행해 다음 두 가지를 확정한다:

1. **현재 동작 사실 확정**: graph.py의 RAG 호출 흐름, guard 발동 조건, b_dataset_rag 컬렉션의 카드 분포 — 추측이 아닌 코드/DB 기반으로 보고.
2. **다음 라운드 설계 입력**: 진단 결과로 R12a/R12b/R12c 각각의 설계 방향과 우선순위가 자동 도출되게 한다.

R11 분석에서 외부 검토자가 짚은 핵심 통찰 세 가지가 진단의 출발점:
- **cause–status 모순**: generate가 텍스트 결론에서는 건조를 인식했는데 enum에서는 다른 카테고리를 고름 (haengun_003 사례).
- **analyze 4축의 양날의 검**: 건조 케이스에 변별 단서가 들어왔지만, 건강 케이스에서도 표현이 강화되어 FP 폭증 가능성.
- **guard의 구조적 취약점**: 위치+변색 토큰만으로 cosmetic 판정 → 진행성 신호가 있어도 건강으로 over-correct.

## 1. 절대 제약 (Read-Only 게이트)

다음 행위는 **전부 금지**:
- `app/`, `scripts/`, `eval/`, `prompts.py`, `graph.py`, `model_utils.py` 등 **소스 코드 어떤 파일도 수정 금지**.
- `run_eval.py` 실행 금지 (Gemini 과금 위험 + baseline 덮어쓰기 위험).
- `build_b_dataset_rag.py` 실행 금지 (재적재 위험, 임베딩 과금).
- Chroma 컬렉션 **수정·삭제·재구성 금지** (조회만 허용).

**허용되는 행위**:
- 코드 파일 `view` (라인 인용 포함).
- Chroma DB **조회 전용** 스크립트를 `scripts/diagnostics/` 또는 `tools/` 임시 디렉터리에 생성해도 됨 — 단, 컬렉션을 변경하지 않는 select-only 코드여야 하고, **읽기 모드**로 client를 열 것 (`PersistentClient`는 OK, `delete_collection`/`upsert`/`add`/`update`/`modify` 호출 금지).
- pytest 실행 금지 (변경 없으므로 의미 없음).

이 라운드는 **보고서 한 개의 생성과 docs 커밋이 전부**다. 코드/DB는 그대로 유지된다.

## 2. 세 진단 영역 명세

### 영역 A — graph.py의 RAG 호출 흐름

#### A.1 무엇을 봐야 하는가
`app/graph.py`의 RAG 관련 부분을 읽고, **observed_symptoms가 RAG 검색 결과로 변환되기까지의 정확한 흐름**을 단계별로 보고.

- 어떤 함수 (또는 노드)에서 RAG가 호출되는가? (시그니처와 호출 위치)
- 입력: `observed_symptoms`가 그대로 쿼리 텍스트로 들어가는가, 아니면 추출/번역/요약/concat 등 가공 단계가 있는가? **가공이 있다면 코드 그대로 인용**.
- 컬렉션 분리: `a_dataset_rag`(보조)와 `b_dataset_rag`(메인) 각각 어떤 query로, 어떤 `top_k`로 호출되는가? :543·:546 부근 코드를 인용.
- 결과 후처리: top_k 결과를 어떻게 top_3로 좁히는가? 메타데이터(`card_id`, `problem_type`, `source`, `title`, `sim`)는 어디서 가져와 어떻게 generate에 전달되는가?
- `RAG_SYMPTOM_KEYWORD_MAX` 같은 상수가 있다면 어디에 정의돼 있고 무엇을 통제하는가?

#### A.2 보고서에 들어가야 할 것
- **흐름도** (텍스트 다이어그램): observed_symptoms → (가공) → query → 컬렉션 호출 → 결과 → generate 입력
- 각 단계의 **코드 인용** (파일·라인 명시)
- **검토자 가설 검증**: "observed_symptoms가 keyword 단계에서 그대로 검색 키워드가 된다"가 사실인가? 가공이 있다면 어떤 가공인가?
- **언어 매칭 확인**: observed_symptoms는 한국어. b_dataset_rag 카드 텍스트는 영어 (예: `Brown leaf tips • Chemical`, `Whiteflies`). 한국어 쿼리로 영어 카드를 어떻게 매칭하는가? 임베딩 모델이 cross-lingual인가, 아니면 어딘가에서 번역하는가?

### 영역 B — Guard 조건 (현재 구조)

#### B.1 무엇을 봐야 하는가
`apply_status_guard()`, `_symptom_is_cosmetic()`, 그리고 관련 상수(`STATUS_GUARD_LESION_TOKENS`, `STATUS_GUARD_COSMETIC_LOCATION`, `STATUS_GUARD_COSMETIC_DISCOLOR` 등)의 정의 위치와 전체 내용을 확인.

- 가드 발동 사유(`by_reason` 키)는 총 몇 종류가 정의돼 있는가? 각각의 트리거 조건은?
- `_symptom_is_cosmetic()` 의 판정 로직: 어떤 토큰을 어떤 조건(AND/OR)으로 매칭하는가?
- 각 토큰 리스트(LESION, COSMETIC_LOCATION, COSMETIC_DISCOLOR)의 **전체 내용을 그대로 인용**.
- 가드가 reroute할 수 있는 status는 무엇무엇인가? 어떤 상태에서 어떤 상태로?

#### B.2 haengun_006 케이스 추적
입력 데이터:
- `observed_symptoms = ["아래쪽 잎의 끝과 가장자리 갈변"]`
- `top_3 problem_types = ["abiotic", "", "nutrient"]`
- `pre_status = "병해 의심"`, `post_status = "건강"`, `guard_reason = "all_cosmetic_nondisease_top1"`

이 입력으로 `_symptom_is_cosmetic()`이 True를 반환하는 **정확한 경로**를 코드 기준으로 단계별로 추적. 어느 토큰이 매칭됐고, 어느 토큰이 매칭되지 않아서 통과했는지.

#### B.3 보고서에 들어가야 할 것
- 가드 발동 사유 전체 목록 + 각 트리거 조건 한 줄 요약
- `_symptom_is_cosmetic()` 의사코드 또는 흐름도
- LESION/COSMETIC_LOCATION/COSMETIC_DISCOLOR 토큰 리스트 인용
- haengun_006 추적 결과 (어느 토큰이 어디서 매칭됐는가)
- **현재 가드가 "진행성/범위 토큰"(`전체`, `여러`, `고사`, `처짐`, `주름`, `확산`, `괴사`, `마름` 등)을 보는가**? 안 본다면 어디에도 등장하지 않는다는 사실을 확인.

### 영역 C — b_dataset_rag 컬렉션의 카드 분포

#### C.1 무엇을 봐야 하는가
Chroma `b_dataset_rag` 컬렉션을 **읽기 전용**으로 조회해서 다음을 확인:

- 컬렉션 총 카드 수 (컨텍스트상 82건 — 일치하는지 확인)
- `problem_type` 메타데이터 별 카드 수 분포 (예: `disease: N, pest: M, abiotic: K, ...`)
- `source` 별 카드 수 분포 (mobot_indoor, psu_ucanr, mu_trinklein, ...)
- **건조 관련 카드 존재 여부**: 다음 키워드 각각에 대해, `title`/`body`/`metadata`에 포함된 카드 수와 ID 리스트를 조사:
  - 영어: `underwatering`, `drought`, `dry soil`, `dehydration`, `water stress`, `low humidity`, `wilting`, `crispy`, `leaf scorch`
  - 한국어: `건조`, `수분 부족`, `물 부족`, `시듦`

#### C.2 실제 건조 케이스의 검색 결과 깊이 확인
임시 진단 스크립트를 작성해서, R11의 건조 6건(`self_haengun_002`, `_003`, `_005`, `_006`, `_008`, `inat_epipremnum_aureum_004`) 각각의 `observed_symptoms`를 **그대로 RAG 쿼리로 던졌을 때 top_10**까지 어떤 카드가 잡히는지 보고:

- 케이스별 top_10 카드 ID + problem_type + sim score + title
- top_10에 C.1에서 찾은 "건조 관련 카드"가 들어 있는가? 들어 있다면 몇 위인가?

이 진단은 **graph.py의 실제 RAG 호출 함수를 임포트해서** 그대로 호출하는 것이 가장 정확하다. 단, 새로운 측정이 아니므로 Gemini 호출은 발생하지 않게 할 것 — `observed_symptoms`는 R11 결과 JSON(`eval/after_acc_r10_v2_rag_ok.json`)의 `per_case`에서 그대로 가져와 재사용. analyze 단계는 재실행 금지.

#### C.3 보고서에 들어가야 할 것
- 컬렉션 메타 통계 (총 카드 수, problem_type 분포, source 분포)
- 건조 관련 카드 존재 여부 — **있다 / 약하게 있다(짧거나 비특이적) / 없다** 셋 중 하나로 결론
- 6건 case별 top_10 결과 표
- **결론적 분류** (R12c 설계에 직접 입력):
  - 층위 A 실패 (DB에 카드 없음)
  - 층위 B 실패 (카드 있는데 다른 카드에 밀림 — 검색/임베딩 문제)
  - 층위 C 실패 (카드 있는데 problem_type이 broad해서 generate가 status로 못 옮김)
  - 또는 복합

## 3. 산출물

### 3.1 보고서 파일
- 경로: `docs/work_history/R12_0_readonly_diagnosis.md`
- 구조:
  1. 라운드 헤더 (목적 / 게이트 / 절대 제약 재확인)
  2. 영역 A 보고
  3. 영역 B 보고 (haengun_006 추적 포함)
  4. 영역 C 보고
  5. **종합 시사점** — R12a / R12b / R12c 각각의 설계 방향에 어떤 입력이 도출됐는가, 한 섹션당 3~5줄로 요약
  6. **확정된 사실 vs 남은 불확실성** 구분 표 — 진단으로 확정된 것과 측정해야만 알 수 있는 것을 분리
  7. **다음 라운드 추천** — R12a를 어떻게 설계해야 하는지 (구체 토큰/조건 후보 포함)

### 3.2 임시 진단 스크립트 (선택)
영역 C.2 수행에 필요하다면 `scripts/diagnostics/r12_0_probe_rag.py` 같은 경로로 생성. **단 read-only 보장 필수**:
- Chroma client는 일반 PersistentClient로 열되, `add`/`upsert`/`update`/`delete`/`modify_*` 함수 호출 절대 금지.
- Gemini/OpenAI API 호출 0건.
- 스크립트 자체는 다음 라운드에도 재사용할 수 있게 보존. 커밋 메시지에 명시.

### 3.3 변경 금지 파일 명시
보고서 끝에 "이 라운드에서 변경한 파일: `docs/work_history/R12_0_readonly_diagnosis.md` (+ 선택적으로 `scripts/diagnostics/r12_0_probe_rag.py`). 그 외 어떤 파일도 변경하지 않았음" 라는 확인 문장 명시.

## 4. 커밋 컨벤션

- **단일 커밋** 또는 두 커밋:
  - `docs: add R12-0 readonly diagnosis report (RAG flow + guard + b_dataset coverage)`
  - (스크립트 분리 시) `chore: add scripts/diagnostics/r12_0_probe_rag.py (read-only Chroma probe)`
- 푸시는 사용자 검토 후. 보고서 본문에서 의문점이나 불일치가 발견되면 푸시 보류 + 즉시 보고.

## 5. 보고 후 다음 단계 (참고용 — 이 라운드에서는 실행 X)

진단 결과를 받은 뒤, 사용자와 의논해서:
- **R12a**: guard hotfix 설계 (cosmetic 판정에 진행성·범위 토큰 블랙리스트 추가) → 변경 → 합성 검증 → 측정
- **R12b**: generate 단순화 + status-cause 일관성 제약 → 합성 검증 → 측정
- **R12c**: 영역 C 결과에 따라 카드 추가 또는 metadata status hint 또는 query 분리 중 하나 선택 → 진행

R12-0 보고가 부정확하면 후속 라운드 전체가 어긋난다. 추측 금지, 모든 주장에 코드/데이터 근거를 붙일 것.

## 6. 시작 전 마지막 확인

이 작업을 시작하기 전에 다음 한 가지를 확인해 보고하라:
- 현재 브랜치와 마지막 커밋 (R11 측정 직후 상태인지)
- `eval/after_acc_r10_v2_rag_ok.json` 존재 여부 (영역 C.2의 입력 데이터)
- `eval/after_acc_r7_dry_guard.json` 존재 여부 (R8 앵커, 비교용)
- 무효 R11 json (`after_acc_r10_analyze_generate.json`) 처리 상태 (삭제됐는지, untracked인지)

이 네 가지 확인 후 위 진단을 시작.
