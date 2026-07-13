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
        {/* [PWA] "홈 화면에 추가" 설치 지원. 서비스워커 없이 manifest만으로 동작한다
            (오프라인 캐시는 진단 API와 궁합 검증이 필요해 별도 라운드). */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#246257" />
        {/* iOS는 manifest의 icons를 무시하고 apple-touch-icon을 쓴다. */}
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="Plantia" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
