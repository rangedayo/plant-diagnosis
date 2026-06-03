# R2 — 진단 결과 화면(ResultView) 전면 교체

`docs/design/plantia_combined.html`(진단 결과 시안)을 `components/ResultView.tsx`로 이식.
실제 데이터 바인딩 + null 가드 + `statusColor()` 배지 색 + current_state→status 전환.
**R1 산출(globals.css 토큰·lib/status.ts·types)을 기반으로 사용.** 다른 화면(Upload·Loading·홈)은 R4, 케어 가이드 화면은 R3 — 손대지 말 것.

---

## 0. 선결 게이트 (없으면 중단·보고)

- `git status` clean 확인 (R1 푸시 후 상태).
- `docs/design/plantia_combined.html`·`plantia_screen_data_mapping.md`·`plantia_design_system_sheet.md` 존재 확인.
- R1 산출물 존재 확인: `styles/globals.css`(토큰), `lib/status.ts`(`statusColor`), `types/diagnosis.ts`(`CareGuide`·`care_guide`).

## 1. 현 구조·시안 정독 (view)

- `components/ResultView.tsx` 전체 — 현재 props 시그니처(`imageUrl`·`result` 등), 무엇을 어떻게 받는지.
- `pages/index.tsx` — `<ResultView>` 호출부(전달 props), 상태머신 screen 전환.
- `lib/status.ts` — `statusColor()` 시그니처(R1).
- `docs/design/plantia_combined.html` — **전체 정독**. 마크업 구조·클래스명·인라인 SVG·하드코딩 더미데이터(산세베리아 등) 위치 식별.
- `docs/design/plantia_screen_data_mapping.md` §2 — 바인딩 정본.

## 2. 데이터 바인딩 규칙 (매핑 md §2 정본)

| 시안 영역 | 바인딩 | 가드 |
|---|---|---|
| 식물 사진 | `imageUrl` prop (기존 objectURL, 그대로 재사용) | — |
| 상태 배지 | `result.structured_result.status` (원값 텍스트) + 색은 `statusColor(status)` | 빈값→fallback색 |
| 식물 이름 | `result.analysis?.plant_name_korean ?? result.analysis?.plant_name ?? "식물명 미식별"` | 3단 fallback |
| 현재 상태 行 | **`result.structured_result.status`** (원값 그대로, 변환 없음) | — |
| 요약 텍스트 | `result.structured_result.summary` | 빈값→영역 숨김 |
| 원인 본문 | `result.structured_result.cause` | 빈값→"원인 설명" 카드 전체 숨김 |
| 처방 항목 | `result.structured_result.action_plan` (항상 list, map 렌더) | 빈 list→"처방" 카드 숨김 |
| 지속 관리법 보기 버튼 | `result.care_guide !== null`일 때만 표시 | null→버튼 숨김 |

**★current_state→status 전환**: 기존 ResultView가 "현재 상태"行에 `current_state`를 쓰고 있음(R0 §3). 이번에 **status로 교체**. `current_state`는 화면에서 미사용(타입엔 유지).
**표시 변환 없음**: 배지·현재상태行 모두 status 원값 그대로 ("건강"→"건강함" 변환 금지).

## 3. ResultView 전면 재작성

### 3.1 구조
시안 `plantia_combined.html`의 카드 구조를 그대로 옮김: 사진 카드(+배지) → 진단 요약 → 원인 설명 → 처방 → (care_guide 있으면)지속 관리법 보기 → 하단 액션(리포트 저장/홈으로).

### 3.2 스타일 — 전역 오염 방지 (R0 §C)
- 시안의 인라인 `<style>` 클래스는 **`<style jsx>`(scoped)로 이식** — 전역 누수 금지. 공통 색·radius·shadow는 `globals.css`의 `var(--*)` 참조.
- 시안 HTML 상단의 `@import`(Pretendard·Tabler) 줄은 **제거** — R1에서 `_document.tsx`가 이미 로드함.
- 인라인 SVG는 그대로 두되, 동일 SVG 반복이면 작은 내부 컴포넌트로 정리(선택).
- 하드코딩 더미데이터(산세베리아·"전반적으로 건강한…" 등)는 전부 §2 바인딩 지점으로 교체.

### 3.3 배지 색 — lib/status.ts 보강
현재 `statusColor()`는 메인색만 반환. 배지는 배경+텍스트 페어가 필요하니 `lib/status.ts`에 추가:

```ts
// 시트 §상태 색 ※제안값 (R2 시각 확정 대상)
export const STATUS_BADGE: Record<string, { bg: string; fg: string }> = {
  "건강":      { bg: "#D8F0CC", fg: "#2A5428" },
  "과습":      { bg: "#FBF1D2", fg: "#7A5B12" },
  "건조":      { bg: "#FBF1D2", fg: "#7A5B12" },
  "영양 부족": { bg: "#FBF1D2", fg: "#7A5B12" },
  "병해 의심": { bg: "#FBE2DD", fg: "#9A3D32" },
};
export function statusBadge(status: string | null | undefined): { bg: string; fg: string } {
  if (!status) return { bg: "#E3EEF5", fg: "#3A5B70" };       // fallback(정보색)
  return STATUS_BADGE[status] ?? { bg: "#E3EEF5", fg: "#3A5B70" };
}
```

