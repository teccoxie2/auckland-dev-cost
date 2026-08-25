from app.design import _vision_penalty, generate_typology_options
from app.graph import hydrate_site_analysis, merge_advice, site_vision_node
from app.site_vision import _call_vision_model, _hints_from_gis, _looks_like_price, unavailable_analysis, vision_advice


def test_hints_from_existing_roof_and_steep_slope():
    site = {
        "terrain": {"slope_deg": 9},
        "parcel": {"found": True, "area_m2": 400},
    }
    buildings = {"found": True, "count": 1, "parcel_coverage": 0.45}
    rules = {"coverage": 0.5}
    hints = _hints_from_gis(site, buildings, rules)
    assert "prefer_two_storey" in hints
    assert "prefer_compact" in hints
    assert "existing_rebuild" in hints
    assert "avoid_terrace" in hints
    assert "vacant_infill" not in hints


def test_hints_from_empty_outlines_are_vacant_infill():
    hints = _hints_from_gis(
        {"terrain": {"slope_deg": 2}},
        {"found": True, "count": 0},
        {"coverage": 0.5},
    )
    assert hints == ["vacant_infill"]


def test_failed_outline_query_is_not_treated_as_vacant():
    hints = _hints_from_gis(
        {"terrain": {"slope_deg": 2}},
        {"found": False, "note": "timeout"},
        {"coverage": 0.5},
    )
    assert "vacant_infill" not in hints
    assert "existing_rebuild" not in hints


def test_vision_penalty_ranks_rebuild_over_terrace():
    site = {"vision": {"scheme_hints": ["avoid_terrace", "existing_rebuild", "prefer_compact"]}}
    terrace = {"template": {"kind": "terrace", "storeys": 2, "dwellings": 3, "gfa_m2": 330}}
    compact = {"template": {"kind": "standalone", "storeys": 2, "dwellings": 1, "gfa_m2": 110}}
    assert _vision_penalty(terrace, site) > _vision_penalty(compact, site)


def test_vision_hints_do_not_mark_terrace_infeasible():
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
        "vision": {"scheme_hints": ["existing_rebuild", "avoid_terrace"]},
    }
    options, skipped = generate_typology_options(rules, site)
    assert skipped == 0
    terrace = next(item for item in options if item["template"]["kind"] == "terrace")
    assert terrace["verdict"]["status"] != "infeasible"
    recommended = [item for item in options if item.get("recommended")]
    assert recommended
    assert recommended[0]["template"]["kind"] == "standalone"


def test_vision_advice_without_model():
    site = {
        "imagery": [
            {
                "id": "current_export",
                "label_zh": "最新公开航拍（地块范围）",
                "source_name": "Esri World Imagery",
                "source_url": "https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08fda2d9bc",
            }
        ],
        "buildings": {"found": True, "count": 1, "roof_area_m2": 90, "parcel_coverage": 0.2, "note": "相交"},
        "vision": {
            "status": "imagery_only",
            "findings": ["地籍面积 400 m² 保持议会读数，航拍不改这个数字。"],
            "note": "未配置视觉模型",
        },
    }
    ids = {item["id"] for item in vision_advice(site)}
    assert "imagery" in ids
    assert "buildings" in ids
    assert "vision_model" in ids


def test_call_vision_model_skips_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _call_vision_model([{"url": "https://example.invalid/a.jpg"}], {}, {}) is None


def test_price_like_findings_are_detected():
    assert _looks_like_price("总价 NZD 12") is True
    assert _looks_like_price("屋顶轮廓 1 栋") is False


def test_hydrate_site_analysis_skip_paths():
    assert hydrate_site_analysis({"site": {}}) is None
    assert hydrate_site_analysis({"error": {"message": "x"}, "site": {"geo": {"lat": -36.8, "lon": 174.7}}}) is None
    already = {
        "site": {
            "geo": {"lat": -36.8, "lon": 174.7},
            "imagery": [{"id": "current_export", "url": "https://services.arcgisonline.com/x"}],
            "vision": {"status": "imagery_only"},
        }
    }
    assert hydrate_site_analysis(already) is None


def test_needs_site_analysis_retries_outline_timeout():
    from app.graph import _needs_site_analysis

    assert _needs_site_analysis(
        {
            "imagery": [{"id": "current_export"}],
            "vision": {"status": "imagery_only"},
            "buildings": {"found": False, "note": "LINZ 屋顶轮廓查询失败：The read operation timed out"},
        }
    )
    assert not _needs_site_analysis(
        {
            "imagery": [{"id": "current_export"}],
            "vision": {"status": "imagery_only"},
            "buildings": {"found": True, "count": 1},
        }
    )
    assert _needs_site_analysis(
        {
            "imagery": [{"id": "current_export"}],
            "vision": {"status": "imagery_only"},
            "parcel": {"found": True, "area_m2": 109.5},
            "buildings": {"found": True, "count": 3, "parcel_coverage": 2.6},
        }
    )


def test_site_vision_node_fail_open():
    assert site_vision_node({"error": {"message": "geocode failed"}}) == {}
    empty = site_vision_node({"site": {}, "rules": {}})
    assert empty["site"]["vision"]["status"] in {"unavailable", "imagery_only"}
    assert empty["trace"][-1]["node"] == "site_vision"


def test_merge_advice_dedupes_by_id():
    merged = merge_advice(
        [{"id": "zone", "title_zh": "a"}, {"id": "parcel", "title_zh": "b"}],
        [{"id": "zone", "title_zh": "dup"}, {"id": "imagery", "title_zh": "c"}],
    )
    assert [item["id"] for item in merged] == ["zone", "parcel", "imagery"]
    pruned = merge_advice(
        [{"id": "buildings_missing", "title_zh": "old"}],
        [{"id": "buildings", "title_zh": "new"}],
    )
    assert [item["id"] for item in pruned] == ["buildings"]


def test_unavailable_analysis_has_no_invented_sightings():
    payload = unavailable_analysis("timeout")
    assert payload["imagery"] == []
    assert payload["vision"]["scheme_hints"] == []
    assert payload["vision"]["findings"] == []
    assert payload["vision"]["model"] is None
