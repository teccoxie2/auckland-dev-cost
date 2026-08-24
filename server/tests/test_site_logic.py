from app.design import default_gfa_m2, parse_spec
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


def test_drawing_uses_subdivision_combined_area():
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
            },
        },
    )
    assert clustered["status"] != "infeasible"
    assert "放不下" not in "".join(clustered["reasons"])


def test_refresh_stored_drawing_verdict_after_cluster():
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
                    "status": "infeasible",
                    "needs_resource_consent": False,
                    "reasons": ["初版占地 313 m² 已大于地块 110 m²，这块地放不下该户型。"],
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
            },
        },
    )
    assert result["options"][0]["verdict"]["status"] != "infeasible"


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
