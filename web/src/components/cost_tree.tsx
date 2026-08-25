import type { CostLine } from "@/lib/api";
import { nzdExact } from "@/lib/money";

const CATEGORY_LABELS: Record<string, string> = {
  materials: "材料",
  labour: "人工",
  statutory: "法定费用",
  design: "设计",
  contingency: "预备",
  missing: "价源缺失",
};

export default function CostTree({ lines }: { lines: CostLine[] }) {
  if (!lines.length) {
    return <p className="text-sm text-[#9a6b12]">这一版还没有分项行。</p>;
  }
  const groups = new Map<string, CostLine[]>();
  for (const line of lines) {
    const key = line.status === "missing" ? "missing" : line.category || "other";
    const bucket = groups.get(key) || [];
    bucket.push(line);
    groups.set(key, bucket);
  }
  return (
    <ul className="space-y-3">
      {[...groups.entries()].map(([category, items]) => {
        const priced = items
          .filter((item) => item.status !== "missing")
          .reduce((sum, item) => sum + (item.amount_incl_gst || 0), 0);
        return (
          <li key={category} className="rounded-xl bg-[#f3eee4] px-3 py-3">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>{CATEGORY_LABELS[category] || category}</span>
              <span>{category === "missing" ? `${items.length} 项缺价` : nzdExact(priced)}</span>
            </div>
            <ul className="mt-2 space-y-1 text-xs text-[#5c6754]">
              {items.map((item) => (
                <li key={item.id} className="flex justify-between gap-3">
                  <span>{item.name_zh || item.id}</span>
                  <span>
                    {item.status === "missing" ? "缺价" : nzdExact(item.amount_incl_gst)}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        );
      })}
    </ul>
  );
}
