# Plantia 화면 ↔ 데이터 매핑

> 각 UI 영역이 어떤 백엔드 필드를 표시하는지 한 줄씩 정리.
> 경로 표기: `DiagnosisResponse` 기준 (`app/schemas.py`).
> ※ R0 게이트(실제 백엔드 실측) 반영본.

---

## 1. 업로드 화면 (`plantia_home` 내 진단 카드 / `plantia_upload`)

| UI 영역 | 데이터 소스 | 비고 |
|---------|-----------|------|
| 타이틀 "식물 진단 시작하기" | 정적 텍스트 | — |
| 촬영 가이드 3포인트 | 정적 텍스트 | 잎 전체 · 초점 · 화분 배경 |
| 카메라 버튼 | 디바이스 카메라 호출 | — |
| 앨범에서 선택 | 디바이스 갤러리 호출 | — |
| **→ 촬영/선택된 이미지** | **`POST /diagnose` 요청 body (file)** | multipart/form-data. `lib/api.ts diagnosePlant(file)` |

---

## 2. 진단 결과 화면 (`plantia_combined.html`)

### 사진 카드

| UI 영역 | 필드 경로 | 타입 |
|---------|----------|------|
| 식물 사진 | 업로드 이미지 (클라이언트 state, `URL.createObjectURL`) | objectURL |
| 상태 뱃지 | `structured_result.status` | `str` — **5종 enum** (아래) |

> **status 원값 5종** (`ALLOWED_STRUCT_STATUS`, model_utils.py): `건강` · `과습` · `건조` · `병해 의심` · `영양 부족`.
> 배지 색 매핑은 `plantia_design_system_sheet.md` §상태 색 참조.
> ⚠ 기존 매핑의 "질병의심"은 오기 — 실제 값은 "병해 의심"(공백 포함).

### 진단 요약 카드

| UI 영역 | 필드 경로 | 타입 |
|---------|----------|------|
| 식물 이름 값 (예: "산세베리아") | `analysis.plant_name_korean` ➜ fallback `analysis.plant_name` | `str` (한국어 통명 우선, 없으면 학명) |
| 현재 상태 값 (예: "건강") | `structured_result.status` | `str` — **원값 그대로 표시(변환 없음)** |
| 요약 텍스트 ("전반적으로 건강한…") | `structured_result.summary` | `str` |

> **표시 변환 없음 (R0 §2.3 확정)**: 배지와 "현재 상태"行 모두 status 원값을 가공 없이 출력.
> (시안의 "건강함" → "건강"으로 통일. 다른 status도 원값 그대로.)
> **`structured_result.current_state` 는 화면에 표시하지 않음** — summary와 의미 중복 서술형이라
> "현재 상태"行은 status를 쓰고 current_state는 미사용. (타입엔 유지 = 백엔드 호환, 표시층에서만 제외.)

### 원인 설명 카드

| UI 영역 | 필드 경로 | 타입 |
|---------|----------|------|
| 원인 본문 | `structured_result.cause` | `str` |

### 처방 카드

| UI 영역 | 필드 경로 | 타입 |
|---------|----------|------|
| 처방 항목 1..N | `structured_result.action_plan[i]` | `str` (리스트 각 항목) |

> `action_plan`은 **항상 `list[str]`** (백엔드 `normalize_structured_result`가 보장, 최소 2개로 패딩).
> ⚠ 기존 매핑의 "str로 올 경우 split 필요"는 불필요 — split 하지 말 것.

### 케어 가이드 이동 버튼

| UI 영역 | 조건 | 비고 |
|---------|------|------|
| "지속 관리법 보기" 카드 | `care_guide !== null` 일 때만 표시 | 미커버종(9종 외)이면 `care_guide`가 `null` → 버튼 숨김 |

### 하단 액션

| UI 영역 | 동작 |
|---------|------|
| "리포트 저장" | 진단 결과 로컬 저장 / PDF 내보내기 (추후) |
| "홈으로 돌아가기" | 홈 화면 네비게이션 (상태머신 screen→"home") |

---

## 3. 케어 가이드 화면 (`plantia_care_guide.html`)

> 전체가 `care_guide: CareGuide` 객체 기반. `care_guide === null`이면 화면 진입 불가(버튼 자체 숨김).
> 필드 전부 R0 §B-4에서 `app/schemas.py`와 1:1 확인됨 (`species_key`만 non-null, 나머지 nullable).

