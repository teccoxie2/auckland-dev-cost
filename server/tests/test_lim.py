import pytest

from app.costing import ensure_lim_cost_on_options, lim_statutory_lines
from app.design import _vision_penalty, generate_typology_options
from app.graph import hydrate_lim, lim_node
from app.lim import LAYERS, NOT_QUERIED, lim_advice, lim_sections_from_report, lookup_lim, unavailable_lim
from app.pricing import lim_report_fee


def test_lim_report_fee_is_official_standard():
    fee = lim_report_fee()
    assert fee["amount"] == 387
    assert fee["urgent_fee"] == 522
    assert fee["source_url"].endswith("order-lim.html")
    assert fee["retrieved_at"] == "2026-08-25"


def test_every_scheme_includes_standard_lim_fee():
    lines = {item["id"]: item for item in lim_statutory_lines(None)}
    assert lines["lim_report_fee"]["status"] == "priced"
    assert lines["lim_report_fee"]["amount_incl_gst"] == 387
    assert "flood_hazard_assessment" not in lines
    assert "nes_cs_psi" not in lines
    assert lines["official_lim_drainage_notices"]["status"] == "missing"
    assert lines["official_lim_drainage_notices"]["amount_incl_gst"] == 0


def test_flood_hit_adds_missing_assessment_not_a_made_up_price():
    site = {
        "lim": {
            "constraints": {
                "flood": True,
                "coastal_inundation": False,
                "landfill": False,
                "landslide": "Low",
            }
        }
    }
    lines = {item["id"]: item for item in lim_statutory_lines(site)}
    assert lines["lim_report_fee"]["amount_incl_gst"] == 387
    assert lines["flood_hazard_assessment"]["status"] == "missing"
    assert lines["flood_hazard_assessment"]["amount_incl_gst"] == 0
    assert "geotech_landslide" not in lines
    assert "nes_cs_psi" not in lines


def test_landfill_and_high_landslide_are_missing_specialist_work():
    site = {
        "lim": {
            "constraints": {
                "flood": False,
                "coastal_inundation": False,
                "landfill": True,
                "landslide": "High",
            }
        }
    }
    ids = {item["id"]: item for item in lim_statutory_lines(site)}
    assert ids["nes_cs_psi"]["status"] == "missing"
    assert ids["geotech_landslide"]["status"] == "missing"
    assert ids["nes_cs_psi"]["amount_incl_gst"] == 0


def test_olfp_hit_adds_flood_assessment_not_a_price():
    site = {
        "lim": {
            "constraints": {
                "flood": False,
                "overland_flow": True,
                "coastal_inundation": False,
                "landfill": False,
                "landslide": "Low",
            }
        }
    }
    lines = {item["id"]: item for item in lim_statutory_lines(site)}
    assert lines["flood_hazard_assessment"]["status"] == "missing"
    assert lines["flood_hazard_assessment"]["amount_incl_gst"] == 0
    assert "geotech_landslide" not in lines


def test_lim_advice_from_explicit_hits_is_not_an_official_pdf():
    site = {
        "lim": {
            "status": "checked",
            "is_official_lim": False,
            "disclaimer_zh": "这不是已购买的正式 LIM PDF。",
            "constraints": {
                "flood": True,
                "overland_flow": True,
                "coastal_inundation": False,
                "landfill": False,
                "landslide": "Low",
            },
            "layers": [
                {
                    "id": "flood_plains",
                    "label_zh": "洪水平原 Flood Plains",
                    "present": True,
                    "sample": {"Hazard": "Flood Plain", "RAINFALL_EVENT": 100, "YEAR_PRODUCED": "2023"},
                },
                {
                    "id": "overland_flow_paths",
                    "label_zh": "地面径流 Overland Flow Paths",
                    "present": True,
                    "sample": {"CatchmentAreaGroup": 2, "CatchmentAreaGroup_label": "4000m²–1ha"},
                },
            ],
            "not_queried": list(NOT_QUERIED),
            "fee": {
                "standard_fee": 387,
                "urgent_fee": 522,
                "card_surcharge_percent": 1.75,
                "standard_working_days": 10,
                "urgent_working_days": 3,
                "source_name": "Auckland Council LIM",
                "source_url": "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html",
            },
        }
    }
    items = {item["id"]: item for item in lim_advice(site)}
    assert items["lim_official"]["severity"] == "info"
    assert "正式 LIM" in items["lim_official"]["title_zh"] or "尚未购买" in items["lim_official"]["title_zh"]
    assert items["lim_flood"]["severity"] == "constraint"
    assert items["lim_olfp"]["severity"] == "constraint"
    assert "lim_landslide" not in items
    assert "lim_landfill" not in items


