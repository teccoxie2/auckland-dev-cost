from app.design import default_gfa_m2, parse_spec, recommend_schemes
from app.gis import filter_parcels_for_address
from app.graph import _refresh_drawing_verdicts
from app.quantity import retaining_takeoff
from app.zoning import filter_template


def test_parse_spec_defaults_gfa():
    spec = parse_spec({"kind": "standalone", "dwellings": 1, "storeys": 2, "bedrooms": 3, "bathrooms": 2, "kitchens": 1})
    assert spec["gfa_m2"] == 165


def test_default_gfa_matches_templates():
    assert default_gfa_m2(3, 1, 1) == 110
    assert default_gfa_m2(4, 2, 1) == 220


def test_small_parcel_rejects_terrace():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
    }
    site = {"parcel": {"found": True, "area_m2": 110}}
    template = {
        "kind": "terrace",
        "dwellings": 3,
        "storeys": 2,
        "gfa_m2": 330,
    }
    verdict = filter_template(template, rules, site)
    assert verdict["status"] == "infeasible"


def test_typology_ignores_subdivision_combined_area():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
    }
    site = {
        "parcel": {"found": True, "area_m2": 110},
        "subdivision": {"found": True, "combined_area_m2": 734.9, "title_plan": "DP 580591", "unit_count": 6},
    }
    template = {
        "kind": "terrace",
        "dwellings": 3,
        "storeys": 2,
        "gfa_m2": 330,
    }
    verdict = filter_template(template, rules, site)
    assert verdict["status"] == "infeasible"


def test_drawing_stays_on_current_council_parcel():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
    }
    template = {
        "kind": "terrace",
        "dwellings": 6,
        "storeys": 3,
        "gfa_m2": 939,
        "footprint_m2_drawn": 313,
        "quantity_source": "drawing",
    }
    too_small = filter_template(template, rules, {"parcel": {"found": True, "area_m2": 109.5}})
    assert too_small["status"] == "infeasible"
    clustered = filter_template(
        template,
        rules,
        {
            "parcel": {"found": True, "area_m2": 109.5},
            "subdivision": {
                "found": True,
                "combined_area_m2": 734.9,
                "title_plan": "DP 580591",
                "unit_count": 6,
                "selected_unit": "115B",
            },
        },
    )
    assert clustered["status"] == "infeasible"
    assert "现址" in "".join(clustered["reasons"])


def test_refresh_stored_drawing_verdict_uses_current_parcel():
    result = {
        "rules": {
            "residential": True,
            "permitted_dwellings": 3,
            "terrace_ok": True,
            "storeys": 3,
            "coverage": 0.5,
            "qualifying_matters": [],
        },
        "options": [
            {
                "id": "drawings",
                "origin": "drawings",
                "template": {
                    "kind": "terrace",
                    "dwellings": 6,
                    "storeys": 3,
                    "gfa_m2": 939,
                    "quantity_source": "drawing",
                    "footprint_m2_drawn": 313,
                },
                "verdict": {
                    "status": "resource_consent",
                    "needs_resource_consent": True,
                    "reasons": ["套数 6 超过许可活动上限 3，需要 Resource Consent。"],
                },
            }
        ],
    }
    _refresh_drawing_verdicts(
        result,
        {
            "parcel": {"found": True, "area_m2": 109.5},
            "subdivision": {
                "found": True,
                "combined_area_m2": 734.9,
                "title_plan": "DP 580591",
                "unit_count": 6,
                "selected_unit": "115B",
            },
        },
    )
    assert result["options"][0]["verdict"]["status"] == "infeasible"


def test_retaining_none_on_flat_site():
    qty = retaining_takeoff({"gfa_m2": 110}, {"terrain": {"height_range_m": 0.2, "slope_deg": 1}}, 12)
    assert qty is None


def test_retaining_none_when_dem_noise_on_gentle_slope():
    qty = retaining_takeoff({"gfa_m2": 110}, {"terrain": {"height_range_m": 0.96, "slope_deg": 1.0, "run_m": 40}}, 12)
    assert qty is None


def test_retaining_sleeper_on_moderate_rise():
    qty = retaining_takeoff(
        {"gfa_m2": 110},
        {"terrain": {"height_range_m": 2.4, "slope_deg": 8, "run_m": 20}, "parcel": {"frontage_m": 14}},
        12,
    )
    assert qty is not None
    assert qty["sleeper_ok"] is True
    assert qty["surcharge_likely"] is True
    assert qty["timber_lm"] > 0


def test_existing_unit_title_filters_multi_unit_schemes():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
        "height_m": 11,
    }
    site = {
        "parcel": {"found": True, "area_m2": 109.5, "frontage_m": 8},
        "subdivision": {
            "found": True,
            "combined_area_m2": 734.9,
            "title_plan": "DP 580591",
            "unit_count": 6,
            "selected_unit": "115B",
        },
        "terrain": {"slope_deg": 1.0, "height_range_m": 0.4},
    }
    options, skipped = recommend_schemes(rules, site)
    kinds = {item["template"]["kind"] for item in options}
    assert "terrace" not in kinds
    assert "duplex" not in kinds
    assert skipped >= 2
    assert all(item["template"]["dwellings"] == 1 for item in options)
    assert all(item["verdict"]["status"] != "infeasible" for item in options)


def test_vacant_lot_still_lists_terrace_templates():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
        "height_m": 11,
    }
    site = {"parcel": {"found": True, "area_m2": 800, "frontage_m": 20}, "terrain": {"slope_deg": 1.0, "height_range_m": 0.4}}
    options, skipped = recommend_schemes(rules, site)
    assert skipped == 0
    assert any(item["template"]["kind"] == "terrace" for item in options)


def test_parcel_filter_keeps_selected_unit_only():
    candidates = [
        {"formatted_address": "115A Bruce Road Glenfield", "area_m2": 159.3},
        {"formatted_address": "115B Bruce Road Glenfield", "area_m2": 109.5},
        {"formatted_address": "115C Bruce Road Glenfield", "area_m2": 109.4},
    ]
    kept = filter_parcels_for_address(candidates, "115B Bruce Road Glenfield")
    assert len(kept) == 1
    assert kept[0]["formatted_address"].startswith("115B")
