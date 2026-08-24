from pathlib import Path

from app.costing import cost_option
from app.design import wrap_typology
from app.drawing_flow import run_drawings, template_from_extract
from app.drawing_parse import extract_from_text, extract_pdf, infer_kind, merge_extracts
from app.quantity import takeoff
from app.zoning import filter_template


RC_TEXT = """
Resource consent architectural notes
Gross floor area: 186.4 m2
Ground floor area: 98.2 m2
Roof area: 112 m2
2 storeys
Wall height: 2.55 m
Eaves: 450 mm
Building coverage: 35 %
3 bedrooms
2 bathrooms
1 kitchen
1 dwelling
Block veneer cladding
Stud spacing 400 mm
Retaining wall height 1.1 m
W9 900 x 900 Qty 1
"""

BC_TEXT = """
Approved architectural plans window schedule
W1 1800 x 1200 Qty 4
W2 1200 x 1200 Qty 4
ED1 860 x 2040 Qty 2
SL1 3000 x 2100 Qty 1
"""


def _site():
    return {
        "parcel": {"found": True, "area_m2": 620, "frontage_m": 16},
        "terrain": {"slope_deg": 1.2, "height_range_m": 0.4},
    }


def _rules():
    return {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
    }


def write_text_pdf(path: Path, text: str) -> None:
    escaped = " ".join(text.split()).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 11 Tf 40 720 Td ({escaped}) Tj ET\n"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream.encode('ascii'))} >> stream\n{stream}endstream\nendobj\n",
    ]
    header = "%PDF-1.4\n"
    body = "".join(objects)
    offsets = [0]
    cursor = len(header.encode("ascii"))
    for item in objects:
        offsets.append(cursor)
        cursor += len(item.encode("ascii"))
    xref = ["xref\n0 6\n0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n")
    trailer = f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{cursor}\n%%EOF\n"
    path.write_bytes((header + body + "".join(xref) + trailer).encode("ascii"))


def test_infer_kind_from_filenames():
    assert infer_kind("115 bruce rd - 20121.06.03 - rc 1.pdf") == "rc"
    assert infer_kind("BCO10279820 - Approved -Architectural Plans.pdf") == "bc"


def test_extract_rc_fields_from_explicit_schedule_text():
    parsed = extract_from_text(RC_TEXT, kind="rc", filename="rc-notes.pdf")
    assert parsed["fields"]["gfa_m2"]["value"] == 186.4
    assert parsed["fields"]["footprint_m2"]["value"] == 98.2
    assert parsed["fields"]["roof_m2"]["value"] == 112.0
    assert parsed["fields"]["storeys"]["value"] == 2
    assert parsed["fields"]["stud_spacing_mm"]["value"] == 400
    assert parsed["fields"]["cladding"]["value"] == "block_veneer"
    assert parsed["fields"]["kitchens"]["value"] == 1
    assert parsed["fields"]["bathrooms"]["value"] == 2
    assert parsed["fields"]["retaining_height_m"]["value"] == 1.1
    assert parsed["fields"]["gfa_m2"]["evidence"]


def test_extract_window_schedule_rows():
    parsed = extract_from_text(BC_TEXT, kind="bc", filename="bc-plans.pdf")
    by_code = {item["code"]: item for item in parsed["windows"]}
    assert by_code["W1"]["w_mm"] == 1800
    assert by_code["W1"]["h_mm"] == 1200
    assert by_code["W1"]["count"] == 4
    assert by_code["ED1"]["count"] == 2
    assert by_code["SL1"]["w_mm"] == 3000
    assert by_code["SL1"]["evidence"]


def test_merge_prefers_rc_area_and_bc_windows():
    rc = extract_from_text(RC_TEXT, kind="rc", filename="rc.pdf")
    bc = extract_from_text(BC_TEXT, kind="bc", filename="bc.pdf")
    merged = merge_extracts([bc, rc])
    assert merged["fields"]["gfa_m2"]["source_file"] == "rc.pdf"
    assert merged["windows"][0]["source_file"] == "bc.pdf"
    assert not any(item["code"] == "W9" for item in merged["windows"])


