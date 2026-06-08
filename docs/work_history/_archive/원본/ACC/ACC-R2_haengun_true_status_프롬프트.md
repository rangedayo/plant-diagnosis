# ACC-R2: 행운목 5장 `true_status="건조"` 입력 + 전체 검증

## 컨텍스트

`context_v24_accuracy_track_R1_datahygiene_done.md` §3, §5, §6, §8, §9 참조.
- R1(라벨 스키마) + 데이터위생 완료 상태.
- 사용자가 행운목 5장(`self_haengun_002·003·005·006·008`) 사진을 직접 검토 → **`true_status="건조"` 결정** (잎끝·일부 잎 완전 갈변·고사 패턴, 사용자 본인 식물의 동일 개체 다각도 촬영).
- 이번 라운드 = `labels.json` 5건 입력 + 전체 데이터셋 검증 + atomic 커밋.

> 주의: §9 "라벨링 자동화 금지" 원칙 위배 아님 — 이번 5건은 **사용자가 직접 결정한 값**을 단순 입력하는 작업. CC가 라벨 값을 추정·확장하는 것이 아님.

## 작업 범위 (scope)

### 수정 대상
- `test_data/main_eval/labels.json` — 5개 항목의 `true_status` 필드만

### (필요 시) 추가 대상
- 전체 데이터셋 validate 진입점이 부재할 경우 신설 (예: `scripts/validate_main_eval.py`). 기존에 동등 기능 진입점이 있으면 재사용하고 신설 금지.

### 금지 (가드)
- `main_rag` 명명 변경 ([B-2] 보류, §7)
- `test_data/moneyplant_candidates/` 폴더 일체 수정·이동·삭제 (R3에서 별도 라운드)
- 다른 평가셋(`plantvillage_50` 등)·RAG DB·`eval/baseline*.json` 수정
- 5건 외 라벨 값 변경·추정·확장
- `labeling_vocab.py` 변경 (R1에서 확정, 이번 라운드 무변경)

## 절차

### Step 1 — Read-only 선결 게이트 (§8)

변경 전 다음을 **읽기 전용으로 보고**. 불일치·예상 외 상태 발견 시 중단하고 사용자에게 질의.

1. `test_data/main_eval/labels.json` 전체 항목 수 및 status 분포 요약 (현재 33장 예상, 28장 건강 + 5장 TODO)
2. 5개 대상 항목 현재 상태 출력 (each: `is_healthy`, `true_status`, 기타 필드):
   - `self_haengun_002`
   - `self_haengun_003`
   - `self_haengun_005`
   - `self_haengun_006`
   - `self_haengun_008`
3. 위 5개 항목이 모두 `is_healthy: false`이고 `true_status` 미설정(null/TODO/누락)인지 확인
4. 5개 외 다른 항목 중 `true_status` 미설정 항목 존재 여부 (있으면 보고, 본 라운드 범위 외이므로 손대지 않음)
5. `test_data/labeling_vocab.py`의 `STATUS_VOCAB`, `STATUS_AMBIGUOUS` 현재 값 출력 (확인용)
6. 전체 데이터셋 validate 진입점 존재 여부 (`scripts/`·`test_data/` 내 grep). 없으면 Step 3에서 신설 예정 명시.

### Step 2 — 5건 입력

Step 1 보고 검증 후:
- 5개 항목 각각 `true_status: "건조"` 입력
- **다른 필드 절대 수정 금지** (`is_healthy`·`image`·`species` 등 기존 값 유지)
- BOM 없는 UTF-8 유지 (§9)
- JSON 들여쓰기·키 순서·trailing newline 기존 스타일 유지

### Step 3 — 전체 검증

1. 진입점:
   - Step 1에서 기존 진입점 확인됐으면 실행
   - 없으면 `scripts/validate_main_eval.py` 신설 — `labeling_vocab.validate_label`로 `labels.json` 전체 순회, 결과 집계 출력. 인자 없이 실행, 종료 코드 = 위반 수
2. 검증 항목 (모두 0건이어야 함):
   - `validate_label` ValueError 0
   - `true_status` 미설정·TODO 0
   - enum 위반 0 (`STATUS_VOCAB ∪ STATUS_AMBIGUOUS` 외 값 0)
   - `is_healthy ↔ true_status` 정합성 위반 0
     - `is_healthy=true` ↔ `true_status="건강"`
     - `is_healthy=false` ↔ `true_status ∈ {과습, 건조, 병해 의심, 영양 부족, ambiguous}`
3. 출력:
   - status별 count (5-status + ambiguous, 총합 = 전체 항목 수)
   - 항목 수 일치 확인

### Step 4 — Atomic 커밋

검증 모두 통과 후:

1. validate 진입점 **신설했을 경우** 별도 커밋 분리:
   - `feat(scripts): main_eval 전체 validate 진입점 추가`
2. 라벨 입력 커밋:
   - `feat(eval): ACC-R2 행운목 5건 true_status="건조" 입력`
   - 본문에 5개 파일명·status 분포 변화 (before/after) 명시
3. 본 작업 프롬프트 보존 커밋:
   - 이 `.md` 파일을 `docs/work_history/ACC-R2_haengun_true_status_프롬프트.md`로 복사
   - `docs(work_history): ACC-R2 작업 프롬프트 보존`

3개 커밋 모두 푸시.

## 완료 보고 (사용자에게)

- status별 분포 (before/after 표)
- 변경된 파일·라인 수
- 신설 파일 (있다면)
- 커밋 해시(들)
- 검증 통과 여부
- 다음 후보 라운드: **R3 — Money Plant `bacterial_wilt`·`healthy` 검수·편입** (manganese_toxicity는 §4 결정에 따라 편입 보류·보관만)
