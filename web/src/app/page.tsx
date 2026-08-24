import Link from "next/link";
import AddressForm from "@/components/address_form";
import { listProjects } from "@/lib/engine";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let projects: Awaited<ReturnType<typeof listProjects>> = [];
  let listError = "";
  try {
    projects = await listProjects();
  } catch {
    listError = "暂时读不到已建项目（核算服务未启动时会这样）。你仍可以直接输入地址开始核算。";
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-8 sm:px-8">
      <header className="mb-10 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">AUCKLAND · MVP</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">奥克兰住宅开发核算台</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#5c6754]">
            从奥克兰议会地址库选出物业后，系统读取地块面积、Unitary Plan 区划和 DEM 坡度，给出适合这块地的初版方案。你再选户型大小、厨房和卫生间数量；挡土墙、覆盖率和叠加层会写进建议和核算。
          </p>
        </div>
      </header>

      <AddressForm />

      <section className="mt-10">
        <h2 className="text-lg font-semibold">已建项目</h2>
        {listError ? (
          <p className="mt-3 text-sm text-[#9a6b12]">{listError}</p>
        ) : projects.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-[#d9d0c0] px-4 py-8 text-sm text-[#5c6754]">
            还没有项目。从议会地址库选出物业后会保存在本机工作台，可同时对比多块地。
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
