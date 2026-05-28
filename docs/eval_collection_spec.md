# 평가셋 자동 수집 스크립트 사양서

> plant-diagnosis 프로젝트의 평가셋(메인 25장 + 보조 50장) 구축을 위한 자동화 스크립트 사양.
> Claude Code에 의뢰할 작업 명세서.
>
> 작성일: 2026-05-27
> 후속 작업: [1-0] 평가셋 라벨링 + baseline 측정

---

## 0. 컨텍스트 요약

### 평가셋 전체 구성

| 구분 | 출처 | 수량 | 라벨링 방식 |
|---|---|---|---|
| 메인 (식집사 시나리오) | 본인 식물 | 15장 (정상 10 + 약한 증상 5) | 본인 수동 |
| 메인 (식집사 시나리오) | iNaturalist | 5장 | 자동 수집 + 본인 라벨링 |
| 메인 (식집사 시나리오) | Wikimedia Commons | 5장 | 자동 수집 + 본인 라벨링 |
| 보조 (잎 증상 시각 인식) | PlantVillage | 50장 | 사전 매핑 자동 변환 |

### 본인 식물 (참고)

- **행운목 (Dracaena fragrans)** — 통나무에서 새 순이 자라는 형태
- **드라세나 송 오브 인디아 (Dracaena reflexa)** — 잎 가장자리 흰색·노란색 무늬, 잎 끝이 자연스럽게 마른 상태 (`leaf_edge_dry` 증상 활용 가능)

둘 다 Dracaena 속이라 자동 수집 8종과 중복 없음.

### 핵심 원칙: 라벨링 자동화 금지

이 스크립트들은 **이미지 수집 + 메타데이터 정리 + 라벨 템플릿 생성**까지만 담당.
ground_truth(`plant_name_korean`, `is_healthy`, `symptoms`, `diagnosis`)는 자동 추론 금지.
LLM/Vision API 호출 금지.

예외: PlantVillage는 **폴더명 → 사전 매핑**(사람이 정의한 dict)이므로 자동화 허용.

### 코드 스타일

기존 `scripts/build_rag_db.py`와 동일:
- `httpx.AsyncClient` + asyncio
- type hint (Python 3.12)
- `python-dotenv`로 .env 로드
- `print()` 기반 단계별 로깅

---

## 1. 디렉토리 구조

```
test_data/
├── labeling_vocab.py               # 공통 모듈 (Task 4)
├── self_captured/                  # 본인 촬영 (수동, 자동화 X)
│   ├── images/
│   └── labels.json
├── inaturalist_candidates/         # Task 1 출력
│   ├── images/
│   └── metadata.json
├── wikimedia_candidates/           # Task 2 출력
│   ├── images/
│   └── metadata.json
├── plantvillage_50/                # Task 3 출력
│   ├── images/
│   └── labels.json
└── main_eval/                      # 검수 후 본인이 채움 (생성만 해두기)
    ├── images/                     # 빈 디렉토리
    └── labels.json                 # 빈 배열 []로 초기화
```

`.gitignore` 추가:
```
test_data/inaturalist_candidates/images/
test_data/wikimedia_candidates/images/
test_data/plantvillage_50/images/
test_data/self_captured/images/
test_data/main_eval/images/
```

`metadata.json`·`labels.json`은 git 포함 (데이터셋 구성 추적용).

---

## 2. Task 1: scripts/collect_inaturalist.py

### CLI 인터페이스

```bash
python scripts/collect_inaturalist.py \
    --output-dir test_data/inaturalist_candidates \
    --per-taxon 5 \
    --min-short-side 400
```

옵션:
- `--per-taxon N` — 종당 받을 사진 수 (기본 5)
- `--min-short-side N` — 이미지 짧은 변의 최소 픽셀 (기본 400). `medium → large → original` 순으로 시도해 첫 통과 variant 채택
- `--dry-run` — API 호출 없이 파라미터·예상 호출 수만 출력
- `--taxa-only "Monstera deliciosa,Epipremnum aureum"` — 특정 종만 수집 (재시도용)

### 수집 대상 학명 (스크립트 상단 상수)

