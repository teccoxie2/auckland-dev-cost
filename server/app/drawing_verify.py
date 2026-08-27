from __future__ import annotations

from typing import Any

from .costing import cost_option
from .drawing_flow import template_from_extract
from .drawing_parse import merge_extracts

ZONE_DEFS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("foundation", "筏板与基础", ("concrete_", "expol_", "drawing_area_unknown")),
    ("structure", "木结构", ("timber_sg8", "framing_labour")),
    ("interior", "室内衬板", ("gib_",)),
    ("envelope", "外墙保温与空腔", ("pink_batts", "cavity_")),
    ("roof", "屋面", ("roofing_",)),
    ("joinery", "门窗", ("window_", "door_", "joinery_")),
    ("kitchen", "厨房", ("kaboodle_", "sink_", "oven_", "tap_mondella", "plumber_prepipe_kitchen", "kitchen_")),
    (
        "bathroom",
        "卫生间",
        (
            "toilet_",
            "shower_",
            "tap_caroma",
            "membrane_",
            "plumber_prepipe_bathroom",
            "plumber_fitoff",
            "bathroom_",
        ),
    ),
    ("plumbing", "整栋给排水", ("plumber_prepipe_mains",)),
    ("scaffold", "外围脚手架", ("scaffolding_",)),
    ("retaining", "挡土与室外", ("retaining_", "pile_h5", "geotextile")),
)

NO_ZONING = {"status": "permitted", "needs_resource_consent": False, "reasons": []}


def zone_for_line(line: dict[str, Any]) -> tuple[str, str]:
    line_id = str(line.get("id") or "")
    for zone_id, label, prefixes in ZONE_DEFS:
        if any(line_id.startswith(prefix) or line_id == prefix.rstrip("_") for prefix in prefixes):
            return zone_id, label
    return "other", "未能分区"


def group_lines_by_zone(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for line in lines:
        zone_id, label = zone_for_line(line)
        if zone_id not in buckets:
            buckets[zone_id] = {
                "id": zone_id,
                "name_zh": label,
                "lines": [],
                "priced_incl_gst": 0.0,
                "missing_count": 0,
            }
            order.append(zone_id)
        bucket = buckets[zone_id]
        item = {**line, "zone": zone_id, "zone_name_zh": label}
        bucket["lines"].append(item)
        if item.get("status") == "missing":
            bucket["missing_count"] += 1
        elif item.get("status") in {"priced", "rule", "zero"}:
            bucket["priced_incl_gst"] = round(
                float(bucket["priced_incl_gst"]) + float(item.get("amount_incl_gst") or 0),
                2,
            )
    preferred = [zone_id for zone_id, _, _ in ZONE_DEFS if zone_id in buckets]
    rest = [zone_id for zone_id in order if zone_id not in preferred]
    return [buckets[zone_id] for zone_id in [*preferred, *rest]]


def field_values(fields: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, item in fields.items():
        if not isinstance(item, dict) or "value" not in item:
            continue
        rows.append(
            {
                "key": key,
                "value": item["value"],
                "evidence": item.get("evidence"),
                "source_file": item.get("source_file"),
            }
        )
    return rows


def verify_drawing_parts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    merged = merge_extracts(parts)
    if not merged["enough_to_cost"]:
        return {
            "error": {
                "code": "drawing_empty",
                "message": "图纸文字层里没有可核对的建筑面积或门窗表。扫描件无法量尺寸，请上传可选中文字的 RC/BC PDF。",
            },
            "extracted": merged,
        }
    template = template_from_extract(merged, {})
    cost = cost_option(template, NO_ZONING, site={}, include_overheads=False)
    zones = group_lines_by_zone(cost["lines"])
    n_win = sum(int(item["count"]) for item in merged.get("windows") or [])
    fields = merged.get("fields") or {}
    bits = ["本页只读 PDF 文字层，按施工区域列出材料与人工，不含议会法定费用。"]
    if fields.get("gfa_m2"):
        bits.append(f"建筑面积 {fields['gfa_m2']['value']} m²。")
    elif fields.get("footprint_m2"):
        bits.append(f"占地 {fields['footprint_m2']['value']} m²。")
    if n_win:
        bits.append(f"门窗表 {n_win} 樘。")
    bits.append("对不上公开 SKU 的科目标缺项，不编单价。")
    return {
        "error": None,
        "explanation": "".join(bits),
        "documents": merged.get("documents") or [],
        "fields": field_values(fields),
        "windows": merged.get("windows") or [],
        "warnings": merged.get("warnings") or [],
        "quantities": cost["quantities"],
        "zones": zones,
        "totals": cost["totals"],
        "template": {
            "name_zh": template.get("name_zh"),
            "gfa_m2": template.get("gfa_m2"),
            "gfa_missing": template.get("gfa_missing"),
            "storeys": template.get("storeys"),
            "kitchens": template.get("kitchens"),
            "bathrooms": template.get("bathrooms"),
            "dwellings": template.get("dwellings"),
        },
    }