def test_lim_sections_follow_official_headings_without_copying_a_pdf():
    report = {
        "status": "checked",
        "constraints": {
            "flood": False,
            "overland_flow": True,
            "coastal_inundation": False,
            "landfill": False,
            "landslide": "Low",
        },
        "layers": [
            {"id": "flood_plains", "present": False},
            {"id": "flood_prone", "present": False},
            {"id": "flood_sensitive", "present": False},
            {
                "id": "overland_flow_paths",
                "present": True,
                "sample": {"groups": "2000m²–4000m²、4000m²–1ha"},
            },
            {"id": "landfill", "present": False},
            {"id": "landslide", "present": True, "sample": {"SusceptibilityValue": "Low"}},
            {"id": "coastal_inundation", "present": False},
        ],
    }
    by_id = {item["id"]: item for item in lim_sections_from_report(report)}
    assert by_id["flooding"]["state"] == "public_clear"
    assert "不排除" in by_id["flooding"]["body_zh"]
    assert "每份都有" in by_id["flooding"]["body_zh"]
    assert by_id["overland_flow"]["state"] == "public_hit"
    assert "2000m²–4000m²" in by_id["overland_flow"]["body_zh"]
    assert by_id["site_contamination"]["state"] == "public_clear"
    assert "无污染" not in by_id["site_contamination"]["body_zh"]
    assert by_id["wind_zones"]["state"] == "official_only"
    assert "32 m/s" not in by_id["wind_zones"]["body_zh"]
    assert "LIR_00014017" not in by_id["drainage"]["body_zh"]
    assert by_id["drainage"]["state"] == "official_only"
    assert by_id["consents"]["state"] == "official_only"
    assert by_id["soil_issues"]["state"] == "public_clear"


def test_catchment_contaminant_layer_is_not_queried_as_hail():
    assert all("FeatureServer/9" not in layer["url"] for layer in LAYERS)
    assert any(item["id"] == "overland_flow_paths" for item in LAYERS)
    assert all(item["id"] != "overland_flow_paths" for item in NOT_QUERIED)
    assert any(item["id"] == "contaminated_sites_catchment" for item in NOT_QUERIED)
    assert any(item["id"] == "drainage_lir" for item in NOT_QUERIED)
    assert any(item["id"] == "exposure_zone" for item in NOT_QUERIED)
    assert any(item["id"] == "coastal_erosion" for item in NOT_QUERIED)
    assert all(layer["id"] != "contaminated_sites_catchment" for layer in LAYERS)


def test_flood_hints_do_not_mark_schemes_infeasible():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
        "height_m": 12,
    }
    site = {
        "parcel": {"found": True, "area_m2": 800},
        "lim": {
            "scheme_hints": ["prefer_two_storey", "prefer_compact"],
            "constraints": {"flood": True, "coastal_inundation": False, "landfill": False, "landslide": None},
        },
    }
    options, skipped = generate_typology_options(rules, site)
    assert skipped == 0
    terrace = next(item for item in options if item["template"]["kind"] == "terrace")
    assert terrace["verdict"]["status"] != "infeasible"
    compact = {"template": {"kind": "standalone", "storeys": 2, "dwellings": 1, "gfa_m2": 110}}
    sprawl = {"template": {"kind": "standalone", "storeys": 1, "dwellings": 1, "gfa_m2": 220}}
    assert _vision_penalty(compact, site) < _vision_penalty(sprawl, site)


def test_inject_lim_fee_onto_existing_option_lines():
    options = [
        {
            "id": "compact_3bed2bath",
            "lines": [{"id": "building_consent_deposit", "status": "priced", "amount_incl_gst": 5479, "category": "statutory"}],
            "totals": {"statutory_incl_gst": 5479, "confirmed_total_incl_gst": 10000, "missing_count": 1},
        }
    ]
    updated, changed = ensure_lim_cost_on_options(options, None)
    assert changed is True
    ids = [item["id"] for item in updated[0]["lines"]]
    assert "lim_report_fee" in ids
    assert updated[0]["totals"]["statutory_incl_gst"] == 5479 + 387
    assert updated[0]["totals"]["confirmed_total_incl_gst"] == 10000 + 387
    again, changed_again = ensure_lim_cost_on_options(updated, None)
    assert changed_again is False
    assert sum(1 for item in again[0]["lines"] if item["id"] == "lim_report_fee") == 1


def test_hydrate_lim_adds_official_sections_without_requery(monkeypatch):
    called = {"n": 0}

    def boom(_site):
        called["n"] += 1
        raise AssertionError("已有 OLFP 层时不应再查公开图层")

    monkeypatch.setattr("app.graph.lookup_lim", boom)
    result = {
        "site": {
            "geo": {"lat": -36.8, "lon": 174.7},
            "lim": {
                "status": "checked",
                "layers": [
                    {"id": "flood_plains", "label_zh": "洪水平原", "present": False},
                    {
                        "id": "overland_flow_paths",
                        "label_zh": "地面径流",
                        "present": True,
                        "sample": {"groups": "4000m²–1ha"},
                    },
                ],
                "constraints": {
                    "flood": False,
                    "overland_flow": True,
                    "coastal_inundation": False,
                    "landfill": False,
                    "landslide": None,
                },
                "findings": ["公开地面径流与本户相交。"],
                "not_queried": list(NOT_QUERIED),
                "fee": lim_report_fee(),
            },
        },
        "explanation": "LIM 公开核对：公开地面径流与本户相交。",
        "options": [],
        "advice": [],
    }
    updated = hydrate_lim(result)
    assert called["n"] == 0
    assert updated is not None
    sections = {item["id"]: item for item in updated["site"]["lim"]["sections"]}
    assert sections["overland_flow"]["state"] == "public_hit"
    assert sections["flooding"]["state"] == "public_clear"


