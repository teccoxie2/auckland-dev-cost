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
    ("thermakraft_", "structure"),
    ("concrete_", "structure"),
    ("expol_", "structure"),
    ("framing_", "structure"),
    ("scaffolding_", "prelim"),
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

LINE_WBS_ITEM: tuple[tuple[str, str], ...] = (
    ("timber_sg8_90x45_h12", "wbs_e01_ext_framing"),
    ("timber_sg8_140x45_h12", "wbs_e03_thick_studs"),
    ("cavity_batten_h31_45x20", "wbs_h06_cavity"),
    ("cavity_closers_flashings", "wbs_g07_window_seals"),
    ("gib_ceiling_10mm", "wbs_i04_ceiling_gib"),
    ("gib_std_10mm", "wbs_i01_gib_wall"),
    ("pink_batts_r22_wall", "wbs_h07_wall_insulation"),
    ("roofing_corrugate_colour_845", "wbs_f01_metal_roof"),
    ("thermakraft_215_underlay", "wbs_f02_underlay"),
    ("concrete_readymix_20mpa", "wbs_d07_waffle"),
    ("expol_tuffpod_1100x300", "wbs_d08_pods"),
    ("framing_labour_gfa", "wbs_e01_ext_framing"),
    ("scaffolding_perimeter_erect", "wbs_a07_scaffold"),
    ("scaffolding_perimeter_hire_week", "wbs_a07_scaffold"),
    ("window_", "wbs_g01_alu_windows"),
    ("door_hume_nexus15_860", "wbs_g03_entry_doors"),
    ("joinery_", "wbs_g02_sliding_doors"),
    ("kaboodle_", "wbs_k01_kitchen"),
    ("sink_", "wbs_k04_sinks"),
    ("oven_", "wbs_k05_appliances"),
    ("tap_mondella", "wbs_k04_sinks"),
    ("tap_caroma_luna_shower", "wbs_l03_shower_ware"),
    ("tap_caroma_luna_basin", "wbs_l02_vanity"),
    ("toilet_stein_ero", "wbs_l01_wc"),
    ("shower_stein_georgia_750", "wbs_l03_shower_ware"),
    ("membrane_crommelin_4l", "wbs_j09_floor_wp"),
    ("plumber_prepipe_kitchen", "wbs_k04_sinks"),
    ("plumber_prepipe_bathroom", "wbs_l01_wc"),
    ("retaining_sleeper_h4_200x50", "wbs_d12_timber_retaining"),
    ("pile_h5_125_2400", "wbs_d12_timber_retaining"),
    ("plumber_fitoff_toilet", "wbs_l01_wc"),
    ("plumber_fitoff_shower", "wbs_l03_shower_ware"),
    ("plumber_fitoff_basin", "wbs_l02_vanity"),
    ("kitchen_install_other_trades", "wbs_k10_joinery_install"),
    ("retaining_engineer_wall", "wbs_keystone_retaining"),
    ("retaining_posts_drainage_labour", "wbs_d14_blind_drain"),
    ("geotextile_strol_50m", "wbs_d14_blind_drain"),
    ("ccc_base_fee", "wbs_r09_asbuilt"),
    ("street_damage_inspection", "wbs_r08_council_attend"),
    ("building_consent_deposit", "wbs_r08_council_attend"),
    ("resource_consent_deposit", "wbs_pre_construction"),
    ("branz_levy", "wbs_r08_council_attend"),
    ("mbie_levy", "wbs_r08_council_attend"),
    ("bca_accreditation_levy", "wbs_r08_council_attend"),
)


def _matches(item_id: str, token: str) -> bool:
    if token.endswith("_"):
        return item_id == token.rstrip("_") or item_id.startswith(token)
    return item_id == token or item_id.startswith(token)


def catalog_by_id() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for group in full_contract_wbs().get("groups") or []:
        group_id = str(group.get("id") or "structure")
        group_when = group.get("include_when") or {}
        for item in group.get("items") or []:
            item_id = str(item.get("id") or "")
            if not item_id:
                continue
            index[item_id] = {**item, "wbs_group": group_id, "group_when": group_when}
    return index


def include_when_applies(when: dict[str, Any] | None, template: dict[str, Any] | None) -> bool:
    rules = when or {}
    storeys = int((template or {}).get("storeys") or 1)
    dwellings = int((template or {}).get("dwellings") or 1)
    storeys_gte = int(rules.get("storeys_gte") or 0)
    dwellings_gte = int(rules.get("dwellings_gte") or 0)
    if storeys_gte and storeys < storeys_gte:
        return False
    if dwellings_gte and dwellings < dwellings_gte:
        return False
    return True


def _infer_wbs_item(item_id: str) -> str | None:
    for token, wbs_item in LINE_WBS_ITEM:
        if _matches(item_id, token):
            return wbs_item
    return None


def tag_wbs_group(line: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    index = catalog if catalog is not None else catalog_by_id()
    item_id = str(line.get("id") or "")
    wbs_item = str(line.get("wbs_item") or "") or _infer_wbs_item(item_id)
    meta = index.get(wbs_item or "") or index.get(item_id)
    tagged = dict(line)
    if wbs_item:
        tagged["wbs_item"] = wbs_item
    elif meta:
        tagged["wbs_item"] = item_id
        wbs_item = item_id
    if meta:
        tagged["wbs_item_zh"] = str(meta.get("name_zh") or tagged.get("wbs_item_zh") or "")
        tagged["wbs_group"] = tagged.get("wbs_group") or str(meta.get("wbs_group") or "structure")
        return tagged
    if tagged.get("wbs_group"):
        return tagged
    for prefix, group in GROUP_BY_PREFIX:
        if item_id == prefix.rstrip("_") or item_id.startswith(prefix):
            tagged["wbs_group"] = group
            return tagged
    category = str(line.get("category") or "")
    if category in {"statutory", "design"}:
        tagged["wbs_group"] = "fees"
        return tagged
    if category == "preliminaries":
        tagged["wbs_group"] = "prelim"
        return tagged
    if category == "contingency":
        tagged["wbs_group"] = "contingency"
        return tagged
    tagged["wbs_group"] = "structure"
    return tagged


def _is_covered(item: dict[str, Any], existing_ids: set[str]) -> bool:
    for token in item.get("covered_by") or []:
        token_s = str(token)
        if any(_matches(existing_id, token_s) for existing_id in existing_ids):
            return True
    return False


def apply_full_contract_wbs(
    lines: list[dict[str, Any]],
    template: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    index = catalog_by_id()
    tagged = [tag_wbs_group(item, index) for item in lines]
    existing_ids = {str(item.get("id")) for item in tagged}
    existing_items = {str(item.get("wbs_item") or "") for item in tagged if item.get("wbs_item")}
    catalog = full_contract_wbs()
    for group in catalog.get("groups") or []:
        group_id = str(group.get("id") or "structure")
        if not include_when_applies(group.get("include_when"), template):
            continue
        for item in group.get("items") or []:
            item_id = str(item.get("id") or "")
            if not item_id or item_id in existing_ids:
                continue
            when = item.get("include_when") or group.get("include_when")
            if not include_when_applies(when, template):
                continue
            if _is_covered(item, existing_ids) or item_id in existing_items:
                continue
            tagged.append(
                missing_line(
                    item_id,
                    str(item.get("name_zh") or item_id),
                    str(item.get("reason") or "无公开可核对单价，故不计金额。"),
                    wbs_group=group_id,
                    wbs_item=item_id,
                    wbs_item_zh=str(item.get("name_zh") or item_id),
                )
            )
            existing_ids.add(item_id)
            existing_items.add(item_id)
    return tagged
