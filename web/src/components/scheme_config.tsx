"use client";

import { useActionState, useMemo, useState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import { configureProjectAction } from "@/app/actions";
import type { SchemeOption } from "@/lib/api";

const GFA: Record<string, Record<string, number>> = {
  "1": { "2": 85, "3": 110, "4": 150, "5": 180 },
  "2": { "2": 110, "3": 165, "4": 220, "5": 260 },
  "3": { "2": 130, "3": 180, "4": 240, "5": 280 },
};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="h-11 rounded-xl bg-[#2f4a32] px-5 text-sm font-medium text-white hover:bg-[#3f6b45] disabled:opacity-60"
    >
      {pending ? "正在按选装重新核算…" : "按选装生成这一版"}
    </button>
  );
}

export default function SchemeConfig({
  projectId,
  option,
}: {
  projectId: string;
  option?: SchemeOption;
}) {
  const bound = useMemo(() => configureProjectAction.bind(null, projectId), [projectId]);
  const [state, formAction] = useActionState(bound, null);
  const template = option?.template;
  const [kind, setKind] = useState(template?.kind || "standalone");
  const [dwellings, setDwellings] = useState(template?.dwellings || 1);
  const [storeys, setStoreys] = useState(template?.storeys || 1);
  const [bedrooms, setBedrooms] = useState(template?.bedrooms || 3);
  const [bathrooms, setBathrooms] = useState(template?.bathrooms || 2);
  const [kitchens, setKitchens] = useState(template?.kitchens || 1);
  const [gfa, setGfa] = useState(template?.gfa_m2 || 110);
  const [gfaTouched, setGfaTouched] = useState(false);

  const handleStoreys = (value: number) => {
    setStoreys(value);
    if (!gfaTouched) setGfa(suggestGfa(bedrooms, value, dwellings));
  };
  const handleBedrooms = (value: number) => {
    setBedrooms(value);
    if (!gfaTouched) setGfa(suggestGfa(value, storeys, dwellings));
    setBathrooms((current) => Math.max(current, value >= 4 ? 3 : value >= 3 ? 2 : 1));
  };
  const handleDwellings = (value: number) => {
    setDwellings(value);
    setKitchens((current) => Math.max(current, value));
    if (!gfaTouched) setGfa(suggestGfa(bedrooms, storeys, value));
  };

  return (
    <form action={formAction} className="rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 sm:p-6">
      <h2 className="text-lg font-semibold">按你的需求选装</h2>
      <p className="mt-1 text-sm leading-6 text-[#5c6754]">
        先点上方一张初版方案作起点，再改户型大小、厨房和卫生间。核算仍用这块地已经读到的区划、面积和坡度。
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="形态">
          <select
            name="kind"
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            className="h-11 w-full rounded-xl border border-[#cfc4b0] bg-white px-3"
            aria-label="形态"
          >
            <option value="standalone">独栋</option>
            <option value="duplex">双拼</option>
            <option value="terrace">联排</option>
            <option value="minor_dwelling">主屋 + 独立住宅</option>
          </select>
        </Field>
        <NumberField label="套数" name="dwellings" value={dwellings} min={1} max={6} onChange={handleDwellings} />
        <NumberField label="层数" name="storeys" value={storeys} min={1} max={5} onChange={handleStoreys} />
        <NumberField label="每套卧室" name="bedrooms" value={bedrooms} min={1} max={6} onChange={handleBedrooms} />
        <NumberField label="卫生间" name="bathrooms" value={bathrooms} min={1} max={6} onChange={setBathrooms} />
        <NumberField label="厨房" name="kitchens" value={kitchens} min={1} max={4} onChange={setKitchens} />
        <label className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3">
          <span className="text-xs text-[#7b8474]">建筑面积 GFA（m²）</span>
          <input
            name="gfa_m2"
            type="number"
            min={60}
            max={450}
            step={5}
            value={gfa}
            onChange={(event) => {
              setGfaTouched(true);
              setGfa(Number(event.target.value));
            }}
            className="h-11 rounded-xl border border-[#cfc4b0] bg-white px-3"
            aria-label="建筑面积"
          />
        </label>
      </div>
      <p className="mt-3 text-xs leading-5 text-[#7b8474]">
        未手改面积时，按初版规则：单层三房约 110 m²、二层三房 165 m²、二层四房 220 m²。厨房无公开总价，会按套数标缺价。
      </p>
      <div className="mt-4">
        <SubmitButton />
      </div>
      {state?.error ? (
        <p className="mt-3 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="alert">
          {state.error}
        </p>
      ) : null}
    </form>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-[#7b8474]">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  name,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  name: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-[#7b8474]">{label}</span>
      <input
        name={name}
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-11 rounded-xl border border-[#cfc4b0] bg-white px-3"
        aria-label={label}
      />
    </label>
  );
}

function suggestGfa(bedrooms: number, storeys: number, dwellings: number) {
  const storeyKey = String(Math.min(Math.max(storeys, 1), 3));
  const bedKey = String(Math.min(Math.max(bedrooms, 2), 5));
  return (GFA[storeyKey]?.[bedKey] || 165) * Math.max(dwellings, 1);
}
