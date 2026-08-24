from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

import httpx

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

ADDRESS_URL = (
    "https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/"
    "AC_Address_Query/FeatureServer/0/query"
)
ADDRESS_SOURCE_NAME = "Auckland Council AC_Address（Open Data, CC-BY 4.0）"
ADDRESS_SOURCE_URL = ADDRESS_URL.rsplit("/query", 1)[0]

STREET_TYPES = frozenset(
    {
        "STREET",
        "ST",
        "ROAD",
        "RD",
        "AVENUE",
        "AVE",
        "DRIVE",
        "DR",
        "LANE",
        "LN",
        "PLACE",
        "PL",
        "CRESCENT",
        "CRES",
        "TERRACE",
        "TCE",
        "WAY",
        "PARADE",
        "HIGHWAY",
        "HWY",
        "CLOSE",
        "CL",
        "COURT",
        "CT",
        "RISE",
        "GROVE",
        "ESPLANADE",
        "CIRCUIT",
        "QUAY",
        "TRACK",
        "BEND",
        "LOOP",
        "MALL",
        "SQUARE",
        "SQ",
        "HEIGHTS",
        "VIEW",
        "HILL",
        "VALE",
        "GLADE",
        "PARK",
        "CREST",
        "POINT",
        "PT",
        "WALK",
        "MEWS",
        "ROW",
        "BOULEVARD",
        "BLVD",
    }
)
NUMBER_RE = re.compile(r"^(\d+)([A-Za-z])?(?:-(\d+)([A-Za-z])?)?$")
DP_RE = re.compile(r"\bDP\s+(\d+)\b", re.I)
MAX_CLUSTER_LOTS = 12
CITY_TOKENS = frozenset({"AUCKLAND", "TAMAKI", "TĀMAKI", "MAKAURAU", "NZ", "NEW", "ZEALAND"})

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


def _sql_lit(value: str) -> str:
    return value.replace("'", "''")


