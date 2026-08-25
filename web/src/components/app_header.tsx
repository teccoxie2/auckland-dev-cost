import Link from "next/link";

export default function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-[#e4dccb] bg-[#f3eee4]/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-8">
        <Link href="/" className="min-w-0 truncate text-sm font-semibold tracking-tight sm:text-base">
          奥克兰开发核算台
        </Link>
        <p className="shrink-0 text-xs text-[#7b8474]">MVP · 公开报价源</p>
      </div>
    </header>
  );
}
