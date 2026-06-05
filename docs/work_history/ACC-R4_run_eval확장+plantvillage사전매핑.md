# ACC-R4: run_eval.py status 혼동표 확장 + PlantVillage 사전매핑 + --aux

## 컨텍스트

`context_v24_accuracy_track_R1_datahygiene_done.md` §6·§7 + R3 라벨링 완료(39건, validate exit 0) 직후.

### 라운드 목표

3가지 작업을 하나의 atomic 라운드로:

1. **`scripts/prepare_plantvillage.py` 부작용 해소** (§7) — `validate_label` true_status 필수화로 plantvillage labels 재생성 시 validate 깨지는 잠재 위험을 코드에서 사전 차단. **사람 정의 사전매핑이라 §9 자동화 금지의 예외** (PlantVillage·Money Plant 사전 매핑은 명시적 예외).
2. **`test_data/plantvillage_50/labels.json` 마이그레이션** — 현존 50건에 true_status 사전매핑 추가 (병해류 → `"병해 의심"`, healthy → `"건강"`). 멱등 마이그레이션 스크립트로.
3. **`scripts/run_eval.py` 확장**:
   - 5-status 혼동표 계산·출력 (미측정 칸 명시)
   - `--aux` 옵션 — PlantVillage 50장으로 보조 sanity check (게이트 제외, 메인 측정과 분리)

### Gemini 호출 없음

R4는 **코드 정비 라운드**. 실제 측정(Gemini 과금)은 R5에서 사용자가 PowerShell로 진행. CC는 합성 데이터·dry-run으로 sanity check만.

## 작업 범위

### 수정 대상

- `scripts/prepare_plantvillage.py` — 클래스명 → true_status 사전매핑 dict 추가, labels 생성 시 자동 박기
- `scripts/migrate_plantvillage_add_status.py` (신규) — 현존 plantvillage_50/labels.json에 true_status 사전매핑 추가, 멱등·`--dry-run` 지원
- `test_data/plantvillage_50/labels.json` — true_status 50건 추가 (마이그레이션 결과물)
- `scripts/run_eval.py` — 5-status 혼동표 계산·출력 + `--aux` 옵션
- `scripts/validate_plantvillage_50.py` (있으면) 또는 `scripts/validate_main_eval.py`의 plantvillage 검증 호출부 — 필요 시 minimal 보강

### 금지 (가드)

- `main_rag` 명명 변경 ([B-2] 보류)
- `eval/baseline*.json` 일체 무변경 (L0 앵커 보존)
- `test_data/main_eval/` 일체 무변경 (R3 종료, labels.json·SOURCE.md·images 그대로)
- `test_data/labeling_vocab.py` 무변경 — STATUS_VOCAB은 5-status 그대로, ambiguous 그대로
- `app/` 일체 무변경 — 본 라운드는 평가 도구 정비, 진단 로직 무관
- `data/vector_db/` (Chroma) 무변경
- `test_data/inaturalist_candidates/` · `moneyplant_candidates/` 무변경
- §9 자동화 금지 — main_eval ground_truth는 손대지 않음. PlantVillage 사전매핑은 §9 명시 예외라 OK.

## PlantVillage 클래스 → true_status 사전매핑 (사람 정의 룰)

PlantVillage 클래스 폴더명을 5-status에 매핑하는 dict. **CC가 추론하지 말고 아래 표 그대로 박기**.

| PlantVillage 클래스 | true_status |
|---|---|
| `*_healthy` (모든 작물의 healthy 클래스) | `"건강"` |
| `*_early_blight` | `"병해 의심"` |
| `*_late_blight` | `"병해 의심"` |
| `*_leaf_mold` | `"병해 의심"` |
| `*_septoria_leaf_spot` | `"병해 의심"` |
| `*_spider_mites` | `"병해 의심"` |
| `*_target_spot` | `"병해 의심"` |
| `*_mosaic_virus` | `"병해 의심"` |
| `*_yellow_leaf_curl_virus` | `"병해 의심"` |
| `*_bacterial_spot` | `"병해 의심"` |
| `*_leaf_blight` | `"병해 의심"` |
| `*_leaf_spot` | `"병해 의심"` |
| `*_rust` | `"병해 의심"` |
| `*_powdery_mildew` | `"병해 의심"` |
| `*_scab` | `"병해 의심"` |
| `*_black_rot` | `"병해 의심"` |
| `*_esca` / `*_black_measles` | `"병해 의심"` |
| `*_haunglongbing` / `*_citrus_greening` | `"병해 의심"` |

⚠ **Step 1 read-only 게이트에서 plantvillage_50/labels.json의 실제 클래스 분포를 확인 후, 위 표에 없는 클래스 발견 시 중단·사용자에게 매핑 결정 요청**. 자동 추론 금지.

