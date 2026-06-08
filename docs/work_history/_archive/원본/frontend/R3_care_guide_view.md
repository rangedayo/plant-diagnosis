# R3 — 케어 가이드 화면 + 화면 전환 연결

`docs/design/plantia_care_guide.html` → 케어 가이드 화면 신설. 상태머신에 "care" screen 추가하고
R2의 `onViewCare` placeholder를 실제 전환에 연결. 시작 전 시트 ※제안→확정 docs 정리(별도 커밋).
R2 산출(ResultView·status·index)·R1 토큰을 기반으로. 다른 화면(Upload·Loading·홈)은 R4 — 손대지 말 것.

---

## 0. 선결 게이트 (없으면 중단·보고)

- `git status` clean (R2 푸시 후).
- `docs/design/plantia_care_guide.html`·`plantia_screen_data_mapping.md`·`plantia_design_system_sheet.md` 존재.
- R2 산출 확인: `components/ResultView.tsx`에 `onViewCare` prop, `pages/index.tsx`에 placeholder, `types/diagnosis.ts`에 `CareGuide`/`care_guide`.

---

## 1. 시트 ※제안 → 확정 격상 (작은 docs 수정, 먼저 별도 커밋)

R2 검증에서 비건강 배지 색(노랑/코랄)이 확정됨. `docs/design/plantia_design_system_sheet.md`
"상태(status) 색" 표에서:
- `※제안` 표식 4건(주의 bg/fg·병해 bg/fg·fallback bg/fg) **제거**, 값은 그대로(확정).
- 표 아래 ※제안 설명 문구를 "R2에서 시각 확정됨"으로 갱신.
- 변경 이력에 한 줄 추가: "R2 검증으로 비건강 배지 색 확정 (노랑 #FBF1D2/#7A5B12, 코랄 #FBE2DD/#9A3D32, fallback #E3EEF5/#3A5B70)."

→ 이 docs 수정만 **먼저 커밋** (코드와 분리):
```
docs: 디자인 시트 상태 색 확정 (R2 배지 검증 반영)
```
커밋 후 §2로.

---

## 2. 현 구조·시안 정독 (view)

- `pages/index.tsx` — 상태머신 Screen 타입(`"home"|"loading"|"result"`), screen 전환 로직, result 데이터(diagnosis 응답)를 어느 state에 들고 있는지, `<ResultView onViewCare=...>` 호출부.
- `components/ResultView.tsx` — `onViewCare` prop 사용처(케어 버튼 onClick).
- `docs/design/plantia_care_guide.html` — **전체 정독**. 카드 구조(지속 관리법 4그리드 + 계절 물주기 2x2 + 환경정보 리스트), 헤더(`케어 가이드` 타이틀 + ✦ 버튼), 인라인 SVG(계절 물방울 4종·토양·배치·환경 아이콘), 하드코딩 더미값 위치.
- `docs/design/plantia_screen_data_mapping.md` §3 — 바인딩 정본.

---

## 3. 케어 가이드 화면 컴포넌트 신설 — `components/CareGuideView.tsx`

### 3.1 props
```ts
type Props = {
  careGuide: CareGuide;   // null 아님 보장(care 화면 진입 = care_guide 존재). 방어적 처리는 §5.
  onBack: () => void;     // 결과 화면으로 복귀
};
```

### 3.2 데이터 바인딩 (매핑 md §3 정본)

| 시안 영역 | 바인딩 |
|---|---|
| 토양 값 | `careGuide.soil` |
| 광량 값 | `careGuide.light` |
| 배치 값 | `careGuide.placement` |
| 관리 난이도 뱃지 | `careGuide.manage_level` |
| 봄/여름/가을/겨울 주기 | `careGuide.water?.spring` / `.summer` / `.autumn` / `.winter` |
| 생육 적온 | `careGuide.temperature` |
| 습도 | `careGuide.humidity` |
| 비료 | `careGuide.fertilizer` |

하드코딩 더미(배수 좋은 흙·1주 1회 등)는 전부 위 바인딩으로 교체.
**미표시 필드**(타입엔 있으나 화면 출력 안 함): `species_key`·`display_name`·`src_cntntsNo`·`scientific_name`·`note`·`winter_min_temp`·`growth_height_cm`·`growth_area_cm`.

### 3.3 헤더 — 뒤로가기 필수
시안 헤더는 `케어 가이드` 타이틀 + `✦` 버튼뿐 (뒤로가기 없음). 화면 전환 구조상 **뒤로가기(←) 추가**:
- 헤더 좌측에 뒤로가기 아이콘(`ti ti-chevron-left`) 버튼 → `onBack()` 호출.
- `✦` 버튼은 기능 미정의 → **제거** (또는 비활성 placeholder, 동작 연결 금지).

### 3.4 스타일 — R2와 동일 원칙
- 시안 인라인 `<style>` → `<style jsx>`(scoped). 공통 토큰은 `globals.css` `var(--*)` 참조.
- 시안 `@import`(Pretendard·Tabler) 줄 **제거** (_document 의존).
- 계절 물방울 SVG 4종(봄 새싹/여름 태양/가을 잎/겨울 눈)은 반복 구조 → 내부 헬퍼 컴포넌트로 정리 권장(필수 아님).

