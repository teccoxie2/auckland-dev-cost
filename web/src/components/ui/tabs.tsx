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
  const current = Math.max(
    0,
    tabs.findIndex((tab) => tab.id === value),
  );

  return (
    <div
      role="tablist"
      className="flex flex-wrap gap-2"
      onKeyDown={(event) => {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        const delta = event.key === "ArrowRight" ? 1 : -1;
        const next = tabs[(current + delta + tabs.length) % tabs.length];
        if (next) onChange(next.id);
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === value}
          tabIndex={tab.id === value ? 0 : -1}
          onClick={() => onChange(tab.id)}
          className={cn(
            "min-h-11 rounded-full border px-4 py-2 text-sm",
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
