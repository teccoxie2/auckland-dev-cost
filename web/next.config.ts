import type { NextConfig } from "next";

const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: "20mb",
    },
    proxyClientMaxBodySize: "20mb",
  },
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "demo-cost.vsense.co.nz",
    "*.vsense.co.nz",
    "*.cursor.com",
    "*.cursor.sh",
    "*.cursorusercontent.com",
    "*.trycloudflare.com",
  ],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "Cache-Control", value: "private, no-store, max-age=0, must-revalidate" }],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/engine/:path*",
        destination: `${ENGINE_URL.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

export default nextConfig;
