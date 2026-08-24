import type { ConfigureSpec, ProjectRecord, ProjectSummary } from "./api";

const ENGINE_URL = process.env.ENGINE_URL || "http://127.0.0.1:8764";

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await fetch(`${ENGINE_URL}/projects`, { cache: "no-store" });
  if (!response.ok) throw new Error("无法读取项目列表");
  const data = await response.json();
  return data.projects ?? [];
}

export async function getProject(id: string): Promise<ProjectRecord | null> {
  const response = await fetch(`${ENGINE_URL}/projects/${id}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("无法读取项目");
  return response.json();
}

export async function postProject(input: {
  address: string;
  lat: number;
  lon: number;
  full_address?: string;
  sap_address_id?: string | null;
  sap_site_id?: string | null;
}): Promise<ProjectRecord> {
  const response = await fetch(`${ENGINE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.detail?.error?.message || data?.error?.message || "核算失败");
  }
  return data;
}

export async function configureProject(projectId: string, spec: ConfigureSpec): Promise<ProjectRecord> {
  const response = await fetch(`${ENGINE_URL}/projects/${projectId}/configure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : data?.detail?.error?.message;
    throw new Error(detail || "选装核算失败");
  }
  return data;
}
