import Link from "next/link";
import { notFound } from "next/navigation";
import RememberRecentProject from "@/components/remember_recent_project";
import ProjectView from "./view";
import { getProject } from "@/lib/engine";

export const dynamic = "force-dynamic";

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) notFound();

  const remembered = (
    <RememberRecentProject
      id={project.id}
      address={project.address}
      created_at={project.created_at}
      status={project.status}
    />
  );

  if (project.result.error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        {remembered}
        <Link href="/" className="text-sm text-[#2f4a32]">
          ← 返回工作台
        </Link>
        <h1 className="mt-6 text-2xl font-semibold">{project.address}</h1>
        <p className="mt-4 rounded-xl bg-[#f8e7dc] px-4 py-3 text-[#8a3b1d]" role="alert">
          {project.result.error.message}
        </p>
      </main>
    );
  }

  return (
    <>
      {remembered}
      <ProjectView project={project} />
    </>
  );
}