매핑 룰 본질: **모든 비-healthy 병해 클래스 → "병해 의심"**. PlantVillage는 작물 잎 병해 데이터셋이라 5-status 중 "병해 의심"·"건강" 외의 status(과습/건조/영양 부족)에는 매핑되지 않음 → 작물 도메인 한계, 보조 sanity check 한정 용도.

## 절차

### Step 1 — Read-only 선결 게이트 (§8)

변경 전 다음을 **읽기 전용으로 보고**. 불일치 시 중단·질의.

1. `scripts/run_eval.py` 현 구조 — 혼동표 계산 부분(있다면), status 처리 로직, 출력 포맷, CLI 인자 처리
2. `scripts/prepare_plantvillage.py` 현 구조 — labels.json 생성하는 함수 위치(§7에서 L249 언급), 현재 사용 중인 클래스명 → 라벨 매핑 룰 확인
3. `test_data/plantvillage_50/labels.json` 현 상태 — 50건의 스키마, `is_healthy`/`true_status` 필드 유무, 클래스 분포
4. `test_data/labeling_vocab.py`의 `STATUS_VOCAB` · `STATUS_AMBIGUOUS` · `validate_label` 확인 (무변경 대상이지만 호출 방식 파악)
5. `test_data/main_eval/labels.json` 39건 분포 — status별·species별 카운트, R3-labels 결과 그대로인지 확인
6. `python scripts/validate_main_eval.py` exit 0 (39건 valid) 확인
7. `plantvillage_50`에 대한 validate 스크립트 존재 여부 확인 — `validate_plantvillage_50.py` 또는 `validate_main_eval.py`의 plantvillage 호출
8. 클래스 분포 매핑 표 충돌 검사 — 위 매핑 표에 없는 PlantVillage 클래스 있는지

⚠ Step 1 보고에 반드시 포함: **plantvillage_50의 실제 클래스 분포** + **위 매핑 표 외 클래스 존재 여부**. 매핑 누락 시 중단.

### Step 2 — `prepare_plantvillage.py` 코드 수정

§7 부작용 사전 차단:

- 클래스명 → true_status 사전매핑 dict 상수로 추가 (위 매핑 표 그대로)
- labels.json 생성 함수에서 각 항목에 `true_status` 자동 박기
- 멱등성 유지 — 기존 동작(클래스명 → `is_healthy` 매핑 등)은 그대로, true_status만 추가
- 미래에 prepare_plantvillage.py가 재실행돼도 validate 통과 보장

⚠ 본 단계에서는 `prepare_plantvillage.py` 재실행하지 않음. 코드 수정만. 현존 plantvillage_50/labels.json 갱신은 Step 3에서 별도 마이그레이션으로.

### Step 3 — `migrate_plantvillage_add_status.py` 신규 작성·실행

`scripts/migrate_labels_add_status.py`(R1) 패턴 참조 — 멱등·`--dry-run`·타임스탬프 백업.

- 입력: `test_data/plantvillage_50/labels.json` 50건
- 동작:
  - 각 항목의 클래스 정보(image_path의 폴더명 또는 source 블록의 class 필드)에서 PlantVillage 클래스명 추출
  - 위 매핑 표로 true_status 결정
  - 기존 항목에 `true_status` 필드 추가 (이미 있으면 skip = 멱등)
  - 매핑 표에 없는 클래스 발견 시 즉시 중단·보고 (Step 1에서 다 잡혔어야 함, 안전망)
- 실행 순서:
  - `--dry-run`으로 먼저 변경 미리보기 (변경 항목 수, 신규 true_status 분포)
  - 사용자 보고 후 실행 (자동 진행 금지, 사용자 confirm 받기)
  - 실제 실행 전 타임스탬프 백업 (`labels.json.bak.YYYYMMDD_HHMMSS`)

⚠ §9 PlantVillage 사전매핑 예외 명시 — 매핑 룰은 사람이 정의한 dict, LLM 추론 아님.

### Step 4 — `run_eval.py` status 혼동표 확장

기존 측정 출력에 5-status 혼동표 추가:

#### 4.1 혼동표 정의

- 행(true): `STATUS_VOCAB` 5개 + `ambiguous`(평가 제외 표시용)
- 열(predicted): `STATUS_VOCAB` 5개
- 셀: 카운트
- **미측정 셀 명시**: true status 표본이 0인 행은 빈칸 + "미측정" 표기 (예: "과습" 행, "영양 부족" 행)
- ambiguous 행은 항상 "평가 제외" 표기

#### 4.2 측정 가능 status (현 39건 기준 예상)

- 건강 (n=28) — 측정 가능
- 건조 (n=6) — 측정 가능
- 병해 의심 (n=2) — 측정 가능 (표본 작음, 신뢰구간 넓음 명시)
- ambiguous (n=3) — 평가 제외
- 과습 (n=0) — 미측정
- 영양 부족 (n=0) — 미측정

