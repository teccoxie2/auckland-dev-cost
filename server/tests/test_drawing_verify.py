from pathlib import Path
import sys

from fastapi.testclient import TestClient

from app.drawing_parse import extract_from_text
from app.drawing_verify import group_lines_by_zone, verify_drawing_parts, zone_for_line
from app.main import app

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drawing_parse import BC_TEXT, RC_TEXT, write_text_pdf


def test_zone_for_known_line_ids():
    assert zone_for_line({"id": "kaboodle_base_600"})[0] == "kitchen"
    assert zone_for_line({"id": "toilet_stein_ero"})[0] == "bathroom"
    assert zone_for_line({"id": "window_alu_1800x1200_dg"})[0] == "joinery"
    assert zone_for_line({"id": "timber_sg8_90x45_h12"})[0] == "structure"
    assert zone_for_line({"id": "concrete_readymix_20mpa"})[0] == "foundation"


def test_verify_groups_kitchen_bath_and_joinery():
    parts = [
        extract_from_text(RC_TEXT, kind="rc", filename="rc-notes.pdf"),
        extract_from_text(BC_TEXT, kind="bc", filename="bc-plans.pdf"),
    ]
    result = verify_drawing_parts(parts)
    assert result.get("error") is None
    zones = {item["id"]: item for item in result["zones"]}
    kitchen_ids = {line["id"] for line in zones["kitchen"]["lines"]}
    bathroom_ids = {line["id"] for line in zones["bathroom"]["lines"]}
    joinery_ids = {line["id"] for line in zones["joinery"]["lines"]}
    assert "kaboodle_base_600" in kitchen_ids
    assert "toilet_stein_ero" in bathroom_ids
    assert "window_alu_1800x1200_dg" in joinery_ids
    assert "joinery_SL1_3000x2100" in joinery_ids
    assert all(item["id"] != "watercare_igc" for zone in result["zones"] for item in zone["lines"])
    assert result["totals"]["missing_count"] >= 1
    gfa = next(item for item in result["fields"] if item["key"] == "gfa_m2")
    assert gfa["value"] == 186.4
    assert gfa["evidence"]


def test_group_preserves_missing_joinery_in_joinery_zone():
    grouped = group_lines_by_zone(
        [
            {"id": "window_alu_1800x1200_dg", "status": "priced", "amount_incl_gst": 10},
            {"id": "joinery_SL1_3000x2100", "status": "missing", "amount_incl_gst": 0},
        ]
    )
    by_id = {item["id"]: item for item in grouped}
    assert by_id["joinery"]["missing_count"] == 1
    assert by_id["joinery"]["priced_incl_gst"] == 10


def test_http_verify_reads_text_pdf(tmp_path):
    rc = tmp_path / "rc-notes.pdf"
    bc = tmp_path / "bc-plans.pdf"
    write_text_pdf(rc, RC_TEXT)
    write_text_pdf(bc, BC_TEXT)
    client = TestClient(app)
    response = client.post(
        "/drawings/verify",
        files=[
            ("files", ("rc-notes.pdf", rc.read_bytes(), "application/pdf")),
            ("files", ("bc-plans.pdf", bc.read_bytes(), "application/pdf")),
        ],
        data={"kinds": "rc,bc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    zones = {item["id"]: item for item in body["zones"]}
    assert "kitchen" in zones
    assert "bathroom" in zones
    assert "joinery" in zones
    assert any(item["id"] == "window_alu_1800x1200_dg" for item in zones["joinery"]["lines"])
