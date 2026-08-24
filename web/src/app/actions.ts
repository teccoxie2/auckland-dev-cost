"use server";

import { redirect } from "next/navigation";
import { postProject } from "@/lib/engine";

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