def test_template_does_not_invent_gfa_when_area_missing():
    extracted = extract_from_text(BC_TEXT, kind="bc", filename="bc.pdf")
    merged = merge_extracts([extracted])
    template = template_from_extract(merged, _site())
    assert template["gfa_missing"] is True
    assert template["gfa_m2"] == 0
    assert template["kitchens"] == 0
    assert template["bathrooms"] == 0
    wrapped = wrap_typology(template)
    assert wrapped["kitchens"] == 0
    assert wrapped["gfa_missing"] is True


def test_drawing_without_area_does_not_price_timber_or_kitchen():
    template = template_from_extract(merge_extracts([extract_from_text(BC_TEXT, kind="bc", filename="bc.pdf")]), _site())
    result = cost_option(template, {"needs_resource_consent": False, "reasons": []}, site=_site())
    by_id = {item["id"]: item for item in result["lines"]}
    assert "drawing_area_unknown" in by_id
    assert "timber_sg8_90x45_h12" not in by_id
    assert "kaboodle_base_600" not in by_id
    assert "kitchen_count_unknown" in by_id
    assert "bathroom_count_unknown" in by_id
    assert by_id["window_alu_1800x1200_dg"]["status"] == "priced"
    assert by_id["window_alu_1800x1200_dg"]["quantity"] == 4
    assert by_id["door_hume_nexus15_860"]["quantity"] == 2
    assert by_id["joinery_SL1_3000x2100"]["status"] == "missing"


def test_drawing_with_area_uses_400mm_studs_and_drawn_retaining():
    merged = merge_extracts(
        [
            extract_from_text(RC_TEXT, kind="rc", filename="rc.pdf"),
            extract_from_text(BC_TEXT, kind="bc", filename="bc.pdf"),
        ]
    )
    template = template_from_extract(merged, _site())
    assert template["gfa_missing"] is False
    assert template["stud_spacing_mm"] == 400
    qty = takeoff(template, _site())
    assert qty["kitchens"] == 1
    assert qty["bathrooms"] == 2
    assert qty["wide_slider"] is True
    assert qty["retaining"]["height_m"] == 1.1
    assert qty["retaining"]["note"].startswith("挡土墙高度来自图纸文字")
    compact = takeoff(
        {
            **template,
            "stud_spacing_mm": 600,
            "storey_heights_m": None,
            "footprint_m2_drawn": template["footprint_m2_drawn"],
        },
        _site(),
    )
    assert qty["timber_90_lm"] > compact["timber_90_lm"]
    result = cost_option(template, {"needs_resource_consent": False, "reasons": []}, site=_site())
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["timber_sg8_90x45_h12"]["status"] == "priced"
    assert by_id["kaboodle_base_600"]["status"] == "priced"
    assert "cavity_closers_flashings" in by_id


def test_gfa_missing_skips_coverage_infeasibility():
    template = {
        "kind": "standalone",
        "dwellings": 1,
        "storeys": 2,
        "gfa_m2": 0,
        "gfa_missing": True,
    }
    verdict = filter_template(template, _rules(), {"parcel": {"found": True, "area_m2": 80}})
    assert verdict["status"] != "infeasible"


def test_extract_pdf_reads_text_layer(tmp_path: Path):
    path = tmp_path / "schedule.pdf"
    write_text_pdf(path, "Gross floor area: 165 m2\nW1 1800 x 1200 Qty 4")
    parsed = extract_pdf(path, kind="bc", filename="schedule.pdf")
    assert parsed["char_count"] > 20
    assert parsed.get("error") is None
    assert parsed["fields"]["gfa_m2"]["value"] == 165.0
    assert parsed["windows"][0]["count"] == 4


def test_blank_pdf_is_rejected(tmp_path: Path):
    path = tmp_path / "blank.pdf"
    write_text_pdf(path, "")
    parsed = extract_pdf(path, kind="rc", filename="blank.pdf")
    assert "scanned_or_empty_text" in parsed["warnings"]
    merged = merge_extracts([parsed])
    state = run_drawings(_site(), _rules(), [parsed])
    assert merged["enough_to_cost"] is False
    assert state["error"]["code"] == "drawing_empty"


