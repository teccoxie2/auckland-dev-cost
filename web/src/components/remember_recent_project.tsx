"use client";

import { useEffect } from "react";
import type { ProjectSummary } from "@/lib/api";
import { rememberRecentProject } from "@/lib/recent_projects";

export default function RememberRecentProject({
  id,
  address,
  created_at,
  status,
}: ProjectSummary) {
  useEffect(() => {
    rememberRecentProject({ id, address, created_at, status });
  }, [id, address, created_at, status]);
  return null;
}
