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
    ];
  },
};

export default nextConfig;
