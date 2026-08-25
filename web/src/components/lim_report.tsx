"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectRecord } from "@/lib/api";
import { formatAucklandTime } from "@/lib/datetime";

const ORDER_URL =
  "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html";

export default function LimReport({ project }: { project: ProjectRecord }) {
  const lim = project.result.site?.lim;
  const fee = lim?.fee;

  if (!lim) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>LIM 公开核对</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-[#9a6b12]" role="status">
            还没有读到公开洪水、地面径流和填埋图层。打开项目时会补读 Healthy Waters 公开图。这不是已购买的正式 LIM PDF。
          </p>
          <OrderLink />
        </CardContent>
      </Card>
    );
  }

  const layers = lim.layers || [];
  const notQueried = lim.not_queried || [];
  const hits = layers.filter((item) => item.present);

  return (
    <Card>
      <CardHeader>
        <CardTitle>LIM 公开核对</CardTitle>
        <p className="mt-1 text-xs leading-5 text-[#7b8474]">{lim.disclaimer_zh}</p>
      </CardHeader>
      <CardContent>
        {lim.status === "unavailable" ? (
          <p className="rounded-xl bg-[#f8e7dc] px-3 py-2 text-sm leading-6 text-[#8a3b1d]" role="alert">
            {lim.note || "公开图层未读到。正式 LIM 仍需向议会订购。"}
          </p>
        ) : null}

        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Fact
            label="正式 LIM"
            value="未购买。本页只做公开图层核对"
            href={lim.about_url}
          />
          <Fact
            label="Standard 订购费"
            value={
              fee?.standard_fee != null
                ? `$${fee.standard_fee} · 最多 ${fee.standard_working_days} 个工作日`
                : "见议会订购页"
            }
            href={fee?.source_url || lim.order_url || ORDER_URL}
          />
          <Fact
            label="加急"
            value={
              fee?.urgent_fee != null
                ? `$${fee.urgent_fee} · 最多 ${fee.urgent_working_days} 个工作日`
                : "见议会订购页"
            }
            href={fee?.source_url || lim.order_url || ORDER_URL}
          />
        </dl>

        {lim.queried_at ? (
          <p className="mt-3 text-xs text-[#7b8474]">核对时刻 {formatAucklandTime(lim.queried_at)}（奥克兰）</p>
        ) : null}

        {(lim.sections || []).length ? (
          <ol className="mt-5 grid gap-3 md:grid-cols-2">
            {lim.sections?.map((section) => (
              <li key={section.id} className="rounded-xl bg-[#f3eee4] px-3 py-3">
                <p className="text-sm font-medium leading-6">
                  {section.heading_zh}
                  {section.heading_en ? (
                    <span className="ml-2 text-xs font-normal text-[#7b8474]">{section.heading_en}</span>
                  ) : null}
                </p>
                <p className="mt-1 text-xs text-[#7b8474]">
                  {section.s44a ? `${section.s44a} · ` : ""}
                  {sectionStateLabel(section.state)}
                </p>
                <p className="mt-2 text-sm leading-6 text-[#5c6754]">{section.body_zh}</p>
                {section.source_url ? (
                  <a
                    href={section.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-xs text-[#2f4a32]"
                  >
                    数据源
                  </a>
                ) : null}
              </li>
            ))}
          </ol>
        ) : null}

        {lim.findings?.length ? (
          <ul className="mt-4 space-y-2 text-sm leading-6 text-[#5c6754]">
            {lim.findings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : hits.length === 0 && lim.status === "checked" && !(lim.sections || []).length ? (
          <p className="mt-4 text-sm leading-6 text-[#5c6754]" role="status">
            抽查的公开洪水、沿海淹没与填埋点未与本户相交。正式 LIM 仍可能有管网、许可、通知或其他灾害记录。
          </p>
        ) : null}

        {layers.length ? (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <caption className="mb-2 text-left text-xs text-[#7b8474]">已查询的公开图层</caption>
              <thead>
                <tr className="text-xs text-[#7b8474]">
                  <th scope="col" className="pb-2 pr-3 font-medium">
                    图层
                  </th>
                  <th scope="col" className="pb-2 pr-3 font-medium">
                    结果
                  </th>
                  <th scope="col" className="pb-2 font-medium">
                    说明
                  </th>
                </tr>
              </thead>
              <tbody>
                {layers.map((layer) => (
                  <tr key={layer.id} className="border-t border-[#e4dccb] align-top">
                    <th scope="row" className="py-2 pr-3 font-medium">
                      {layer.source_url ? (
                        <a href={layer.source_url} target="_blank" rel="noreferrer" className="text-[#2f4a32]">
                          {layer.label_zh}
                        </a>
                      ) : (
                        layer.label_zh
                      )}
                    </th>
                    <td className="py-2 pr-3">{layerStatus(layer)}</td>
                    <td className="py-2 text-xs leading-5 text-[#5c6754]">
                      {sampleText(layer.sample)}
                      {layer.note ? ` ${layer.note}` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {notQueried.length && !(lim.sections || []).length ? (
          <div className="mt-4 rounded-xl bg-[#f3eee4] px-3 py-3">
            <p className="text-sm font-medium">未查询（避免误判）</p>
            <ul className="mt-2 space-y-2 text-xs leading-5 text-[#5c6754]">
              {notQueried.map((item) => (
                <li key={item.id}>
                  {item.source_url ? (
                    <a href={item.source_url} target="_blank" rel="noreferrer" className="text-[#2f4a32]">
                      {item.label_zh}
                    </a>
                  ) : (
                    item.label_zh
                  )}
                  {item.reason ? `：${item.reason}` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <p className="mt-4 text-xs leading-5 text-[#7b8474]">
          信用卡/借记卡另加 {fee?.card_surcharge_percent ?? 1.75}% ，未计入造价。每个方案的法定费已计入 Standard LIM。
        </p>
        <OrderLink href={lim.order_url || ORDER_URL} />
      </CardContent>
    </Card>
  );
}

function sectionStateLabel(state?: string) {
  if (state === "public_hit") return "公开图层命中";
  if (state === "public_clear") return "公开图层未命中";
  if (state === "official_only") return "正式 LIM 才有";
  if (state === "timeout") return "查询超时，失败开放";
  if (state === "unavailable") return "未读到公开图层";
  return "未核对";
}

function layerStatus(layer: { present?: boolean; error?: string | null; count?: number }) {
  if (layer.error === "timeout") return "超时";
  if (layer.error) return "失败开放";
  if (layer.present) return `命中${layer.count ? ` · ${layer.count}` : ""}`;
  return "未命中";
}

function sampleText(sample?: Record<string, string | number | boolean> | null) {
  if (!sample) return "";
  return Object.entries(sample)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${value}`)
    .join("，");
}

function Fact({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <dt className="text-xs text-[#7b8474]">{label}</dt>
      <dd className="mt-1 font-medium leading-6">{value}</dd>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-[#2f4a32]">
          数据源
        </a>
      ) : null}
    </div>
  );
}

function OrderLink({ href = ORDER_URL }: { href?: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="mt-3 inline-block text-sm text-[#2f4a32] underline"
    >
      向奥克兰议会订购正式 LIM
    </a>
  );
}
