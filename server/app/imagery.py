from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from .gis import haversine_m

WAYBACK_CATALOG = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer"
WAYBACK_TILE = (
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/"
    "WMTS/1.0.0/default028mm/MapServer/tile/{m}/{z}/{y}/{x}"
)
ESRI_EXPORT = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
BUILDING_OUTLINES = (
    "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/"
    "LINZ_NZ_Building_Outlines/FeatureServer/0/query"
)
ESRI_IMAGERY_ABOUT = "https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08fda2d9bc"
WAYBACK_ABOUT = "https://livingatlas.arcgis.com/wayback/"
BUILDING_ABOUT = "https://data.linz.govt.nz/layer/101290-nz-building-outlines/"

TILE_ZOOM = 18


def _client(timeout: float = 12.0) -> httpx.Client:
    return httpx.Client(timeout=timeout, follow_redirects=True)


def _webmercator_tile(lat: float, lon: float, zoom: int = TILE_ZOOM) -> tuple[int, int, int]:
    lat_rad = math.radians(min(max(lat, -85.05), 85.05))
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return zoom, min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def _bbox(site: dict[str, Any]) -> dict[str, float] | None:
    parcel = site.get("parcel") or {}
    box = parcel.get("bbox") if parcel.get("found") else None
    if box and all(box.get(key) is not None for key in ("min_lon", "max_lon", "min_lat", "max_lat")):
        return {
            "min_lon": float(box["min_lon"]),
            "max_lon": float(box["max_lon"]),
            "min_lat": float(box["min_lat"]),
            "max_lat": float(box["max_lat"]),
        }
    geo = site.get("geo") or {}
    if geo.get("lat") is None or geo.get("lon") is None:
        return None
    lat = float(geo["lat"])
    lon = float(geo["lon"])
    pad = 0.0007
    return {"min_lon": lon - pad, "max_lon": lon + pad, "min_lat": lat - pad, "max_lat": lat + pad}


@lru_cache(maxsize=1)
def wayback_releases() -> list[dict[str, str]]:
    with _client() as client:
        response = client.get(WAYBACK_CATALOG, params={"f": "json"})
        response.raise_for_status()
        payload = response.json()
    return [
        {"name": item["Name"], "m": str(item["M"]), "id": item.get("ID") or ""}
        for item in payload.get("Selection") or []
        if item.get("Name") and item.get("M") is not None
    ]


def _release_year(name: str) -> int | None:
    match = None
    for token in name.replace("_", "-").split():
        if token[:4].isdigit() and len(token) >= 4:
            year = int(token[:4])
            if 1990 <= year <= 2100:
                match = year
    return match


def pick_historic_release(releases: list[dict[str, str]], newest_year: int | None) -> dict[str, str] | None:
    target = (newest_year or 2026) - 8
    historic = [item for item in releases if (_release_year(item["name"]) or 9999) <= target]
    return historic[0] if historic else (releases[-1] if releases else None)


def current_export_url(box: dict[str, float]) -> str:
    bbox = f"{box['min_lon']},{box['min_lat']},{box['max_lon']},{box['max_lat']}"
    params = (
        f"bbox={bbox}&bboxSR=4326&imageSR=3857&size=800,800&format=jpg&f=image"
    )
    return f"{ESRI_EXPORT}?{params}"


def wayback_tile_url(release: dict[str, str], lat: float, lon: float) -> str:
    zoom, x, y = _webmercator_tile(lat, lon)
    return WAYBACK_TILE.format(m=release["m"], z=zoom, y=y, x=x)


def collect_imagery(site: dict[str, Any]) -> list[dict[str, Any]]:
    geo = site.get("geo") or {}
    lat = geo.get("lat")
    lon = geo.get("lon")
    if lat is None or lon is None:
        return []
    lat_f = float(lat)
    lon_f = float(lon)
    box = _bbox(site)
    frames: list[dict[str, Any]] = []
    if box:
        frames.append(
            {
                "id": "current_export",
                "kind": "current",
                "label_zh": "最新公开航拍（地块范围）",
                "note": "Esri World Imagery 镶嵌，持续更新，不是直播卫星。",
                "url": current_export_url(box),
                "source_name": "Esri World Imagery",
                "source_url": ESRI_IMAGERY_ABOUT,
            }
        )
    try:
        releases = wayback_releases()
    except Exception as exc:  # noqa: BLE001
        if frames:
            frames[0]["note"] = (frames[0].get("note") or "") + f" 历史图层目录读取失败：{exc}"
        return frames
    if not releases:
        return frames
    newest = releases[0]
    frames.append(
        {
            "id": "wayback_current",
            "kind": "current",
            "label_zh": f"最新 Wayback 航拍 · {newest['name'].replace('World Imagery (Wayback ', '').rstrip(')')}",
            "note": "与历史图同一瓦片位置，便于对照地块变化。",
            "url": wayback_tile_url(newest, lat_f, lon_f),
            "source_name": newest["name"],
            "source_url": WAYBACK_ABOUT,
            "captured_label": newest["name"],
        }
    )
    historic = pick_historic_release(releases, _release_year(newest["name"]))
    if historic and historic["m"] != newest["m"]:
        frames.append(
            {
                "id": "wayback_historic",
                "kind": "historic",
                "label_zh": f"历史航拍 · {historic['name'].replace('World Imagery (Wayback ', '').rstrip(')')}",
                "note": "同一位置的历史镶嵌，用来看现有房屋和场地是否近年才变化。",
                "url": wayback_tile_url(historic, lat_f, lon_f),
                "source_name": historic["name"],
                "source_url": WAYBACK_ABOUT,
                "captured_label": historic["name"],
            }
        )
    return frames


