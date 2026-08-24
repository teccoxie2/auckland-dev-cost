from app.costing import cost_option
from app.data_loader import typologies
from app.quantity import takeoff


def _compact():
    return next(item for item in typologies()["templates"] if item["id"] == "compact_3bed2bath")


def test_kitchen_kit_and_pods_from_takeoff():
    qty = takeoff(_compact(), None)
    assert qty["kitchens"] == 1
    assert qty["kitchen_base_600"] == 5
    assert qty["kitchen_wall_600"] == 5
    assert qty["kitchen_door_600"] == 10
    assert qty["kitchen_bench_2400"] == 2
    assert qty["pod_count"] > 0


def test_priced_catalog_lines_use_public_skus():
    result = cost_option(_compact(), {"needs_resource_consent": False, "reasons": []})
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["kaboodle_base_600"]["status"] == "priced"
    assert by_id["kaboodle_base_600"]["amount_incl_gst"] == round(130.92 * 5, 2)
    assert by_id["window_alu_1800x1200_dg"]["status"] == "priced"
    assert by_id["window_alu_1800x1200_dg"]["quantity"] == 4
    assert by_id["window_alu_1200x1200_dg"]["quantity"] == 4
    assert by_id["expol_tuffpod_1100x300"]["status"] == "priced"
    assert by_id["tap_caroma_luna_shower"]["amount_incl_gst"] == 518.0
    assert by_id["scaffolding_mobile_3m_week"]["status"] == "priced"
    assert by_id["scaffolding_delivery"]["amount_incl_gst"] == 255.0
    assert "kitchen_package" not in by_id
    missing_ids = [item["id"] for item in result["lines"] if item["status"] == "missing"]
    assert any("2100" in item_id for item_id in missing_ids)
    assert "bathroom_plumber_labour" in missing_ids
    assert "kitchen_appliances_install" in missing_ids


def test_resource_consent_deposit_is_official_lodgement():
    result = cost_option(_compact(), {"needs_resource_consent": True, "reasons": ["覆盖率"]})
    rc = next(item for item in result["lines"] if item["id"] == "resource_consent_deposit")
    assert rc["status"] == "priced"
    assert rc["amount_incl_gst"] == 6500