```python
TAXA_LIST = [
    "Monstera deliciosa",
    "Epipremnum aureum",
    "Sansevieria trifasciata",
    "Ficus elastica",
    "Spathiphyllum",
    "Zamioculcas zamiifolia",
    "Chlorophytum comosum",
    "Pilea peperomioides",
]
```

선정 의도: 잎 형태 다양성 + 의도적 혼동 페어 3쌍 포함
- 몬스테라 ↔ 스킨답서스 (잎 형태 유사)
- 산세베리아 ↔ 금전수 (다육질 잎)
- 산세베리아 ↔ 접란 (가늘고 긴 잎)

### API 호출

- **엔드포인트**: `https://api.inaturalist.org/v1/observations`
- **인증**: 없음 (공개 API)
- **타임아웃**: 30초
- **종 사이 sleep**: 1초 (60 req/min 여유)

### 쿼리 파라미터

```python
params = {
    "taxon_name": "<학명>",
    "photo_license": "cc0,cc-by",
    "quality_grade": "research",
    "photos": "true",
    "per_page": 30,                  # 후보 풀 크게 받기
    "order_by": "votes",
}
```

> 이 설정은 iNaturalist 웹 UI 필터와 다음과 같이 대응:
>
> | 웹 UI 필터 | API 파라미터 |
> |---|---|
> | ✅ Verifiable | `quality_grade=research`에 포함됨 |
> | ✅ 연구 자료 등급 | `quality_grade=research` |
> | ✅ 사진이 있음 | `photos=true` |
> | 분류: 식물 | `taxon_name=<학명>` (학명 직접 지정으로 대체) |
> | 사진 라이선스: CC0 + CC BY | `photo_license=cc0,cc-by` |

### taxon_name fallback

일부 학명은 동의어·속명 입력 등의 이유로 `taxon_name`으로 한 번에 안 잡힐 수 있음. 그 경우:

```python
# Fallback: taxa 검색 → taxon_id 조회
fallback_url = "https://api.inaturalist.org/v1/taxa"
fallback_params = {"q": "<학명>", "rank": "species,genus", "per_page": 1}
# 응답에서 results[0].id를 받아 다시 observations에 taxon_id 파라미터로 재호출
```

본 검색에서 결과 0건이면 fallback 시도, 그래도 0건이면 경고 로그 + 다음 종으로 진행.

### 사진 선별 로직

1. 응답에서 observation 순회
2. 각 observation의 첫 번째 사진만 사용 (`photos[0].url`, 기본 `square` 크기)
3. variant fallback: `/square.`를 차례로 `/medium.` → `/large.` → `/original.`로 치환해 다운로드, 짧은 변(`min(width, height)`)이 `--min-short-side`(기본 400) 이상인 첫 variant 채택
4. 모든 variant가 미달이면 해당 사진은 스킵
5. 채택된 variant 이름과 실제 해상도를 `hints.resolved_variant` / `hints.resolved_size`에 기록 (`image_dimensions`는 하위 호환 유지용 동일 값)
6. 종당 `--per-taxon`개 모이면 다음 종으로
7. 부족하면 경고 출력 후 계속 (실패 아님)

### 출력 metadata.json

```json
{
  "collected_at": "2026-05-27T14:30:00+09:00",
  "source_site": "iNaturalist",
  "search_params": {
    "license_filter": ["cc0", "cc-by"],
    "quality_grade": "research",
    "per_taxon": 5,
    "min_short_side": 400,
    "variant_order": ["medium", "large", "original"]
  },
  "items": [
    {
      "candidate_id": "inat_monstera_deliciosa_001",
      "image_path": "test_data/inaturalist_candidates/images/inat_monstera_deliciosa_001.jpg",
      "source": {
        "site": "iNaturalist",
        "url": "https://www.inaturalist.org/observations/12345",
        "photographer": "Jane Doe",
        "license": "CC BY 4.0"
      },
      "hints": {
        "scientific_name": "Monstera deliciosa",
        "common_name_guess": "몬스테라",
        "observation_location": "Hawaii, USA",
        "image_dimensions": [1024, 768],
        "resolved_size": [1024, 768],
        "resolved_variant": "large"
      }
    }
  ]
}
```

