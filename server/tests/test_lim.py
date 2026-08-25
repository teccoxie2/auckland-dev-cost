from pathlib import Path

import pytest

from app.costing import ensure_lim_cost_on_options, lim_statutory_lines
from app.design import _vision_penalty, generate_typology_options
from app.graph import apply_customer_lim, hydrate_lim, lim_node
from app.lim import awaiting_lim, lim_advice, report_from_parsed
from app.lim_parse import address_matches_project, parse_lim_pdf, parse_lim_text

HOWITK_LIM = Path("/home/ubuntu/.cursor/projects/workspace/uploads/895269-LIM_-_Land_Information_Memorandum_c03a.pdf")

HOWITK_TEXT = """
This Land Information Memorandum (LIM) has been prepared for the applicant for the purpose of
section 44A of the Local Government Official Information and Meetings Act 1987.
55 Nelson Street HOWICK Auckland 2014LIM address
8270537955Application number
23-Jul-2024Date issued
LOT 1 DP 535138Legal Description
s44A(2)(a) Information identifying any special feature or characteristics of the land
Site Contamination
No land contamination data are available in Council's regulatory records.
Wind Zones
Wind Zone(s) for this property: Low wind speed of 32 m/s
The wind zones are based on wind speed data specific to all building sites as outlined in NZS 3604:2011.
Soil Issues
The Auckland Council is not aware of any soil issues in relation to this land.
Flooding
This statement entitled "Flooding" appears on all LIMs.
The absence of flooding on the Special Land Features map does not exclude the possibility of the site flooding, particularly from Overland Flow Paths which may be on other properties.
Overland Flow Path
This site (property parcel) spatially intersects with one or more Overland Flow Paths, as displayed on the map attached to this LIM entitled Special Land Features.
Exposure Zones
This property is classified as: Unknown or Unassessed Corrosion Zone
Coastal Erosion
This explanation appears on all LIMs, not just sites that may be susceptible to coastal erosion.
s44A(2)(b) Information on private and public stormwater and sewerage drains
29/09/1995 Wastewater - outer drainage LIR_00014017 Description: No further development until such time there is an adequate stormwater system for connection. Refer development engineer, land development control.
s44A(2)(ba) Information notified to Council by a drinking water supplier
BCO10251617 DBC - Low block retaining wall adjacent to driveway, bridging public SS and SW drains
VXG21409322 Vehicle crossing application Completion Certificate Issued
s44A(2)(ea) Information notified under Section 124 of the Weathertight Homes Resolution Services Act 2006
The Council has not been notified of any information under Section 124 of the Weathertight Homes Resolution Services Act 2006 relating to this property.
"""


def test_parse_howick_lim_text_does_not_invent_fields():
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    assert parsed["ok"] is True
    assert parsed["is_official_lim"] is True
    assert parsed["application_number"] == "8270537955"
    assert parsed["issued_at"] == "2024-07-23"
    assert "55 Nelson Street" in (parsed["lim_address"] or "")
    assert parsed["legal_description"] == "LOT 1 DP 535138"
    assert parsed["site_contamination"]["has_regulatory_data"] is False
    assert parsed["wind_zone"]["label"] == "Low"
    assert parsed["wind_zone"]["speed_mps"] == 32
    assert parsed["soil_issues"]["council_aware"] is False
    assert parsed["overland_flow"]["intersects"] is True
    assert parsed["drainage_notices"][0]["lir_id"] == "LIR_00014017"
    assert "No further development" in parsed["drainage_notices"][0]["description"]
    assert any(item["id"] == "BCO10251617" for item in parsed["building_consents"])


def test_reject_non_lim_pdf_text():
    parsed = parse_lim_text(
        "Approved architectural plans window schedule\n"
        "EW1 1800 x 1200 qty 4\nEW2 1200 x 1200 qty 2\n"
        "Gross floor area 110 m2\nProposed Coverage 35 180\n"
        "This file is a building consent drawing not a council property report.\n" * 3,
        filename="bc.pdf",
    )
    assert parsed["ok"] is False
    assert "不像奥克兰议会正式 LIM" in parsed["error"]


