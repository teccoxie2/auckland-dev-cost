"use client";

import ProjectView from "./view";

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  return <ProjectView params={params} />;
}