---

## 4. 상태머신 "care" screen + 전환 연결 — `pages/index.tsx`

- `Screen` 타입에 `"care"` 추가: `"home"|"loading"|"result"|"care"`.
- result 화면의 `onViewCare` → `setScreen("care")`. (result의 diagnosis 데이터는 **유지** — state 비우지 말 것. care 화면이 같은 응답의 `care_guide`를 참조.)
- screen이 `"care"`이면 `<CareGuideView careGuide={result.care_guide} onBack={() => setScreen("result")} />` 렌더.
- care 화면의 뒤로가기 → `setScreen("result")` (결과 화면 그대로 복귀, 재진단 없음).
- ⚠ 브라우저 라우팅 도입 안 함(현 구조는 단일 페이지 상태머신, R0). care는 state 전환만. 브라우저 뒤로가기 대응은 범위 밖.
- `onViewCare`는 `result.care_guide`가 있을 때만 버튼이 보이므로(R2 가드), 전환 시 care_guide는 존재 보장. 그래도 §5 방어.

---

## 5. null 가드 (매핑 md §5)

- `care_guide` 자체가 어떤 이유로 null이면 → care 화면 진입 직전 차단 또는 빈 화면 방지(예: onViewCare에서 가드, 또는 CareGuideView 상단에서 null이면 onBack/안내). 정상 흐름상 발생 안 하나 방어.
- `careGuide.water`가 null → **계절별 물주기 서브섹션 전체 숨김**.
- 개별 water 분기(spring 등) null → 해당 계절 카드만 숨김(또는 "—").
- `soil`·`light`·`placement`·`manage_level` 개별 null → 해당 그리드 셀 숨김(빈 라벨 노출 금지).
- `temperature`·`humidity`·`fertilizer` 개별 null → 해당 환경정보 행 숨김.

---

## 6. 검증

```bash
npx tsc --noEmit          # 0
```

**화면 시각 확인** (next dev, mock care_guide 주입). 케이스:

1. **전 필드 채워진 커버종**(예: 산세베리아/드라세나 care_guide) — 4그리드·물주기 2x2·환경정보 전부 렌더.
2. **result → "지속 관리법 보기" → care 전환 → 뒤로 → result 복귀** 흐름 동작.
3. **water=null** — 계절별 물주기 섹션 통째 숨김, 레이아웃 깨짐 없음.
4. **개별 필드 null**(예: fertilizer=null, water.winter=null) — 해당 행/카드만 숨김.

mock은 검증 후 제거(커밋 미포함). 각 케이스 스크린샷/상태 보고. 콘솔 에러 0.

---

## 7. 보고 + 커밋

### 변경 파일
```
components/CareGuideView.tsx   (신설)
pages/index.tsx                (Screen "care" 추가 + 전환 연결)
components/ResultView.tsx      (onViewCare 연결 확인 — 필요 시 미세 조정)
```
(시트 docs 수정은 §1에서 이미 별도 커밋됨.)

### 보고
- 4개 검증 케이스 결과 + care 화면 스크린샷
- 헤더 뒤로가기/✦ 처리 방식
- 전환 흐름(result↔care) 동작

### 커밋 메시지 (사용자 확정 후)
```
feat: [리디자인 R3] 케어 가이드 화면 + 결과↔케어 전환 연결

- components/CareGuideView.tsx 신설: plantia_care_guide.html 시안 이식
  (styled-jsx scoped, @import 제거, 더미→care_guide 바인딩)
  - 4그리드(토양·광량·배치·관리난이도) + 계절 물주기 2x2 + 환경정보(적온·습도·비료)
  - 헤더 뒤로가기 추가, ✦ 제거
- pages/index.tsx: 상태머신 "care" screen 추가, ResultView onViewCare→care 전환,
  care 뒤로가기→result 복귀 (diagnosis 데이터 유지)
- null 가드: water 없으면 물주기 섹션 숨김, 개별 care 필드 null 시 셀/행 숨김

범위: 케어 가이드 화면 + 전환만. 업로드·홈=R4. 백엔드·측정 무관.
```

`eval/`·`data/`·백엔드·Upload/Loading/홈 컴포넌트 add 금지. mock 커밋 금지.

---

## 8. 주의
- **R4 영역 금지**: 업로드·홈·탭바는 손대지 말 것.
- 미사용 care 필드·`current_state`는 타입에서 제거 금지(백엔드 호환).
- care 화면은 result의 `care_guide`를 **재사용**(재요청·재진단 없음).
- `eval/baseline.json` 절대 손대지 말 것.
- 다음(R4): `plantia_home.html` → 홈 화면 + 업로드 카드 + 탭바. "최근 진단 기록"은 데이터 소스 없음 → 플레이스홀더/조건부(매핑 md §4). 기능 없는 탭 진입 시 빈 화면 방지.
