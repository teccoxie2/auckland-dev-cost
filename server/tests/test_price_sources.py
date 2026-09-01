from app.costing import cost_option
from app.data_loader import typologies
from app.pricing import GST
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
    assert qty["external_wall_m2"] > 0


def test_priced_catalog_lines_use_public_skus():
    template = _compact()
    qty = takeoff(template, None)
    result = cost_option(template, {"needs_resource_consent": False, "reasons": []})
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["kaboodle_base_600"]["status"] == "priced"
    assert by_id["kaboodle_base_600"]["amount_incl_gst"] == round(130.92 * 5, 2)
    assert by_id["window_alu_1800x1200_dg"]["status"] == "priced"
    assert by_id["window_alu_1800x1200_dg"]["quantity"] == 4
    assert by_id["window_alu_1200x1200_dg"]["quantity"] == 4
    assert by_id["expol_tuffpod_1100x300"]["status"] == "priced"
    assert by_id["tap_caroma_luna_shower"]["amount_incl_gst"] == 518.0
    assert by_id["sink_mondella_concerto"]["amount_incl_gst"] == 198.0
    assert by_id["oven_bellini_60_pack"]["amount_incl_gst"] == 549.0
    assert by_id["tap_mondella_resonance_kitchen"]["amount_incl_gst"] == 146.0
    assert by_id["plumber_prepipe_kitchen"]["name_zh"] == "厨房给排水预埋"
    assert by_id["plumber_prepipe_kitchen"]["amount_incl_gst"] == 1000.0
    assert by_id["plumber_prepipe_bathroom"]["name_zh"] == "卫生间给排水预埋（马桶+淋浴+面盆）"
    assert by_id["plumber_prepipe_bathroom"]["quantity"] == 6
    assert by_id["plumber_prepipe_bathroom"]["amount_incl_gst"] == 6000.0
    assert by_id["plumber_prepipe_mains"]["amount_incl_gst"] == 1000.0
    assert by_id["plumber_fitoff_toilet"]["amount_incl_gst"] == 800.0
    assert by_id["plumber_fitoff_shower"]["amount_incl_gst"] == 900.0
    assert by_id["plumber_fitoff_basin"]["amount_incl_gst"] == 800.0
    wall = qty["external_wall_m2"]
    assert by_id["scaffolding_perimeter_erect"]["status"] == "priced"
    assert by_id["scaffolding_perimeter_erect"]["amount_incl_gst"] == round(18.0 * wall * (1 + GST), 2)
    assert by_id["scaffolding_perimeter_hire_week"]["amount_incl_gst"] == round(1.0 * wall * (1 + GST), 2)
    topping = qty["slab_topping_m3"]
    assert qty["slab_m3"] > topping
    assert by_id["thermakraft_215_underlay"]["status"] == "priced"
    assert by_id["thermakraft_215_underlay"]["amount_incl_gst"] == round(3.15 * qty["roof_underlay_m2"], 2)
    assert by_id["gib_ceiling_10mm"]["status"] == "priced"
    assert by_id["gib_ceiling_10mm"]["name_zh"] == "GIB 10mm 天花"
    assert "kitchen_package" not in by_id
    assert "scaffolding_mobile_3m_week" not in by_id
    missing_ids = [item["id"] for item in result["lines"] if item["status"] == "missing"]
    assert any("2100" in item_id for item_id in missing_ids)
    assert "bathroom_plumber_labour" not in missing_ids
    assert "kitchen_appliances_install" not in missing_ids
    assert "scaffolding_perimeter" not in missing_ids
    assert "kitchen_install_other_trades" in missing_ids
    assert by_id["official_lim_pdf"]["status"] == "missing"
    assert by_id["official_lim_pdf"]["amount_incl_gst"] == 0
    assert "lim_report_fee" not in by_id


def test_full_contract_wbs_reads_out_unpriced_trades():
    result = cost_option(_compact(), {"needs_resource_consent": False, "reasons": []})
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["ccc_base_fee"]["status"] == "priced"
    assert by_id["ccc_base_fee"]["amount_incl_gst"] == 722
    assert by_id["street_damage_inspection"]["amount_incl_gst"] == 124
    assert by_id["wbs_demolition"]["status"] == "missing"
    assert by_id["wbs_electrician"]["status"] == "missing"
    assert by_id["wbs_hvac_hrv"]["status"] == "missing"
    assert by_id["wbs_cladding_system"]["status"] == "missing"
    assert by_id["wbs_driveway"]["status"] == "missing"
    assert by_id["wbs_electrician"]["amount_incl_gst"] == 0
    assert by_id["wbs_electrician"]["wbs_group"] == "interior"
    assert by_id["wbs_e02_internal_framing"]["status"] == "missing"
    assert by_id["wbs_n01_switchboard"]["status"] == "missing"
    assert by_id["wbs_o01_heatpump"]["status"] == "missing"
    assert by_id["wbs_r04_power_connection"]["status"] == "missing"
    assert by_id["wbs_q03_external_general"]["status"] == "missing"
    assert by_id["wbs_j11_fireplace"]["status"] == "missing"
    assert "wbs_p01_lift" not in by_id
    assert by_id["timber_sg8_90x45_h12"]["wbs_group"] == "structure"
    assert by_id["ccc_base_fee"]["wbs_group"] == "fees"
    tall = {**_compact(), "storeys": 3}
    tall_ids = {item["id"] for item in cost_option(tall, {"needs_resource_consent": False, "reasons": []})["lines"]}
    assert "wbs_p01_lift" in tall_ids
    verify = cost_option(_compact(), {"needs_resource_consent": False, "reasons": []}, include_overheads=False)
    verify_ids = {item["id"] for item in verify["lines"]}
    assert "wbs_electrician" not in verify_ids
    assert "ccc_base_fee" not in verify_ids


def test_1800x600_window_uses_public_sku():
    template = {
        **_compact(),
        "windows": [{"code": "W3", "w_mm": 1800, "h_mm": 600, "count": 2}],
    }
    result = cost_option(template, {"needs_resource_consent": False, "reasons": []}, include_overheads=False)
    by_id = {item["id"]: item for item in result["lines"]}
    assert by_id["window_alu_1800x600_dg"]["status"] == "priced"
    assert by_id["window_alu_1800x600_dg"]["quantity"] == 2
    assert by_id["window_alu_1800x600_dg"]["amount_incl_gst"] == 1538.0


def test_resource_consent_deposit_is_official_lodgement():
    result = cost_option(_compact(), {"needs_resource_consent": True, "reasons": ["覆盖率"]})
    rc = next(item for item in result["lines"] if item["id"] == "resource_consent_deposit")
    assert rc["status"] == "priced"
    assert rc["amount_incl_gst"] == 6500
