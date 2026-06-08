# [정확도 트랙 R1] 라벨 스키마 마이그레이션 — CC 작업 프롬프트

> 트랙: 1차 진단 정확도 — 첫 코드 라운드
> 설계 근거: `docs/design/design_accuracy_track.md` §4 결정4 · §5 · §7-1
> 성격: Python 코드(공통 모듈 + 스크립트). 진단/프론트 코드 무관.

---

## 0. 목적

기존 평가셋 라벨(`test_data/main_eval/labels.json`, 9종 33장)에 **5-status 정답 라벨(`true_status`)**을 추가할 수 있도록 라벨 스키마를 확장한다. 이번 라운드는 **스키마·검증·마이그레이션 도구**까지만이며, 비건강 케이스의 status 값 채우기는 다음 라운드(사람 작업)다.

---

## 1. read-only 선결 게이트 (변경 전 먼저 보고)

코드를 건드리기 전에 아래를 읽고 **현황을 보고**하라. 보고 내용이 이 프롬프트의 전제와 어긋나면 **중단하고 질문**하라.

1. `test_data/labeling_vocab.py` — 현재 `SYMPTOM_VOCAB`, `PLANT_NAME_KO_MAP`, `ALLOWED_LICENSES`, `validate_label`, `validate_dataset`의 정의. 특히 `validate_label`의 필수 필드 집합과 검증 규칙.
2. `test_data/main_eval/labels.json` — 현재 항목 수, 각 `ground_truth`의 키, `is_healthy` 분포(true/false 각 몇 개).
3. `app/model_utils.py` — `ALLOWED_STRUCT_STATUS` 정의 위치와 5종 값(공백 포함 정확히).
4. `scripts/` 디렉토리 — 기존 스크립트 코드 스타일(argparse, `--dry-run` 패턴, print 로깅).

**보고 형식**: 위 4개 각각 1~2줄 요약. 특히 (a) `labels.json` 항목 수와 is_healthy 분포, (b) `ALLOWED_STRUCT_STATUS` 5종 값이 `["건강","과습","건조","병해 의심","영양 부족"]`과 정확히 일치하는지.

---

## 2. 작업 A — `test_data/labeling_vocab.py` 갱신

### 2-1. 신규 상수 추가

```python
# 5-status 정답 라벨용 enum (app/model_utils.py ALLOWED_STRUCT_STATUS와 동일 5종)
STATUS_VOCAB: list[str] = ["건강", "과습", "건조", "병해 의심", "영양 부족"]

# 사람이 잎 사진만으로 5종 판정이 곤란한 케이스 → 평가에서 제외
STATUS_AMBIGUOUS: str = "ambiguous"
```

> ⚠ `STATUS_VOCAB` 값은 §1에서 확인한 `ALLOWED_STRUCT_STATUS`와 **글자·공백까지 정확히 일치**해야 한다("병해 의심"의 공백 포함). 불일치 시 중단·보고.

### 2-2. `validate_label` 갱신

기존 검증은 유지하고 다음을 추가한다:

- `required` 필수 필드 집합에 `"true_status"` 추가.
- `true_status` enum 검증: `STATUS_VOCAB` ∪ `{STATUS_AMBIGUOUS}`에 없는 값이면 `ValueError`.
- `is_healthy ↔ true_status` 방향 정합성 (ambiguous는 면제):
  - `true_status == "건강"`인데 `is_healthy == False` → `ValueError`
  - `true_status ∈ {"과습","건조","병해 의심","영양 부족"}`인데 `is_healthy == True` → `ValueError`
- **기존 규칙 유지**: `is_healthy=True` + `symptoms=[...]` 조합은 계속 허용(드라세나 잎끝 마름 등 경증). `true_status="건강"` + 비어있지 않은 `symptoms`도 허용.

> 마이그레이션 직후 비건강 5장은 `true_status="TODO"`(아래 작업 B) 상태이므로, `validate_label`에서 enum 미포함으로 `ValueError`가 나는 것이 **정상**이다. 이는 "아직 사람이 안 채운 항목"을 드러내는 게이트 역할이다. `"TODO"`를 위한 특별 분기는 만들지 마라.

### 2-3. `validate_dataset` 갱신

- `true_status` 분포 통계를 리포트에 추가(5종 + ambiguous + 그 외(TODO 등) 각 몇 건).
- 단건 `ValueError`를 모아서 어떤 `image_id`가 실패했는지 보여주도록(기존 동작이 이미 그러하면 유지).

---

## 3. 작업 B — 마이그레이션 스크립트 작성

`scripts/migrate_labels_add_status.py` 신규 작성.

### 동작

