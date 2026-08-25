"use client";

import { cn } from "@/lib/cn";

export function Tabs({
  tabs,
  value,
  onChange,
}: {
  tabs: Array<{ id: string; label: string }>;
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === value}
          tabIndex={0}
          onClick={() => onChange(tab.id)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm",
            tab.id === value
              ? "border-[#2f4a32] bg-[#2f4a32] text-white"
              : "border-[#d9d0c0] bg-[#fffaf3] text-[#5c6754] hover:border-[#2f4a32]",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