def test_address_must_match_suburb_not_just_street_number():
    ok, _ = address_matches_project("55 Nelson Street HOWICK Auckland 2014", "55 Nelson Street, Howick, Auckland 2014")
    assert ok is True
    ok, message = address_matches_project(
        "55 Nelson Street HOWICK Auckland 2014",
        "55 Nelson Street, Auckland Central, Auckland 1010",
    )
    assert ok is False
    assert "不一致" in message or "郊区" in message


def test_awaiting_lim_is_not_sold_as_official():
    report = awaiting_lim()
    assert report["is_official_lim"] is False
    assert report["status"] == "awaiting_upload"
    assert report["source"] == "customer_pdf"
    assert all(item["state"] == "awaiting" for item in report["sections"])


def test_parsed_report_drives_constraints_from_text():
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    report = report_from_parsed(parsed)
    assert report["is_official_lim"] is True
    assert report["constraints"]["overland_flow"] is True
    assert report["constraints"]["flood"] is False
    assert report["constraints"]["contamination_data"] is False
    assert report["constraints"]["drainage_notices"] is True
    sections = {item["id"]: item for item in report["sections"]}
    assert sections["overland_flow"]["state"] == "recorded"
    assert "32 m/s" in sections["wind_zones"]["body_zh"]
    assert "LIR_00014017" in sections["drainage"]["body_zh"]
    items = {item["id"]: item for item in lim_advice({"lim": report})}
    assert items["lim_olfp"]["severity"] == "constraint"
    assert items["lim_drainage"]["severity"] == "constraint"


def test_missing_upload_is_not_an_order_fee():
    lines = {item["id"]: item for item in lim_statutory_lines(None)}
    assert "lim_report_fee" not in lines
    assert lines["official_lim_pdf"]["status"] == "missing"
    assert lines["official_lim_pdf"]["amount_incl_gst"] == 0
    assert "flood_hazard_assessment" not in lines


def test_parsed_olfp_adds_flood_assessment_not_a_price():
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    site = {"lim": report_from_parsed(parsed)}
    lines = {item["id"]: item for item in lim_statutory_lines(site)}
    assert "lim_report_fee" not in lines
    assert "official_lim_pdf" not in lines
    assert lines["flood_hazard_assessment"]["status"] == "missing"
    assert lines["official_lim_drainage_notices"]["status"] == "missing"
    assert "LIR_00014017" in lines["official_lim_drainage_notices"]["name_zh"]
    assert lines["flood_hazard_assessment"]["amount_incl_gst"] == 0
    assert "geotech_landslide" not in lines
    assert "nes_cs_psi" not in lines


def test_replace_old_order_fee_when_awaiting_upload():
    options = [
        {
            "id": "compact_3bed2bath",
            "lines": [
                {"id": "building_consent_deposit", "status": "priced", "amount_incl_gst": 5479, "category": "statutory"},
                {"id": "lim_report_fee", "status": "priced", "amount_incl_gst": 387, "category": "statutory"},
            ],
            "totals": {"statutory_incl_gst": 5479 + 387, "confirmed_total_incl_gst": 10000, "missing_count": 1},
        }
    ]
    updated, changed = ensure_lim_cost_on_options(options, {"lim": awaiting_lim()})
    assert changed is True
    ids = [item["id"] for item in updated[0]["lines"]]
    assert "lim_report_fee" not in ids
    assert "official_lim_pdf" in ids
    assert updated[0]["totals"]["statutory_incl_gst"] == 5479
    assert updated[0]["totals"]["confirmed_total_incl_gst"] == 10000 - 387


def test_lim_node_awaits_customer_pdf():
    result = lim_node({"site": {"geo": {"lat": -36.8, "lon": 174.7}}, "trace": []})
    assert result["lim"]["status"] == "awaiting_upload"
    assert result["site"]["lim"]["is_official_lim"] is False


