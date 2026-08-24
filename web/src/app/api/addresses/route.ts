import { NextRequest } from "next/server";

const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") || "";
  const response = await fetch(`${ENGINE_URL}/addresses?q=${encodeURIComponent(query)}`, {
    cache: "no-store",
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") || "application/json" },
  });
}
