# Plantia 디자인 시스템 시트

> ※ R0 게이트(실제 백엔드 status 실측) 반영본. "상태(status) 색" 섹션 추가.

## 색상 토큰

### 배경

| 토큰 | HEX | 용도 |
|------|-----|------|
| `bg-page` | `#F4F7F2` | 전체 화면 배경 |
| `bg-card` | `#FFFFFF` | 카드 배경 |
| `bg-icon-circle` | `#F2F8F2` | 아이콘 원형 배경 (케어 그리드, 환경 정보) |
| `bg-icon-circle-accent` | `#C8E6BF` | 강조 아이콘 원형 (진단 요약 잎) |
| `bg-section-header-icon` | `#E6F4E0` | 섹션 헤더 아이콘 원형 (진단 요약·케어 가이드) |
| `bg-season-wrap` | `#F2F8F2` | 계절별 물주기 서브섹션 |
| `bg-season-icon` | `#D6ECCC` | 물방울 헤더 아이콘 |
| `bg-info-row` | `#F9FAF7` | 진단 요약 행 강조 블록 |
| `bg-drop-fill` | `#EBF6E5` | 계절 물방울 SVG 내부 |
| `bg-status-badge` | `#D8F0CC` | 상태 뱃지 배경 — **"건강" 전용** (비건강은 아래 §상태 색 참조) |
| `bg-photo-placeholder` | `linear-gradient(170deg, #EDE8DE, #E0D9CB, #D4CDB8)` | 사진 플레이스홀더 |
| `bg-camera-section` | `#ECF4EC` | 업로드 화면 카메라 영역 |

### 텍스트

| 토큰 | HEX | 용도 |
|------|-----|------|
| `text-primary` | `#1F2A21` / `#1B2B1C` | 제목, 본문 강조 |
| `text-secondary` | `#4A5C4C` | 본문, 설명 |
| `text-muted` | `#7A8C7B` / `#8A9A8B` | 부제, 라벨 |
| `text-disabled` | `#B8CCB8` / `#B0C4B2` | 비활성 탭, 플레이스홀더 |

### 브랜드 그린

| 토큰 | HEX | 용도 |
|------|-----|------|
| `green-dark` | `#2A5428` | 주 액센트 (타이틀, 값, 버튼 fill) |
| `green-medium` | `#3A6E37` | 보조 액센트 (아이콘, 버튼 outline border) |
| `green-camera` | `#1B5E20` | 카메라 버튼 (업로드 화면) |
| `green-check` | `#2E7D32` | 체크 원형 (업로드 촬영 가이드) |

### 상태(status) 색 — ★R0 확정 (실제 백엔드 status 5종 기준)

실제 `ALLOWED_STRUCT_STATUS`는 5종: `건강` · `과습` · `건조` · `병해 의심` · `영양 부족`.
이를 **3색 + fallback 1색**에 매핑 (해충색·정보 메인색은 현 백엔드에 대응 status 없음).

| status 원값 | 의미 | 메인색 | 배지 배경 | 배지 텍스트 |
|---|---|---|---|---|
| `건강` | 건강 | `#7BCB8F` | `#D8F0CC` (= `bg-status-badge`) | `#2A5428` |
| `과습` · `건조` · `영양 부족` | 환경 스트레스(주의) | `#F5CD64` | `#FBF1D2` ※제안 | `#7A5B12` ※제안 |
| `병해 의심` | 병해 | `#F3A096` | `#FBE2DD` ※제안 | `#9A3D32` ※제안 |
| (미스/빈값) | fallback | `#8FBBD9` | `#E3EEF5` ※제안 | `#3A5B70` ※제안 |

- **CSS 변수**(R1 globals.css): `--status-healthy #7BCB8F` · `--status-caution #F5CD64` · `--status-disease #F3A096` · `--status-info #8FBBD9`(fallback).
- 매핑 로직은 `lib/status.ts`의 `statusColor(status)` — status 원값 키, 미스 키는 fallback.
- ⚠ ※제안 배경/텍스트는 시안에 비건강 배지가 없어 메인색에서 파생한 값. **R2(ResultView 이식)에서 실제 노란/코랄 배지를 띄워보고 시각 확정** — 어색하면 조정.
- 미사용: `해충 발견 #F08C82`(대응 status 없음), `정보 #8FBBD9`는 메인 배지 아닌 fallback 전용.

