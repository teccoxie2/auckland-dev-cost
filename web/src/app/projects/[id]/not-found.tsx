import Link from "next/link";
import ForgetMissingProject from "@/components/forget_missing_project";

export default function ProjectNotFound() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <ForgetMissingProject />
      <Link href="/" className="text-sm text-[#2f4a32]">
        ← 返回工作台
      </Link>
      <h1 className="mt-6 text-2xl font-semibold">找不到这个项目</h1>
      <p className="mt-4 text-sm leading-6 text-[#5c6754]">
        查询记录已被清空，或链接已失效。请从首页重新点选议会地址。
      </p>
    </main>
  );
}
