"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import type { DrawingVerifyResult, DrawingVerifyZone } from "@/lib/api";
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

function errorMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== "object") return fallback;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return fallback;
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

export default function DrawingVerify() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DrawingVerifyResult | null>(null);

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
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/drawings/verify", {
        method: "POST",
        body: forward,
        cache: "no-store",
      });
      const payload = (await response.json().catch(() => ({}))) as DrawingVerifyResult & { detail?: unknown };
      if (!response.ok) {
        throw new Error(errorMessage(payload, "图纸物料核算失败"));
      }
      setResult(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "图纸物料核算失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
      <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">VERIFY</p>
      <h1 className="mt-2 text-3xl font-semibold">RC / BC 图纸物料验证</h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#5c6754]">
        上传可选中文字的 Resource Consent 或 Building Consent PDF。系统只读文字层里的面积、层高、厨卫套数和门窗表，按施工区域列出材料。扫描件没有文字层会失败，不会用图像识别猜毫米，也不会编单价。
      </p>

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
            {busy ? "正在读文字层并按区域套料…" : "按图纸列出材料"}
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
          正在读取 PDF 文字层。没有文字层会失败，请不要关闭页面。
        </p>
      ) : null}

      {result ? (
        <div className="mt-8 space-y-6">
          <section>
            <h2 className="text-xl font-semibold">读到的图纸字段</h2>
            <p className="mt-2 text-sm leading-6 text-[#5c6754]">{result.explanation}</p>
            {result.warnings?.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#9a6b12]">
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
            {result.fields?.length ? (
              <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {result.fields.map((field) => (
                  <div key={`${field.key}-${field.source_file}`} className="rounded-xl bg-[#f3eee4] px-3 py-3">
                    <dt className="text-xs text-[#7b8474]">{FIELD_LABELS[field.key] || field.key}</dt>
                    <dd className="mt-1 text-sm font-medium">{String(field.value)}</dd>
                    {field.evidence ? <p className="mt-1 text-xs text-[#7b8474]">{field.evidence}</p> : null}
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-3 text-sm text-[#9a6b12]">文字层没有读到面积或户型字段，仅可能有门窗表。</p>
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
                        <td className="px-3 py-2 text-xs text-[#7b8474]">{opening.source_file}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          <section className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 className="text-xl font-semibold">按区域列出的材料</h2>
              <p className="text-sm text-[#5c6754]">
                已确认 {nzdExact(result.totals?.confirmed_total_incl_gst)}
                {result.totals?.missing_count ? ` · ${result.totals.missing_count} 项缺价` : ""}
              </p>
            </div>
            {result.zones?.length ? (
              result.zones.map((zone) => <ZoneTable key={zone.id} zone={zone} />)
            ) : (
              <p className="text-sm text-[#9a6b12]">没有可列出的材料行。</p>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
