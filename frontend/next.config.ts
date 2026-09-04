import type { NextConfig } from "next";

const backendUrl =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://recoverai-u329.onrender.com";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl.replace(/\/$/, "").replace(/\/api\/v1$/, "")}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;