QUERY_PAD_DEG = 0.002
KEEP_PAD_DEG = 0.00006
SMALL_PARCEL_M2 = 250
NEAR_ROOF_M = 15


def _centroid(rings: list[list[list[float]]]) -> tuple[float, float] | None:
    points = [point for ring in rings for point in ring]
    if not points:
        return None
    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return lon, lat


def _in_box(lon: float, lat: float, box: dict[str, float], pad: float) -> bool:
    return (
        box["min_lon"] - pad <= lon <= box["max_lon"] + pad
        and box["min_lat"] - pad <= lat <= box["max_lat"] + pad
    )


def _keep_box(site: dict[str, Any]) -> dict[str, float] | None:
    box = _bbox(site)
    if box:
        return box
    geo = site.get("geo") or {}
    if geo.get("lat") is None or geo.get("lon") is None:
        return None
    lat = float(geo["lat"])
    lon = float(geo["lon"])
    pad = 0.00015
    return {"min_lon": lon - pad, "max_lon": lon + pad, "min_lat": lat - pad, "max_lat": lat + pad}


def lookup_building_outlines(site: dict[str, Any]) -> dict[str, Any]:
    keep_box = _keep_box(site)
    if not keep_box:
        return {"found": False, "note": "没有地块范围，无法查询 LINZ 屋顶轮廓。"}
    envelope = (
        f"{keep_box['min_lon'] - QUERY_PAD_DEG},{keep_box['min_lat'] - QUERY_PAD_DEG},"
        f"{keep_box['max_lon'] + QUERY_PAD_DEG},{keep_box['max_lat'] + QUERY_PAD_DEG}"
    )
    try:
        with _client(timeout=20.0) as client:
            response = client.get(
                BUILDING_OUTLINES,
                params={
                    "geometry": envelope,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": 4326,
                    "outSR": 4326,
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "f": "json",
                    "resultRecordCount": 200,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001
        return {"found": False, "note": f"LINZ 屋顶轮廓查询失败：{exc}"}
    if payload.get("error"):
        return {"found": False, "note": f"LINZ 屋顶轮廓查询被拒绝：{payload['error']}"}
    center_lon = (keep_box["min_lon"] + keep_box["max_lon"]) / 2
    center_lat = (keep_box["min_lat"] + keep_box["max_lat"]) / 2
    ranked: list[tuple[float, dict[str, Any]]] = []
    for feature in payload.get("features") or []:
        rings = ((feature.get("geometry") or {}).get("rings")) or []
        center = _centroid(rings)
        if center is None or not _in_box(center[0], center[1], keep_box, KEEP_PAD_DEG):
            continue
        attrs = feature.get("attributes") or {}
        area = attrs.get("Shape__Area")
        try:
            area_m2 = float(area) if area is not None else None
        except (TypeError, ValueError):
            area_m2 = None
        building = {
            "building_id": attrs.get("building_id"),
            "use": attrs.get("use_") or attrs.get("use"),
            "suburb": attrs.get("suburb_locality"),
            "area_m2": round(area_m2, 1) if area_m2 is not None else None,
            "imagery_date": attrs.get("imagery_capture_date") or attrs.get("image_capture_date"),
            "capture_source": attrs.get("capture_source") or attrs.get("imagery_source"),
        }
        dist_m = haversine_m(center_lat, center_lon, center[1], center[0])
        ranked.append((dist_m, building))
    parcel_area = ((site.get("parcel") or {}).get("area_m2")) if (site.get("parcel") or {}).get("found") else None
    if parcel_area and parcel_area < SMALL_PARCEL_M2:
        close = [item for item in ranked if item[0] <= NEAR_ROOF_M]
        if close:
            ranked = [max(close, key=lambda item: item[1].get("area_m2") or 0)]
    buildings = [item[1] for item in ranked]
    total_m2 = sum(float(item["area_m2"]) for item in buildings if item.get("area_m2"))
    coverage = round(total_m2 / float(parcel_area), 3) if parcel_area and total_m2 else None
    return {
        "found": True,
        "count": len(buildings),
        "roof_area_m2": round(total_m2, 1),
        "parcel_coverage": coverage,
        "buildings": buildings,
        "note": (
            "先按约 200 m 范围查询 LINZ 屋顶轮廓，再只保留质心落在本户地块外包矩形（外扩约 7 m）内的记录。"
            + ("本户地块较小，只保留距中心 15 m 内面积最大的一栋，避免把拆分后的邻户屋顶算进来。" if parcel_area and parcel_area < SMALL_PARCEL_M2 else "")
            + "面积来自该图层，不是议会地籍面积。"
        ),
        "source_name": "LINZ NZ Building Outlines",
        "source_url": BUILDING_ABOUT,
    }
