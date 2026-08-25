"use client";

import { useEffect } from "react";
import { forgetRecentProject } from "@/lib/recent_projects";

export default function ForgetMissingProject() {
  useEffect(() => {
    const projectId = window.location.pathname.split("/").filter(Boolean).at(-1);
    if (projectId) forgetRecentProject(projectId);
  }, []);
  return null;
}
