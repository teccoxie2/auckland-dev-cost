from __future__ import annotations

from typing import Any

from .costing import cost_option
from .data_loader import design_rules, typologies
from .quantity import takeoff
from .zoning import filter_template, is_existing_unit_title


KIND_LABELS = {
    "standalone": "独栋",
    "duplex": "双拼",
    "terrace": "联排",
    "minor_dwelling": "主屋+独立住宅",
}


def default_gfa_m2(bedrooms: int, storeys: int, dwellings: int) -> float:
    table = design_rules()["gfa_m2"]
    storey_key = str(min(max(storeys, 1), 3))
    bed_key = str(min(max(bedrooms, 2), 5))
    per_unit = table.get(storey_key, table["2"]).get(bed_key, 165)
    return round(per_unit * max(dwellings, 1), 0)


def default_bathrooms(bedrooms: int) -> int:
    table = design_rules()["bathrooms_by_bedrooms"]
    return int(table.get(str(min(max(bedrooms, 1), 5)), 2))


def default_kitchens(dwellings: int) -> int:
    return int(design_rules()["kitchens_per_dwelling"]) * max(dwellings, 1)


def parse_spec(raw: dict[str, Any]) -> dict[str, Any]:
    kind = str(raw.get("kind") or "standalone")
    if kind not in KIND_LABELS:
        kind = "standalone"
    dwellings = _clip(raw.get("dwellings"), 1, 6)
    storeys = _clip(raw.get("storeys"), 1, 5)
    bedrooms = _clip(raw.get("bedrooms"), 1, 6)
    bathrooms = _clip(raw.get("bathrooms"), 1, 6)
    kitchens = _clip(raw.get("kitchens"), 1, 4)
    gfa = raw.get("gfa_m2")
    try:
        gfa_value = float(gfa) if gfa not in (None, "") else default_gfa_m2(bedrooms, storeys, dwellings)
    except (TypeError, ValueError):
        gfa_value = default_gfa_m2(bedrooms, storeys, dwellings)
    gfa_value = min(max(gfa_value, 60), 450)
    return {
        "kind": kind,
        "dwellings": dwellings,
        "storeys": storeys,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "kitchens": kitchens,
        "gfa_m2": gfa_value,
    }


