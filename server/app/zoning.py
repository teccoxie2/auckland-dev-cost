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
    if parcel.get("found") and not template.get("gfa_missing"):
        area = float(parcel["area_m2"])
        footprint = float(template.get("footprint_m2_drawn") or (float(template["gfa_m2"]) / max(storeys, 1)))
        coverage_cap = area * float(spec.get("coverage") or 0)
        if footprint > area:
            return {
                "status": "infeasible",
                "needs_resource_consent": False,
                "reasons": [f"初版占地 {footprint:.0f} m² 已大于地块 {area:.0f} m²，这块地放不下该户型。"],
            }
        min_fp = 40.0
        if dwellings * min_fp > coverage_cap and coverage_cap > 0:
            status = "infeasible"
            reasons.append(
                f"地块按覆盖率大约只能拿出 {coverage_cap:.0f} m² 占地，{dwellings} 套按初版每套至少 {min_fp:.0f} m² 占地会塞不下。"
            )
            return {
                "status": "infeasible",
                "needs_resource_consent": False,
                "reasons": reasons,
            }
        if footprint > coverage_cap * 1.05:
            status = "resource_consent"
            reasons.append(
                f"初版占地 {footprint:.0f} m² 超过覆盖率上限约 {coverage_cap:.0f} m²（{area:.0f} m² × {int((spec.get('coverage') or 0)*100)}%）。"
            )

    return {
        "status": status,
        "needs_resource_consent": status == "resource_consent",
        "reasons": reasons,
    }
