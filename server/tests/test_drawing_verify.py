from pathlib import Path
import sys

from fastapi.testclient import TestClient

from app.drawing_llm import evidence_in_source, parse_llm_json
from app.drawing_llm import llm_base_url, probe_llm
from app.drawing_parse import extract_from_text
from app.drawing_verify import group_lines_by_zone, verify_drawing_parts, verify_drawing_parts_rules, zone_for_line
from app.main import app

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drawing_parse import BC_TEXT, RC_TEXT, write_text_pdf

GFA_EVIDENCE = "Gross floor area: 186.4 m2"
KITCHEN_EVIDENCE = "1 kitchen"
BATH_EVIDENCE = "2 bathrooms"
W1_EVIDENCE = "W1 1800 x 1200 Qty 4"
W2_EVIDENCE = "W2 1200 x 1200 Qty 4"
ED_EVIDENCE = "ED1 860 x 2040 Qty 2"
SL_EVIDENCE = "SL1 3000 x 2100 Qty 1"


def sample_llm_payload() -> dict:
    return {
        "summary_zh": "两层住宅，文字层写明建筑面积与门窗表。",
        "fields": [
            {"key": "gfa_m2", "value": 186.4, "evidence": GFA_EVIDENCE},
            {"key": "footprint_m2", "value": 98.2, "evidence": "Ground floor area: 98.2 m2"},
            {"key": "storeys", "value": 2, "evidence": "2 storeys"},
            {"key": "kitchens", "value": 1, "evidence": KITCHEN_EVIDENCE},
            {"key": "bathrooms", "value": 2, "evidence": BATH_EVIDENCE},
            {"key": "dwellings", "value": 1, "evidence": "1 dwelling"},
            {"key": "wall_height_m", "value": 2.55, "evidence": "Wall height: 2.55 m"},
        ],
        "windows": [
            {"code": "W1", "w_mm": 1800, "h_mm": 1200, "count": 4, "evidence": W1_EVIDENCE},
            {"code": "W2", "w_mm": 1200, "h_mm": 1200, "count": 4, "evidence": W2_EVIDENCE},
            {"code": "ED1", "w_mm": 860, "h_mm": 2040, "count": 2, "evidence": ED_EVIDENCE},
            {"code": "SL1", "w_mm": 3000, "h_mm": 2100, "count": 1, "evidence": SL_EVIDENCE},
        ],
        "lines": [
            {
                "item_id": "timber_sg8_90x45_h12",
                "quantity": 9999,
                "unit_price": 1,
                "zone": "structure",
                "evidence": GFA_EVIDENCE,
                "reason_zh": "按建筑面积套结构材",
            },
            {
                "item_id": "kaboodle_base_600",
                "quantity": 99,
                "zone": "kitchen",
                "evidence": KITCHEN_EVIDENCE,
                "reason_zh": "厨房柜体",
            },
            {
                "item_id": "toilet_stein_ero",
                "quantity": 99,
                "zone": "bathroom",
                "evidence": BATH_EVIDENCE,
                "reason_zh": "卫生间马桶",
            },
            {
                "item_id": "window_alu_1800x1200_dg",
                "quantity": 99,
                "zone": "joinery",
                "evidence": W1_EVIDENCE,
                "reason_zh": "铝窗",
            },
            {
                "item_id": "not_in_catalog",
                "quantity": 1,
                "evidence": GFA_EVIDENCE,
                "reason_zh": "应被丢弃",
            },
        ],
    }


def drawing_parts():
    return [
        extract_from_text(RC_TEXT, kind="rc", filename="rc-notes.pdf"),
        extract_from_text(BC_TEXT, kind="bc", filename="bc-plans.pdf"),
    ]


def test_zone_for_known_line_ids():
    assert zone_for_line({"id": "kaboodle_base_600"})[0] == "kitchen"
    assert zone_for_line({"id": "toilet_stein_ero"})[0] == "bathroom"
    assert zone_for_line({"id": "window_alu_1800x1200_dg"})[0] == "joinery"
    assert zone_for_line({"id": "timber_sg8_90x45_h12"})[0] == "structure"
    assert zone_for_line({"id": "concrete_readymix_20mpa"})[0] == "foundation"


