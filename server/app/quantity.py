from __future__ import annotations

import math
from typing import Any


WASTAGE = {
    "timber": 0.10,
    "gib": 0.15,
    "insulation": 0.08,
    "roofing": 0.10,
    "batten": 0.08,
    "concrete": 0.05,
}

ROOF_COVER_M = 0.762
POD_GRID_M = 1.2
KITCHEN_BASE_600 = 5
KITCHEN_WALL_600 = 5
KITCHEN_DOOR_600 = 10
KITCHEN_BENCH_2400 = 2
RETAINING_POST_SPACING_M = 1.2
GEOTEXTILE_ROLL_M2 = 50.0


def takeoff(template: dict[str, Any], site: dict[str, Any] | None = None) -> dict[str, Any]:
    gfa = float(template["gfa_m2"])
    storeys = int(template["storeys"])
    footprint = gfa / storeys
    length, width = _rectangle(footprint, float(template.get("aspect") or 1.4))
    perimeter = 2 * (length + width)
    wall_height = float(template["wall_height_m"])
    external_wall_m2 = perimeter * wall_height * storeys
    openings = _opening_area(template.get("windows") or [])
    lining_m2 = max(external_wall_m2 * 1.65 - openings, external_wall_m2 * 0.8)
    bathrooms = int(template.get("bathrooms") or 1)
    kitchens = int(template.get("kitchens") or template.get("dwellings") or 1)
    extra_wet = max(bathrooms - 1, 0) * 16 + max(kitchens - 1, 0) * 10
    lining_m2 += extra_wet
    pitch = math.radians(float(template.get("roof_pitch_deg") or 25))
    roof_m2 = footprint / max(math.cos(pitch), 0.5)
    spacing = float(template.get("stud_spacing_mm") or 600) / 1000.0
    studs = (perimeter / spacing) * storeys + 8
    timber_90_lm = studs * wall_height + 3 * perimeter * storeys
    e2 = e2_score(template)
    cavity = e2["score"] >= 7 or storeys >= 2
    batten_lm = (external_wall_m2 / 0.6) if cavity else 0.0
    roof_sheet_lm = roof_m2 / ROOF_COVER_M
    slab_m2 = footprint
    slab_m3 = slab_m2 * 0.085
    wide_slider = any(item["w_mm"] >= 3000 and item["h_mm"] >= 2000 for item in template.get("windows") or [])
    if wide_slider:
        timber_140_lm = 8.0
    else:
        timber_140_lm = 2.4
    retaining = retaining_takeoff(template, site or {}, length)
    pod_nx = max(int(length // POD_GRID_M), 0)
    pod_ny = max(int(width // POD_GRID_M), 0)
    pod_count = pod_nx * pod_ny

    return {
        "gfa_m2": round(gfa, 2),
        "footprint_m2": round(footprint, 2),
        "length_m": round(length, 2),
        "width_m": round(width, 2),
        "perimeter_m": round(perimeter, 2),
        "external_wall_m2": round(external_wall_m2, 2),
        "opening_m2": round(openings, 2),
        "lining_m2": round(lining_m2, 2),
        "roof_m2": round(roof_m2, 2),
        "timber_90_lm": round(timber_90_lm * (1 + WASTAGE["timber"]), 2),
        "timber_140_lm": round(timber_140_lm * (1 + WASTAGE["timber"]), 2),
        "batten_lm": round(batten_lm * (1 + WASTAGE["batten"]), 2) if cavity else 0.0,
        "insulation_m2": round(external_wall_m2 * (1 + WASTAGE["insulation"]), 2),
        "gib_m2": round(lining_m2 * (1 + WASTAGE["gib"]), 2),
        "roof_sheet_lm": round(roof_sheet_lm * (1 + WASTAGE["roofing"]), 2),
        "slab_m2": round(slab_m2, 2),
        "slab_m3": round(slab_m3 * (1 + WASTAGE["concrete"]), 2),
        "cavity_required": cavity,
        "e2": e2,
        "wide_slider": wide_slider,
        "window_schedule": template.get("windows") or [],
        "wastage": WASTAGE,
        "bathrooms": bathrooms,
        "kitchens": kitchens,
        "kitchen_base_600": KITCHEN_BASE_600 * kitchens,
        "kitchen_wall_600": KITCHEN_WALL_600 * kitchens,
        "kitchen_door_600": KITCHEN_DOOR_600 * kitchens,
        "kitchen_bench_2400": KITCHEN_BENCH_2400 * kitchens,
        "pod_count": pod_count,
        "pod_grid_m": POD_GRID_M,
        "retaining": retaining,
    }


def e2_score(template: dict[str, Any]) -> dict[str, Any]:
    storeys = int(template["storeys"])
    eaves = int(template.get("eaves_mm") or 0)
    kind = template.get("kind")
    wind = 1
    storey_score = 0 if storeys == 1 else 1 if storeys == 2 else 2
    eaves_score = 0 if eaves >= 600 else 2 if eaves >= 300 else 5
    envelope = 2 if kind == "terrace" else 1
    roof_wall = 1
    deck = 0
    score = wind + storey_score + eaves_score + envelope + roof_wall + deck
    return {
        "score": score,
        "factors": {
            "wind_zone_assumed_medium": wind,
            "storeys": storey_score,
            "eaves": eaves_score,
            "envelope": envelope,
            "roof_wall": roof_wall,
            "deck": deck,
        },
        "source_name": "E2/AS1 weathertightness risk matrix（BRANZ 说明）",
        "source_url": "https://www.branz.co.nz/design-build/articles/using-the-e2as1-risk-matrix",
        "note": "风区未做 NIWA 查询，MVP 按中等风区计 1 分。得分≥7 则计入空腔系统。",
    }


def _rectangle(area: float, aspect: float) -> tuple[float, float]:
    length = math.sqrt(area * aspect)
    width = area / length
    return length, width


def _opening_area(windows: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in windows:
        total += (item["w_mm"] / 1000.0) * (item["h_mm"] / 1000.0) * int(item["count"])
    return total


def retaining_takeoff(template: dict[str, Any], site: dict[str, Any], building_length_m: float) -> dict[str, Any] | None:
    terrain = site.get("terrain") or {}
    parcel = site.get("parcel") or {}
    rise = float(terrain.get("height_range_m") or 0)
    slope_deg = float(terrain.get("slope_deg") or 0)
    if rise < 2.0 and slope_deg < 5:
        return None
    height = min(max(rise * 0.5, 0.5), 3.0)
    length = float(parcel.get("frontage_m") or terrain.get("run_m") or building_length_m)
    length = max(min(length, 40.0), 6.0)
    courses = max(math.ceil(height / 0.20), 1)
    timber_lm = courses * length * (1 + WASTAGE["timber"])
    posts = max(math.ceil(length / RETAINING_POST_SPACING_M), 1)
    face_m2 = height * length
    geotextile_rolls = max(math.ceil(face_m2 / GEOTEXTILE_ROLL_M2), 1)
    return {
        "needed": True,
        "height_m": round(height, 2),
        "length_m": round(length, 1),
        "courses": courses,
        "timber_lm": round(timber_lm, 2),
        "posts": posts,
        "geotextile_rolls": geotextile_rolls,
        "surcharge_likely": True,
        "sleeper_ok": height <= 1.2,
        "formula": "墙高≈DEM高差×0.5（平台取中位）；延米=层数×临街面宽；层数=墙高/0.20m 枕木；立柱按 1.2m 间距",
        "note": "支撑建筑平台视为 surcharge。墙高>1.2m 不定零售枕木价。",
    }
