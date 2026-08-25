import AddressForm from "@/components/address_form";
import RecentQueries from "@/components/recent_queries";
import { listProjects } from "@/lib/engine";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let projects: Awaited<ReturnType<typeof listProjects>> = [];
  let listError = "";
  try {
    projects = await listProjects();
  } catch {
    listError = "暂时读不到已查询的项目，仍可直接检索议会地址。";
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-10 sm:px-6">
      <header className="mb-8">
        <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">AUCKLAND</p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">奥克兰住宅开发核算台</h1>
        <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#5c6754]">
          从议会地址库点选物业，读取地块与区划后给出适合这块地的初版方案。拆分门牌只核算当前这一户。
        </p>
      </header>

      <div className="rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 shadow-[0_12px_40px_rgba(40,32,18,0.06)] sm:p-7">
        <AddressForm embedded>
          <RecentQueries projects={projects} error={listError} />
        </AddressForm>
      </div>
    </div>
  );
}
