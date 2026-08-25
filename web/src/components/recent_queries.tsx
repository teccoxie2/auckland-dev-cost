"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ProjectSummary } from "@/lib/api";
import { cn } from "@/lib/cn";

function latestByAddress(projects: ProjectSummary[]): ProjectSummary[] {
  const unique: ProjectSummary[] = [];
  const seen = new Set<string>();
  for (const project of projects) {
    const key = project.address.trim().toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(project);
  }
  return unique;
}

function statusLabel(status: string) {
  if (status === "ready") return "已出方案";
  if (status === "running") return "核算中";
  return "未完成";
}

export default function RecentQueries({
  projects,
  error,
}: {
  projects: ProjectSummary[];
  error?: string;
}) {
  const items = useMemo(() => latestByAddress(projects), [projects]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handlePointer = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handlePointer);
    return () => document.removeEventListener("mousedown", handlePointer);
  }, []);

  if (error) {
    return <p className="mt-4 text-xs leading-5 text-[#9a6b12]">{error}</p>;
  }
  if (!items.length) return null;

  const latest = items[0];

  return (
    <div ref={boxRef} className="relative mt-5 border-t border-[#eee6d8] pt-4">
      <div className="flex items-center gap-3">
        <p className="shrink-0 text-xs text-[#7b8474]">已查询的项目</p>
        <button
          type="button"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-label="打开已查询的项目"
          onClick={() => setOpen((value) => !value)}
          className={cn(
            "flex min-w-0 flex-1 items-center justify-between gap-3 rounded-lg border bg-white px-3 py-2 text-left text-sm transition",
            open ? "border-[#2f4a32]" : "border-[#d9d0c0] hover:border-[#2f4a32]",
          )}
        >
          <span className="min-w-0 truncate">{latest.address}</span>
          <span className="shrink-0 text-xs text-[#7b8474]">
            {items.length} 处 ▾
          </span>
        </button>
      </div>
      {open ? (
        <ul
          role="listbox"
          aria-label="已查询的项目"
          className="absolute z-20 mt-2 max-h-64 w-full overflow-auto rounded-xl border border-[#d9d0c0] bg-white py-1 shadow-[0_12px_40px_rgba(40,32,18,0.12)]"
        >
          {items.map((project) => (
            <li key={project.id} role="presentation">
              <Link
                href={`/projects/${project.id}`}
                role="option"
                aria-selected={project.id === latest.id}
                className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm hover:bg-[#eef3ea]"
                onClick={() => setOpen(false)}
              >
                <span className="min-w-0 truncate">{project.address}</span>
                <span className="shrink-0 text-xs text-[#7b8474]">{statusLabel(project.status)}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
