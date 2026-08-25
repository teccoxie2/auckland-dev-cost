import type { SchemeOption } from "@/lib/api";
import { nzd } from "@/lib/money";
import { Badge } from "@/components/ui/badge";

export default function SchemeCompare({ options }: { options: SchemeOption[] }) {
  if (!options.length) {
    return (
      <p className="rounded-xl border border-dashed border-[#d9d0c0] px-4 py-8 text-sm text-[#5c6754]">
        这块地还没有生成方案。请确认地址核算已完成。
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-[#e4dccb] text-xs text-[#7b8474]">
            <th className="py-2 font-medium">方案</th>
            <th className="py-2 font-medium">形态</th>
            <th className="py-2 font-medium">套数 / 户型</th>
            <th className="py-2 font-medium">GFA</th>
            <th className="py-2 font-medium">许可</th>
            <th className="py-2 font-medium">已核对总价</th>
            <th className="py-2 font-medium">缺项</th>
          </tr>
        </thead>
        <tbody>
          {options.map((option) => {
            const blocked = option.verdict.status === "infeasible";
            const total = option.totals?.confirmed_total_incl_gst;
            return (
              <tr key={option.id} className="border-b border-[#f0e8da] align-top">
                <td className="py-3 font-medium">
                  {option.template.name_zh}
                  {option.recommended ? (
                    <Badge tone="ok" className="ml-2">
                      推荐
                    </Badge>
                  ) : null}
                </td>
                <td className="py-3 text-[#5c6754]">{option.template.kind}</td>
                <td className="py-3 text-[#5c6754]">
                  {option.template.dwellings} 套 · {option.template.bedrooms} 房 {option.template.bathrooms} 卫
                </td>
                <td className="py-3 text-[#5c6754]">
                  {option.template.gfa_missing ? "未读到" : `${option.template.gfa_m2} m²`}
                </td>
                <td className="py-3">
                  <VerdictBadge status={option.verdict.status} />
                </td>
                <td className="py-3">
                  {blocked && option.origin !== "drawings" ? "—" : total != null ? nzd(total) : "—"}
                </td>
                <td className="py-3 text-[#9a6b12]">
                  {option.totals?.missing_count ? `${option.totals.missing_count} 项` : blocked ? "—" : "无"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function VerdictBadge({ status }: { status: string }) {
  if (status === "permitted") return <Badge tone="ok">许可路径</Badge>;
  if (status === "resource_consent") return <Badge tone="warn">需 RC</Badge>;
  return <Badge tone="bad">不可行</Badge>;
}
