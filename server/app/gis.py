from __future__ import annotations

import math
import re
from typing import Any

import httpx

NOMINATIM = "https://nominatim.openstreetmap.org/search"
ZONE_URL = (
    "https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/"
    "Unitary_Plan_Base_Zone/FeatureServer/0/query"
)
OVERLAY_MAP = (
    "https://mapspublic.aucklandcouncil.govt.nz/arcgis3/rest/services/"
    "NonCouncil/UnitaryPlanManagementLayers/MapServer/{layer}/query"
)

OVERLAYS = [
    (10, "significant_ecological_area"),
    (19, "notable_trees"),
    (25, "volcanic_viewshaft"),
    (32, "historic_heritage"),
    (34, "special_character"),
    (55, "height_variation"),
    (58, "coastal_inundation"),
    (7, "precinct"),
]

PROPERTY_LAYERS = [
    {
        "id": "ac_property_query",
        "url": (
            "https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/"
            "AC_Property_Query/FeatureServer/0/query"
        ),
        "source_name": "Auckland Council AC_Property（Open Data, CC-BY 4.0）",
    },
    {
        "id": "ac_property_dev_view",
        "url": (
            "https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/"
            "AC_Property_DEV_view/FeatureServer/0/query"
        ),
        "source_name": "Auckland Council AC_Property DEV view（Open Data, CC-BY 4.0）",
    },
]

ELEVATION_URL = "https://api.opentopodata.org/v1/nzdem8m"

AUCKLAND_BBOX = {
    "min_lat": -37.30,
    "max_lat": -35.89,
    "min_lon": 174.15,
    "max_lon": 175.59,
}

USER_AGENT = "AucklandDevCostMVP/1.0 (homeowner-feasibility)"


class GisError(Exception):
    def __init__(self, message: str, code: str = "gis_error"):
        super().__init__(message)
        self.code = code


def _client() -> httpx.Client:
    return httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT})


def geocode_address(address: str) -> dict[str, Any]:
    query = address.strip()
    if not query:
        raise GisError("请输入地址", "empty_address")
    if "auckland" not in query.lower() and "tāmaki" not in query.lower():
        query = f"{query}, Auckland, New Zealand"
    with _client() as client:
        response = client.get(
            NOMINATIM,
            params={"q": query, "format": "json", "limit": 5, "addressdetails": 1, "countrycodes": "nz"},
        )
        response.raise_for_status()
        hits = response.json()
    if not hits:
        raise GisError("找不到该地址，请补全市区或邮编", "not_found")
    chosen = None
    for hit in hits:
        lat = float(hit["lat"])
        lon = float(hit["lon"])
        if _in_auckland(lat, lon):
            chosen = hit
            break
    if chosen is None:
        raise GisError("该地址不在奥克兰范围内（第一期仅支持 Auckland）", "outside_auckland")
    lat = float(chosen["lat"])
    lon = float(chosen["lon"])
    return {
        "query": address,
        "display_name": chosen.get("display_name"),
        "lat": lat,
        "lon": lon,
        "osm_id": chosen.get("osm_id"),
        "source_name": "OpenStreetMap Nominatim",
        "source_url": "https://nominatim.openstreetmap.org/",
    }


def _in_auckland(lat: float, lon: float) -> bool:
    box = AUCKLAND_BBOX
    return box["min_lat"] <= lat <= box["max_lat"] and box["min_lon"] <= lon <= box["max_lon"]


