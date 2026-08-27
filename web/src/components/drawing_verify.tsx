"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Tabs } from "@/components/ui/tabs";
import type { DrawingAudit, DrawingChart, DrawingPageDebug, DrawingVerifyResult, DrawingVerifyZone } from "@/lib/api";
import { nzdExact } from "@/lib/money";

const FIELD_LABELS: Record<string, string> = {
  gfa_m2: "建筑面积 m²",
  footprint_m2: "占地 m²",
  roof_m2: "屋面 m²",
  storeys: "层数",
  wall_height_m: "层高 m",
  eaves_mm: "出檐 mm",
  bedrooms: "卧室",
  bathrooms: "卫生间",
  kitchens: "厨房",
  dwellings: "套数",
  coverage_pct: "覆盖率 %",
  retaining_height_m: "挡土墙高 m",
  stud_spacing_mm: "立柱间距 mm",
  cladding: "外墙做法",
  site_area_m2: "地块面积 m²",
};

const PAGE_ROLE_LABELS: Record<string, string> = {
  drawing_no_text: "几乎无文字（不做 OCR）",
  schedule: "门窗表 / 面积表",
  notes: "说明或其他",
};

function errorMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== "object") return fallback;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return fallback;
}

function networkErrorMessage(caught: unknown, fallback: string) {
  if (caught instanceof DOMException && (caught.name === "AbortError" || caught.name === "TimeoutError")) {
    return "核对超时。请确认 CPA 隧道仍可用后重试。";
  }
  const name = caught instanceof Error ? caught.name : "";
  const message = caught instanceof Error ? caught.message : "";
  if (name === "AbortError" || name === "TimeoutError") {
    return "核对超时。请确认 CPA 隧道仍可用后重试。";
  }
  if (/failed to fetch|networkerror|load failed|fetch failed/i.test(message)) {
    return "无法连上核算服务（连接被中断）。请再试一次；若仍失败，请确认本页和 CPA 隧道都还开着。";
  }
  return message || fallback;
}

