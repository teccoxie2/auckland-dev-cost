import { NextRequest } from "next/server";

const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export const maxDuration = 120;

export async function POST(request: NextRequest) {
  const body = await request.formData();
  const response = await fetch(`${ENGINE_URL}/drawings/verify`, {
    method: "POST",
    body,
    cache: "no-store",
  });
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") || "application/json" },
  });
}
