const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export const dynamic = "force-dynamic";

export async function GET() {
  const response = await fetch(`${ENGINE_URL}/drawings/verify/ready`, { cache: "no-store" });
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") || "application/json" },
  });
}
