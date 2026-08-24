"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createProject, fetchProjects, type ProjectSummary } from "@/lib/api";

const EXAMPLES = [
  "115 Bruce Road, Glenfield, Auckland",
  "1 Queen Street, Auckland CBD",
  "24 Hurstmere Road, Takapuna, Auckland",
];

export default function HomePage() {
  const router = useRouter();
  const [address, setAddress] = useState("115 Bruce Road, Glenfield, Auckland");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isListing, setIsListing] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchProjects()
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setIsListing(false));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const project = await createProject(address.trim());
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "核算失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-8 sm:px-8">
      <header className="mb-10 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">AUCKLAND · MVP</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">奥克兰住宅开发核算台</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#5c6754]">
            输入一个地址。系统读取公开地块与 Unitary Plan 区划，生成 3 房、4 房、联排等方案，并用可核对的奥克兰/新西兰公开报价核算材料、人工、Council 与 Watercare 费用。
          </p>
        </div>
      </header>

      <form
        onSubmit={handleSubmit}
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
          />
          <button
            type="submit"
            disabled={isLoading || address.trim().length < 3}
            className="h-12 rounded-xl bg-[#2f4a32] px-6 text-sm font-medium text-white transition hover:bg-[#3f6b45] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "正在读地并核算…" : "生成开发方案"}
          </button>
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
        {error ? (
          <p className="mt-4 rounded-lg bg-[#f8e7dc] px-3 py-2 text-sm text-[#8a3b1d]" role="alert">
            {error}
          </p>
        ) : null}
        <p className="mt-4 text-xs leading-5 text-[#7b8474]">
          第一期金额禁止由模型口算。材料以 Bunnings 公开 SKU 为主，法定费用以 Auckland Council / Watercare
          官方表为准；厨房、铝窗整樘等无公开总价的科目会标成缺项，不会填假数。
        </p>
      </form>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">已建项目</h2>
        {isListing ? (
          <p className="mt-3 text-sm text-[#5c6754]">正在读取项目列表…</p>
        ) : projects.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-[#d9d0c0] px-4 py-8 text-sm text-[#5c6754]">
            还没有项目。输入地址后会保存在本机工作台，可同时对比多块地。
          </p>
        ) : (
          <ul className="mt-4 grid gap-3">
            {projects.map((project) => (
              <li key={project.id}>
                <Link
                  href={`/projects/${project.id}`}
                  className="flex items-center justify-between rounded-xl border border-[#d9d0c0] bg-[#fffaf3] px-4 py-4 hover:border-[#2f4a32]"
                >
                  <span>
                    <span className="block font-medium">{project.address}</span>
                    <span className="mt-1 block text-xs text-[#7b8474]">
                      {new Date(project.created_at).toLocaleString("zh-CN")} · {project.status === "ready" ? "已核算" : "失败"}
                    </span>
                  </span>
                  <span className="text-sm text-[#2f4a32]">查看方案</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
