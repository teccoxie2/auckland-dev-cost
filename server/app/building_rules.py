from __future__ import annotations

from typing import Any

STUD_SPACING_DEFAULT_MM = 600
STUD_SPACING_TIGHT_MM = 400
LINTEL_WIDE_OPENING_MM = 3000


def building_rules_for(template: dict[str, Any], quantities: dict[str, Any] | None) -> dict[str, Any]:
    qty = quantities or {}
    pending = (template.get("quantity_source") or "template") != "drawing"
    stud = int(template.get("stud_spacing_mm") or STUD_SPACING_DEFAULT_MM)
    e2 = qty.get("e2") or {}
    notes: list[str] = []
    if qty.get("cavity_required"):
        notes.append("E2/AS1 风险分或二层及以上，计入空腔垫条。")
    if qty.get("wide_slider"):
        notes.append(f"门窗表最大宽≥{LINTEL_WIDE_OPENING_MM}mm，过梁木料升级为 140×45。")
    if pending:
        notes.append(
            f"第一期按户型模板几何套 E2/NZS3604（立柱默认 {STUD_SPACING_DEFAULT_MM}mm）。"
            f"砌块贴面或高风区加密到 {STUD_SPACING_TIGHT_MM}mm、过梁跨度升级需要详图毫米输入。"
        )
    elif stud == STUD_SPACING_TIGHT_MM:
        notes.append("图纸文字层立柱间距 400mm，已按该间距出木材工程量。")
    return {
        "e2_score": e2.get("score"),
        "cavity_required": bool(qty.get("cavity_required")),
        "stud_spacing_mm": stud,
        "lintel_upgrade": bool(qty.get("wide_slider")),
        "pending_detail_drawing": pending,
        "notes": notes,
        "source_name": e2.get("source_name"),
        "source_url": e2.get("source_url"),
    }


def annotate_option(option: dict[str, Any]) -> dict[str, Any]:
    item = dict(option)
    full = item.get("_full_template") or {}
    quantities = item.get("quantities")
    if not quantities:
        return item
    item["building_rules"] = building_rules_for(full, quantities)
    return item