- 입력: `test_data/main_eval/labels.json`.
- 각 항목 `ground_truth`에 `true_status` 키를 추가:
  - `is_healthy == True` → `true_status = "건강"` (**정합성 규칙상 유일 해 — 자동 채움 허용**)
  - `is_healthy == False` → `true_status = "TODO"` (**사람이 채울 자리. 절대 값 추론 금지**)
- **멱등성**: 이미 `true_status`가 있는 항목은 건너뛴다(재실행 안전).
- 원본 백업: 덮어쓰기 전 `labels.json.bak`(또는 타임스탬프 버전) 생성.
- 출력 로깅:
  - 자동 채움("건강") 건수
  - `TODO` 건수 + **해당 `image_id` 전체 목록**(사람이 채워야 할 대상)
  - 건너뛴(이미 있는) 건수
- `--dry-run` 옵션: 파일을 쓰지 않고 위 통계만 출력.

### 자동화 경계 (엄수)

- ❌ `is_healthy=False` 항목의 `true_status`를 `symptoms`·`diagnosis`·이미지로부터 **추론하지 마라**. 무조건 `"TODO"`.
- ❌ LLM/Vision API 호출 금지.
- ✅ `is_healthy=True → "건강"`만 자동. 이는 §2-2 정합성 규칙이 강제하는 유일 값이라 추론이 아님.

### 코드 스타일

기존 `scripts/` 컨벤션 준수: argparse, type hint(Python 3.12), `print()` 단계별 로깅, BOM 없는 UTF-8.

---

## 4. 제약

- **변경 가능 파일**: `test_data/labeling_vocab.py`, 신규 `scripts/migrate_labels_add_status.py`, (실행 결과로) `test_data/main_eval/labels.json` + 백업.
- **절대 무변경**: `scripts/run_eval.py`, `scripts/eval_avg.py`, `app/*`, 프론트 전체, `eval/baseline*.json`, `test_data/plantvillage_50/*`, 다른 수집 스크립트.
- `labels.json`의 기존 필드(`plant_name_korean`·`is_healthy`·`symptoms`·`diagnosis`·`source` 등)는 **건드리지 말고 `true_status`만 추가**.

---

## 5. 검증 절차 (커밋 전)

```bash
# 1) import·문법
python -c "from test_data.labeling_vocab import STATUS_VOCAB, STATUS_AMBIGUOUS, validate_label; print(STATUS_VOCAB, STATUS_AMBIGUOUS)"
# 기대: ['건강','과습','건조','병해 의심','영양 부족'] ambiguous

# 2) 마이그레이션 dry-run (파일 미변경)
python scripts/migrate_labels_add_status.py --dry-run
# 기대: 자동 채움 28 / TODO 5 (+ image_id 목록) — §1 보고와 일치해야 함

# 3) 실제 마이그레이션
python scripts/migrate_labels_add_status.py
# 기대: labels.json에 true_status 추가, labels.json.bak 생성

# 4) validate — TODO 5장이 ValueError로 잡히는 것이 정상
python -c "import json; from test_data.labeling_vocab import validate_dataset; validate_dataset(json.load(open('test_data/main_eval/labels.json', encoding='utf-8')))"
# 기대: true_status 분포 리포트 + 비건강 5장(TODO)이 실패로 보고됨
```

- 1·2 통과 후 3 실행. 4의 TODO 실패는 의도된 게이트이므로 **에러 메시지에 5개 image_id가 명확히 드러나는지** 확인.
- 기존 단위 테스트가 있으면 `pytest tests/ -v -m "not integration"`로 회귀 없음 확인.

---

## 6. 산출물 + 커밋 (atomic 분리)

- **커밋 1 (feat)**: `labeling_vocab.py` 갱신 + `migrate_labels_add_status.py` 신규
  - 예: `feat: 라벨 스키마에 true_status(5-status) 추가 + 마이그레이션 도구`
- **커밋 2 (chore 또는 data)**: 마이그레이션 실행 결과 `labels.json`(28 건강 자동 + 5 TODO) + 백업
  - 예: `chore: main_eval 라벨 true_status 마이그레이션 실행 (비건강 5장 TODO)`
  - 백업 파일(`labels.json.bak`)은 `.gitignore` 대상인지 확인 후 결정.

> 비건강 5장 `TODO` → 5종 중 하나로 채우는 작업은 **다음 라운드(사람)**다. 이 라운드에서 CC가 채우지 않는다.

---

## 7. 완료 보고에 포함할 것

- §1 read-only 보고 결과.
- 변경 파일 목록 + 각 diff 요약.
- 검증 1~4 출력(특히 TODO 5장의 image_id).
- 자동 채움/TODO 건수가 §1 분포와 일치하는지.
