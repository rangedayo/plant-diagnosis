# R0 게이트 — 프론트 전면 리디자인 구현 전 read-only 파악·결정

**원칙:** 코드/파일 수정 절대 금지. 빌드·측정 실행 금지. view + grep + 보고만.
끝에 "결정 필요 5포인트" 각각에 사실 기반 답을 달고 멈춤. 추측 금지, 확인 불가면 그 이유 명시.

배경: 디자인 전면 리디자인 확정(Plantia). 새 시안 3화면(업로드·진단결과·케어가이드)을
기존 Next.js 프론트에 구현 예정. 본 게이트는 그 구현이 안전하도록 현 구조·정합을 못박는 단계.

---

## 1. 기존 프론트 구조 파악 (view)

다음을 view 후 구조 보고:

```
pages/                       (라우팅 구조 — 어떤 페이지들이 있는지)
pages/index.tsx              (전체 — 업로드·진단 흐름, ResultView 호출, 상태관리)
components/ResultView.tsx    (전체 — 현재 카드 구조, 스타일 방식)
types/diagnosis.ts           (전체 — 현재 타입; care_guide 부재 확인)
lib/api.ts                   (POST /diagnose 호출 방식, 응답 처리, 에러 경로)
```

추가로 확인:
- **스타일 방식**: styled-jsx인가, CSS module인가, 전역 CSS인가? (시안은 인라인 `<style>` + 클래스. 기존 방식에 맞춰 이식해야 함)
- **전역 스타일·폰트 로드 위치**: `pages/_app.tsx`·`_document.tsx`·`styles/` 존재 여부. 현재 폰트가 무엇인지.
- **라우팅**: 진단 결과·케어 가이드를 별도 페이지(`pages/result.tsx`·`pages/care.tsx`)로 둘 수 있는 구조인지, 아니면 index 내 상태 전환인지. 현재 진단 결과는 어떻게 보여지는가(같은 페이지? 라우팅?).
- **이미지 보관**: 업로드 이미지를 진단 결과 화면에서 다시 보여주려면 클라이언트에 들고 있어야 함. 현재 업로드 이미지를 어떻게 다루는지(state? objectURL?).

## 2. status 정합 — ★가장 중요

### 2.1 `ALLOWED_STRUCT_STATUS` 전체 목록

`app/model_utils.py`에서 `ALLOWED_STRUCT_STATUS` 정의를 grep·view. **정확한 허용 status 문자열 전부**를 나열.
(지금까지 관측: "건강", "병해 의심". 그 외 "주의 필요"·"해충 발견"·"정보" 등이 있는지 확정)

### 2.2 status → 디자인 색 매핑 가능 여부

디자인 시스템 상태 색은 5종:
- 건강함 `#7BCB8F` / 주의 필요 `#F5CD64` / 병해 의심 `#F3A096` / 해충 발견 `#F08C82` / 정보·중립 `#8FBBD9`

→ 실제 `ALLOWED_STRUCT_STATUS` 값들이 이 5색 중 무엇에 각각 대응하는지 **매핑표 초안**을 만들어 보고.
실제 status 값이 디자인 5종과 정확히 안 맞으면(예: status는 2종뿐) 그 사실을 보고 — 색 매핑은 실제 값 기준으로 단순화.

### 2.3 표시 텍스트 변환 — ★결정 완료 (확인만)

**결정: 변환 없음.** status 원값을 배지와 진단 요약 "현재 상태"行 **양쪽에 그대로** 표시.
(시안의 "건강함"은 "건강"으로 통일 = 원값 그대로. 다른 상태값도 전부 원값 그대로 출력.)
→ 별도 변환 맵 만들지 말 것. 표시층에서 status를 가공 없이 출력.
확인만: §2.1에서 status 원값 전체를 확보한 뒤, 원값이 길어서 배지에 어색하게
들어가는 값이 있는지만 한 줄 보고 (없으면 "이상 없음").

## 3. structured_result 필드 사용 결정

`structured_result` 5키: summary, current_state, cause, action_plan, status.
매핑 md는 `current_state`를 UI에 안 씀(요약=summary, 현재상태=status).
→ `current_state`(서술형) 실제 예시값을 1~2개 확보(run_eval 결과 JSON 또는 schemas 주석)하고,
   UI에서 **버릴지 / 요약과 함께 쓸지** 판단 근거 보고. (결정은 다음 라운드, 여기선 근거만)

## 4. care_guide 타입 부재 확인

`types/diagnosis.ts`의 `DiagnosisResponse`에 `care_guide` 필드가 **없음**을 확인(백엔드 schemas.py에는 있음).
R1에서 추가할 `CareGuide`·`CareWater` 인터페이스가 백엔드 `app/schemas.py`의 동명 모델과 1:1 대응하도록,
schemas.py의 두 모델 필드를 정확히 발췌해 둘 것(R1 입력).

## 5. Pretendard·Tabler 로드 방식 결정

시안은 CDN `@import`(Pretendard `orioncactus/pretendard`, Tabler `@tabler/icons-webfont`)를 씀.
Next.js에서 권장 방식 검토:
- 폰트: `next/font` 사용 가능한지, 아니면 `_document.tsx`에 `<link>`, 아니면 전역 CSS `@import` 중 무엇이 현 구조에 맞는지.
- Tabler 아이콘: webfont CDN vs `@tabler/icons-react` 패키지 중 무엇이 나은지 (시안은 webfont 클래스 `ti ti-*` 사용 → webfont 유지가 이식 단순).
- 현재 프로젝트가 오프라인/CSP 제약이 있는지(있으면 CDN 불가 → 패키지 번들). package.json·next.config 확인.

## 6. 시안 HTML → React 이식 시 주의 식별

업로드된 시안 HTML 3개(`plantia_home.html`·`plantia_care_guide.html`·`plantia_combined.html`)를 읽고,
React 이식 시 그대로 못 옮기는 부분을 식별:
- 인라인 `<style>` 클래스명 충돌 가능성(전역 오염) → CSS module 또는 styled-jsx scope 필요 여부
- `@import` 위치(컴포넌트 내 vs 전역)
- SVG 인라인 다수 → 컴포넌트 분리 필요한지
- 하드코딩 더미 데이터(산세베리아·몬스테라 등)를 props 바인딩 지점으로 표시

---

## 출력 형식

### A. 현 구조 요약
- 라우팅·스타일 방식·폰트·이미지 보관 방식 (각 1~2줄, 파일:줄 근거)

### B. 결정 필요 5포인트 — 각각 사실 + 권고
1. status 허용값 전체 + 디자인 5색 매핑표 초안
2. status 표시 변환 규칙 (배지/요약行)
3. current_state 사용 여부 근거
4. care_guide 타입 부재 확인 + schemas.py CareGuide·CareWater 필드 발췌
5. Pretendard·Tabler 로드 방식 권고 (현 구조 기준)

### C. 이식 주의점
- 시안 HTML → React 이식 시 손볼 지점 목록

### D. R1 착수 가능 여부
- 위가 다 확인되면 "R1(토큰+타입) 착수 가능", 막힌 게 있으면 무엇인지.

코드 변경·커밋 절대 없음. 보고 후 정지.
