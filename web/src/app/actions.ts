"use server";

import { redirect } from "next/navigation";
import { configureProject, postProject, uploadDrawings } from "@/lib/engine";

export async function createProjectAction(_prev: { error: string } | null, formData: FormData) {
  const address = String(formData.get("address") || "").trim();
  const latRaw = String(formData.get("selected_lat") || "").trim();
  const lonRaw = String(formData.get("selected_lon") || "").trim();
  const lat = Number(latRaw);
  const lon = Number(lonRaw);
  const inAuckland = lat >= -37.3 && lat <= -35.89 && lon >= 174.15 && lon <= 175.59;
  if (!latRaw || !lonRaw || !Number.isFinite(lat) || !Number.isFinite(lon) || !inAuckland || address.length < 3) {
    return { error: "请从下拉列表选择一条奥克兰议会地址。同一门牌可能对应多条记录。" };
  }
  let project;
  try {
    project = await postProject({
      address,
      lat,
      lon,
      full_address: String(formData.get("full_address") || address).trim(),
      sap_address_id: String(formData.get("sap_address_id") || "") || null,
      sap_site_id: String(formData.get("sap_site_id") || "") || null,
    });
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

export async function uploadDrawingsAction(projectId: string, _prev: { error: string } | null, formData: FormData) {
  const forward = new FormData();
  const kinds: string[] = [];
  const rc = formData.get("rc");
  const bc = formData.get("bc");
  if (rc instanceof File && rc.size > 0) {
    forward.append("files", rc);
    kinds.push("rc");
  }
  if (bc instanceof File && bc.size > 0) {
    forward.append("files", bc);
    kinds.push("bc");
  }
  for (const extra of formData.getAll("extras")) {
    if (extra instanceof File && extra.size > 0) {
      forward.append("files", extra);
      kinds.push("unknown");
    }
  }
  if (!forward.has("files")) {
    return { error: "请至少上传一份 RC 或 BC 的 PDF。" };
  }
  forward.append("kinds", kinds.join(","));
  try {
    await uploadDrawings(projectId, forward);
  } catch (error) {
    const message = error instanceof Error ? error.message : "图纸核算失败";
    return { error: message };
  }
  redirect(`/projects/${projectId}`);
}
