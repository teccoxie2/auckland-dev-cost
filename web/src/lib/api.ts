export interface ProjectSummary {
  id: string;
  address: string;
  created_at: string;
  status: string;
}

export interface CostLine {
  id: string;
  status: "priced" | "missing" | "rule" | "zero";
  category?: string;
  name_zh?: string;
  unit?: string;
  quantity?: number;
  unit_price?: number;
  amount_incl_gst?: number;
  sku?: string | null;
  source_name?: string;
  source_url?: string | null;
  retrieved_at?: string;
  notes?: string;
  formula?: string | null;
}

export interface SchemeOption {
  id: string;
  template: {
    id: string;
    name_zh: string;
    kind: string;
    dwellings: number;
    bedrooms: number;
    bathrooms: number;
    storeys: number;
    gfa_m2: number;
  };
  verdict: {
    status: string;
    needs_resource_consent: boolean;
    reasons: string[];
  };
  quantities?: {
    footprint_m2: number;
    timber_90_lm: number;
    cavity_required: boolean;
    e2: { score: number; note: string };
    window_schedule: Array<{ code: string; w_mm: number; h_mm: number; count: number }>;
  };
  totals?: {
    construction_confirmed_incl_gst: number;
    design_incl_gst: number;
    statutory_incl_gst: number;
    contingency_incl_gst: number;
    confirmed_total_incl_gst: number;
    missing_count: number;
    rlb_benchmark_low?: number;
    rlb_benchmark_high?: number;
    rlb_source_name?: string;
    rlb_source_url?: string;
  };
  lines?: CostLine[];
  intensity_note?: string;
}

export interface ProjectRecord {
  id: string;
  address: string;
  created_at: string;
  status: string;
  result: {
    error?: { code: string; message: string };
    site?: {
      geo: { display_name: string; lat: number; lon: number; source_url: string };
      zone?: { zone_name: string; zone_code: number; source_url: string };
      overlays?: Array<{ key: string; present: boolean }>;
    };
    rules?: {
      permitted_dwellings: number;
      height_m: number;
      coverage: number;
      landscaped: number;
      qualifying_matters: string[];
      consent_note: string;
    };
    explanation?: string;
    pm_review?: { status: string; note: string };
    options?: SchemeOption[];
    trace?: Array<{ node: string; detail: string }>;
  };
}

export async function fetchProjects(): Promise<ProjectSummary[]> {
  const response = await fetch("/engine/projects", { cache: "no-store" });
  if (!response.ok) throw new Error("无法读取项目列表");
  const data = await response.json();
  return data.projects;
}

export async function createProject(address: string): Promise<ProjectRecord> {
  const response = await fetch("/engine/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.detail?.error?.message || data?.error?.message || "核算失败");
  }
  return data;
}

export async function fetchProject(id: string): Promise<ProjectRecord> {
  const response = await fetch(`/engine/projects/${id}`, { cache: "no-store" });
  if (!response.ok) throw new Error("项目不存在");
  return response.json();
}