### 파일명 규칙

`inat_<학명_snake_case>_<3자리 시퀀스>.jpg`

예: `inat_monstera_deliciosa_001.jpg`, `inat_epipremnum_aureum_003.jpg`

### 에러 처리

- 다운로드 실패 1건 → 스킵 + print 로그
- API 5xx → 2초 backoff 후 1회 재시도
- 429 → `Retry-After` 헤더 우선, 없으면 60초 sleep 후 재시도
- 라이선스 정보 누락 → 스킵 (안전망)

---

## 3. Task 2: scripts/collect_wikimedia.py

### CLI 인터페이스

```bash
python scripts/collect_wikimedia.py \
    --output-dir test_data/wikimedia_candidates \
    --per-query 5
```

옵션:
- `--per-query N` — 검색어당 받을 사진 수 (기본 5)
- `--dry-run` — API 호출 없이 검색어 리스트만 출력

### 검색어 (스크립트 상단 상수, 학명+증상 조합)

```python
WIKIMEDIA_QUERIES = [
    # 종별 증상
    "Monstera deliciosa yellowing",
    "Monstera deliciosa root rot",
    "Epipremnum aureum yellow leaves",
    "Epipremnum aureum leaf spot",
    "Sansevieria overwatering",
    "Sansevieria root rot",
    "Ficus elastica leaf drop",
    "Spathiphyllum brown tips",
    "Zamioculcas yellowing",
    # 일반 증상 (보조)
    "houseplant leaf scorch",
    "houseplant spider mite damage",
    "houseplant powdery mildew leaf",
]
```

목표: 12개 검색어 × 5장 = 60장 후보 풀 → 검수 통과 5장이 목표.

### API 호출

- **엔드포인트**: `https://commons.wikimedia.org/w/api.php`
- **인증**: 없음으로 시작. 차단(429/403) 시 OAuth 발급으로 fallback
  - `.env`에 `WIKIMEDIA_OAUTH_TOKEN` 환경변수 지원 추가
  - 토큰 있으면 `Authorization: Bearer <token>` 헤더 자동 부착
- **User-Agent 필수**: `plant-diagnosis-eval/0.1 (https://github.com/rangedayo/plant-diagnosis; contact via github)`
- **호출 간격**: 500ms

### 검색 방식 (전문 검색)

```python
search_params = {
    "action": "query",
    "format": "json",
    "list": "search",
    "srsearch": "<query>",
    "srnamespace": 6,        # File 네임스페이스만
    "srlimit": 20,            # 후보 많이 받아 라이선스 필터링 여유 확보
}
```

검색 결과의 각 `title`(예: `File:Monstera_yellowing.jpg`)에 대해 imageinfo 조회:

```python
imageinfo_params = {
    "action": "query",
    "format": "json",
    "titles": "<File:title>",
    "prop": "imageinfo",
    "iiprop": "url|user|extmetadata|size",
    "iiurlwidth": 800,        # 800px 썸네일 URL
}
```

### 라이선스 필터링

```python
ALLOWED_LICENSES = {
    "CC0", "Public domain",
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
}
EXCLUDED_PATTERNS = ["NC", "ND", "Fair use", "non-free"]
```

`extmetadata.LicenseShortName.value` 값으로 필터.

`CC BY-SA` 항목은 메타데이터에 `share_alike: true` 명시 (포트폴리오 사용 시 동일 라이선스 표기 의무 인지용).

### 출력 metadata.json

```json
{
  "collected_at": "2026-05-27T14:30:00+09:00",
  "source_site": "Wikimedia Commons",
  "search_params": {
    "queries": ["Monstera deliciosa yellowing", "..."],
    "per_query": 5
  },
  "items": [
    {
      "candidate_id": "wiki_monstera_yellowing_001",
      "image_path": "test_data/wikimedia_candidates/images/wiki_monstera_yellowing_001.jpg",
      "source": {
        "site": "Wikimedia Commons",
        "url": "https://commons.wikimedia.org/wiki/File:Monstera_yellowing.jpg",
        "photographer": "Wikimedia User: PlantLover123",
        "license": "CC BY-SA 4.0",
        "share_alike": true
      },
      "hints": {
        "query_used": "Monstera deliciosa yellowing",
        "image_dimensions": [800, 600],
        "filename_original": "Monstera_yellowing.jpg"
      }
    }
  ]
}
```