def _clean_query(raw: str) -> str:
    cleaned = re.sub(r"[%_]", "", raw)
    cleaned = re.sub(r"[^A-Za-z0-9ĀāĒēĪīŌōŪū'\-\s,/]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_address_query(raw: str) -> dict[str, str]:
    cleaned = _clean_query(raw)
    tokens = [token for token in re.split(r"[\s,/]+", cleaned) if token]
    number = ""
    number_index = -1
    for index, token in enumerate(tokens):
        if NUMBER_RE.fullmatch(token):
            number = token.upper()
            number_index = index
            break
    rest_upper = [token.upper() for token in (tokens[number_index + 1 :] if number_index >= 0 else tokens)]
    street_index = -1
    for index, token in enumerate(rest_upper):
        if token in STREET_TYPES:
            street_index = index
    if street_index >= 0:
        road_tokens = [token for token in rest_upper[:street_index] if token not in STREET_TYPES]
        locality_tokens = [token for token in rest_upper[street_index + 1 :] if token not in STREET_TYPES]
    elif len(rest_upper) >= 2:
        locality_tokens = [rest_upper[-1]]
        road_tokens = rest_upper[:-1]
    else:
        road_tokens = rest_upper
        locality_tokens = []
    while locality_tokens and locality_tokens[-1] in CITY_TOKENS:
        locality_tokens = locality_tokens[:-1]
    road = " ".join(road_tokens)
    locality = " ".join(locality_tokens)
    if locality and locality == road:
        locality = ""
    return {"raw": cleaned, "number": number, "road": road, "locality": locality}


def _number_clause(number: str) -> str:
    match = NUMBER_RE.fullmatch(number)
    if not match:
        return ""
    head, unit, range_end, range_unit = match.groups()
    if range_end:
        literal = _sql_lit(number)
        return f"UPPER(FullNumber)='{literal}'"
    if unit:
        literal = _sql_lit(number)
        return f"UPPER(FullNumber)='{literal}'"
    prefix = _sql_lit(head)
    return (
        f"(FullNumber='{prefix}' OR FullNumber LIKE '{prefix}-%' "
        f"OR UPPER(FullNumber) LIKE '{prefix}[A-Z]%')"
    )


def _full_address_prefixes(number: str, road: str) -> list[str]:
    if not number or not road:
        return []
    road_lit = _sql_lit(road)
    match = NUMBER_RE.fullmatch(number)
    if not match:
        return [f"UPPER(FullAddress) LIKE '{_sql_lit(number)} {road_lit}%'"]
    head, unit, range_end, _range_unit = match.groups()
    clauses = [f"UPPER(FullAddress) LIKE '{_sql_lit(number)} {road_lit}%'"]
    if range_end:
        return clauses
    if unit:
        return clauses
    prefix = _sql_lit(head)
    clauses.append(f"UPPER(FullAddress) LIKE '{prefix}-% {road_lit}%'")
    clauses.append(f"UPPER(FullAddress) LIKE '{prefix}[A-Z] {road_lit}%'")
    return clauses


def address_where(parsed: dict[str, str]) -> str | None:
    number = parsed.get("number") or ""
    road = parsed.get("road") or ""
    locality = parsed.get("locality") or ""
    if not number and not road:
        return None
    parts: list[str] = ["AddressStatus='Current'"]
    match_bits: list[str] = []
    if number and road:
        number_sql = _number_clause(number)
        match_bits.append(f"(UPPER(RoadName) LIKE '{_sql_lit(road)}%' AND {number_sql})")
        match_bits.extend(_full_address_prefixes(number, road))
    elif number:
        match_bits.append(_number_clause(number))
    else:
        match_bits.append(f"UPPER(RoadName) LIKE '{_sql_lit(road)}%'")
        match_bits.append(f"UPPER(FullAddress) LIKE '%{_sql_lit(road)}%'")
    parts.append("(" + " OR ".join(bit for bit in match_bits if bit) + ")")
    if locality:
        parts.append(f"UPPER(Locality) LIKE '{_sql_lit(locality)}%'")
    return " AND ".join(parts)


def _hit_from_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    attributes = feature.get("attributes") or {}
    geometry = feature.get("geometry") or {}
    lon = geometry.get("x")
    lat = geometry.get("y")
    if lat is None or lon is None:
        return None
    lat_f = float(lat)
    lon_f = float(lon)
    if not in_auckland(lat_f, lon_f):
        return None
    full_address = (attributes.get("FullAddress") or "").strip()
    if not full_address:
        return None
    road_name = attributes.get("RoadName") or ""
    road_type = attributes.get("RoadType") or ""
    road = " ".join(part for part in [road_name, road_type] if part).strip()
    return {
        "label": full_address,
        "full_address": full_address,
        "full_number": attributes.get("FullNumber"),
        "road_name": road_name,
        "road_type": road_type,
        "road": road,
        "locality": attributes.get("Locality"),
        "address_type": attributes.get("AddressType"),
        "lat": lat_f,
        "lon": lon_f,
        "sap_site_id": attributes.get("SAPsiteID"),
        "sap_address_id": attributes.get("SAPAddressID"),
        "source_name": ADDRESS_SOURCE_NAME,
        "source_url": ADDRESS_SOURCE_URL,
    }


def search_addresses(query: str, limit: int = 12) -> list[dict[str, Any]]:
    cleaned = _clean_query(query)
    if len(cleaned) < 3:
        return []
    parsed = parse_address_query(cleaned)
    where = address_where(parsed)
    if not where:
        return []
    fetch_limit = limit
    number_match = NUMBER_RE.fullmatch(parsed.get("number") or "")
    if number_match and not number_match.group(2) and not number_match.group(3):
        fetch_limit = max(limit, 16)
    params = {
        "where": where,
        "outFields": (
            "FullAddress,FullNumber,RoadName,RoadType,Locality,"
            "AddressType,AddressStatus,SAPsiteID,SAPAddressID"
        ),
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
        "resultRecordCount": max(1, min(fetch_limit, 20)),
        "orderByFields": "FullAddress ASC",
    }
    with _client() as client:
        try:
            response = client.get(ADDRESS_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise GisError(f"议会地址库暂时读不到：{exc}", "address_search_failed") from exc
    if payload.get("error"):
        message = payload["error"].get("message") or "议会地址库查询失败"
        raise GisError(message, "address_search_failed")
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feature in payload.get("features") or []:
        hit = _hit_from_feature(feature)
        if not hit:
            continue
        key = f"{hit['full_address']}|{round(hit['lat'], 6)}|{round(hit['lon'], 6)}"
        if key in seen:
            continue
        seen.add(key)
        hits.append(hit)
    return hits


def split_estate_note(query: str, hits: list[dict[str, Any]]) -> str | None:
    parsed = parse_address_query(query)
    number = (parsed.get("number") or "").upper()
    match = NUMBER_RE.fullmatch(number)
    if not match or match.group(2) or match.group(3):
        return None
    if len(hits) < 2:
        return None
    head = match.group(1)
    units: list[str] = []
    for hit in hits:
        token = (hit.get("full_number") or "").strip().upper().replace(" ", "")
        if not token:
            token = (hit.get("full_address") or "").split()[0].upper()
        house = NUMBER_RE.fullmatch(token)
        if not house or house.group(1) != head or not house.group(2) or house.group(3):
            return None
        units.append(house.group(2).upper())
    unique = sorted(set(units))
    if len(unique) < 2:
        return None
    labels = "、".join(f"{head}{unit}" for unit in unique)
    place = " ".join(part for part in [parsed.get("road") or "", parsed.get("locality") or ""] if part).title()
    where = f"{head} {place}".strip()
    return (
        f"议会已无整宗门牌 {where}；开发完成后现址为 {labels}。"
        "请选其中一户读地。开发完成后只按该户的议会现址核算，不把兄弟地块合计成整宗。"
    )


def geocode_from_selection(
    address: str,
    *,
    lat: float,
    lon: float,
    full_address: str | None = None,
    sap_address_id: str | None = None,
    sap_site_id: str | None = None,
) -> dict[str, Any]:
    if not in_auckland(lat, lon):
        raise GisError("该地址不在奥克兰范围内（第一期仅支持 Auckland）", "outside_auckland")
    display = (full_address or address).strip()
    return {
        "query": address,
        "display_name": display,
        "lat": float(lat),
        "lon": float(lon),
        "sap_address_id": sap_address_id,
        "sap_site_id": sap_site_id,
        "source_name": ADDRESS_SOURCE_NAME,
        "source_url": ADDRESS_SOURCE_URL,
    }


def geocode_address(
    address: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    full_address: str | None = None,
    sap_address_id: str | None = None,
    sap_site_id: str | None = None,
) -> dict[str, Any]:
    query = address.strip()
    if not query:
        raise GisError("请输入地址", "empty_address")
    if lat is not None and lon is not None:
        return geocode_from_selection(
            query,
            lat=lat,
            lon=lon,
            full_address=full_address,
            sap_address_id=sap_address_id,
            sap_site_id=sap_site_id,
        )
    hits = search_addresses(query)
    if len(hits) == 1:
        hit = hits[0]
        return geocode_from_selection(
            query,
            lat=hit["lat"],
            lon=hit["lon"],
            full_address=hit["full_address"],
            sap_address_id=hit.get("sap_address_id"),
            sap_site_id=hit.get("sap_site_id"),
        )
    if len(hits) > 1:
        raise GisError("该门牌对应多条议会地址，请从下拉列表选择一条", "ambiguous_address")
    raise GisError("奥克兰议会地址库没有匹配。请改写门牌或路名后从下拉列表选择。", "not_found")


def in_auckland(lat: float, lon: float) -> bool:
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


def filter_parcels_for_address(candidates: list[dict[str, Any]], address: str) -> list[dict[str, Any]]:
    number, unit = _house_token(address)
    if not number or not unit:
        return list(candidates)
    matched: list[dict[str, Any]] = []
    for item in candidates:
        cand_number, cand_unit = _house_token(item.get("formatted_address") or "")
        if cand_number == number and cand_unit == unit:
            matched.append(item)
    return matched or list(candidates)


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
    ranked = filter_parcels_for_address(ranked, address)
    ranked = sorted(ranked, key=lambda item: _score_parcel(item, address), reverse=True)
    if not ranked:
        return {
            "found": False,
            "note": "公开地籍未命中该点。坡度仍按地址点周围网格估算，覆盖率校核暂缺。",
        }
    chosen = ranked[0]
    chosen["found"] = True
    chosen["note"] = "面积由地块多边形经纬度环按球面近似计算，不是 Shape__Area（Web Mercator）原值。"
    return chosen


def deposited_plan_id(legal: str | None) -> str | None:
    if not legal:
        return None
    match = DP_RE.search(legal)
    return match.group(1) if match else None


def _siblings_by_deposited_plan(dp: str, street: str, number: str) -> list[dict[str, Any]]:
    if not dp.isdigit() or not street or not number:
        return []
    where = (
        f"UPPER(PROPERTYDESCRIPTION) LIKE '%DP {_sql_lit(dp)}%' "
        f"AND UPPER(STREETNAME) LIKE '%{_sql_lit(street)}%' "
        f"AND UPPER(FORMATTEDADDRESS) LIKE '{_sql_lit(number)}[A-Z]%'"
    )
    units: list[dict[str, Any]] = []
    seen: set[str] = set()
    with _client() as client:
        for layer in PROPERTY_LAYERS:
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
                if not parsed:
                    continue
                legal = parsed.get("legal_description") or ""
                if not re.search(rf"\bDP\s+{re.escape(dp)}\b", legal, re.I):
                    continue
                formatted = parsed.get("formatted_address") or ""
                sib_number, sib_unit = _house_token(formatted)
                if sib_number != number or not sib_unit:
                    continue
                key = str(parsed.get("property_id") or formatted or parsed.get("legal_description"))
                if key in seen:
                    continue
                seen.add(key)
                units.append(parsed)
            if units:
                break
    units.sort(key=lambda item: (item.get("formatted_address") or "", item.get("legal_description") or ""))
    return units


def lookup_unit_cluster(
    lat: float,
    lon: float,
    address: str,
    parcel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = (lat, lon)
    number, unit = _house_token(address)
    if not unit:
        return {"found": False, "reason": "not_a_unit_title"}
    parcel = parcel or {}
    legal = parcel.get("legal_description") or ""
    dp = deposited_plan_id(legal)
    selected = f"{number}{unit}"
    if not dp:
        return {
            "found": False,
            "reason": "no_deposited_plan",
            "selected_unit": selected,
            "selected_area_m2": parcel.get("area_m2"),
        }
    street = ""
    street_match = re.search(r"\d+[A-Za-z]?\s+([A-Za-z]+)", address)
    if not street_match:
        street_match = re.search(r"\d+[A-Za-z]?\s+([A-Za-z]+)", parcel.get("formatted_address") or "")
    if street_match:
        street = street_match.group(1).upper()
    try:
        units = _siblings_by_deposited_plan(dp, street, number)
    except Exception:  # noqa: BLE001
        return {
            "found": False,
            "reason": "cluster_lookup_failed",
            "title_plan": f"DP {dp}",
            "selected_unit": selected,
            "selected_area_m2": parcel.get("area_m2"),
        }
    if len(units) < 2:
        return {
            "found": False,
            "reason": "no_sibling_lots",
            "title_plan": f"DP {dp}",
            "selected_unit": selected,
            "selected_area_m2": parcel.get("area_m2"),
        }
    if len(units) > MAX_CLUSTER_LOTS:
        return {
            "found": False,
            "reason": "too_many_lots",
            "title_plan": f"DP {dp}",
            "unit_count": len(units),
            "note": (
                f"同一 DP {dp} 命中 {len(units)} 宗，超出单元簇上限 {MAX_CLUSTER_LOTS}，"
                "不按合计面积核算。"
            ),
        }
    areas = [float(item["area_m2"]) for item in units if item.get("area_m2")]
    combined = round(sum(areas), 1) if areas else None
    source = units[0]
    selected_area = parcel.get("area_m2")
    cluster = {
        "found": True,
        "title_plan": f"DP {dp}",
        "unit_count": len(units),
        "combined_area_m2": combined,
        "selected_unit": selected,
        "selected_area_m2": selected_area,
        "units": [
            {
                "formatted_address": item.get("formatted_address"),
                "legal_description": item.get("legal_description"),
                "area_m2": item.get("area_m2"),
                "property_id": item.get("property_id"),
            }
            for item in units
        ],
        "source_name": source.get("source_name"),
        "source_url": source.get("source_url"),
        "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
    }
    cluster["note"] = display_note_for_cluster(cluster)
    return cluster


def display_note_for_cluster(cluster: dict[str, Any]) -> str:
    selected = cluster.get("selected_unit") or "本户"
    selected_area = cluster.get("selected_area_m2")
    selected_bit = f"（约 {selected_area} m²）" if selected_area else ""
    short_labels: list[str] = []
    for item in cluster.get("units") or []:
        house, letter = _house_token(item.get("formatted_address") or "")
        if house and letter:
            short_labels.append(f"{house}{letter}")
    label_text = "、".join(short_labels) if short_labels else "拆分后各户"
    plan = cluster.get("title_plan") or "同一 DP"
    count = cluster.get("unit_count") or len(cluster.get("units") or [])
    return (
        f"开发完成后议会现址是当前选中的 {selected}{selected_bit}。"
        f"同号还有 {label_text}（{count} 户，{plan}），需分别从地址库点选。"
        "本页只显示并核算这一条议会记录，不把兄弟地块面积合计成整宗。"
    )


def attach_subdivision(site: dict[str, Any], address: str) -> dict[str, Any]:
    existing = site.get("subdivision") or {}
    if existing.get("found"):
        return site
    if existing.get("reason") in {"not_a_unit_title", "no_deposited_plan", "no_sibling_lots", "too_many_lots"}:
        return site
    parcel = site.get("parcel") or {}
    geo = site.get("geo") or {}
    if not parcel.get("found") or geo.get("lat") is None or geo.get("lon") is None:
        return site
    display = address or geo.get("display_name") or ""
    try:
        cluster = lookup_unit_cluster(float(geo["lat"]), float(geo["lon"]), display, parcel)
    except Exception:  # noqa: BLE001
        cluster = {"found": False, "reason": "cluster_lookup_failed"}
    out = dict(site)
    out["subdivision"] = cluster
    return out


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
