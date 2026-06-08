# R1 — 디자인 토큰·폰트 인프라 + 타입 (시안 화면 이식 전 기반 깔기)

본 라운드는 **전역 기반만** 깐다. 실제 화면 컴포넌트(ResultView·UploadCard 등)는 R2+에서.
R1 변경 후 기존 진단 흐름이 외관만 바뀐 채 **그대로 동작**해야 한다.

---

## 0. 선결 게이트 (없으면 중단·보고)

- `docs/design/`에 5개 파일 존재 확인:
  `plantia_home.html` · `plantia_combined.html` · `plantia_care_guide.html`
  · `plantia_design_system_sheet.md` · `plantia_screen_data_mapping.md`
  없으면 중단하고 "디자인 파일 누락" 보고.
- `git status` clean 확인.

---

## 1. 폰트·아이콘 로드 — `pages/_document.tsx` 신설

현재 `_document.tsx` 없음(R0 확인). 신설하여 `<Head>`에 CDN `<link>` 2줄:

```tsx
import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="ko">
      <Head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.min.css"
        />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css"
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
```

(styled-jsx 내 `@import`는 호이스팅 불안정 → 쓰지 말 것. R0 §5 권고.)

---

## 2. 전역 토큰·기본 스타일 — `pages/_app.tsx` + `styles/globals.css` 신설

현재 `_app.tsx`·`styles/` 없음. 둘 다 신설.

### 2.1 `styles/globals.css`

`docs/design/plantia_design_system_sheet.md`의 토큰을 **CSS 변수로 1:1 이식**.
`:root`에 색·radius·shadow 변수 + body 기본. 시트의 값을 그대로 옮길 것. 핵심 발췌(시트와 대조 확인):

```css
:root {
  /* 배경 */
  --bg-page: #F4F7F2;
  --bg-card: #FFFFFF;
  --bg-icon-circle: #F2F8F2;
  --bg-section-header-icon: #E6F4E0;
  --bg-status-badge: #D8F0CC;
  /* 텍스트 */
  --text-primary: #1F2A21;
  --text-secondary: #4A5C4C;
  --text-muted: #7A8C7B;
  --text-disabled: #B8CCB8;
  /* 브랜드 그린 */
  --green-dark: #2A5428;
  --green-medium: #3A6E37;
  --green-camera: #1B5E20;
  --green-check: #2E7D32;
  /* status (R0 §B-1 확정: 3색 + fallback) */
  --status-healthy: #7BCB8F;
  --status-caution: #F5CD64;
  --status-disease: #F3A096;
  --status-info: #8FBBD9;   /* fallback 전용 */
  /* radius */
  --radius-card: 22px;
  --radius-button: 30px;
  --radius-badge: 40px;
  --radius-circle: 50%;
  /* shadow */
  --shadow-card: 0 2px 12px rgba(42,84,40,.07);
  --shadow-card-elevated: 0 4px 20px rgba(46,125,50,.13);
  --shadow-camera-btn: 0 8px 22px rgba(27,94,32,.35);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg-page);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}
```

> 시트에 더 있는 토큰(season·drop·info-row 배경 등)도 누락 없이 `:root`에 포함.
> 시트 값과 위 발췌가 어긋나면 **시트를 정본**으로.

### 2.2 `pages/_app.tsx`

```tsx
import type { AppProps } from "next/app";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
```

### 2.3 기존 `index.tsx` 전역 선언 정리

`index.tsx`의 `<style jsx global>`(R0: index.tsx:94~)에 있는 **body font-family(Inter)·배경(녹색 그라데이션)** 선언을 제거 — 이제 `globals.css`가 담당.
⚠ index.tsx의 **컴포넌트 scope `<style jsx>`(UploadCard·Loading·Result 등 구체 스타일)는 건드리지 말 것** — R2+ 대상. 전역 충돌 선언만 제거.

---

## 3. 타입 — `types/diagnosis.ts`

기존 필드 보존하고 추가만. (R0 §B-4 발췌 = `app/schemas.py`와 1:1)

```ts
export type CareWater = {
  spring: string | null;
  summer: string | null;
  autumn: string | null;
  winter: string | null;
};

export type CareGuide = {
  species_key: string;
  display_name: string | null;
  src_cntntsNo: string | null;
  scientific_name: string | null;
  soil: string | null;
  water: CareWater | null;
  light: string | null;
  temperature: string | null;
  humidity: string | null;
  fertilizer: string | null;
  placement: string | null;
  manage_level: string | null;
  winter_min_temp: string | null;
  growth_height_cm: string | null;
  growth_area_cm: string | null;
  note: string | null;
};
```

