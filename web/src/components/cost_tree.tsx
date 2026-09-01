import type { CostLine } from "@/lib/api";
import { nzdExact } from "@/lib/money";

const GROUP_ORDER = [
  "prelim",
  "structure",
  "interior",
  "outdoor",
  "fees",
  "lift",
  "contingency",
  "missing",
  "materials",
  "labour",
  "statutory",
  "design",
];

const GROUP_LABELS: Record<string, string> = {
  prelim: "前期准备",
  structure: "建筑主体",
  interior: "内装",
  outdoor: "室外场地工程",
  fees: "法定与专业费",
  lift: "电梯",
  contingency: "预备",
  missing: "价源缺失",
  materials: "材料",
  labour: "人工",
  statutory: "法定费用",
  design: "设计",
};

function groupKey(line: CostLine): string {
  if (line.wbs_group) return line.wbs_group;
  if (line.status === "missing") return "missing";
  return line.category || "other";
}

function itemKey(line: CostLine): string {
  return line.wbs_item || line.id;
}

function itemLabel(line: CostLine): string {
  return line.wbs_item_zh || line.name_zh || line.id;
}

function isPriced(line: CostLine): boolean {
  return line.status !== "missing";
}

export default function CostTree({ lines }: { lines: CostLine[] }) {
  if (!lines.length) {
    return <p className="text-sm text-[#9a6b12]">这一版还没有分项行。</p>;
  }
  const groups = new Map<string, CostLine[]>();
  for (const line of lines) {
    const key = groupKey(line);
    const bucket = groups.get(key) || [];
    bucket.push(line);
    groups.set(key, bucket);
  }
  const ordered = [...groups.entries()].sort((left, right) => {
    const leftRank = GROUP_ORDER.indexOf(left[0]);
    const rightRank = GROUP_ORDER.indexOf(right[0]);
    return (leftRank < 0 ? 99 : leftRank) - (rightRank < 0 ? 99 : rightRank);
  });
  return (
    <ul className="space-y-3">
      {ordered.map(([category, items]) => {
        const priced = items.filter(isPriced).reduce((sum, item) => sum + (item.amount_incl_gst || 0), 0);
        const missingCount = items.filter((item) => item.status === "missing").length;
        const subgroups = new Map<string, CostLine[]>();
        for (const line of items) {
          const key = itemKey(line);
          const bucket = subgroups.get(key) || [];
          bucket.push(line);
          subgroups.set(key, bucket);
        }
        return (
          <li key={category} className="rounded-xl bg-[#f3eee4] px-3 py-3">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>{GROUP_LABELS[category] || category}</span>
              <span className="text-right">
                {nzdExact(priced)}
                {missingCount ? (
                  <span className="ml-2 text-xs font-normal text-[#9a6b12]">{missingCount} 项缺价</span>
                ) : null}
              </span>
            </div>
            <ul className="mt-2 space-y-2 text-xs text-[#5c6754]">
              {[...subgroups.entries()].map(([subKey, subItems]) => {
                const header = itemLabel(subItems[0]);
                const nested = subItems.length > 1 || (subItems[0].wbs_item && subItems[0].wbs_item !== subItems[0].id);
                if (!nested) {
                  const item = subItems[0];
                  return (
                    <li key={subKey} className="flex justify-between gap-3">
                      <span>{item.name_zh || item.id}</span>
                      <span>{item.status === "missing" ? "缺价" : nzdExact(item.amount_incl_gst)}</span>
                    </li>
                  );
                }
                const subPriced = subItems.filter(isPriced).reduce((sum, item) => sum + (item.amount_incl_gst || 0), 0);
                const subMissing = subItems.filter((item) => item.status === "missing").length;
                return (
                  <li key={subKey}>
                    <div className="flex justify-between gap-3 font-medium text-[#2f4a32]">
                      <span>{header}</span>
                      <span>
                        {subMissing && !subPriced ? "缺价" : nzdExact(subPriced)}
                        {subMissing && subPriced ? (
                          <span className="ml-1 font-normal text-[#9a6b12]">{subMissing} 缺价</span>
                        ) : null}
                      </span>
                    </div>
                    <ul className="mt-1 space-y-1 border-l border-[#d9d0c0] pl-3">
                      {subItems.map((item) => (
                        <li key={item.id} className="flex justify-between gap-3">
                          <span>{item.name_zh || item.id}</span>
                          <span>{item.status === "missing" ? "缺价" : nzdExact(item.amount_incl_gst)}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                );
              })}
            </ul>
          </li>
        );
      })}
    </ul>
  );
}
