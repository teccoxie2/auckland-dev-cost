from __future__ import annotations

from typing import Any

from .data_loader import full_contract_wbs
from .pricing import missing_line

GROUP_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("joinery_", "structure"),
    ("window_", "structure"),
    ("door_", "structure"),
    ("timber_", "structure"),
    ("cavity_", "structure"),
    ("gib_", "structure"),
    ("pink_batts", "structure"),
    ("roofing_", "structure"),
    ("concrete_", "structure"),
    ("expol_", "structure"),
    ("framing_", "structure"),
    ("scaffolding_", "structure"),
    ("drawing_area", "structure"),
    ("kaboodle_", "interior"),
    ("sink_", "interior"),
    ("oven_", "interior"),
    ("tap_", "interior"),
    ("toilet_", "interior"),
    ("shower_", "interior"),
    ("membrane_", "interior"),
    ("plumber_", "interior"),
    ("kitchen_", "interior"),
    ("bathroom_", "interior"),
    ("retaining_", "outdoor"),
    ("pile_", "outdoor"),
    ("geotextile_", "outdoor"),
    ("prelim", "prelim"),
    ("design_", "fees"),
    ("watercare_", "fees"),
    ("development_", "fees"),
    ("building_consent", "fees"),
    ("branz_", "fees"),
    ("mbie_", "fees"),
    ("bca_", "fees"),
    ("resource_consent", "fees"),
    ("ccc_", "fees"),
    ("street_damage", "fees"),
    ("official_lim", "fees"),
    ("flood_", "fees"),
    ("public_drain", "fees"),
    ("nes_cs", "fees"),
    ("geotech_", "fees"),
    ("contingency", "contingency"),
)


def tag_wbs_group(line: dict[str, Any]) -> dict[str, Any]:
    if line.get("wbs_group"):
        return line
    item_id = str(line.get("id") or "")
    for prefix, group in GROUP_BY_PREFIX:
        if item_id == prefix.rstrip("_") or item_id.startswith(prefix):
            return {**line, "wbs_group": group}
    category = str(line.get("category") or "")
    if category in {"statutory", "design"}:
        return {**line, "wbs_group": "fees"}
    if category == "preliminaries":
        return {**line, "wbs_group": "prelim"}
    if category == "contingency":
        return {**line, "wbs_group": "contingency"}
    return {**line, "wbs_group": "structure"}


def apply_full_contract_wbs(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged = [tag_wbs_group(item) for item in lines]
    existing = {str(item.get("id")) for item in tagged}
    catalog = full_contract_wbs()
    for group in catalog.get("groups") or []:
        group_id = str(group.get("id") or "structure")
        for item in group.get("items") or []:
            item_id = str(item.get("id") or "")
            if not item_id or item_id in existing:
                continue
            tagged.append(
                missing_line(
                    item_id,
                    str(item.get("name_zh") or item_id),
                    str(item.get("reason") or "无公开可核对单价，故不计金额。"),
                    wbs_group=group_id,
                )
            )
            existing.add(item_id)
    return tagged
