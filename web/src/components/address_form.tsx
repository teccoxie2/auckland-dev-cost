"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";
import { createProjectAction } from "@/app/actions";

const EXAMPLES = [
  "115 Bruce Road, Glenfield, Auckland",
  "1 Queen Street, Auckland CBD",
  "24 Hurstmere Road, Takapuna, Auckland",
];

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="h-12 rounded-xl bg-[#2f4a32] px-6 text-sm font-medium text-white transition hover:bg-[#3f6b45] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? "正在读地并核算…" : "生成开发方案"}
    </button>
  );
}

export default function AddressForm() {
  const [address, setAddress] = useState("115 Bruce Road, Glenfield, Auckland");
  const [state, formAction] = useActionState(createProjectAction, null);

  return (
    <form
      action={formAction}
      className="rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 shadow-[0_12px_40px_rgba(40,32,18,0.06)] sm:p-7"
    >
      <label htmlFor="address" className="text-sm font-medium">
        物业地址
      </label>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <input
          id="address"
          name="address"
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          placeholder="例如 115 Bruce Road, Glenfield"
          className="h-12 flex-1 rounded-xl border border-[#cfc4b0] bg-white px-4 text-base outline-none ring-[#2f4a32] focus:ring-2"
          aria-label="物业地址"
          required
          minLength={3}
        />
        <SubmitButton />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setAddress(example)}
            className="rounded-full border border-[#d9d0c0] px-3 py-1 text-xs text-[#5c6754] hover:border-[#2f4a32] hover:text-[#1c2416]"
          >
            {example}
          </button>
        ))}
      </div>
      {state?.error ? (
        <p className="mt-4 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="alert">
          {state.error}
        </p>
      ) : null}
      <p className="mt-4 text-xs leading-5 text-[#7b8474]">
        第一期金额禁止由模型口算。材料以 Bunnings 公开 SKU 为主，法定费用以 Auckland Council / Watercare
        官方表为准；厨房、铝窗整樘等无公开总价的科目会标成缺项，不会填假数。提交后请等待约数秒。
      </p>
    </form>
  );
}
