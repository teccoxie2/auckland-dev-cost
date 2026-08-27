const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const response = await fetch(`${ENGINE_URL}/drawings/verify/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(12_000),
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({
        llm: false,
        configured: false,
        reachable: false,
        note: "无法连上核算服务，暂时不能确认大模型是否就绪。",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  }
}