def test_hydrate_replaces_public_gis_lim():
    result = {
        "site": {
            "geo": {"lat": -36.8, "lon": 174.7},
            "lim": {
                "status": "checked",
                "layers": [{"id": "overland_flow_paths", "present": True}],
                "constraints": {"overland_flow": True, "flood": False},
                "findings": ["公开地面径流"],
            },
        },
        "explanation": "LIM 公开图层已核对，这不是已购买的正式 LIM PDF。",
        "options": [
            {
                "id": "compact_3bed2bath",
                "lines": [
                    {"id": "building_consent_deposit", "status": "priced", "amount_incl_gst": 5479, "category": "statutory"},
                    {"id": "lim_report_fee", "status": "priced", "amount_incl_gst": 387, "category": "statutory"},
                ],
                "totals": {"statutory_incl_gst": 5866, "confirmed_total_incl_gst": 10387, "missing_count": 0},
            }
        ],
        "advice": [{"id": "lim_olfp", "title_zh": "old"}],
    }
    updated = hydrate_lim(result)
    assert updated is not None
    assert updated["site"]["lim"]["status"] == "awaiting_upload"
    assert "lim_report_fee" not in {item["id"] for item in updated["options"][0]["lines"]}
    assert "尚未上传" in updated["explanation"]


def test_hydrate_keeps_uploaded_lim(monkeypatch):
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    report = report_from_parsed(parsed)
    result = {
        "site": {"geo": {"lat": -36.8, "lon": 174.7}, "lim": report},
        "explanation": "正式 LIM：" + " ".join(report["findings"][:3]),
        "options": [],
        "advice": lim_advice({"lim": report}),
    }
    assert hydrate_lim(result) is None


def test_apply_customer_lim_rejects_other_street():
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    updated, error = apply_customer_lim({"site": {}, "options": [], "advice": []}, parsed, "12 Queen Street, Auckland Central")
    assert updated is None
    assert error


def test_apply_customer_lim_accepts_howick_project():
    parsed = parse_lim_text(HOWITK_TEXT, filename="895269-LIM.pdf")
    updated, error = apply_customer_lim(
        {"site": {}, "options": [], "advice": [], "explanation": ""},
        parsed,
        "55 Nelson Street, Howick, Auckland 2014",
    )
    assert error is None
    assert updated is not None
    assert updated["site"]["lim"]["constraints"]["overland_flow"] is True


def test_flood_hints_from_official_lim_do_not_mark_schemes_infeasible():
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
            "scheme_hints": ["prefer_compact"],
            "constraints": {"flood": False, "overland_flow": True, "coastal_inundation": False, "landfill": False},
        },
    }
    options, skipped = generate_typology_options(rules, site)
    assert skipped == 0
    terrace = next(item for item in options if item["template"]["kind"] == "terrace")
    assert terrace["verdict"]["status"] != "infeasible"
    compact = {"template": {"kind": "standalone", "storeys": 2, "dwellings": 1, "gfa_m2": 110}}
    sprawl = {"template": {"kind": "standalone", "storeys": 1, "dwellings": 1, "gfa_m2": 220}}
    assert _vision_penalty(compact, site) < _vision_penalty(sprawl, site)


@pytest.mark.skipif(not HOWITK_LIM.exists(), reason="环境里没有 55 Nelson 正式 LIM PDF")
def test_live_howick_pdf_text_layer():
    parsed = parse_lim_pdf(HOWITK_LIM, filename=HOWITK_LIM.name)
    assert parsed["ok"] is True
    assert parsed["overland_flow"]["intersects"] is True
    assert parsed["wind_zone"]["label"] == "Low"
    assert parsed["drainage_notices"][0]["lir_id"] == "LIR_00014017"
    assert parsed["site_contamination"]["has_regulatory_data"] is False
