import type { ProjectSummary } from "./api";

const STORAGE_KEY = "auckland-dev-cost-recent-v1";
const MAX_RECENT = 12;

function sameAddress(left: string, right: string) {
  return left.trim().toLowerCase() === right.trim().toLowerCase();
}

export function readRecentProjects(): ProjectSummary[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((row): row is ProjectSummary => {
      if (!row || typeof row !== "object") return false;
      const item = row as ProjectSummary;
      return Boolean(item.id && item.address && item.created_at && item.status);
    });
  } catch {
    return [];
  }
}

export function rememberRecentProject(item: ProjectSummary) {
  if (typeof window === "undefined") return;
  const next = [
    item,
    ...readRecentProjects().filter(
      (row) => row.id !== item.id && !sameAddress(row.address, item.address),
    ),
  ].slice(0, MAX_RECENT);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function forgetRecentProject(projectId: string) {
  if (typeof window === "undefined") return;
  const next = readRecentProjects().filter((row) => row.id !== projectId);
  if (!next.length) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function clearRecentProjects() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