배지 배경=`statusBadge(status).bg`, 텍스트색=`.fg`, 텍스트=status 원값.

### 3.4 지속 관리법 보기 버튼
- 시안 combined.html에 해당 버튼이 **있으면** 그대로 활용, **없으면** 하단 액션 위에 카드형 버튼 신설(매핑 md §2 "지속 관리법 보기 카드"). 디자인 톤은 시트 토큰.
- `result.care_guide`가 null이면 이 버튼 **미렌더**.
- **onClick은 R3에서 케어 화면 연결 예정** — R2에서는 클릭 시 동작 placeholder(예: `onViewCare?.()` prop만 받아두고 index에서 아직 미연결, 또는 주석으로 "R3 연결"). 상태머신에 "care" screen 추가는 R3 작업이므로 여기선 만들지 말 것.

## 4. 검증

```bash
npx tsc --noEmit          # 타입 에러 0
```

**화면 시각 확인** (next dev). 실제 진단 데이터가 없으면 mock으로 ResultView를 직접 렌더해 상태별 확인 — 다음 케이스 필수:

1. **건강** (status="건강", care_guide 있음): 초록 배지 + "지속 관리법 보기" 버튼 표시
2. **병해 의심** (status="병해 의심"): **코랄 배지** 색 확인
3. **과습/건조/영양 부족** 중 1 (status="과습"): **노랑 배지** 색 확인
4. **care_guide=null**: "지속 관리법 보기" 버튼 미표시
5. **cause 빈값 / action_plan 빈 list**: 해당 카드 숨김 확인

> mock 방식: 임시로 index의 result state에 mock 객체를 주입하거나, 별도 임시 확인 코드 사용 후 **검증 끝나면 제거**(커밋에 mock 남기지 말 것). 백엔드 e2e가 가능하면 건강/비건강·9종/비9종 실제 진단으로 대체 가능.

**★비건강 배지 색(노랑/코랄) ※제안값이 어색하지 않은지 눈으로 확인** — 어색하면 §3.3 값 조정하고 보고(시트도 함께 갱신 제안).

각 케이스 스크린샷 또는 화면 상태 보고. 콘솔 에러 0.

## 5. 보고 + 커밋

### 변경 파일
```
components/ResultView.tsx   (전면 재작성)
lib/status.ts               (statusBadge 추가)
pages/index.tsx             (필요 시 onViewCare prop 전달 자리만 — 미연결)
```

### 보고
- 5개 검증 케이스 결과 + 배지 3색(초록/노랑/코랄) 스크린샷
- ※제안 배지 색 조정 여부
- combined.html에 케어 버튼 유무 / 신설 여부

### 커밋 메시지 (사용자 확정 후)
```
feat: [리디자인 R2] 진단 결과 화면 ResultView 전면 교체

- components/ResultView.tsx: plantia_combined.html 시안 이식
  (styled-jsx scoped, @import 제거·_document 의존, 더미데이터→실데이터 바인딩)
- 데이터 바인딩: status 배지·식물명(ko→학명 fallback)·summary·cause·action_plan(list map)
  + care_guide 있을 때 "지속 관리법 보기" 버튼
- "현재 상태"行 current_state→status 전환 (current_state 미사용, 타입 유지)
- null 가드: cause/action_plan/care_guide 빈값 시 해당 영역 숨김
- lib/status.ts: statusBadge() 추가 (status별 배지 bg/fg, 건강 초록·주의 노랑·병해 코랄·fallback 정보색)

범위: 진단 결과 화면만. 케어 화면=R3, 업로드·홈=R4. 백엔드·측정 무관.
```

`eval/`·`data/`·백엔드·다른 화면 컴포넌트 add 금지. mock 검증 코드 커밋 금지.

## 6. 주의
- **R3·R4 영역 금지**: 케어 가이드 화면(plantia_care_guide.html)·업로드/홈은 손대지 말 것. care 버튼 onClick은 미연결 placeholder.
- `current_state`·미사용 care 필드는 타입에서 제거하지 말 것(백엔드 호환).
- 시안 고정폭(390px)은 기존 index 레이아웃과 충돌 없게 — 모바일 컨테이너 max-width 수준으로, 기존 화면 폭 관례 따름(view 후 판단).
- `eval/baseline.json` 절대 손대지 말 것.
- 다음(R3): `plantia_care_guide.html` → 케어 가이드 화면 신설 + 상태머신 "care" screen 추가 + R2의 care 버튼 onClick 연결.
