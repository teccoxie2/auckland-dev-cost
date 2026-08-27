const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function engineError(message: string, status = 502) {
  return new Response(JSON.stringify({ detail: message }), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  if (!jobId) {
    return engineError("缺少核对任务编号。", 400);
  }
  try {
    const response = await fetch(`${ENGINE_URL}/drawings/verify/jobs/${encodeURIComponent(jobId)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(12_000),
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json" },
    });
  } catch (caught) {
    const name = caught instanceof Error ? caught.name : "";
    if (name === "TimeoutError" || name === "AbortError") {
      return engineError("查询核对进度超时。", 504);
    }
    return engineError("无法连上核算服务。", 502);
  }
}
