export default function ProjectLoading() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-16" aria-busy="true">
      <p className="text-sm text-[#5c6754]" role="status">
        正在读取地块并核算，通常需要十几秒到一分钟…
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-hidden>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-xl bg-[#e8e0d2]" />
        ))}
      </div>
    </main>
  );
}
