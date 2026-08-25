"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { uploadLimAction } from "@/app/actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectRecord } from "@/lib/api";
import { formatAucklandTime } from "@/lib/datetime";

const ORDER_URL =
  "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html";

export default function LimReport({ project }: { project: ProjectRecord }) {
  const lim = project.result.site?.lim;
  const fee = lim?.fee;
  const parsed = lim?.status === "parsed";

  return (
    <Card>
      <CardHeader>
        <CardTitle>正式 LIM</CardTitle>
        <p className="mt-1 text-xs leading-5 text-[#7b8474]">
          {lim?.disclaimer_zh || "由客户上传已购买的议会 LIM PDF。只读文字层，不识别附图。"}
        </p>
      </CardHeader>
      <CardContent>
        <UploadForm projectId={project.id} />

        {lim?.status === "awaiting_upload" || !lim ? (
          <p className="mt-4 text-sm leading-6 text-[#9a6b12]" role="status">
            还没有客户 LIM。地址查询不会用公开洪水图层冒充正式报告，也不会把订购费计入造价。
          </p>
        ) : null}

        {parsed ? (
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <Fact label="应用号" value={lim?.application_number || "文字层未读到"} />
            <Fact label="签发" value={lim?.issued_at || "文字层未读到"} />
            <Fact label="LIM 地址" value={lim?.lim_address || "文字层未读到"} />
            <Fact label="地籍" value={lim?.legal_description || "文字层未读到"} />
            <Fact label="文件" value={lim?.filename || "已上传"} />
            {lim?.queried_at ? (
              <Fact label="读取时刻" value={formatAucklandTime(lim.queried_at) + "（奥克兰）"} />
            ) : null}
          </dl>
        ) : (
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <Fact
              label="若尚未购买"
              value={
                fee?.standard_fee != null
                  ? `Standard $${fee.standard_fee} · 最多 ${fee.standard_working_days} 个工作日`
                  : "见议会订购页"
              }
              href={fee?.source_url || lim?.order_url || ORDER_URL}
            />
            <Fact
              label="加急"
              value={
                fee?.urgent_fee != null
                  ? `$${fee.urgent_fee} · 最多 ${fee.urgent_working_days} 个工作日`
                  : "见议会订购页"
              }
              href={fee?.source_url || lim?.order_url || ORDER_URL}
            />
          </dl>
        )}

        {(lim?.sections || []).length ? (
          <ol className="mt-5 grid gap-3 md:grid-cols-2">
            {lim?.sections?.map((section) => (
              <li key={section.id} className="rounded-xl bg-[#f3eee4] px-3 py-3">
                <p className="text-sm font-medium leading-6">
                  {section.heading_zh}
                  {section.heading_en ? (
                    <span className="ml-2 text-xs font-normal text-[#7b8474]">{section.heading_en}</span>
                  ) : null}
                </p>
                <p className="mt-1 text-xs text-[#7b8474]">
                  {section.s44a ? `${section.s44a} · ` : ""}
                  {sectionStateLabel(section.state)}
                </p>
                <p className="mt-2 text-sm leading-6 text-[#5c6754]">{section.body_zh}</p>
              </li>
            ))}
          </ol>
        ) : null}

        {parsed && lim?.findings?.length ? (
          <ul className="mt-4 space-y-2 text-sm leading-6 text-[#5c6754]">
            {lim.findings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}

        <a
          href={lim?.order_url || ORDER_URL}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-block text-sm text-[#2f4a32] underline"
        >
          向奥克兰议会订购正式 LIM
        </a>
      </CardContent>
    </Card>
  );
}

function UploadForm({ projectId }: { projectId: string }) {
  const bound = uploadLimAction.bind(null, projectId);
  const [state, formAction] = useActionState(bound, null);
  return (
    <form action={formAction} className="rounded-xl bg-[#f3eee4] px-3 py-3">
      <label className="flex flex-col gap-1">
        <span className="text-xs text-[#7b8474]">客户 LIM PDF（文字层）</span>
        <input
          name="lim"
          type="file"
          accept="application/pdf"
          required
          className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[#e4f0e6] file:px-3 file:py-2 file:text-[#2f4a32]"
          aria-label="正式 LIM PDF"
        />
      </label>
      <p className="mt-2 text-xs leading-5 text-[#7b8474]">
        单份不超过 15MB。地址必须与当前项目一致。扫描件没有文字层会报错，不会用图像识别猜附图。
      </p>
      <div className="mt-3">
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

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="h-11 rounded-xl bg-[#2f4a32] px-5 text-sm font-medium text-white hover:bg-[#3f6b45] disabled:opacity-60"
    >
      {pending ? "正在读 LIM 文字层…" : "上传并读取 LIM"}
    </button>
  );
}

function sectionStateLabel(state?: string) {
  if (state === "recorded") return "已从正文读到";
  if (state === "not_stated") return "正文未写明";
  if (state === "awaiting") return "等待上传";
  if (state === "public_hit") return "公开图层命中";
  if (state === "public_clear") return "公开图层未命中";
  if (state === "official_only") return "正式 LIM 才有";
  return "未核对";
}

function Fact({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <dt className="text-xs text-[#7b8474]">{label}</dt>
      <dd className="mt-1 font-medium leading-6">{value}</dd>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-[#2f4a32]">
          数据源
        </a>
      ) : null}
    </div>
  );
}