### 파일명 규칙

`wiki_<query_snake>_<3자리 시퀀스>.jpg`

예: `wiki_monstera_deliciosa_yellowing_001.jpg`

### 에러 처리

iNaturalist와 동일 (2초/60초 backoff).

---

## 4. Task 3: scripts/prepare_plantvillage.py

### CLI 인터페이스

```bash
python scripts/prepare_plantvillage.py \
    --source-dir <PlantVillage 원본 경로> \
    --output-dir test_data/plantvillage_50 \
    --total 50 \
    --seed 42
```

옵션:
- `--source-dir` — PlantVillage 데이터셋 루트 (사용자가 Mendeley에서 별도 다운로드: https://data.mendeley.com/datasets/tywbtsjrjv/1, CC0 1.0). `without_augmentation` 버전만 사용 (증강 데이터는 평가셋에 부적합).
- `--total N` — 추출할 총 장수 (기본 50)
- `--seed N` — 랜덤 시드 (기본 42, 재현 가능성)

### 선별 로직

1. `--source-dir` 아래에서 PlantVillage 폴더 구조 인식 (`<Plant>___<Status>` 형식, Mendeley·Kaggle 모두 동일 컨벤션)
2. `PRIORITY_CLASSES` 5개 클래스에서만 추출 (각 10장)
3. 각 클래스 내에서 시드 고정 랜덤 샘플링
4. 부족한 클래스 있으면 다른 우선순위 클래스에서 보충

```python
PRIORITY_CLASSES = [
    "Tomato___Late_blight",
    "Tomato___Early_blight",
    "Potato___Late_blight",
    "Apple___Apple_scab",
    "Tomato___healthy",
]

PLANTVILLAGE_LABEL_MAP = {
    "Tomato___Late_blight": {
        "plant_name_korean": "토마토",
        "is_healthy": False,
        "symptoms": ["leaf_spots", "leaf_browning"],
        "diagnosis": "토마토 잎마름병 (Late blight)",
    },
    "Tomato___Early_blight": {
        "plant_name_korean": "토마토",
        "is_healthy": False,
        "symptoms": ["leaf_spots"],
        "diagnosis": "토마토 겹무늬병 (Early blight)",
    },
    "Potato___Late_blight": {
        "plant_name_korean": "감자",
        "is_healthy": False,
        "symptoms": ["leaf_spots", "leaf_browning"],
        "diagnosis": "감자 잎마름병 (Late blight)",
    },
    "Apple___Apple_scab": {
        "plant_name_korean": "사과",
        "is_healthy": False,
        "symptoms": ["leaf_spots"],
        "diagnosis": "사과 검은별무늬병 (Apple scab)",
    },
    "Tomato___healthy": {
        "plant_name_korean": "토마토",
        "is_healthy": True,
        "symptoms": [],
        "diagnosis": "정상 상태",
    },
}
```

### 출력 labels.json

```json
[
  {
    "image_id": "pv_tomato_late_blight_001",
    "image_path": "test_data/plantvillage_50/images/pv_tomato_late_blight_001.jpg",
    "ground_truth": {
      "plant_name_korean": "토마토",
      "is_healthy": false,
      "symptoms": ["leaf_spots", "leaf_browning"],
      "diagnosis": "토마토 잎마름병 (Late blight)"
    },
    "source": {
      "site": "PlantVillage",
      "url": "https://data.mendeley.com/datasets/tywbtsjrjv/1",
      "photographer": "PlantVillage Dataset",
      "license": "CC0"
    }
  }
]
```

Task 3은 라벨이 사전 매핑이므로 `ground_truth` 전체가 채워진 상태로 출력. 자동화 정책 위반 아님 (LLM 추론 없음, 사람이 정의한 dict 매핑).

### 파일명 규칙

`pv_<class_snake>_<3자리 시퀀스>.jpg`

예: `pv_tomato_late_blight_001.jpg`

---

## 5. Task 4: test_data/labeling_vocab.py

```python
"""평가셋 라벨링 공통 모듈."""
from __future__ import annotations

SYMPTOM_VOCAB = [
    "leaf_yellowing",   # 잎 황변
    "leaf_browning",    # 잎 갈변
    "leaf_droop",       # 잎 처짐
    "leaf_spots",       # 잎 반점
    "leaf_holes",       # 잎 구멍
    "leaf_edge_dry",    # 잎 끝 마름
    "wet_soil",         # 흙 과습
    "dry_soil",         # 흙 건조
    "pests_visible",    # 해충
    "white_powder",     # 흰가루병
    "leggy_growth",     # 웃자람
    "leaf_pale",        # 잎 색 옅음
]

PLANT_NAME_KO_MAP = {
    "Monstera deliciosa": "몬스테라",
    "Epipremnum aureum": "스킨답서스",
    "Sansevieria trifasciata": "산세베리아",
    "Ficus elastica": "고무나무",
    "Spathiphyllum": "스파티필름",
    "Zamioculcas zamiifolia": "금전수",
    "Chlorophytum comosum": "접란",
    "Pilea peperomioides": "필레아",
    "Dracaena fragrans": "행운목",
    "Dracaena": "드라세나",
}

ALLOWED_LICENSES = {
    "CC0", "Public domain", "self_owned",
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
}


def validate_label(label: dict) -> None:
    """단건 라벨 검증, 위반 시 ValueError."""
    if "image_id" not in label or "ground_truth" not in label:
        raise ValueError(f"필수 필드 누락: {label}")

    gt = label["ground_truth"]
    required = {"plant_name_korean", "is_healthy", "symptoms", "diagnosis"}
    missing = required - gt.keys()
    if missing:
        raise ValueError(f"{label['image_id']}: ground_truth 누락 필드 {missing}")

    # 주: is_healthy=true + symptoms=[...] 조합은 허용한다.
    # 종 특성상 잎끝 마름 등 경증 증상이 있어도 전반적으로 건강한 케이스
    # (예: 드라세나)를 라벨링할 수 있어야 하므로 검증하지 않는다.
    if not gt["is_healthy"] and not gt["symptoms"]:
        raise ValueError(f"{label['image_id']}: unhealthy인데 symptoms 없음")

    for s in gt["symptoms"]:
        if s not in SYMPTOM_VOCAB:
            raise ValueError(f"{label['image_id']}: 알 수 없는 증상 {s}")


def validate_dataset(labels: list[dict]) -> dict:
    """전체 데이터셋 검증 + 통계 리포트 출력."""
    for label in labels:
        validate_label(label)

    n = len(labels)
    n_healthy = sum(1 for l in labels if l["ground_truth"]["is_healthy"])
    symptom_counts: dict[str, int] = {}
    plant_counts: dict[str, int] = {}
    for l in labels:
        for s in l["ground_truth"]["symptoms"]:
            symptom_counts[s] = symptom_counts.get(s, 0) + 1
        p = l["ground_truth"]["plant_name_korean"]
        plant_counts[p] = plant_counts.get(p, 0) + 1

    report = {
        "total": n,
        "healthy_ratio": n_healthy / n if n else 0,
        "symptom_distribution": symptom_counts,
        "plant_distribution": plant_counts,
    }
    print("=== Dataset validation passed ===")
    print(f"Total: {n}, Healthy: {n_healthy} ({report['healthy_ratio']:.1%})")
    print(f"Plant distribution: {plant_counts}")
    print(f"Symptom distribution: {symptom_counts}")
    return report


def validate_metadata(items: list[dict]) -> None:
    """수집 단계(Task 1, 2)의 metadata.json 검증."""
    seen_ids: set[str] = set()
    for item in items:
        cid = item.get("candidate_id")
        if not cid:
            raise ValueError(f"candidate_id 누락: {item}")
        if cid in seen_ids:
            raise ValueError(f"중복 candidate_id: {cid}")
        seen_ids.add(cid)

        path = item.get("image_path")
        if not path:
            raise ValueError(f"{cid}: image_path 누락")

        src = item.get("source", {})
        license_name = src.get("license")
        if not license_name:
            raise ValueError(f"{cid}: license 누락")
        if license_name not in ALLOWED_LICENSES:
            raise ValueError(f"{cid}: 허용되지 않은 라이선스 {license_name}")

    print(f"=== Metadata validation passed: {len(items)} items ===")
```

각 스크립트는 종료 직전 다음을 호출:
- Task 1, 2 → `validate_metadata(items)`
- Task 3 → `validate_dataset(labels)`

---

## 6. 공통 사항

### 의존성

```
# requirements.txt에 추가 필요 (이미 있을 가능성 높음)
httpx
python-dotenv
Pillow
```

### 환경 변수 (.env)

추가 항목:
- `WIKIMEDIA_OAUTH_TOKEN` (선택, Wikimedia 차단 시에만)

`.env.example`에도 위 변수 추가 (값은 빈 문자열).

### 로깅 스타일

기존 `scripts/build_rag_db.py`와 동일:

```python
print(f"[1] iNaturalist 수집 시작 (학명 {len(TAXA_LIST)}종)…")
print(f"    taxon={taxon!r} 응답 {len(items)}건")
print(f"[2] 저장 대상 이미지: {len(saved)}/{target}")
```

---

## 7. 검증 절차 (작성 직후)

각 스크립트 작성 후 다음 명령으로 검증:

```bash
# 1) Dry run으로 파라미터 확인
python scripts/collect_inaturalist.py --dry-run
python scripts/collect_wikimedia.py --dry-run

# 2) 작은 수로 실제 실행 테스트
python scripts/collect_inaturalist.py --per-taxon 1 --taxa-only "Monstera deliciosa"
python scripts/collect_wikimedia.py --per-query 1

# 3) PlantVillage는 데이터셋 다운로드 후 실행
python scripts/prepare_plantvillage.py --source-dir <path> --total 5
```

검증 체크리스트:
- [ ] 출력 디렉토리에 이미지 파일 존재
- [ ] `metadata.json` / `labels.json` 파일 존재 + JSON 유효성
- [ ] `validate_metadata` / `validate_dataset` 통과
- [ ] 라이선스 필드가 `ALLOWED_LICENSES`에 포함됨

---

## 8. 금지 사항

- ❌ 이미지 자체에 대한 자동 라벨링 (LLM·Vision API 호출 금지)
- ❌ `ground_truth.{plant_name_korean, is_healthy, symptoms, diagnosis}` 자동 추론 (Task 3 사전 매핑 제외)
- ❌ Plant.id, Gemini, OpenAI 호출
- ❌ Task 1, 2의 `metadata.json`에 `ground_truth` 필드 추가 (구조상 분리 유지)
- ❌ 본인이 다운로드해야 하는 PlantVillage를 Claude Code가 임의로 다운로드 시도

---

## 9. 작업 순서 권장

1. **Task 4** (`labeling_vocab.py`) — 다른 스크립트가 import 하므로 먼저
2. **Task 1** (iNaturalist) — 가장 단순
3. **Task 2** (Wikimedia) — 라이선스 필터링 복잡
4. **Task 3** (PlantVillage) — 독립적

---

## 10. 작업 완료 후 (본인이 진행할 단계)

1. 본인 식물 2종 촬영 → `test_data/self_captured/images/`
2. 자동 수집 실행: `--per-taxon 5`, `--per-query 5`
3. 후보 풀에서 메인 평가셋용 사진 5장씩 검수 → `test_data/main_eval/images/`로 복사
4. 본인 사진 + 자동 수집 사진 합쳐서 `main_eval/labels.json` 작성 (수동)
5. `validate_dataset()` 호출로 라벨 검증
6. PlantVillage 실행 (보조 평가셋)
7. baseline 측정 스크립트 작성 (`scripts/run_eval.py`)
