import Link from "next/link";

export default function ProjectNotFound() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <Link href="/" className="text-sm text-[#2f4a32]">
        ← 返回工作台
      </Link>
      <h1 className="mt-6 text-2xl font-semibold">找不到这个项目</h1>
      <p className="mt-3 text-sm leading-6 text-[#5c6754]">
        可能已被删除，或核算服务还没有这条记录。请从工作台重新选择议会地址创建。
      </p>
    </main>
  );
}
