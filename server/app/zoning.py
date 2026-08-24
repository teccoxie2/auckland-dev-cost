from __future__ import annotations

from typing import Any

from .data_loader import zone_rules


QUALIFYING_KEYS = {
    "significant_ecological_area",
    "historic_heritage",
    "special_character",
    "notable_trees",
    "coastal_inundation",
}


def apply_zone_rules(zone_code: int | None, overlays: list[dict[str, Any]]) -> dict[str, Any]:
    rules = zone_rules()
    table = rules["zones"]
    key = str(zone_code) if zone_code is not None else ""
    spec = table.get(key, rules["default_non_residential"]).copy()
    spec["zone_code"] = zone_code
    hits = [item["key"] for item in overlays if item.get("present") and item.get("key") in QUALIFYING_KEYS]
    spec["qualifying_matters"] = hits
    spec["residential"] = key in table
    if hits:
        spec["consent_note"] = "存在可能构成 qualifying matter 的叠加层，许可套数可能下降，需规划核对。"
    else:
        spec["consent_note"] = spec.get("notes") or ""
    return spec


def is_existing_unit_title(site: dict[str, Any] | None) -> bool:
    return bool(((site or {}).get("subdivision") or {}).get("found"))


def coverage_site_area(template: dict[str, Any], site: dict[str, Any] | None) -> tuple[float | None, str]:
    del template
    parcel = (site or {}).get("parcel") or {}
    if parcel.get("found") and parcel.get("area_m2"):
        return float(parcel["area_m2"]), "parcel"
    return None, "none"


def format_area_m2(area: float) -> str:
    rounded = round(float(area), 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.1f}"


def coverage_area_label(source: str, area: float, site: dict[str, Any] | None) -> str:
    del source
    if is_existing_unit_title(site):
        selected = ((site or {}).get("subdivision") or {}).get("selected_unit")
        unit_bit = f"本户 {selected} " if selected else "本户 "
        return f"{unit_bit}地块 {format_area_m2(area)} m²"
    return f"地块 {format_area_m2(area)} m²"


def filter_template(template: dict[str, Any], spec: dict[str, Any], site: dict[str, Any] | None = None) -> dict[str, Any]:
    dwellings = int(template["dwellings"])
    permitted = int(spec.get("permitted_dwellings") or 0)
    terrace_ok = bool(spec.get("terrace_ok"))
    storeys = int(template["storeys"])
    max_storeys = int(spec.get("storeys") or 0)
    reasons: list[str] = []
    status = "permitted"

    if not spec.get("residential"):
        return {
            "status": "infeasible",
            "needs_resource_consent": False,
            "reasons": ["当前区划不是住宅区，第一期不生成住宅开发方案。"],
        }
    if dwellings > permitted:
        status = "resource_consent"
        reasons.append(f"套数 {dwellings} 超过许可活动上限 {permitted}，需要 Resource Consent。")
    if template["kind"] == "terrace" and not terrace_ok:
        status = "infeasible"
        reasons.append("该区划不适合联排形态。")
    if storeys > max_storeys:
        status = "resource_consent"
        reasons.append(f"层数 {storeys} 可能超过区划常规层数 {max_storeys}。")
    if spec.get("qualifying_matters") and dwellings > 1:
        status = "resource_consent"
        reasons.append("叠加层（qualifying matter）可能限制加密，需按 Resource Consent 路径评估。")

    parcel = (site or {}).get("parcel") or {}
    area, area_source = coverage_site_area(template, site)
    if parcel.get("found") and area and not template.get("gfa_missing"):
        footprint = float(template.get("footprint_m2_drawn") or (float(template["gfa_m2"]) / max(storeys, 1)))
        coverage_cap = area * float(spec.get("coverage") or 0)
        area_label = coverage_area_label(area_source, area, site)
        if footprint > area:
            if is_existing_unit_title(site) and template.get("quantity_source") == "drawing":
                reason = (
                    f"图纸是开发完成前的整宗方案（占地 {footprint:.0f} m²），"
                    f"议会现址{area_label}。本页只按当前门牌地籍校核，不把兄弟地块合计进去。"
                )
            else:
                reason = f"初版占地 {footprint:.0f} m² 已大于{area_label}，这块地放不下该户型。"
            return {
                "status": "infeasible",
                "needs_resource_consent": False,
                "reasons": [reason],
            }
        min_fp = 40.0
        if dwellings * min_fp > coverage_cap and coverage_cap > 0:
            status = "infeasible"
            reasons.append(
                f"{area_label}按覆盖率大约只能拿出 {coverage_cap:.0f} m² 占地，"
                f"{dwellings} 套按初版每套至少 {min_fp:.0f} m² 占地会塞不下。"
            )
            return {
                "status": "infeasible",
                "needs_resource_consent": False,
                "reasons": reasons,
            }
        if footprint > coverage_cap * 1.05:
            status = "resource_consent"
            reasons.append(
                f"初版占地 {footprint:.0f} m² 超过覆盖率上限约 {coverage_cap:.0f} m²"
                f"（{format_area_m2(area)} m² × {int((spec.get('coverage') or 0)*100)}%）。"
            )

    return {
        "status": status,
        "needs_resource_consent": status == "resource_consent",
        "reasons": reasons,
    }