def lookup_zone(lat: float, lon: float) -> dict[str, Any]:
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "NAME,ZONE",
        "returnGeometry": "false",
        "f": "json",
    }
    with _client() as client:
        response = client.get(ZONE_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    features = payload.get("features") or []
    if not features:
        raise GisError("公开区划图层未覆盖该坐标", "zone_missing")
    attributes = features[0]["attributes"]
    zone_code = attributes.get("ZONE")
    zone_name = _decode_zone(payload, zone_code) or attributes.get("NAME") or f"ZONE {zone_code}"
    return {
        "zone_code": int(zone_code) if zone_code is not None else None,
        "zone_name": zone_name,
        "source_name": "Auckland Council Unitary Plan Base Zone (Open Data, CC-BY 4.0)",
        "source_url": ZONE_URL.split("/query")[0],
    }


def _decode_zone(payload: dict[str, Any], code: Any) -> str | None:
    if code is None:
        return None
    fields = payload.get("fields") or []
    for field in fields:
        if field.get("name") != "ZONE":
            continue
        domain = (field.get("domain") or {}).get("codedValues") or []
        for item in domain:
            if item.get("code") == code or item.get("code") == int(code):
                return item.get("name")
    return None


def lookup_overlays(lat: float, lon: float) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 5,
    }
    with _client() as client:
        for layer_id, key in OVERLAYS:
            try:
                response = client.get(OVERLAY_MAP.format(layer=layer_id), params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError:
                found.append({"key": key, "present": False, "error": "overlay_request_failed", "layer_id": layer_id})
                continue
            features = payload.get("features") or []
            found.append(
                {
                    "key": key,
                    "present": bool(features),
                    "layer_id": layer_id,
                    "count": len(features),
                    "sample": (features[0].get("attributes") if features else None),
                    "source_url": OVERLAY_MAP.format(layer=layer_id).split("/query")[0],
                }
            )
    return found


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _ring_area_m2(ring: list[list[float]]) -> float:
    if len(ring) < 4:
        return 0.0
    radius = 6371000.0
    lat0 = math.radians(sum(point[1] for point in ring[:-1]) / (len(ring) - 1))
    xs: list[float] = []
    ys: list[float] = []
    for lon, lat in ring:
        xs.append(math.radians(lon) * math.cos(lat0) * radius)
        ys.append(math.radians(lat) * radius)
    area = 0.0
    for index in range(len(xs) - 1):
        area += xs[index] * ys[index + 1] - xs[index + 1] * ys[index]
    return abs(area) / 2.0


def _bbox(rings: list[list[list[float]]]) -> dict[str, float] | None:
    points = [point for ring in rings for point in ring]
    if not points:
        return None
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return {
        "min_lon": min(lons),
        "max_lon": max(lons),
        "min_lat": min(lats),
        "max_lat": max(lats),
    }


def _house_token(address: str) -> tuple[str, str]:
    match = re.search(r"\b(\d+)([A-Za-z])?\b", address)
    if not match:
        return "", ""
    return match.group(1), (match.group(2) or "").upper()


def _score_parcel(candidate: dict[str, Any], address: str) -> float:
    formatted = (candidate.get("formatted_address") or "").upper()
    number, unit = _house_token(address)
    score = 0.0
    if number and re.search(rf"\b{re.escape(number)}{re.escape(unit)}\b", formatted):
        score += 20
    if number and not unit:
        if re.search(rf"\b{re.escape(number)}\s", formatted) and not re.search(
            rf"\b{re.escape(number)}[A-Z]\b", formatted
        ):
            score += 40
        score += min(float(candidate.get("area_m2") or 0) / 100.0, 15)
    if number and unit and f"{number}{unit}" in formatted.replace(" ", ""):
        score += 50
    return score


def _parcel_from_feature(feature: dict[str, Any], layer: dict[str, str]) -> dict[str, Any] | None:
    attributes = feature.get("attributes") or {}
    rings = ((feature.get("geometry") or {}).get("rings")) or []
    area = sum(_ring_area_m2(ring) for ring in rings)
    if area <= 5:
        return None
    box = _bbox(rings)
    width_m = 0.0
    depth_m = 0.0
    if box:
        width_m = haversine_m(box["min_lat"], box["min_lon"], box["min_lat"], box["max_lon"])
        depth_m = haversine_m(box["min_lat"], box["min_lon"], box["max_lat"], box["min_lon"])
    return {
        "formatted_address": attributes.get("FORMATTEDADDRESS"),
        "property_id": attributes.get("PROPERTYID"),
        "parent_property_id": attributes.get("PARENTPROPERTYID"),
        "legal_description": attributes.get("PROPERTYDESCRIPTION"),
        "area_m2": round(area, 1),
        "frontage_m": round(min(width_m, depth_m), 1) if width_m and depth_m else None,
        "depth_m": round(max(width_m, depth_m), 1) if width_m and depth_m else None,
        "bbox": box,
        "layer_id": layer["id"],
        "source_name": layer["source_name"],
        "source_url": layer["url"].split("/query")[0],
    }


def lookup_parcel(lat: float, lon: float, address: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    number, _unit = _house_token(address)
    street = ""
    street_match = re.search(r"\d+[A-Za-z]?\s+([A-Za-z]+)", address)
    if street_match:
        street = street_match.group(1).upper()
    with _client() as client:
        for layer in PROPERTY_LAYERS:
            params = {
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "f": "json",
                "resultRecordCount": 8,
            }
            try:
                response = client.get(layer["url"], params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError:
                continue
            for feature in payload.get("features") or []:
                parsed = _parcel_from_feature(feature, layer)
                if parsed:
                    candidates.append(parsed)
            if number and street:
                where = (
                    f"FORMATTEDADDRESS LIKE '%{number}%' AND STREETNAME LIKE '%{street}%'"
                )
                try:
                    response = client.get(
                        layer["url"],
                        params={
                            "where": where,
                            "outFields": "*",
                            "returnGeometry": "true",
                            "outSR": 4326,
                            "f": "json",
                            "resultRecordCount": 20,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError:
                    continue
                for feature in payload.get("features") or []:
                    parsed = _parcel_from_feature(feature, layer)
                    if parsed:
                        candidates.append(parsed)
    uniq: dict[str, dict[str, Any]] = {}
    for item in candidates:
        key = f"{item.get('formatted_address')}|{item.get('area_m2')}|{item.get('layer_id')}"
        uniq[key] = item
    ranked = sorted(uniq.values(), key=lambda item: _score_parcel(item, address), reverse=True)
    if not ranked:
        return {
            "found": False,
            "note": "公开地籍未命中该点。坡度仍按地址点周围网格估算，覆盖率校核暂缺。",
        }
    chosen = ranked[0]
    chosen["found"] = True
    chosen["note"] = "面积由地块多边形经纬度环按球面近似计算，不是 Shape__Area（Web Mercator）原值。"
    return chosen


def lookup_terrain(lat: float, lon: float, parcel: dict[str, Any] | None = None) -> dict[str, Any]:
    box = (parcel or {}).get("bbox") if parcel else None
    if box:
        lats = [box["min_lat"], (box["min_lat"] + box["max_lat"]) / 2, box["max_lat"]]
        lons = [box["min_lon"], (box["min_lon"] + box["max_lon"]) / 2, box["max_lon"]]
    else:
        delta_lat = 40 / 111_320
        delta_lon = 40 / (111_320 * max(math.cos(math.radians(lat)), 0.2))
        lats = [lat - delta_lat, lat, lat + delta_lat]
        lons = [lon - delta_lon, lon, lon + delta_lon]
    locations = [f"{sample_lat},{sample_lon}" for sample_lat in lats for sample_lon in lons]
    with _client() as client:
        response = client.get(ELEVATION_URL, params={"locations": "|".join(locations)})
        response.raise_for_status()
        payload = response.json()
    if payload.get("status") != "OK":
        raise GisError("高程服务未返回有效 DEM", "terrain_failed")
    samples = []
    for item in payload.get("results") or []:
        elevation = item.get("elevation")
        location = item.get("location") or {}
        if elevation is None:
            continue
        samples.append(
            {
                "lat": location.get("lat"),
                "lon": location.get("lng"),
                "elevation_m": round(float(elevation), 2),
            }
        )
    if len(samples) < 3:
        raise GisError("DEM 取样不足，无法估计坡度", "terrain_failed")
    elevations = [item["elevation_m"] for item in samples]
    low = min(samples, key=lambda item: item["elevation_m"])
    high = max(samples, key=lambda item: item["elevation_m"])
    run_m = haversine_m(low["lat"], low["lon"], high["lat"], high["lon"])
    rise_m = high["elevation_m"] - low["elevation_m"]
    slope_ratio = rise_m / run_m if run_m else 0.0
    slope_deg = math.degrees(math.atan(slope_ratio)) if run_m else 0.0
    return {
        "samples": samples,
        "min_elevation_m": round(min(elevations), 2),
        "max_elevation_m": round(max(elevations), 2),
        "height_range_m": round(rise_m, 2),
        "run_m": round(run_m, 1),
        "slope_percent": round(slope_ratio * 100, 1),
        "slope_deg": round(slope_deg, 1),
        "source_name": "LINZ NZ 8m DEM（OpenTopodata nzdem8m，Topo50 等高线插值）",
        "source_url": "https://www.opentopodata.org/datasets/nzdem/",
        "note": "该 DEM 由 20m 等高线插值，LINZ 说明不宜作精密地形分析；初版只用来判断缓坡/中坡/陡坡与挡土墙是否值得列入。",
    }
