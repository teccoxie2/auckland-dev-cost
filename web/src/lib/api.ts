export interface AddressHit {
  label: string;
  full_address: string;
  full_number?: string | null;
  road?: string | null;
  locality?: string | null;
  lat: number;
  lon: number;
  sap_site_id?: string | null;
  sap_address_id?: string | null;
  source_name?: string;
  source_url?: string;
}

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
  origin?: string;
  recommended?: boolean;
  why?: string[];
  template: {
    id: string;
    name_zh: string;
    kind: string;
    dwellings: number;
    bedrooms: number;
    bathrooms: number;
    kitchens?: number;
    storeys: number;
    gfa_m2: number;
    gfa_missing?: boolean;
    quantity_source?: string;
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
    bathrooms?: number;
    kitchens?: number;
    retaining?: {
      height_m: number;
      length_m: number;
      sleeper_ok: boolean;
      note?: string;
    } | null;
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
  drawing_extract?: {
    documents?: Array<{
      kind?: string | null;
      filename?: string;
      page_count?: number;
      char_count?: number;
      error?: string | null;
    }>;
    fields?: Record<string, { value: unknown; evidence?: string; source_file?: string }>;
    windows?: Array<{
      code: string;
      w_mm: number;
      h_mm: number;
      count: number;
      evidence?: string;
      source_file?: string;
    }>;
    warnings?: string[];
  };
}

export interface AdviceItem {
  id: string;
  severity: "info" | "watch" | "constraint";
  title_zh: string;
  body_zh: string;
  source_name?: string | null;
  source_url?: string | null;
}

export interface ProjectRecord {
  id: string;
  address: string;
  created_at: string;
  status: string;
  result: {
    error?: { code: string; message: string };
    selected_id?: string;
    site?: {
      geo: {
        display_name: string;
        lat: number;
        lon: number;
        source_name?: string;
        source_url: string;
      };
      zone?: { zone_name: string; zone_code: number; source_url: string };
      overlays?: Array<{ key: string; present: boolean }>;
      parcel?: {
        found?: boolean;
        formatted_address?: string;
        area_m2?: number;
        frontage_m?: number;
        depth_m?: number;
        legal_description?: string;
        source_url?: string;
        note?: string;
      };
      terrain?: {
        slope_deg?: number;
        slope_percent?: number;
        height_range_m?: number;
        source_url?: string;
        note?: string;
      };
    };
    rules?: {
      permitted_dwellings: number;
      height_m: number;
      coverage: number;
      landscaped: number;
      qualifying_matters: string[];
      consent_note: string;
    };
    advice?: AdviceItem[];
    explanation?: string;
    drawing_explanation?: string;
    drawings?: Array<{
      kind?: string | null;
      filename?: string;
      page_count?: number;
      char_count?: number;
      error?: string | null;
    }>;
    drawing_trace?: Array<{ node: string; detail: string }>;
    pm_review?: { status: string; note: string };
    options?: SchemeOption[];
    trace?: Array<{ node: string; detail: string }>;
  };
}

export interface ConfigureSpec {
  kind: string;
  dwellings: number;
  storeys: number;
  bedrooms: number;
  bathrooms: number;
  kitchens: number;
  gfa_m2: number;
}
