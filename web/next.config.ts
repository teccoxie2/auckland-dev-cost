import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
  ],
  async rewrites() {
    return [
      {
        source: "/engine/:path*",
        destination: "http://127.0.0.1:8764/:path*",
      },
    ];
  },
};

export default nextConfig;
