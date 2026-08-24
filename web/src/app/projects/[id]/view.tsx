"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import SchemeConfig from "@/components/scheme_config";
import type { AdviceItem, CostLine, ProjectRecord, SchemeOption } from "@/lib/api";
import { nzd, nzdExact } from "@/lib/money";

export default function ProjectView({ project }: { project: ProjectRecord }) {
  const result = project.result;
  const firstId =
    result.selected_id ||
    result.options?.find((item) => item.recommended && item.verdict.status !== "infeasible")?.id ||
    result.options?.find((item) => item.verdict.status !== "infeasible")?.id ||
    result.options?.[0]?.id ||
    "";
  const [selected, setSelected] = useState(firstId);
  const option = useMemo(
    () => result.options?.find((item) => item.id === selected),
    [result.options, selected],
  );

  if (result.error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        <Link href="/" className="text-sm text-[#2f4a32]">
          ← 返回工作台
        </Link>
        <h1 className="mt-6 text-2xl font-semibold">{project.address}</h1>
        <p className="mt-4 rounded-xl bg-[#f8e7dc] px-4 py-3 text-[#8a3b1d]" role="alert">
          {result.error.message}
        </p>
      </main>
    );
  }

  const parcel = result.site?.parcel;
  const terrain = result.site?.terrain;
  const overlays = (result.site?.overlays || []).filter((item) => item.present);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
      <Link href="/" className="text-sm text-[#2f4a32]">
        ← 返回工作台
      </Link>
      <header className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-[#7a5a2b]">初版设计方案</p>
          <h1 className="mt-1 text-3xl font-semibold">{project.address}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#5c6754]">{result.explanation}</p>
        </div>
        <p className="text-xs text-[#7b8474]">{result.pm_review?.note}</p>
      </header>

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label="规范地址" value={result.site?.geo.display_name || "—"} />
        <Fact
          label="Unitary Plan 区划"
          value={result.site?.zone?.zone_name || "—"}
          href={result.site?.zone?.source_url}
        />
        <Fact
          label="地块面积"
          value={parcel?.found && parcel.area_m2 ? `${parcel.area_m2} m²` : parcel?.note || "未读到"}
          href={parcel?.source_url}
        />
        <Fact
          label="DEM 坡度 / 高差"
          value={
            terrain?.slope_deg != null
              ? `${terrain.slope_deg}° · ${terrain.height_range_m} m`
              : terrain?.note || "未读到"
          }
          href={terrain?.source_url}
        />
        <Fact label="许可套数（规则表）" value={`${result.rules?.permitted_dwellings ?? "—"} 套`} />
        <Fact
          label="覆盖率上限"
          value={
            parcel?.found && parcel.area_m2 && result.rules?.coverage
              ? `约 ${Math.round(parcel.area_m2 * result.rules.coverage)} m² 占地`
              : `${intPct(result.rules?.coverage)} 覆盖率`
          }
        />
        <Fact
          label="叠加层命中"
          value={overlays.length ? overlays.map((item) => item.key).join("、") : "抽查层未命中"}
        />
        <Fact label="地籍" value={parcel?.legal_description || parcel?.formatted_address || "—"} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">这块地需要考虑的事</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(result.advice || []).map((item) => (
            <AdviceCard key={item.id} item={item} />
          ))}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">因地制宜初版方案</h2>
        <p className="mt-1 text-sm text-[#5c6754]">点选一张作为起点，再在下方改厨卫和户型。</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(result.options || []).map((item) => (
            <OptionCard
              key={item.id}
              option={item}
              selected={item.id === selected}
              onSelect={() => item.verdict.status !== "infeasible" && setSelected(item.id)}
            />
          ))}
        </div>
      </section>

      <div className="mt-8">
        <SchemeConfig projectId={project.id} option={option} />
      </div>

      {option && option.verdict.status !== "infeasible" ? <CostPanel option={option} /> : null}

      <section className="mt-10 rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5">
        <h2 className="text-lg font-semibold">LangGraph 运行轨迹</h2>
        <ol className="mt-3 space-y-2 text-sm text-[#5c6754]">
          {(result.trace || []).map((step, index) => (
            <li key={`${step.node}-${index}`}>
              <span className="font-medium text-[#1c2416]">{step.node}</span>
              <span className="mx-2">→</span>
              <span>{step.detail}</span>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function intPct(value?: number) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function Fact({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div className="rounded-xl border border-[#d9d0c0] bg-[#fffaf3] px-4 py-3">
      <p className="text-xs text-[#7b8474]">{label}</p>
      <p className="mt-1 text-sm font-medium leading-6">{value}</p>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-[#2f4a32]">
          数据源
        </a>
      ) : null}
    </div>
  );
}

function AdviceCard({ item }: { item: AdviceItem }) {
  const tone =
    item.severity === "constraint"
      ? "border-[#e4c4b4] bg-[#f8e7dc]"
      : item.severity === "watch"
        ? "border-[#ead9b0] bg-[#f7f0de]"
        : "border-[#d9d0c0] bg-[#fffaf3]";
  return (
    <article className={`rounded-2xl border p-4 ${tone}`}>
      <h3 className="font-semibold">{item.title_zh}</h3>
      <p className="mt-2 text-sm leading-6 text-[#5c6754]">{item.body_zh}</p>
      {item.source_url ? (
        <a href={item.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-[#2f4a32]">
          {item.source_name || "依据"}
        </a>
      ) : null}
    </article>
  );
}

function OptionCard({
  option,
  selected,
  onSelect,
}: {
  option: SchemeOption;
  selected: boolean;
  onSelect: () => void;
}) {
  const blocked = option.verdict.status === "infeasible";
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={blocked}
      className={`rounded-2xl border p-4 text-left transition ${
        blocked
          ? "cursor-not-allowed border-dashed border-[#d9d0c0] bg-transparent opacity-80"
          : selected
            ? "border-[#2f4a32] bg-[#fffaf3] shadow-[0_8px_24px_rgba(47,74,50,0.08)]"
            : "border-[#d9d0c0] bg-[#fffaf3] hover:border-[#2f4a32]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold">{option.template.name_zh}</h3>
        <span className="flex flex-wrap justify-end gap-1">
          {option.recommended ? (
            <span className="rounded-full bg-[#e4f0e6] px-2 py-0.5 text-xs text-[#2f6b4f]">初版推荐</span>
          ) : null}
          <StatusPill status={option.verdict.status} />
        </span>
      </div>
      <p className="mt-2 text-sm text-[#5c6754]">
        {option.template.dwellings} 套 · {option.template.bedrooms} 房 {option.template.bathrooms} 卫 ·{" "}
        {option.template.kitchens || 1} 厨 · {option.template.storeys} 层 · {option.template.gfa_m2} m²
      </p>
      {option.why?.length ? (
        <ul className="mt-2 space-y-1 text-xs leading-5 text-[#5c6754]">
          {option.why.slice(0, 3).map((reason) => (
            <li key={reason}>· {reason}</li>
          ))}
        </ul>
      ) : null}
      {blocked ? (
        <p className="mt-3 text-sm text-[#8a3b1d]">{option.verdict.reasons.join(" ")}</p>
      ) : (
        <p className="mt-3 text-2xl font-semibold tracking-tight">
          {nzd(option.totals?.confirmed_total_incl_gst)}
          <span className="ml-2 text-xs font-normal text-[#7b8474]">已核对公开价（部分账单）</span>
        </p>
      )}
      {(option.totals?.missing_count || 0) > 0 && !blocked ? (
        <p className="mt-1 text-xs text-[#9a6b12]">另有 {option.totals?.missing_count} 项缺价未计入</p>
      ) : null}
    </button>
  );
}

function StatusPill({ status }: { status: string }) {
  if (status === "permitted") return <span className="rounded-full bg-[#e4f0e6] px-2 py-0.5 text-xs text-[#2f6b4f]">许可路径</span>;
  if (status === "resource_consent") return <span className="rounded-full bg-[#f4ead4] px-2 py-0.5 text-xs text-[#9a6b12]">需 RC</span>;
  return <span className="rounded-full bg-[#f4e4dc] px-2 py-0.5 text-xs text-[#8a3b1d]">不可行</span>;
}

function CostPanel({ option }: { option: SchemeOption }) {
  const joinery = (option.lines || []).filter((line) => line.id.startsWith("joinery_"));
  const rest = (option.lines || []).filter((line) => !line.id.startsWith("joinery_"));
  return (
    <section className="mt-8 rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{option.template.name_zh} · 分项总账</h2>
          <p className="mt-1 text-sm text-[#5c6754]">{option.intensity_note}</p>
        </div>
        <p className="text-2xl font-semibold">{nzd(option.totals?.confirmed_total_incl_gst)}</p>
      </div>
      {option.totals?.rlb_benchmark_low ? (
        <p className="mt-3 rounded-lg bg-[#f3eee4] px-3 py-2 text-sm leading-6 text-[#5c6754]">
          上方是已核对 SKU/官方费率的部分账单，不是整房交钥匙价。厨房、铝窗、水电、外装等缺价未计入。
          完整施工公开基准（
          <a href={option.totals.rlb_source_url} target="_blank" rel="noreferrer" className="text-[#2f4a32] underline">
            RLB 2025 Auckland 独栋 $2,500–$3,800/m²
          </a>
          ）约 {nzd(option.totals.rlb_benchmark_low)} – {nzd(option.totals.rlb_benchmark_high)}。
        </p>
      ) : null}
      <dl className="mt-5 grid gap-3 sm:grid-cols-4">
        <Mini label="已确认施工" value={nzd(option.totals?.construction_confirmed_incl_gst)} />
        <Mini label="设计费" value={nzd(option.totals?.design_incl_gst)} />
        <Mini label="法定费用" value={nzd(option.totals?.statutory_incl_gst)} />
        <Mini label="预备费" value={nzd(option.totals?.contingency_incl_gst)} />
      </dl>
      {option.quantities ? (
        <p className="mt-4 text-xs leading-5 text-[#7b8474]">
          占地 {option.quantities.footprint_m2} m² · {option.quantities.kitchens || 1} 厨 ·{" "}
          {option.quantities.bathrooms || option.template.bathrooms} 卫 · 90×45 木材 {option.quantities.timber_90_lm} m
          {option.quantities.retaining
            ? ` · 挡土墙约 ${option.quantities.retaining.height_m} m × ${option.quantities.retaining.length_m} m`
            : ""}
          。E2 风险分 {option.quantities.e2.score}
          {option.quantities.cavity_required ? "（计入空腔垫条）" : ""}。{option.quantities.e2.note}
        </p>
      ) : null}
      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-[#e4dccb] text-xs text-[#7b8474]">
              <th className="py-2 font-medium">科目</th>
              <th className="py-2 font-medium">数量</th>
              <th className="py-2 font-medium">单价</th>
              <th className="py-2 font-medium">金额</th>
              <th className="py-2 font-medium">报价源</th>
            </tr>
          </thead>
          <tbody>
            {rest.map((line) => (
              <LineRow key={line.id} line={line} />
            ))}
            {joinery.length ? (
              <tr className="border-t border-[#eee6d8]">
                <td className="py-3 align-top font-medium">门窗表（不计价）</td>
                <td colSpan={4} className="py-3 text-[#5c6754]">
                  {joinery.map((line) => line.name_zh).join("；")}。无公开整樘零售价。
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-[#f3eee4] px-3 py-3">
      <p className="text-xs text-[#7b8474]">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function LineRow({ line }: { line: CostLine }) {
  return (
    <tr className="border-b border-[#f0e8da] align-top">
      <td className="py-3">
        <p className="font-medium">{line.name_zh || line.id}</p>
        {line.formula ? <p className="mt-1 text-xs text-[#7b8474]">{line.formula}</p> : null}
        {line.notes ? <p className="mt-1 text-xs text-[#7b8474]">{line.notes}</p> : null}
      </td>
      <td className="py-3 whitespace-nowrap text-[#5c6754]">
        {line.unit === "percent" && line.quantity
          ? `${(line.quantity * 100).toFixed(0)}%`
          : line.quantity
            ? `${line.quantity} ${line.unit || ""}`
            : "—"}
      </td>
      <td className="py-3 whitespace-nowrap text-[#5c6754]">
        {line.unit === "percent"
          ? "—"
          : line.unit_price !== undefined
            ? nzdExact(line.unit_price)
            : "—"}
      </td>
      <td className="py-3 whitespace-nowrap">
        {line.status === "missing" ? <span className="text-[#9a6b12]">缺价</span> : nzdExact(line.amount_incl_gst)}
      </td>
      <td className="py-3">
        {line.source_url ? (
          <a href={line.source_url} target="_blank" rel="noreferrer" className="text-[#2f4a32] underline-offset-2 hover:underline">
            {line.source_name}
          </a>
        ) : (
          <span className="text-[#7b8474]">{line.source_name || "—"}</span>
        )}
        {line.sku ? <p className="text-xs text-[#7b8474]">SKU {line.sku}</p> : null}
        {line.retrieved_at ? <p className="text-xs text-[#7b8474]">{line.retrieved_at}</p> : null}
      </td>
    </tr>
  );
}
