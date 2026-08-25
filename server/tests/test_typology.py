from app.building_rules import building_rules_for
from app.design import generate_typology_options
from app.quantity import takeoff
from app.data_loader import typologies


def test_typology_tries_four_kinds_on_large_residential_site():
    rules = {
        "residential": True,
        "permitted_dwellings": 3,
        "terrace_ok": True,
        "storeys": 3,
        "coverage": 0.5,
        "qualifying_matters": [],
        "height_m": 12,
    }
    site = {"parcel": {"found": True, "area_m2": 800}}
    options, skipped = generate_typology_options(rules, site)
    kinds = {item["template"]["kind"] for item in options}
    assert {"standalone", "duplex", "terrace", "minor_dwelling"} <= kinds
    assert len(options) >= 4
    assert skipped == 0
    blocked = [item for item in options if item["verdict"]["status"] == "infeasible"]
    for item in blocked:
        assert item["verdict"]["reasons"]
        assert "cost" not in item


def test_template_building_rules_mark_pending_detail():
    template = next(item for item in typologies()["templates"] if item["id"] == "compact_3bed2bath")
    qty = takeoff(template, None)
    rules = building_rules_for(template, qty)
    assert rules["pending_detail_drawing"] is True
    assert rules["stud_spacing_mm"] == 600
    assert rules["e2_score"] == qty["e2"]["score"]
