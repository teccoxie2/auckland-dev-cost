"use server";

import { redirect } from "next/navigation";
import { configureProject, postProject } from "@/lib/engine";

export async function createProjectAction(_prev: { error: string } | null, formData: FormData) {
  const address = String(formData.get("address") || "").trim();
  if (address.length < 3) {
    return { error: "请输入完整的奥克兰地址" };
  }
  let project;
  try {
    project = await postProject(address);
  } catch (error) {
    const message = error instanceof Error ? error.message : "核算失败";
    return { error: message };
  }
  redirect(`/projects/${project.id}`);
}

export async function configureProjectAction(projectId: string, _prev: { error: string } | null, formData: FormData) {
  try {
    await configureProject(projectId, {
      kind: String(formData.get("kind") || "standalone"),
      dwellings: Number(formData.get("dwellings") || 1),
      storeys: Number(formData.get("storeys") || 1),
      bedrooms: Number(formData.get("bedrooms") || 3),
      bathrooms: Number(formData.get("bathrooms") || 2),
      kitchens: Number(formData.get("kitchens") || 1),
      gfa_m2: Number(formData.get("gfa_m2") || 110),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "选装核算失败";
    return { error: message };
  }
  redirect(`/projects/${projectId}`);
}