### 구분선

| 토큰 | HEX | 용도 |
|------|-----|------|
| `border-dashed` | `#C4CCC0` | 진단 요약 행 점선 |
| `border-dashed-guide` | `#DDE8DA` | 케어 가이드 환경 정보 점선 |
| `border-dashed-upload` | `#A8DDB5` | 업로드 화면 어노테이션 점선 |
| `border-card-subtle` | `#EEF5EB` | 케어 그리드 컬럼 구분선 |
| `border-tab` | `#E6EEE3` | 탭바 상단 선 |

### 그림자

| 토큰 | 값 | 용도 |
|------|-----|------|
| `shadow-card` | `0 2px 12px rgba(42,84,40,.07)` | 일반 카드 |
| `shadow-card-elevated` | `0 4px 20px rgba(46,125,50,.13)` | 업로드 진단 카드 |
| `shadow-camera-btn` | `0 8px 22px rgba(27,94,32,.35)` | 카메라 플로팅 버튼 |

---

## Border Radius

| 토큰 | 값 | 용도 |
|------|-----|------|
| `radius-card` | `22px` | 카드 |
| `radius-season-wrap` | `18px` | 계절 물주기 서브섹션 |
| `radius-photo-inner` | `16px` | 진단 결과 사진 내부 모서리 |
| `radius-season-card` | `14px` | 계절 카드 |
| `radius-info-block` | `12px` | 진단 요약 강조 블록 |
| `radius-button` | `30px` | 하단 액션 버튼 (pill) |
| `radius-badge` | `40px` | 상태 뱃지 (pill) |
| `radius-circle` | `50%` | 아이콘 원형 |

---

## 타이포그래피

| 레벨 | 크기 | 굵기 | 용도 |
|------|------|------|------|
| Display | `26–28px` | `800` | 페이지 대제목 ("식물 진단 시작하기", 인사말) |
| Title L | `22px` | `800` | 화면 타이틀 (Plantia, 케어 가이드) |
| Title M | `16–18px` | `700` | 섹션 헤더, 네비게이션 바 |
| Body | `14–15px` | `500–600` | 본문, 라벨, 값 |
| Caption | `11–13px` | `500–600` | 부제, 날짜, 배지 텍스트, 케어 그리드 값 |
| Micro | `10.5px` | `500` | 탭바 라벨, 그리드 라벨 |

- 폰트: **Pretendard** (CDN: `orioncactus/pretendard`) — R1에서 `_document.tsx` `<link>`로 로드.
- 아이콘: **Tabler Icons** (CDN webfont: `@tabler/icons-webfont`) — 동일.
- letter-spacing: 제목 `-.02em`, 본문 `-.01em`

---

## 아이콘 원형 크기

| 컨텍스트 | 지름 | 배경 토큰 |
|----------|------|-----------|
| 섹션 헤더 (진단 요약·원인·처방) | `38px` | `bg-section-header-icon` |
| 섹션 헤더 (케어 가이드) | `44px` | `bg-section-header-icon` |
| 케어 그리드 | `52px` | `bg-icon-circle` |
| 환경 정보 리스트 | `42px` | `bg-icon-circle` |
| 진단 요약 행 잎 | `30px` | `bg-icon-circle-accent` |
| 체크 원형 (처방·업로드) | `22px` | `green-check` fill |

---

## 화면별 여백

| 화면 | 카드 좌우 마진 | 내부 패딩 |
|------|---------------|----------|
| 진단 결과 | `21px` | `20px` |
| 케어 가이드 | `0` (화면 패딩 `20px`) | 카드 `20px` |
| 업로드 화면 | 카드 `18px` 패딩 | — |
| 홈 화면 | `16–18px` | `20px` |

---

## 변경 이력 (R0 게이트 반영)

- "상태(status) 색" 섹션 신설 — 실제 status 5종(건강·과습·건조·병해 의심·영양 부족)을
  3색 + fallback에 매핑. 비건강 배지 배경/텍스트는 ※제안값(R2 시각 확정 대상).
- `bg-status-badge`를 "건강 전용"으로 명시 (기존엔 용도가 모호했음).
- 폰트·아이콘 로드를 R1 `_document.tsx` 기준으로 명시.
