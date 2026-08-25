"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { ProjectSummary } from "@/lib/api";
import { cn } from "@/lib/cn";
import { clearRecentProjects, readRecentProjects } from "@/lib/recent_projects";

function statusLabel(status: string) {
  if (status === "ready") return "已出方案";
  if (status === "running") return "核算中";
  return "未完成";
}

export default function RecentQueries() {
  const [items, setItems] = useState<ProjectSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setItems(readRecentProjects());
    setReady(true);
  }, []);

  useEffect(() => {
    const handlePointer = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handlePointer);
    return () => document.removeEventListener("mousedown", handlePointer);
  }, []);

  if (!ready || !items.length) return null;

  const latest = items[0];

  const handleClear = () => {
    clearRecentProjects();
    setItems([]);
    setOpen(false);
  };

  return (
    <div ref={boxRef} className="relative mt-5 border-t border-[#eee6d8] pt-4">
      <div className="flex items-center gap-3">
        <p className="shrink-0 text-xs text-[#7b8474]">本机最近查询</p>
        <button
          type="button"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-label="打开本机最近查询"
          onClick={() => setOpen((value) => !value)}
          className={cn(
            "flex min-w-0 flex-1 items-center justify-between gap-3 rounded-lg border bg-white px-3 py-2 text-left text-sm transition",
            open ? "border-[#2f4a32]" : "border-[#d9d0c0] hover:border-[#2f4a32]",
          )}
        >
          <span className="min-w-0 truncate">{latest.address}</span>
          <span className="shrink-0 text-xs text-[#7b8474]">{items.length} 处 ▾</span>
        </button>
      </div>
      {open ? (
        <ul
          role="listbox"
          aria-label="本机最近查询"
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
          <li className="border-t border-[#eee6d8] px-3 py-2">
            <button
              type="button"
              onClick={handleClear}
              className="text-xs text-[#7b8474] hover:text-[#8a3b1d]"
            >
              清除本机记录
            </button>
          </li>
        </ul>
      ) : null}
    </div>
  );
}
