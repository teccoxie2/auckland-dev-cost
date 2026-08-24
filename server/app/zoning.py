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


def filter_template(template: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
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

    return {
        "status": status,
        "needs_resource_consent": status == "resource_consent",
        "reasons": reasons,
    }