def test_run_drawings_builds_priced_option():
    parts = [
        extract_from_text(RC_TEXT, kind="rc", filename="rc.pdf"),
        extract_from_text(BC_TEXT, kind="bc", filename="bc.pdf"),
    ]
    state = run_drawings(_site(), _rules(), parts)
    assert state.get("error") is None
    option = state["option"]
    assert option["id"] == "drawings"
    assert option["origin"] == "drawings"
    assert option["cost"]["totals"]["confirmed_total_incl_gst"] > 0
    assert option["drawing_extract"]["fields"]["gfa_m2"]["value"] == 186.4


BRUCE_RC = """
Street Address 115 Bruce Road, Glenfield 0629
Gross Site Area 733
Building Coverage % of Net Site Area
Allowable Coverage (MAX) 45 329.9
Proposed Coverage 42.7 313 comply
LOT 1 FFL= 48.0
LOT 2 FFL= 49.2
LOT 3 FFL= 48.9
LOT 4 FFL= 48.6
LOT 5 FFL= 48.3
LOT 6 FFL= 48.0
Second Floor Plan
KITCHEN DINING LIVING
ENS 1 MASTER BR 1
ENS 2 MASTER BR 2
BATH BED RM 3 BED RM 4
Keystone Retaining Wall Max Height 1m
2100H x 860W ED 11
2100H x 2700W ED 12
1200H x 1800W EW 08
2100H x 3000W ED 14
710W ED 08
"""

HART_BC = """
NEW RESIDENCE FOR LOT 1 OF 49 Hart Road HAURAKI 0622 BUILDING CONSENT
3000x2200 W-17
2000w x600h W-1
four bedrooms, three bathrooms
Total 310m2
"""


def test_revit_style_height_width_and_proposed_coverage():
    parsed = extract_from_text(BRUCE_RC, kind="rc", filename="115-bruce-rc.pdf")
    assert parsed["address_hint"].startswith("115 Bruce Road")
    assert parsed["fields"]["footprint_m2"]["value"] == 313.0
    assert parsed["fields"]["coverage_pct"]["value"] == 42.7
    assert parsed["fields"]["dwellings"]["value"] == 6
    assert parsed["fields"]["storeys"]["value"] == 3
    assert parsed["fields"]["kitchens"]["value"] == 6
    assert parsed["fields"]["bathrooms"]["value"] == 18
    assert parsed["fields"]["retaining_height_m"]["value"] == 1.0
    by_code = {item["code"]: item for item in parsed["windows"]}
    assert by_code["ED11"]["w_mm"] == 860
    assert by_code["ED11"]["h_mm"] == 2100
    assert by_code["EW08"]["w_mm"] == 1800
    assert by_code["ED08"]["w_mm"] == 710
    assert by_code["ED08"]["h_mm"] == 2100


def test_merge_drops_bc_from_another_street():
    rc = extract_from_text(BRUCE_RC, kind="rc", filename="115-bruce-rc.pdf")
    bc = extract_from_text(HART_BC, kind="bc", filename="hart-bc.pdf")
    merged = merge_extracts([rc, bc])
    assert merged["fields"]["footprint_m2"]["value"] == 313.0
    assert any("不一致" in item for item in merged["warnings"])
    assert not any(item["code"] == "W-17" or item["code"] == "W17" for item in merged["windows"])
    assert any(item["code"] == "ED11" for item in merged["windows"])


def test_wide_slider_not_priced_as_hume_door():
    template = template_from_extract(merge_extracts([extract_from_text(BRUCE_RC, kind="rc", filename="rc.pdf")]), _site())
    result = cost_option(template, {"needs_resource_consent": True, "reasons": []}, site=_site())
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["door_hume_nexus15_860"]["quantity"] == 1
    assert by_id["window_alu_1800x1200_dg"]["quantity"] == 1
    assert "joinery_ED14_3000x2100" in by_id
    assert "joinery_ED08_710x2100" in by_id
    assert "joinery_ED12_2700x2100" in by_id

