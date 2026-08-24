from __future__ import annotations

import math
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