def test_verify_groups_kitchen_bath_and_joinery():
    result = verify_drawing_parts_rules(drawing_parts())
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


def test_llm_derivation_uses_catalog_prices_and_formula_qty():
    result = verify_drawing_parts(drawing_parts(), llm_payload=sample_llm_payload())
    assert result.get("error") is None
    assert result["derivation"] == "llm"
    assert result["llm"]["status"] == "ok"
    rejected_ids = {item["item_id"] for item in result["llm"]["rejected"]}
    assert "not_in_catalog" in rejected_ids
    zones = {item["id"]: item for item in result["zones"]}
    timber = next(item for item in zones["structure"]["lines"] if item["id"] == "timber_sg8_90x45_h12")
    kitchen = next(item for item in zones["kitchen"]["lines"] if item["id"] == "kaboodle_base_600")
    toilet = next(item for item in zones["bathroom"]["lines"] if item["id"] == "toilet_stein_ero")
    window = next(item for item in zones["joinery"]["lines"] if item["id"] == "window_alu_1800x1200_dg")
    assert timber["quantity"] != 9999
    assert timber["quantity"] > 0
    assert timber["status"] == "priced"
    assert timber["unit_price"] != 1
    assert kitchen["quantity"] == 5
    assert toilet["quantity"] == 2
    assert window["quantity"] == 4
    assert any(item["id"] == "joinery_SL1_3000x2100" for item in zones["joinery"]["lines"])
    assert result["rule_compare"]["zones"]


def test_llm_rejects_ungrounded_fields():
    payload = {
        "fields": [{"key": "gfa_m2", "value": 500, "evidence": "this phrase is not in the drawing"}],
        "windows": [],
        "lines": [],
    }
    result = verify_drawing_parts(drawing_parts(), llm_payload=payload)
    assert result["error"]["code"] == "llm_ungrounded"


def test_evidence_in_source_ignores_whitespace():
    assert evidence_in_source("Gross floor area: 186.4 m2", RC_TEXT)


def test_parse_llm_json_from_fence():
    parsed = parse_llm_json('```json\n{"summary_zh":"ok"}\n```')
    assert parsed == {"summary_zh": "ok"}


def test_http_verify_requires_llm_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CPA_API_KEY", raising=False)
    rc = tmp_path / "rc-notes.pdf"
    write_text_pdf(rc, RC_TEXT)
    client = TestClient(app)
    response = client.post(
        "/drawings/verify",
        files=[("files", ("rc-notes.pdf", rc.read_bytes(), "application/pdf"))],
        data={"kinds": "rc"},
    )
    assert response.status_code == 400
    assert "CPA_API_KEY" in response.json()["detail"]


def test_http_verify_reads_text_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-used")
    monkeypatch.setattr(
        "app.drawing_verify.call_drawing_llm",
        lambda source_text: {"ok": True, "model": "test-model", "payload": sample_llm_payload()},
    )
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
    assert body["derivation"] == "llm"
    zones = {item["id"]: item for item in body["zones"]}
    assert "kitchen" in zones
    assert "bathroom" in zones
    assert "joinery" in zones
    assert any(item["id"] == "window_alu_1800x1200_dg" for item in zones["joinery"]["lines"])


def test_ready_endpoint_reports_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CPA_API_KEY", raising=False)
    client = TestClient(app)
    response = client.get("/drawings/verify/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["llm"] is False
    assert body["configured"] is False


def test_cpa_base_url_from_management_page(monkeypatch):
    monkeypatch.setenv("CPA_BASE_URL", "http://192.168.52.81:8317/management.html")
    assert llm_base_url() == "http://192.168.52.81:8317/v1"


def test_cpa_api_key_marks_llm_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CPA_API_KEY", "cpa-test")
    monkeypatch.setenv("CPA_BASE_URL", "http://127.0.0.1:9")
    probed = probe_llm(ping_chat=False)
    assert probed["configured"] is True
    assert probed["reachable"] is False
    assert "127.0.0.1:9/v1" in probed["base_url"]
