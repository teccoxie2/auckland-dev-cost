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


def coverage_site_area(template: dict[str, Any], site: dict[str, Any] | None) -> tuple[float | None, str]:
    site = site or {}
    parcel = site.get("parcel") or {}
    cluster = site.get("subdivision") or {}
    parcel_area = float(parcel["area_m2"]) if parcel.get("found") and parcel.get("area_m2") else None
    combined = float(cluster["combined_area_m2"]) if cluster.get("found") and cluster.get("combined_area_m2") else None
    drawing_multi = template.get("quantity_source") == "drawing" and int(template.get("dwellings") or 1) > 1
    if drawing_multi and combined:
        return combined, "subdivision"
    if parcel_area:
        return parcel_area, "parcel"
    return None, "none"


def coverage_area_label(source: str, area: float, site: dict[str, Any] | None) -> str:
    cluster = (site or {}).get("subdivision") or {}
    if source == "subdivision":
        plan = cluster.get("title_plan") or "同一 DP"
        count = cluster.get("unit_count")
        count_bit = f"{count} 宗" if count else "各户"
        return f"拆分后合计地块 {area:.0f} m²（{plan} · {count_bit}）"
    return f"地块 {area:.0f} m²"


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
            return {
                "status": "infeasible",
                "needs_resource_consent": False,
                "reasons": [f"初版占地 {footprint:.0f} m² 已大于{area_label}，这块地放不下该户型。"],
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
                f"（{area:.0f} m² × {int((spec.get('coverage') or 0)*100)}%）。"
            )

    return {
        "status": status,
        "needs_resource_consent": status == "resource_consent",
        "reasons": reasons,
    }
