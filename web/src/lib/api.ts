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
    footprint_m2_drawn?: number;
  };
  verdict: {
    status: string;
    needs_resource_consent: boolean;
    reasons: string[];
  };
  building_rules?: {
    e2_score?: number;
    cavity_required?: boolean;
    stud_spacing_mm?: number;
    lintel_upgrade?: boolean;
    pending_detail_drawing?: boolean;
    notes?: string[];
    source_name?: string;
    source_url?: string;
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
    pricebook_version?: string;
    price_as_of?: string;
    fee_book_version?: string;
    fee_as_of?: string;
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
      subdivision?: {
        found?: boolean;
        title_plan?: string;
        unit_count?: number;
        combined_area_m2?: number;
        selected_unit?: string;
        selected_area_m2?: number;
        note?: string;
        source_url?: string;
        units?: Array<{
          formatted_address?: string;
          legal_description?: string;
          area_m2?: number;
        }>;
      };
      terrain?: {
        slope_deg?: number;
        slope_percent?: number;
        height_range_m?: number;
        source_url?: string;
        note?: string;
      };
      captured_at?: string;
      snapshot?: {
        captured_at?: string;
        region?: string;
        geo_source?: string;
        zone_source?: string;
        parcel_source?: string;
        terrain_source?: string;
        imagery_source?: string;
        buildings_source?: string;
      };
      imagery?: Array<{
        id: string;
        kind?: string;
        label_zh: string;
        note?: string;
        url: string;
        source_name?: string;
        source_url?: string;
        captured_label?: string;
      }>;
      buildings?: {
        found?: boolean;
        count?: number;
        roof_area_m2?: number;
        parcel_coverage?: number | null;
        buildings?: Array<{
          building_id?: string | number | null;
          use?: string | null;
          suburb?: string | null;
          area_m2?: number | null;
          imagery_date?: string | null;
          capture_source?: string | null;
        }>;
        note?: string;
        source_name?: string;
        source_url?: string;
      };
      vision?: {
        status?: string;
        scheme_hints?: string[];
        findings?: string[];
        model?: string | null;
        note?: string;
        observations?: string | null;
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
    scheme_filter?: {
      mode?: string;
      skipped?: number;
      note?: string;
    };
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
