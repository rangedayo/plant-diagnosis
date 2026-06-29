import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // 진단(Gemini 2.5 Pro 비전)은 ~20~30초 소요. rewrite 프록시(http-proxy)의 기본 30초
  // proxyTimeout에 걸리면 백엔드가 200으로 완주해도 프록시가 500을 반환하므로 헤드룸 확보.
  experimental: {
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [
      {
        source: "/diagnose",
        destination: `${backendUrl}/diagnose`,
      },
      {
        // [시계열 3단계] 진단 비교 — /diagnose와 동일 프록시 패턴(상대경로 fetch).
        source: "/compare",
        destination: `${backendUrl}/compare`,
      },
      {
        // [추이 요약] 진단 이력 전체 흐름 요약 — /compare와 동일 프록시 패턴.
        source: "/trend",
        destination: `${backendUrl}/trend`,
      },
      {
        // [챗봇 2차 보정] generate-only 재실행 — /diagnose와 동일 프록시 패턴.
        source: "/diagnose/refine",
        destination: `${backendUrl}/diagnose/refine`,
      },
    ];
  },
  // Firebase Auth signInWithPopup이 팝업 창 상태(window.close/closed)를 확인할 때
  // Chrome의 기본 strict COOP 정책이 차단하며 콘솔 경고를 남김. same-origin-allow-popups로
  // 팝업 핸들 접근을 허용해 경고 제거(실 동작엔 영향 없던 알려진 이슈). COEP는 추가하지 않음
  // — Firebase 외부 리소스(googleusercontent.com 아바타 등) 로딩과 충돌 가능성.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