### 지속 관리법 — 4컬럼 그리드

| UI 영역 | 필드 경로 | 예시값 |
|---------|----------|--------|
| 토양 값 | `care_guide.soil` | "배수 좋은 흙" |
| 광량 값 | `care_guide.light` | "밝은 간접광" |
| 배치 값 | `care_guide.placement` | "통풍이 잘 되는 실내" |
| 관리 난이도 뱃지 | `care_guide.manage_level` | "쉬움" |

### 계절별 물주기 — 2×2 그리드

| UI 영역 | 필드 경로 | 예시값 |
|---------|----------|--------|
| 봄 주기 | `care_guide.water.spring` | "1주 1회" |
| 여름 주기 | `care_guide.water.summer` | "3~4일 1회" |
| 가을 주기 | `care_guide.water.autumn` | "1주 1회" |
| 겨울 주기 | `care_guide.water.winter` | "1달 1회" |

### 환경 정보 리스트

| UI 영역 | 필드 경로 | 예시값 |
|---------|----------|--------|
| 생육 적온 값 | `care_guide.temperature` | "16~30°C" |
| 습도 값 | `care_guide.humidity` | "40~50%" |
| 비료 값 | `care_guide.fertilizer` | "봄·여름 한 달 1회" |

> 미사용 필드(현재 화면 미표시): `src_cntntsNo`, `scientific_name`, `note`, `display_name`,
> `winter_min_temp`, `growth_height_cm`, `growth_area_cm`. 타입엔 유지, 화면 출력 안 함.

---

## 4. 홈 화면 (`plantia_home.html`)

| UI 영역 | 데이터 소스 | 현재 상태 |
|---------|-----------|----------|
| 인사말 | 정적 텍스트 | 구현 가능 |
| 진단 시작하기 섹션 | 정적 (업로드 카드 임베드) | 구현 가능 |
| 최근 진단 기록 카드 | 로컬 저장소 또는 DB | **데이터 없음 — 플레이스홀더** |
| 하단 탭바 | 정적 네비게이션 | 구현 가능 |

> ⚠ **최근 진단 기록은 현재 백엔드에 데이터 소스가 없음** (진단 저장·조회 기능 미구현, 시계열 추적 라운드 선행 필요).
> 미리 그리더라도 **데이터 있을 때만 표시(조건부 렌더)** 전제. 빈 껍데기/더미 노출 금지.
> 탭바의 "내 식물"·"설정" 등 다른 탭 화면도 기능 미구현 → 네비게이션 골격만, 진입 시 빈 화면 방지.

---

## 5. 필드 Null 처리 가이드

| 필드 | null/빈값일 때 UI 처리 |
|------|------------------|
| `analysis.plant_name_korean` | `analysis.plant_name`(학명) 표시, 그마저 null이면 "식물명 미식별" |
| `structured_result.status` | 실제론 항상 5종 중 하나(빈값 시 백엔드가 "병해 의심"으로 강제). 방어적으로 미스 키는 배지 fallback색(정보색 `#8FBBD9`) |
| `structured_result.current_state` | **표시 안 함** (새 디자인은 "현재 상태"行에 status 사용) |
| `structured_result.summary` | 해당 영역 숨김 |
| `structured_result.cause` | "원인 설명" 카드 전체 숨김 |
| `structured_result.action_plan` | 항상 list(최소 2). 비는 경우 사실상 없음. 빈 list면 "처방" 카드 숨김 |
| `care_guide` | "지속 관리법 보기" 버튼 숨김, 케어 가이드 화면 진입 차단 |
| `care_guide.water` | 계절별 물주기 서브섹션 숨김 |
| 개별 care 필드 (soil 등) | 해당 그리드 셀/행 숨김 (빈 라벨 노출 금지) |

---

## 변경 이력 (R0 게이트 반영)

- status 타입: "질병의심" 오기 → 실제 5종(건강·과습·건조·병해 의심·영양 부족) 명시.
- "현재 상태"行: 값 "건강함" → "건강"(원값), 표시 변환 없음 명시.
- `current_state`: 화면 미표시 명시 (summary와 중복 서술형).
- `action_plan`: "split 필요" 제거 → 항상 list[str].
- 홈 최근 기록: "데이터 없음/조건부 렌더" 경고 강화 (시계열 기능 선행).
- 케어 미사용 필드 목록 명시. status 색은 디자인 시트로 분리.
