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
        raise AssertionError(result.get("note") or "LINZ 屋顶轮廓未返回")
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


def test_centroid_and_keep_box_filter():
    from app.imagery import KEEP_PAD_DEG, _centroid, _in_box

    lon, lat = _centroid([[[174.0, -36.0], [174.2, -36.0], [174.2, -36.2], [174.0, -36.2]]])
    assert round(lon, 1) == 174.1
    assert round(lat, 1) == -36.1
    box = {"min_lon": 174.0, "max_lon": 174.1, "min_lat": -36.1, "max_lat": -36.0}
    assert _in_box(174.05, -36.05, box, KEEP_PAD_DEG)
    assert not _in_box(175.0, -36.05, box, KEEP_PAD_DEG)
