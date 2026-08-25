import type { NextConfig } from "next";

const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: "20mb",
    },
  },
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "*.cursor.com",
    "*.cursor.sh",
    "*.cursorusercontent.com",
    "*.trycloudflare.com",
  ],
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