def test_hydrate_lim_skip_paths():
    assert hydrate_lim({"site": {}}) is None
    assert hydrate_lim({"error": {"message": "x"}, "site": {"geo": {"lat": -36.8, "lon": 174.7}}}) is None
    already = {
        "site": {
            "geo": {"lat": -36.8, "lon": 174.7},
            "lim": {
                "status": "checked",
                "layers": [
                    {"id": "flood_plains", "present": False},
                    {"id": "overland_flow_paths", "present": False},
                ],
                "constraints": {
                    "flood": False,
                    "overland_flow": False,
                    "coastal_inundation": False,
                    "landfill": False,
                    "landslide": "Low",
                },
                "findings": [],
                "not_queried": [],
                "fee": lim_report_fee(),
            },
        },
        "explanation": "LIM 公开图层已核对，这不是已购买的正式 LIM PDF。",
        "options": [],
    }
    already["site"]["lim"]["sections"] = lim_sections_from_report(already["site"]["lim"])
    already["advice"] = lim_advice(already["site"])
    assert hydrate_lim(already) is None


def test_lim_node_fail_open(monkeypatch):
    def boom(_site):
        raise RuntimeError("layer down")

    monkeypatch.setattr("app.graph.lookup_lim", boom)
    result = lim_node({"site": {"geo": {"lat": -36.8, "lon": 174.7}}, "trace": []})
    assert result["lim"]["status"] == "unavailable"
    assert result["site"]["lim"]["is_official_lim"] is False


def test_unavailable_lim_is_not_sold_as_official():
    report = unavailable_lim("测试失败开放")
    assert report["is_official_lim"] is False
    assert report["status"] == "unavailable"
    assert "正式 LIM" in report["disclaimer_zh"]
    sections = {item["id"]: item for item in report["sections"]}
    assert sections["wind_zones"]["state"] == "official_only"
    assert sections["drainage"]["state"] == "official_only"
    assert sections["flooding"]["state"] == "unavailable"


def test_live_flood_plain_centroid_hits():
    report = lookup_lim({"geo": {"lat": -36.76794152769673, "lon": 174.42311424926376}})
    by_id = {item["id"]: item for item in report["layers"]}
    plains = by_id["flood_plains"]
    if plains.get("error"):
        pytest.skip(f"Flood Plains 公开图层不可用：{plains.get('error')}")
    assert plains["present"] is True
    assert (plains.get("sample") or {}).get("Hazard") == "Flood Plain"
    assert report["constraints"]["flood"] is True
    assert "prefer_compact" in report["scheme_hints"]


def test_live_howick_nelson_is_not_a_flood_or_hail_site():
    report = lookup_lim(
        {
            "geo": {"lat": -36.898391765801, "lon": 174.9238266328954},
            "parcel": {
                "found": True,
                "area_m2": 1033.7,
                "bbox": {
                    "min_lon": 174.923595514397,
                    "max_lon": 174.924059214381,
                    "min_lat": -36.8985345313087,
                    "max_lat": -36.8977903819983,
                },
            },
        }
    )
    by_id = {item["id"]: item for item in report["layers"]}
    if by_id["flood_plains"].get("error"):
        pytest.skip(f"Flood Plains 公开图层不可用：{by_id['flood_plains'].get('error')}")
    for key in ("flood_plains", "flood_prone", "flood_sensitive", "coastal_inundation", "landfill"):
        layer = by_id[key]
        if layer.get("error"):
            continue
        assert layer["present"] is False
    olfp = by_id["overland_flow_paths"]
    if olfp.get("error"):
        pytest.skip(f"Overland Flow Paths 公开图层不可用：{olfp.get('error')}")
    assert olfp["present"] is True
    assert report["constraints"]["overland_flow"] is True
    sample = olfp.get("sample") or {}
    assert sample.get("CatchmentAreaGroup") in {1, 2, 3, 4, 5}
    assert "prefer_compact" in report["scheme_hints"]
    landslide = by_id["landslide"]
    if not landslide.get("error"):
        assert (landslide.get("sample") or {}).get("SusceptibilityValue") == "Low"
        assert report["constraints"]["landslide"] == "Low"
    assert report["constraints"]["flood"] is False
    assert report["constraints"]["landfill"] is False
    assert report["is_official_lim"] is False
    sections = {item["id"]: item for item in report["sections"]}
    assert sections["flooding"]["state"] == "public_clear"
    assert sections["overland_flow"]["state"] == "public_hit"
    assert "不排除" in sections["flooding"]["body_zh"]
    assert "32 m/s" not in sections["wind_zones"]["body_zh"]
