"use client";

import { useActionState, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import { createProjectAction } from "@/app/actions";
import { Button } from "@/components/ui/button";
import type { AddressHit } from "@/lib/api";

const EXAMPLES = ["55 Nelson Street", "115 Bruce Road Glenfield", "115A Bruce Road Glenfield"];

function SubmitButton({ canSubmit }: { canSubmit: boolean }) {
  const { pending } = useFormStatus();
  const disabled = pending || !canSubmit;
  return (
    <Button type="submit" disabled={disabled} className="h-12 px-6">
      {pending ? "正在读地并出初版方案…" : "读取地块并出初版方案"}
    </Button>
  );
}

export default function AddressForm({
  embedded = false,
  children,
}: {
  embedded?: boolean;
  children?: ReactNode;
}) {
  const listId = useId();
  const boxRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<AddressHit[]>([]);
  const [selected, setSelected] = useState<AddressHit | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [splitNote, setSplitNote] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [state, formAction] = useActionState(createProjectAction, null);

  useEffect(() => {
    const trimmed = query.trim();
    if (selected && trimmed === selected.full_address) {
      setHits([]);
      setLoading(false);
      setSearchError("");
      return;
    }
    if (trimmed.length < 3) {
      setHits([]);
      setLoading(false);
      setSearchError("");
      setSplitNote("");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setSearchError("");
      try {
        const response = await fetch(`/api/addresses?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data?.detail?.error?.message || data?.error?.message || "议会地址库暂时读不到");
        }
        const addresses = (data.addresses || []) as AddressHit[];
        setHits(addresses);
        setSplitNote(typeof data.split_note === "string" ? data.split_note : "");
        setActiveIndex(0);
        setOpen(true);
      } catch (error) {
        if (controller.signal.aborted) return;
        setHits([]);
        setSplitNote("");
        setSearchError(error instanceof Error ? error.message : "议会地址库暂时读不到");
        setOpen(true);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 280);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, selected]);

  useEffect(() => {
    const handlePointer = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handlePointer);
    return () => document.removeEventListener("mousedown", handlePointer);
  }, []);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (selected && value.trim() !== selected.full_address) setSelected(null);
  };

  const handleSelect = (hit: AddressHit) => {
    setSelected(hit);
    setQuery(hit.full_address);
    setHits([]);
    setOpen(false);
    setSearchError("");
  };

  const showList = open && query.trim().length >= 3 && !selected;
  const activeHit = hits[activeIndex];

  return (
    <form
      action={formAction}
      onSubmit={(event) => {
        if (!selected) event.preventDefault();
      }}
      className={embedded ? "" : "rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 shadow-[0_12px_40px_rgba(40,32,18,0.06)] sm:p-7"}
    >
      {selected ? (
        <>
          <input type="hidden" name="address" value={selected.full_address} />
          <input type="hidden" name="full_address" value={selected.full_address} />
          <input type="hidden" name="selected_lat" value={String(selected.lat)} />
          <input type="hidden" name="selected_lon" value={String(selected.lon)} />
          <input type="hidden" name="sap_address_id" value={selected.sap_address_id || ""} />
          <input type="hidden" name="sap_site_id" value={selected.sap_site_id || ""} />
        </>
      ) : null}

      <label htmlFor="address-search" className="text-sm font-medium">
        物业地址
      </label>
      <p id="address-hint" className="mt-1 text-xs leading-5 text-[#7b8474]">
        从奥克兰议会地址库检索。开发完成后的拆分门牌（如 115A/B/C…）没有整宗 115，必须点选现址中的一户。
      </p>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start">
        <div ref={boxRef} className="relative flex-1">
          <input
            id="address-search"
            value={query}
            onChange={(event) => handleQueryChange(event.target.value)}
            onFocus={() => {
              if (query.trim().length >= 3 && !selected) setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !selected) event.preventDefault();
              if (!showList) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActiveIndex((index) => Math.min(index + 1, Math.max(hits.length - 1, 0)));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveIndex((index) => Math.max(index - 1, 0));
              } else if (event.key === "Enter" && activeHit) {
                event.preventDefault();
                handleSelect(activeHit);
              } else if (event.key === "Escape") {
                setOpen(false);
              }
            }}
            placeholder="例如 55 Nelson Street"
            className="h-12 w-full rounded-xl border border-[#cfc4b0] bg-white px-4 text-base outline-none ring-[#2f4a32] focus:ring-2"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={showList}
            aria-controls={listId}
            aria-activedescendant={showList && activeHit ? `${listId}-${activeIndex}` : undefined}
            aria-describedby="address-hint"
            autoComplete="off"
          />
          {showList ? (
            <ul
              id={listId}
              role="listbox"
              aria-label="奥克兰议会地址"
              className="absolute z-20 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-[#d9d0c0] bg-white shadow-[0_12px_40px_rgba(40,32,18,0.12)]"
            >
              {loading ? (
                <li className="px-4 py-3 text-sm text-[#5c6754]">正在检索议会地址库…</li>
              ) : searchError ? (
                <li className="px-4 py-3 text-sm text-[#8a3b1d]" role="alert">
                  {searchError}
                </li>
              ) : hits.length === 0 ? (
                <li className="px-4 py-3 text-sm text-[#5c6754]">议会地址库没有匹配。请改写门牌或路名。</li>
              ) : (
                hits.map((hit, index) => (
                  <li key={`${hit.full_address}-${hit.lat}`} role="presentation">
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={index === activeIndex}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => handleSelect(hit)}
                      className={`flex w-full flex-col items-start px-4 py-3 text-left text-sm ${
                        index === activeIndex ? "bg-[#eef3ea]" : "bg-white"
                      }`}
                    >
                      <span className="font-medium">{hit.full_address}</span>
                      <span className="mt-0.5 text-xs text-[#7b8474]">
                        {[hit.locality, hit.full_number].filter(Boolean).join(" · ")}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </div>
        <SubmitButton canSubmit={Boolean(selected)} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => {
              setSelected(null);
              setQuery(example);
              setOpen(true);
            }}
            className="rounded-full border border-[#d9d0c0] px-3 py-1 text-xs text-[#5c6754] hover:border-[#2f4a32] hover:text-[#1c2416]"
          >
            {example}
          </button>
        ))}
      </div>
      {splitNote ? (
        <p className="mt-4 rounded-lg bg-[#f7f0de] px-3 py-2 text-sm leading-6 text-[#9a6b12]" role="status">
          {splitNote}
        </p>
      ) : null}
      {selected ? (
        <p className="mt-4 text-sm text-[#2f6b4f]">已选择 {selected.full_address}</p>
      ) : query.trim().length >= 3 ? (
        <p className="mt-4 text-sm text-[#9a6b12]">还没有选定地址，请从下拉列表点选一条。</p>
      ) : null}
      {state?.error ? (
        <p className="mt-4 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="alert">
          {state.error}
        </p>
      ) : null}
      {children}
      <p className="mt-4 text-xs leading-5 text-[#7b8474]">
        地址来自 Auckland Council AC_Address 公开图层，与 GeoMaps 同一套门牌数据。材料以 Bunnings 公开 SKU
        为主，法定费用以 Auckland Council / Watercare 官方表为准。厨房柜体按 Kaboodle SKU 计，电器安装和未命中尺寸的铝窗仍标缺项。
      </p>
    </form>
  );
}