async function waitForVerifyJob(jobId: string, onNote: (note: string) => void) {
  const deadline = Date.now() + 170_000;
  let failures = 0;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`/api/drawings/verify/jobs/${encodeURIComponent(jobId)}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(12_000),
      });
      const payload = (await response.json().catch(() => ({}))) as {
        status?: string;
        note?: string;
        result?: DrawingVerifyResult;
        detail?: unknown;
      };
      if (response.status === 404) {
        throw new Error(errorMessage(payload, "核对任务已过期，请重新上传。"));
      }
      if (!response.ok) {
        throw new Error(errorMessage(payload, "查询核对进度失败"));
      }
      failures = 0;
      if (payload.note) onNote(payload.note);
      if (payload.status === "ok" && payload.result) return payload.result;
      if (payload.status === "error") {
        throw new Error(
          typeof payload.detail === "string" ? payload.detail : errorMessage(payload, "图纸物料核算失败"),
        );
      }
    } catch (caught) {
      const name = caught instanceof Error ? caught.name : "";
      const message = caught instanceof Error ? caught.message : "";
      const transient = name === "AbortError" || name === "TimeoutError" || /failed to fetch|networkerror|load failed|fetch failed/i.test(message);
      if (!transient) throw caught;
      failures += 1;
      if (failures >= 4) throw new Error(networkErrorMessage(caught, "无法连上核算服务"));
    }
    await new Promise((resolve) => window.setTimeout(resolve, 2000));
  }
  throw new Error("核对超时（约 3 分钟）。请确认 CPA 隧道仍可用后重试。");
}

function ZoneTable({ zone }: { zone: DrawingVerifyZone }) {
  return (
    <section className="rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-4 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h3 className="text-lg font-semibold">{zone.name_zh}</h3>
        <p className="text-sm text-[#5c6754]">
          {zone.missing_count ? `${zone.missing_count} 项缺价 · ` : ""}
          已确认 {nzdExact(zone.priced_incl_gst)}
        </p>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead>
            <tr className="border-b border-[#eee6d8] text-xs text-[#7b8474]">
              <th className="py-2 pr-3 font-medium">材料 / 人工</th>
              <th className="py-2 pr-3 font-medium">数量</th>
              <th className="py-2 pr-3 font-medium">SKU</th>
              <th className="py-2 pr-3 font-medium">金额（含 GST）</th>
            </tr>
          </thead>
          <tbody>
            {zone.lines.map((line) => (
              <tr key={line.id} className="border-b border-[#f3eee4] align-top">
                <td className="py-2 pr-3">
                  <p className="font-medium">{line.name_zh || line.id}</p>
                  {line.llm_reason_zh ? (
                    <p className="mt-0.5 text-xs text-[#2f4a32]">{line.llm_reason_zh}</p>
                  ) : null}
                  {line.formula ? <p className="mt-0.5 text-xs text-[#7b8474]">{line.formula}</p> : null}
                  {line.notes ? <p className="mt-0.5 text-xs text-[#7b8474]">{line.notes}</p> : null}
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-[#5c6754]">
                  {line.quantity ? `${line.quantity} ${line.unit || ""}` : "—"}
                </td>
                <td className="py-2 pr-3 text-xs text-[#5c6754]">
                  {line.sku && line.source_url ? (
                    <a href={line.source_url} className="underline" target="_blank" rel="noreferrer">
                      {line.sku}
                    </a>
                  ) : (
                    line.sku || "—"
                  )}
                </td>
                <td className="whitespace-nowrap py-2 text-[#1c2416]">
                  {line.status === "missing" ? "缺价" : nzdExact(line.amount_incl_gst)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PageAudit({
  pageDebug,
  charts,
  audit,
}: {
  pageDebug?: DrawingPageDebug[];
  charts?: DrawingChart[];
  audit?: DrawingAudit;
}) {
  const noTextPages = (pageDebug || []).filter((item) => item.role === "drawing_no_text");
  return (
    <div className="space-y-4">
      {audit ? (
        <section className="rounded-2xl border border-[#d9d0c0] bg-white p-4 sm:p-5">
          <h2 className="text-xl font-semibold">抽取核对</h2>
          <p className="mt-2 text-sm leading-6 text-[#5c6754]">
            {audit.page_count || 0} 页 · 全文 {audit.full_chars || audit.char_count || 0} 字 · 送给模型{" "}
            {audit.sent_chars || 0} 字 · 表 {audit.chart_count || 0} 张 / {audit.chart_rows || 0} 行 · 门窗{" "}
            {audit.window_count || 0} 樘
            {audit.no_text_pages ? ` · ${audit.no_text_pages} 页几乎无文字` : ""}
            {audit.schedule_pages ? ` · ${audit.schedule_pages} 页含表` : ""}
          </p>
        </section>
      ) : null}
      {noTextPages.length ? (
        <section className="rounded-2xl border border-[#e2b48a] bg-[#f8e7dc] p-4 sm:p-5" role="status">
          <h2 className="text-lg font-semibold text-[#8a3b1d]">这些页几乎没有文字层</h2>
          <p className="mt-2 text-sm leading-6 text-[#8a3b1d]">
            平面/立面如果只是线条图，尺寸不会被读取，也不会做图像识别。请对照下表确认是否缺了门窗表或面积表页。
          </p>
          <ul className="mt-3 space-y-2 text-sm text-[#8a3b1d]">
            {noTextPages.map((item) => (
              <li key={`${item.filename}-${item.page}`}>
                {item.filename || "PDF"} 第 {item.page} 页 · {item.char_count || 0} 字
                {item.preview ? ` · ${item.preview}` : ""}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {pageDebug?.length ? (
        <section>
          <h2 className="text-xl font-semibold">逐页文字层</h2>
          <div className="mt-3 overflow-x-auto rounded-2xl border border-[#d9d0c0] bg-white">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead>
                <tr className="border-b border-[#eee6d8] text-xs text-[#7b8474]">
                  <th className="px-3 py-2 font-medium">文件</th>
                  <th className="px-3 py-2 font-medium">页</th>
                  <th className="px-3 py-2 font-medium">角色</th>
                  <th className="px-3 py-2 font-medium">字数</th>
                  <th className="px-3 py-2 font-medium">表行</th>
                  <th className="px-3 py-2 font-medium">预览</th>
                </tr>
              </thead>
              <tbody>
                {pageDebug.map((item) => (
                  <tr
                    key={`${item.filename}-${item.page}`}
                    className={
                      item.role === "drawing_no_text"
                        ? "border-b border-[#f3eee4] bg-[#f8e7dc]"
                        : "border-b border-[#f3eee4]"
                    }
                  >
                    <td className="px-3 py-2 text-xs">{item.filename}</td>
                    <td className="px-3 py-2">{item.page}</td>
                    <td className="px-3 py-2">{PAGE_ROLE_LABELS[item.role || ""] || item.role}</td>
                    <td className="px-3 py-2">{item.char_count}</td>
                    <td className="px-3 py-2">{item.table_rows || 0}</td>
                    <td className="px-3 py-2 text-xs text-[#7b8474]">{item.preview || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {charts?.length ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">文字层图表每一行</h2>
          {charts.map((chart, index) => (
            <div
              key={`${chart.id}-${chart.source_file}-${chart.page}-${index}`}
              className="overflow-x-auto rounded-2xl border border-[#d9d0c0] bg-white"
            >
              <div className="border-b border-[#eee6d8] px-3 py-2 text-sm">
                <span className="font-medium">{chart.name_zh || chart.id}</span>
                <span className="ml-2 text-xs text-[#7b8474]">
                  {chart.source_file || "PDF"}
                  {chart.page ? ` · 第 ${chart.page} 页` : ""}
                  {` · ${(chart.rows || []).length} 行`}
                </span>
              </div>
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-[#eee6d8] text-xs text-[#7b8474]">
                    <th className="px-3 py-2 font-medium">原文行</th>
                    <th className="px-3 py-2 font-medium">读出</th>
                  </tr>
                </thead>
                <tbody>
                  {(chart.rows || []).map((row, rowIndex) => (
                    <tr key={`${row.line}-${rowIndex}`} className="border-b border-[#f3eee4] align-top">
                      <td className="px-3 py-2 text-xs text-[#5c6754]">{row.line || row.evidence || "—"}</td>
                      <td className="px-3 py-2">
                        {row.code ? (
                          <span>
                            {row.code} {row.w_mm}×{row.h_mm} mm × {row.count}
                            {row.kind ? ` · ${row.kind}` : ""}
                          </span>
                        ) : (
                          <span>
                            {row.label || ""}
                            {row.value ? ` ${row.value}` : ""}
                            {row.pct ? ` ${row.pct}%` : ""}
                            {row.area_m2 ? ` ${row.area_m2} m²` : ""}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </section>
      ) : (
        <p className="text-sm text-[#9a6b12]">文字层没有抽出可识别的表格行。若 PDF 是扫描件，不会对附图做识别。</p>
      )}
    </div>
  );
}

function FieldsAndWindows({
  result,
}: {
  result: Pick<DrawingVerifyResult, "fields" | "windows" | "warnings" | "explanation" | "documents" | "coverage">;
}) {
  return (
    <>
      <section>
        <h2 className="text-xl font-semibold">读到的图纸字段</h2>
        <p className="mt-2 text-sm leading-6 text-[#5c6754]">{result.explanation}</p>
        {result.documents?.length ? (
          <ul className="mt-3 space-y-1 text-xs text-[#7b8474]">
            {result.documents.map((doc) => (
              <li key={`${doc.kind}-${doc.filename}`}>
                {doc.filename || "PDF"}
                {doc.page_count ? ` · ${doc.page_count} 页` : ""}
                {doc.char_count ? ` · ${doc.char_count} 字` : ""}
                {doc.error ? ` · ${doc.error}` : ""}
              </li>
            ))}
          </ul>
        ) : null}
        {result.coverage?.sent_chars ? (
          <p className="mt-2 text-xs leading-5 text-[#7b8474]">
            全文 {result.coverage.full_chars || result.coverage.char_count} 字，送给模型 {result.coverage.sent_chars} 字
            {result.coverage.chart_rows ? ` · 表行 ${result.coverage.chart_rows}` : ""}
            {result.coverage.no_text_pages ? ` · 无文字页 ${result.coverage.no_text_pages}` : ""}。
            {result.coverage.note ? ` ${result.coverage.note}` : ""}
          </p>
        ) : null}
        {result.warnings?.length ? (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#9a6b12]">
            {result.warnings.map((warning, index) => (
              <li key={`${warning}-${index}`}>{warning}</li>
            ))}
          </ul>
        ) : null}
        {result.fields?.length ? (
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {result.fields.map((field) => (
              <div key={`${field.key}-${field.source_file}-${String(field.value)}`} className="rounded-xl bg-[#f3eee4] px-3 py-3">
                <dt className="text-xs text-[#7b8474]">{FIELD_LABELS[field.key] || field.key}</dt>
                <dd className="mt-1 text-sm font-medium">{String(field.value)}</dd>
                {field.evidence ? <p className="mt-1 text-xs text-[#7b8474]">{field.evidence}</p> : null}
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-3 text-sm text-[#9a6b12]">没有对得上原文的面积或户型字段。</p>
        )}
      </section>
      {result.windows?.length ? (
        <section>
          <h2 className="text-xl font-semibold">门窗表</h2>
          <div className="mt-3 overflow-x-auto rounded-2xl border border-[#d9d0c0] bg-white">
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead>
                <tr className="border-b border-[#eee6d8] text-xs text-[#7b8474]">
                  <th className="px-3 py-2 font-medium">代码</th>
                  <th className="px-3 py-2 font-medium">宽 × 高 mm</th>
                  <th className="px-3 py-2 font-medium">数量</th>
                  <th className="px-3 py-2 font-medium">类型</th>
                  <th className="px-3 py-2 font-medium">出处</th>
                </tr>
              </thead>
              <tbody>
                {result.windows.map((opening) => (
                  <tr key={`${opening.code}-${opening.w_mm}-${opening.h_mm}`} className="border-b border-[#f3eee4]">
                    <td className="px-3 py-2 font-medium">{opening.code}</td>
                    <td className="px-3 py-2">
                      {opening.w_mm} × {opening.h_mm}
                    </td>
                    <td className="px-3 py-2">{opening.count}</td>
                    <td className="px-3 py-2 text-xs text-[#5c6754]">{opening.kind || "—"}</td>
                    <td className="px-3 py-2 text-xs text-[#7b8474]">{opening.evidence || opening.source_file}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <p className="text-sm text-[#9a6b12]">文字层没有对得上的门窗表。</p>
      )}
    </>
  );
}

function ZoneList({
  zones,
  totals,
}: {
  zones?: DrawingVerifyZone[];
  totals?: DrawingVerifyResult["totals"];
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-xl font-semibold">按区域列出的材料</h2>
        <p className="text-sm text-[#5c6754]">
          已确认 {nzdExact(totals?.confirmed_total_incl_gst)}
          {totals?.missing_count ? ` · ${totals.missing_count} 项缺价` : ""}
        </p>
      </div>
      {zones?.length ? (
        zones.map((zone) => <ZoneTable key={zone.id} zone={zone} />)
      ) : (
        <p className="text-sm text-[#9a6b12]">没有可列出的材料行。</p>
      )}
    </section>
  );
}

export default function DrawingVerify() {
  const [busy, setBusy] = useState(false);
  const [busyNote, setBusyNote] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<DrawingVerifyResult | null>(null);
  const [tab, setTab] = useState("llm");
  const [llmReady, setLlmReady] = useState<boolean | null>(null);
  const [llmNote, setLlmNote] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/drawings/verify/ready", { cache: "no-store", signal: AbortSignal.timeout(12_000) })
      .then(async (response) => {
        const payload = (await response.json().catch(() => ({}))) as {
          llm?: boolean;
          configured?: boolean;
          reachable?: boolean;
          note?: string;
        };
        if (cancelled) return;
        setLlmReady(Boolean(payload.llm));
        setLlmNote(payload.note || "");
      })
      .catch(() => {
        if (!cancelled) {
          setLlmReady(false);
          setLlmNote("无法确认大模型是否已配置。");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const forward = new FormData();
    const kinds: string[] = [];
    const rc = data.get("rc");
    const bc = data.get("bc");
    if (rc instanceof File && rc.size > 0) {
      forward.append("files", rc);
      kinds.push("rc");
    }
    if (bc instanceof File && bc.size > 0) {
      forward.append("files", bc);
      kinds.push("bc");
    }
    for (const extra of data.getAll("extras")) {
      if (extra instanceof File && extra.size > 0) {
        forward.append("files", extra);
        kinds.push("unknown");
      }
    }
    if (!forward.has("files")) {
      setError("请至少上传一份 RC 或 BC 的 PDF。");
      return;
    }
    forward.append("kinds", kinds.join(","));
    setBusy(true);
    setBusyNote("正在上传图纸并排队核对…");
    setError("");
    setResult(null);
    setTab("llm");
    try {
      const response = await fetch("/api/drawings/verify", {
        method: "POST",
        body: forward,
        cache: "no-store",
        signal: AbortSignal.timeout(30_000),
      });
      const payload = (await response.json().catch(() => ({}))) as DrawingVerifyResult & {
        detail?: unknown;
        job_id?: string;
        status?: string;
        note?: string;
        result?: DrawingVerifyResult;
      };
      if (response.status === 202 && payload.job_id) {
        if (payload.note) setBusyNote(payload.note);
        const finished = await waitForVerifyJob(payload.job_id, setBusyNote);
        setResult(finished);
        return;
      }
      if (!response.ok) {
        throw new Error(errorMessage(payload, "图纸物料核算失败"));
      }
      setResult(payload);
    } catch (caught) {
      setError(networkErrorMessage(caught, "图纸物料核算失败"));
    } finally {
      setBusy(false);
      setBusyNote("");
    }
  };

  const compare = result?.rule_compare;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
      <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">VERIFY</p>
      <h1 className="mt-2 text-3xl font-semibold">RC / BC 图纸物料验证</h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#5c6754]">
        上传可选中文字的 Resource Consent 或 Building Consent PDF。系统按页读文字层：平面图如果几乎没有字会标出来且不做 OCR；门窗表、面积表、覆盖率表按行列抽出，要求每一行都留下核对。正则与大模型结果合并后套价。送给模型时优先保留表页，接地核对应全文。数量按公式、窗表或原文件数重算，单价只走价库。扫描件没有文字层会失败，不会用图像识别猜毫米，也不会采用模型写的金额。
      </p>

      {llmReady === false ? (
        <p className="mt-4 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="status">
          {llmNote || "未配置 OPENAI_API_KEY，无法调用大模型做本页推导。"}
        </p>
      ) : null}
      {llmReady === true && llmNote ? (
        <p className="mt-4 rounded-lg bg-[#eef3ea] px-3 py-2 text-sm text-[#2f4a32]" role="status">
          {llmNote}
        </p>
      ) : null}

      <form
        onSubmit={handleSubmit}
        className="mt-8 rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 shadow-[0_12px_40px_rgba(40,32,18,0.06)] sm:p-7"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-[#7b8474]">RC 图（面积 / 覆盖率 / 层数）</span>
            <input
              name="rc"
              type="file"
              accept="application/pdf"
              className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[#e4f0e6] file:px-3 file:py-2 file:text-[#2f4a32]"
              aria-label="Resource Consent PDF"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-[#7b8474]">BC 建筑图（门窗表优先）</span>
            <input
              name="bc"
              type="file"
              accept="application/pdf"
              className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[#e4f0e6] file:px-3 file:py-2 file:text-[#2f4a32]"
              aria-label="Building Consent PDF"
            />
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span className="text-xs text-[#7b8474]">其他带文字层的 PDF（可选）</span>
            <input
              name="extras"
              type="file"
              accept="application/pdf"
              multiple
              className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[#e4f0e6] file:px-3 file:py-2 file:text-[#2f4a32]"
              aria-label="补充 PDF"
            />
          </label>
        </div>
        <p className="mt-3 text-xs leading-5 text-[#7b8474]">
          区域按施工部位分组（厨房、卫生间、门窗、屋面等），不是 CAD 房间多边形。单份不超过 15MB。文件只用于本次核算，不写入项目库。
        </p>
        <div className="mt-4">
          <Button type="submit" disabled={busy} aria-busy={busy}>
            {busy ? "正在核对图纸…" : "用大模型推导材料"}
          </Button>
        </div>
        {error ? (
          <p className="mt-3 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="alert">
            {error}
          </p>
        ) : null}
      </form>

      {busy ? (
        <p className="mt-6 rounded-lg bg-[#eef3ea] px-3 py-2 text-sm text-[#2f4a32]" role="status">
          {busyNote || "正在读取 PDF 文字层并调用大模型。没有文字层或未配置密钥会失败，请不要关闭页面。"}
        </p>
      ) : null}

      {result ? (
        <div className="mt-8 space-y-6">
          {result.llm ? (
            <section className="rounded-2xl border border-[#d9d0c0] bg-white p-4 sm:p-5">
              <h2 className="text-xl font-semibold">大模型推导</h2>
              <p className="mt-2 text-sm leading-6 text-[#5c6754]">
                {result.llm.model ? `模型 ${result.llm.model}。` : ""}
                {result.llm.note || ""}
              </p>
              {result.llm.rejected?.length ? (
                <div className="mt-3">
                  <p className="text-sm font-medium text-[#9a6b12]">未能采用 {result.llm.rejected.length} 条模型输出</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#9a6b12]">
                    {result.llm.rejected.map((item, index) => (
                      <li key={`${item.item_id}-${index}`}>
                        {item.item_id}：{item.reason_zh}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          {compare ? (
            <Tabs
              tabs={[
                { id: "llm", label: "大模型推导" },
                { id: "rules", label: "公式对照" },
              ]}
              value={tab}
              onChange={setTab}
            />
          ) : null}

          <PageAudit pageDebug={result.page_debug} charts={result.charts} audit={result.audit} />

          {tab === "rules" && compare && !compare.error ? (
            <div className="space-y-6">
              <FieldsAndWindows result={compare} />
              <ZoneList zones={compare.zones} totals={compare.totals} />
            </div>
          ) : tab === "rules" && compare?.error ? (
            <p className="text-sm text-[#9a6b12]">{compare.error.message}</p>
          ) : (
            <div className="space-y-6">
              <FieldsAndWindows result={result} />
              <ZoneList zones={result.zones} totals={result.totals} />
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