def build_template(spec: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_spec(spec)
    base = _nearest_typology(parsed)
    name = (
        f"选装 · {KIND_LABELS[parsed['kind']]} · {parsed['dwellings']}套 · "
        f"{parsed['bedrooms']}房{parsed['bathrooms']}卫 · {parsed['kitchens']}厨 · {int(parsed['gfa_m2'])}m²"
    )
    gfa_ratio = parsed["gfa_m2"] / max(float(base["gfa_m2"]), 1)
    windows = []
    for item in base.get("windows") or []:
        count = max(1, round(int(item["count"]) * max(gfa_ratio, 0.6)))
        windows.append({**item, "count": count})
    return {
        **base,
        "id": "custom",
        "name_zh": name,
        "name_en": name,
        "kind": parsed["kind"],
        "dwellings": parsed["dwellings"],
        "bedrooms": parsed["bedrooms"],
        "bathrooms": parsed["bathrooms"],
        "kitchens": parsed["kitchens"],
        "storeys": parsed["storeys"],
        "gfa_m2": parsed["gfa_m2"],
        "gfa_per_unit_m2": round(parsed["gfa_m2"] / parsed["dwellings"], 1),
        "windows": windows,
    }


def wrap_typology(template: dict[str, Any]) -> dict[str, Any]:
    drawing = template.get("quantity_source") == "drawing"
    if drawing:
        kitchens = int(template["kitchens"]) if template.get("kitchens") is not None else 0
        bathrooms = int(template["bathrooms"]) if template.get("bathrooms") is not None else 0
    else:
        kitchens = int(template.get("kitchens") or default_kitchens(int(template["dwellings"])))
        bathrooms = int(template["bathrooms"])
    return {
        "id": template["id"],
        "name_zh": template["name_zh"],
        "kind": template["kind"],
        "dwellings": template["dwellings"],
        "bedrooms": template["bedrooms"],
        "bathrooms": bathrooms,
        "kitchens": kitchens,
        "storeys": template["storeys"],
        "gfa_m2": template["gfa_m2"],
        "gfa_missing": bool(template.get("gfa_missing")),
        "quantity_source": template.get("quantity_source") or "template",
        "footprint_m2_drawn": template.get("footprint_m2_drawn"),
    }


def costed_option(
    template: dict[str, Any],
    rules: dict[str, Any],
    site: dict[str, Any],
    *,
    why: list[str],
    recommended: bool = False,
    origin: str = "typology",
) -> dict[str, Any]:
    full_template = template if "windows" in template else _hydrate(template)
    if "kitchens" not in full_template:
        full_template = {**full_template, "kitchens": default_kitchens(int(full_template["dwellings"]))}
    verdict = filter_template(full_template, rules, site)
    option: dict[str, Any] = {
        "id": full_template["id"],
        "template": wrap_typology(full_template),
        "verdict": verdict,
        "why": why,
        "recommended": recommended and verdict["status"] != "infeasible",
        "origin": origin,
    }
    if verdict["status"] != "infeasible":
        option["quantities"] = takeoff(full_template, site)
        option["cost"] = cost_option(full_template, verdict, existing_dwellings=1, site=site)
    return option


CURRENT_TITLE_FILTER = "current_council_title"
CURRENT_TITLE_FILTER_COPY = 1


def fits_current_council_title(template: dict[str, Any], site: dict[str, Any] | None) -> bool:
    if not is_existing_unit_title(site):
        return True
    return int(template.get("dwellings") or 1) == 1 and str(template.get("kind") or "") == "standalone"


def scheme_filter_meta(site: dict[str, Any] | None, skipped: int) -> dict[str, Any] | None:
    if not is_existing_unit_title(site):
        return None
    if skipped:
        note = (
            "开发完成后只显示当前这条议会记录。"
            f"已筛掉 {skipped} 个需要整宗地或放不进本户的方案，不把拆分后的兄弟地块合计成一块地。"
        )
    else:
        note = "开发完成后只显示当前这条议会记录，不把拆分后的兄弟地块合计成一块地。"
    return {
        "mode": CURRENT_TITLE_FILTER,
        "copy": CURRENT_TITLE_FILTER_COPY,
        "skipped": skipped,
        "note": note,
    }


def recommend_schemes(rules: dict[str, Any], site: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    options = []
    skipped = 0
    for template in typologies()["templates"]:
        if not fits_current_council_title(template, site):
            skipped += 1
            continue
        why = _why(template, rules, site)
        options.append(costed_option(template, rules, site, why=why, origin="typology"))
    fitted = _site_fit_option(rules, site, options)
    if fitted:
        options.insert(0, fitted)
    if is_existing_unit_title(site):
        kept: list[dict[str, Any]] = []
        for item in options:
            if item["verdict"]["status"] == "infeasible":
                skipped += 1
                continue
            kept.append(item)
        options = kept
    feasible = [item for item in options if item["verdict"]["status"] != "infeasible"]
    ranked = sorted(
        feasible,
        key=lambda item: (
            0 if item.get("origin") == "site_fit" else 1,
            0 if item["verdict"]["status"] == "permitted" else 1,
            _slope_penalty(item, site),
            -int(item["template"]["dwellings"] <= int(rules.get("permitted_dwellings") or 1)),
        ),
    )
    for item in ranked[:3]:
        item["recommended"] = True
        if "初版优先推荐" not in item["why"]:
            item["why"] = ["初版优先推荐：更贴合这块地的区划、面积与坡度。", *item["why"]]
    blocked = [item for item in options if item["verdict"]["status"] == "infeasible"]
    return ranked + blocked, skipped


def _site_fit_option(rules: dict[str, Any], site: dict[str, Any], existing: list[dict[str, Any]]) -> dict[str, Any] | None:
    parcel = site.get("parcel") or {}
    if not parcel.get("found"):
        return None
    permitted_ok = [
        item
        for item in existing
        if item["verdict"]["status"] == "permitted" and item["template"]["kind"] == "standalone"
    ]
    if permitted_ok:
        return None
    area = float(parcel["area_m2"])
    coverage_cap = area * float(rules.get("coverage") or 0)
    if coverage_cap < 40:
        return None
    storeys = 2
    gfa = min(round(coverage_cap * storeys, 0), round(area * 0.9, 0), 160)
    gfa = max(gfa, 80)
    spec = {
        "kind": "standalone",
        "dwellings": 1,
        "storeys": storeys,
        "bedrooms": 3,
        "bathrooms": 2,
        "kitchens": 1,
        "gfa_m2": gfa,
    }
    template = build_template(spec)
    template["id"] = "site_fit_compact"
    template["name_zh"] = f"地块适配 · 二层小独栋 · {int(gfa)}m²"
    return costed_option(
        template,
        rules,
        site,
        why=[
            f"固定模板在这块 {area:.0f} m² 地上占地过大。初版按覆盖率把建筑面积收到约 {int(gfa)} m²、{storeys} 层。",
            "你仍可在选装里改卧室、卫生间和厨房。",
        ],
        recommended=True,
        origin="site_fit",
    )


def _hydrate(template: dict[str, Any]) -> dict[str, Any]:
    for item in typologies()["templates"]:
        if item["id"] == template.get("id"):
            return {**item, **template}
    return build_template(template)


def _nearest_typology(spec: dict[str, Any]) -> dict[str, Any]:
    templates = typologies()["templates"]
    same_kind = [item for item in templates if item["kind"] == spec["kind"]] or templates
    return min(
        same_kind,
        key=lambda item: abs(int(item["bedrooms"]) - spec["bedrooms"])
        + abs(int(item["storeys"]) - spec["storeys"])
        + abs(int(item["dwellings"]) - spec["dwellings"]),
    )


def _why(template: dict[str, Any], rules: dict[str, Any], site: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    parcel = site.get("parcel") or {}
    terrain = site.get("terrain") or {}
    permitted = int(rules.get("permitted_dwellings") or 0)
    if template["dwellings"] <= permitted:
        reasons.append(f"套数 {template['dwellings']} 未超过本区划许可上限 {permitted}。")
    else:
        reasons.append(f"套数超过许可上限 {permitted}，按 Resource Consent 路径列出。")
    if parcel.get("found"):
        footprint = float(template["gfa_m2"]) / max(int(template["storeys"]), 1)
        cap = float(parcel["area_m2"]) * float(rules.get("coverage") or 0)
        reasons.append(
            f"占地约 {footprint:.0f} m²，地块覆盖率上限约 {cap:.0f} m²（{parcel['area_m2']} m² × {int((rules.get('coverage') or 0)*100)}%）。"
        )
    slope_deg = float((terrain or {}).get("slope_deg") or 0)
    if slope_deg >= 5 and int(template["storeys"]) >= 2:
        reasons.append("坡地优先二层，缩小筏板切填。")
    if slope_deg >= 5 and int(template["storeys"]) == 1 and float(template["gfa_m2"]) >= 150:
        reasons.append("单层大占地在坡地上切填更多，初版不优先。")
    if template["kind"] == "terrace" and rules.get("terrace_ok"):
        reasons.append("本区划允许联排形态。")
    return reasons


def _slope_penalty(option: dict[str, Any], site: dict[str, Any]) -> int:
    slope_deg = float(((site.get("terrain") or {}).get("slope_deg")) or 0)
    storeys = int(option["template"]["storeys"])
    gfa = float(option["template"]["gfa_m2"])
    if slope_deg >= 5 and storeys == 1 and gfa >= 150:
        return 2
    if slope_deg >= 5 and storeys >= 2:
        return 0
    return 1


def _clip(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = low
    return min(max(number, low), high)
