import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
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
