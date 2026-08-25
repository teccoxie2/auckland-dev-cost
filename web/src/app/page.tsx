import AddressForm from "@/components/address_form";
import RecentQueries from "@/components/recent_queries";

export const dynamic = "force-dynamic";

export default function HomePage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-10 sm:px-6">
      <header className="mb-8">
        <p className="text-sm tracking-[0.18em] text-[#7a5a2b]">AUCKLAND</p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">奥克兰住宅开发核算台</h1>
      <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#5c6754]">
        从议会地址库点选物业。系统读取地块、区划和坡度，给出适合这一户的初版方案和可核对造价。拆分门牌只核算当前现址。
      </p>
      </header>

      <div className="rounded-2xl border border-[#d9d0c0] bg-[#fffaf3] p-5 shadow-[0_12px_40px_rgba(40,32,18,0.06)] sm:p-7">
        <AddressForm embedded>
          <RecentQueries />
        </AddressForm>
      </div>
    </div>
  );
}