`DiagnosisResponse`에 한 필드 추가 (기존 필드 불변, `StructuredResult.current_state`도 그대로 유지):

```ts
export type DiagnosisResponse = {
  message: string;
  analysis: AnalysisResult | null;
  structured_result: StructuredResult;
  care_guide: CareGuide | null;   // ← 추가
};
```

---

## 4. status 색 유틸 — `lib/status.ts` 신설

R0 §B-1 확정 매핑. status 원값 키, 미스 키는 fallback(정보색).

```ts
// status 원값 → 배지 메인 색 (CSS 변수명 반환)
export const STATUS_COLOR: Record<string, string> = {
  "건강": "var(--status-healthy)",
  "과습": "var(--status-caution)",
  "건조": "var(--status-caution)",
  "영양 부족": "var(--status-caution)",
  "병해 의심": "var(--status-disease)",
};

export function statusColor(status: string | null | undefined): string {
  if (!status) return "var(--status-info)";
  return STATUS_COLOR[status] ?? "var(--status-info)";  // 미스 → fallback
}
```

> 배지 배경/텍스트 색 페어(연한 배경 등)는 시안에 비건강 케이스가 없어 R2 배지 컴포넌트에서
> 확정. R1은 status→메인색 매핑만 둔다. (over-engineering 금지)

---

## 5. 검증

```bash
npx tsc --noEmit          # 타입 에러 0
# next dev 띄우고:
#  - 기존 진단 흐름(업로드→로딩→결과) 그대로 동작하는지
#  - 폰트가 Pretendard로 바뀌고 배경이 #F4F7F2로 바뀌는지 (외관 변화는 정상)
#  - 콘솔 에러 0, CDN 404 없는지
```

⚠ 측정(run_eval)·백엔드 무관 — 프론트만. `eval/baseline.json` 손대지 말 것.

---

## 6. 보고 + 커밋

### 변경/신설 파일
```
pages/_document.tsx   (신설)
pages/_app.tsx        (신설)
styles/globals.css    (신설)
types/diagnosis.ts    (CareWater·CareGuide·care_guide 추가)
lib/status.ts         (신설)
pages/index.tsx       (전역 충돌 선언 제거만)
```

### 보고
- tsc 통과 여부 / 기존 흐름 동작 / 폰트·배경 적용 스크린샷 1장
- 시트 토큰과 globals.css 변수 불일치 있었으면 명시

### 커밋 메시지 (사용자 확정 후)
```
feat: [리디자인 R1] 디자인 토큰·폰트 인프라 + care_guide 타입

- pages/_document.tsx 신설: Pretendard·Tabler webfont CDN link
- pages/_app.tsx + styles/globals.css 신설: 디자인 시스템 토큰(:root CSS 변수)
  + body 기본(Pretendard, bg #F4F7F2). 시트 1:1 이식.
- types/diagnosis.ts: CareWater·CareGuide 인터페이스 + DiagnosisResponse.care_guide
  (백엔드 schemas.py 1:1, care_guide: CareGuide | null)
- lib/status.ts: status 원값→색 매핑 (건강/과습·건조·영양부족/병해의심 = 3색 + fallback)
- index.tsx: 전역 font/배경 선언 제거(globals.css로 이관). 컴포넌트 scope 스타일 불변.

범위: 전역 기반만. 화면 컴포넌트는 R2+. 백엔드·측정 무관.
```

`eval/`·`data/`·백엔드 코드 add 금지.

---

## 7. 주의

- **화면 컴포넌트(ResultView·UploadCard·LoadingView) 구체 스타일 변경 금지** — R2+ 대상. R1은 전역 토큰·폰트·타입·유틸만.
- current_state 표시 전환은 R2(ResultView 교체) 때. R1 타입에선 `StructuredResult.current_state` 유지.
- 시트 토큰을 빠짐없이 옮기되, 시안 HTML에서 실제 쓰는 토큰 위주로(미사용 토큰도 넣어두면 R2에서 편함).
- 다음(R2): `docs/design/plantia_combined.html`(진단 결과) → ResultView 전면 교체.
