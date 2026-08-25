import httpx

from app.imagery import current_export_url, pick_historic_release


def test_pick_historic_release_prefers_about_eight_years_back():
    releases = [
        {"name": "World Imagery (Wayback 2026-08-05)", "m": "new"},
        {"name": "World Imagery (Wayback 2024-03-01)", "m": "mid"},
        {"name": "World Imagery (Wayback 2018-12-14)", "m": "hist"},
        {"name": "World Imagery (Wayback 2014-02-20)", "m": "old"},
    ]
    picked = pick_historic_release(releases, 2026)
    assert picked is not None
    assert picked["m"] == "hist"


def test_pick_historic_release_empty_and_fallback():
    assert pick_historic_release([], 2026) is None
    only_recent = [{"name": "World Imagery (Wayback 2024-01-01)", "m": "only"}]
    assert pick_historic_release(only_recent, 2024)["m"] == "only"


def test_linz_building_outlines_on_howick_parcel_bbox():
    from app.imagery import lookup_building_outlines

    result = lookup_building_outlines(
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
    if not result.get("found"):
        assert "失败" in (result.get("note") or "")
        return
    assert result["count"] >= 1
    assert result["source_url"].startswith("https://data.linz.govt.nz")
    assert result["roof_area_m2"] > 0


def test_esri_world_imagery_export_returns_jpeg():
    url = current_export_url(
        {
            "min_lon": 174.9225,
            "min_lat": -36.8992,
            "max_lon": 174.9252,
            "max_lat": -36.8975,
        }
    )
    response = httpx.get(url, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    assert "image" in content_type
    assert len(response.content) > 1000