⚠ true_status가 ambiguous인 항목은 정확도 계산에서 **완전 제외** (분모에도 안 들어감). 기존 이진 FP/FN 측정도 ambiguous는 제외.

#### 4.3 출력 포맷

기존 측정 결과 JSON에 `status_confusion_matrix` 키 추가:

```json
{
  "status_confusion_matrix": {
    "rows": ["건강", "과습", "건조", "병해 의심", "영양 부족", "ambiguous"],
    "cols": ["건강", "과습", "건조", "병해 의심", "영양 부족"],
    "counts": [[...], [...], ...],
    "unmeasured_rows": ["과습", "영양 부족"],
    "excluded_rows": ["ambiguous"],
    "sample_sizes": {"건강": 28, "건조": 6, "병해 의심": 2, "ambiguous": 3}
  }
}
```

콘솔 출력에도 표 형태로 print (미측정 칸은 "미측정" 명시).

#### 4.4 기존 이진 FP/FN 측정 유지

- `is_healthy ↔ 진단 결과` 기반 이진 메트릭은 그대로 유지 (가장 중요한 안전판)
- 5-status 혼동표는 추가 계층, 기존 메트릭 회귀 0

### Step 5 — `--aux` 옵션 추가

`scripts/run_eval.py --aux` 시:

- 메인 측정(main_eval 39건) 후 plantvillage_50도 보조 측정
- 출력: 메인 결과 + `aux_plantvillage_results` 별도 섹션
- 게이트 제외 — 보조 sanity check 한정, 메인 게이트 통과 여부에 영향 없음
- aux 측정도 5-status 혼동표 포함 (PlantVillage는 "건강"·"병해 의심" 2칸에만 데이터, 나머지는 미측정)
- aux 옵션 없으면 기존 동작 그대로 (main_eval만 측정)

### Step 6 — 검증 (합성·dry-run only)

⚠ **Gemini 실호출 금지**. 본 라운드에서는 측정 인프라 정비만, 실측정은 R5에서.

#### 6.1 코드 sanity

- `python scripts/migrate_plantvillage_add_status.py --dry-run` — 변경 예상치 보고
- 마이그레이션 실행 후 `python scripts/validate_main_eval.py` (또는 plantvillage 검증) → 50건 valid, true_status 50개 박힘
- main_eval validate exit 0 (39건 무변경) 회귀 확인

#### 6.2 혼동표 합성 테스트

- 가짜 진단 결과 dict (예: `{"image1": {"true": "건강", "pred": "건강"}, ...}`)로 혼동표 계산 함수 단독 호출 → 기대값 일치 확인
- 미측정 칸·excluded 행 표시 정확한지 확인

#### 6.3 import·문법

- `python -c "from scripts.run_eval import build_status_confusion_matrix; print('ok')"` (함수 이름은 실제 구현에 맞춰)
- `python scripts/run_eval.py --help` — `--aux` 옵션 노출 확인

### Step 7 — Atomic 커밋 (푸시 보류)

4건 커밋 분리:

1. `feat(eval): prepare_plantvillage.py PlantVillage 클래스 → true_status 사전매핑 추가` — prepare_plantvillage.py
2. `feat(eval): migrate_plantvillage_add_status.py 신규 + plantvillage_50/labels.json 50건 true_status 마이그레이션` — 신규 스크립트 + labels.json
3. `feat(eval): run_eval.py 5-status 혼동표 + --aux PlantVillage 보조 측정` — run_eval.py
4. `docs(work_history): ACC-R4 작업 프롬프트 보존` — 본 .md 파일을 `docs/work_history/`로 복사

푸시는 사용자가 검토 후 직접.

## 완료 보고

- Step 1 read-only 게이트 결과 (특히 PlantVillage 클래스 분포·매핑 표 충돌 여부)
- prepare_plantvillage.py 변경 라인·매핑 dict 위치
- migrate 스크립트 실행 결과 (dry-run 결과 + 실제 적용 후 plantvillage_50/labels.json 분포)
- run_eval.py 변경 라인·신규 함수
- 합성 테스트 통과 여부
- main_eval validate exit 0 회귀 확인 (39건 무변경)
- 커밋 해시 4건
- **다음 라운드 후보**:
  - **R5** [사용자] 39건 main_eval + 50건 PlantVillage aux로 L0' 재측정 (Gemini 과금, PowerShell). 5-status 혼동표 첫 측정.
  - 백로그: 과습·영양 부족 독립 표본 확보 (5-status 혼동표 완성), 라이선스 표기 통일(CC-BY ↔ CC BY), Kaggle Indoor Plant Disease 종결 검토
