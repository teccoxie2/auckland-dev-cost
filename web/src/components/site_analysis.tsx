"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectRecord } from "@/lib/api";

export default function SiteAnalysis({ project }: { project: ProjectRecord }) {
  const site = project.result.site;
  const imagery = site?.imagery || [];
  const buildings = site?.buildings;
  const vision = site?.vision;
  const [failed, setFailed] = useState<Record<string, boolean>>({});

  if (!imagery.length && !buildings && !vision) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>场地航拍核对</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-[#9a6b12]" role="status">
            还没有读到公开航拍。打开项目时会补读 Esri World Imagery 与 Wayback 历史镶嵌，不是实时摄像头。
          </p>
        </CardContent>
      </Card>
    );
  }

  const coveragePct =
    buildings?.parcel_coverage != null ? `${Math.round(buildings.parcel_coverage * 100)}%` : null;
  const modelRan = vision?.status === "model";

  return (
    <Card>
      <CardHeader>
        <CardTitle>场地航拍核对</CardTitle>
        <p className="mt-1 text-xs leading-5 text-[#7b8474]">
          最新公开航拍与历史镶嵌，用来核对现有房屋和场地。不是直播卫星，也不能改地籍面积、区划或金额。
        </p>
      </CardHeader>
      <CardContent>
        {imagery.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {imagery.map((frame) => (
              <figure key={frame.id} className="overflow-hidden rounded-xl border border-[#e4dccb] bg-[#f3eee4]">
                {failed[frame.id] ? (
                  <p className="px-3 py-10 text-center text-sm text-[#9a6b12]" role="status">
                    这张公开航拍没加载出来。可到数据源查看原图。
                  </p>
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={frame.url}
                    alt={frame.label_zh}
                    className="h-56 w-full object-cover"
                    onError={() => setFailed((current) => ({ ...current, [frame.id]: true }))}
                  />
                )}
                <figcaption className="px-3 py-2">
                  <p className="text-sm font-medium">{frame.label_zh}</p>
                  <p className="mt-1 text-xs leading-5 text-[#7b8474]">{frame.note}</p>
                  {frame.source_url ? (
                    <a
                      href={frame.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-[#2f4a32]"
                    >
                      {frame.source_name || "数据源"}
                    </a>
                  ) : null}
                </figcaption>
              </figure>
            ))}
          </div>
        ) : (
          <p className="text-sm leading-6 text-[#9a6b12]" role="status">
            公开航拍地址没拼出来。区划方案仍按议会地籍继续。
          </p>
        )}

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-[#e4dccb] bg-[#f3eee4] p-3">
            <p className="text-xs text-[#7b8474]">LINZ 屋顶轮廓</p>
            {buildings?.found ? (
              <>
                <p className="mt-1 text-sm font-medium">
                  {buildings.count ?? 0} 栋
                  {buildings.roof_area_m2 != null ? ` · 相交屋顶约 ${buildings.roof_area_m2} m²` : ""}
                  {coveragePct ? ` · 约占本户 ${coveragePct}` : ""}
                </p>
                <p className="mt-2 text-xs leading-5 text-[#5c6754]">{buildings.note}</p>
              </>
            ) : (
              <p className="mt-1 text-sm leading-6 text-[#9a6b12]" role="status">
                {buildings?.note || "屋顶轮廓未读到。超时或空结果时不把地块当成空地。"}
              </p>
            )}
            {buildings?.source_url ? (
              <a href={buildings.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-[#2f4a32]">
                {buildings.source_name || "LINZ NZ Building Outlines"}
              </a>
            ) : null}
          </div>
          <div className="rounded-xl border border-[#e4dccb] bg-[#f3eee4] p-3">
            <p className="text-xs text-[#7b8474]">视觉模型</p>
            <p className="mt-1 text-sm font-medium">{modelRan ? vision?.model || "已运行" : "未运行"}</p>
            <p className="mt-2 text-xs leading-5 text-[#5c6754]">
              {modelRan
                ? vision?.note
                : vision?.note || "未配置 OPENAI_API_KEY 时不把航拍送给模型，也不编造看见的树木、车道或空地。"}
            </p>
          </div>
        </div>

        {vision?.observations ? (
          <p className="mt-4 text-sm leading-6 text-[#5c6754]">{vision.observations}</p>
        ) : null}

        {(vision?.findings || []).length ? (
          <ul className="mt-4 space-y-1 text-sm leading-6 text-[#5c6754]">
            {vision?.findings?.map((item) => (
              <li key={item}>· {item}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm leading-6 text-[#7b8474]">
            没有额外场地判读。初版方案仍按区划硬规则与地籍面积排序。
          </p>
        )}
      </CardContent>
    </Card>
  );
}
