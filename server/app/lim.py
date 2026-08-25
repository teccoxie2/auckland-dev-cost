from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from .data_loader import council_fees
from .gis import USER_AGENT

LIM_ORDER_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html"
)
LIM_ABOUT_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/"
    "about-property-files-and-lim-reports.html"
)
HEALTHY_WATERS = "https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services"

LAYER_TIMEOUT_S = 8.0
OLFP_TIMEOUT_S = 12.0
LANDFILL_BBOX_PAD_DEG = 0.0004
LANDFILL_POINT_PAD_DEG = 0.0008
OLFP_POINT_PAD_DEG = 0.0005

CATCHMENT_AREA_GROUPS = {
    1: "2000m²–4000m²",
    2: "4000m²–1ha",
    3: "1ha–3ha",
    4: "3ha–100ha",
    5: "100ha 及以上",
}

LAYERS: list[dict[str, Any]] = [
    {
        "id": "flood_plains",
        "label_zh": "洪水平原 Flood Plains",
        "group": "flood",
        "geometry": "polygon",
        "url": f"{HEALTHY_WATERS}/Flood_Plains/FeatureServer/0/query",
        "source_name": "Auckland Council Healthy Waters Flood Plains（Open Data）",
        "out_fields": "Hazard,RAINFALL_EVENT,YEAR_PRODUCED,CLIMATE_CHANGE_ADJUSTED",
        "sample_keys": ("Hazard", "RAINFALL_EVENT", "YEAR_PRODUCED", "CLIMATE_CHANGE_ADJUSTED"),
    },
    {
        "id": "flood_prone",
        "label_zh": "易涝区 Flood Prone Areas",
        "group": "flood",
        "geometry": "polygon",
        "url": f"{HEALTHY_WATERS}/Flood_Prone_Areas/FeatureServer/0/query",
        "source_name": "Auckland Council Healthy Waters Flood Prone Areas（Open Data）",
        "out_fields": "FPA_ID,Depth100y,MaxDepth",
        "sample_keys": ("FPA_ID", "Depth100y", "MaxDepth"),
    },
    {
        "id": "flood_sensitive",
        "label_zh": "洪水敏感区 Flood Sensitive Areas",
        "group": "flood",
        "geometry": "polygon",
        "url": f"{HEALTHY_WATERS}/Flood_Sensitive_Areas/FeatureServer/0/query",
        "source_name": "Auckland Council Healthy Waters Flood Sensitive Areas（Open Data）",
        "out_fields": "Hazard,RAINFALL_EVENT,YEAR_PRODUCED",
        "sample_keys": ("Hazard", "RAINFALL_EVENT", "YEAR_PRODUCED"),
    },
    {
        "id": "overland_flow_paths",
        "label_zh": "地面径流 Overland Flow Paths",
        "group": "flood",
        "geometry": "polyline",
        "url": f"{HEALTHY_WATERS}/Overland_Flow_Paths/FeatureServer/0/query",
        "source_name": "Auckland Council Overland Flow Paths（GeoMaps 简化图层，CC-BY 4.0）",
        "out_fields": "CatchmentAreaGroup,Shape__Length",
        "sample_keys": ("CatchmentAreaGroup", "Shape__Length"),
        "timeout_s": OLFP_TIMEOUT_S,
        "use_envelope": True,
    },
    {
        "id": "coastal_inundation",
        "label_zh": "沿海淹没 1% AEP +1m 海平面",
        "group": "coastal",
        "geometry": "polygon",
        "url": f"{HEALTHY_WATERS}/Coastal_Inundation_1_AEP_1m_sea_level_rise/FeatureServer/0/query",
        "source_name": "Auckland Council Coastal Inundation 1% AEP 1m sea level rise（Open Data）",
        "out_fields": "Hazard,ARI_years,AEP_percent,SeaLevelRiseScenario,WaveSetUp",
        "sample_keys": ("Hazard", "ARI_years", "AEP_percent", "SeaLevelRiseScenario", "WaveSetUp"),
    },
    {
        "id": "landfill",
        "label_zh": "填埋场 Landfill Sites",
        "group": "landfill",
        "geometry": "point",
        "url": f"{HEALTHY_WATERS}/wm_Contaminant_Sources_Public/FeatureServer/12/query",
        "source_name": "Auckland Council Landfill Sites（wm_Contaminant_Sources_Public / 12）",
        "out_fields": "LANDFILL_TYPE,LANDFILL_STATUS,PURPOSE,WORKS_DESCRIPTION,GRANTED_DATE,EXPIRY_DATE",
        "sample_keys": (
            "LANDFILL_TYPE",
            "LANDFILL_STATUS",
            "PURPOSE",
            "WORKS_DESCRIPTION",
            "GRANTED_DATE",
            "EXPIRY_DATE",
        ),
    },
    {
        "id": "landslide",
        "label_zh": "大尺度滑坡易发性",
        "group": "landslide",
        "geometry": "polygon",
        "url": f"{HEALTHY_WATERS}/Large_Scale_Landslide_Susceptibility/FeatureServer/0/query",
        "source_name": "Auckland Council Large Scale Landslide Susceptibility（Open Data）",
        "out_fields": "SusceptibilityCode,SusceptibilityValue,TotalScore,Zone",
        "sample_keys": ("SusceptibilityCode", "SusceptibilityValue", "TotalScore", "Zone"),
        "use_point": True,
    },
]

NOT_QUERIED: list[dict[str, str]] = [
    {
        "id": "shallow_landslide",
        "label_zh": "浅层滑坡易发性",
        "reason": "该图层点查容易超时。正式 LIM 的土壤问题栏才是议会监管记录；全区大尺度滑坡 Low 分区不按约束列出。",
        "source_url": f"{HEALTHY_WATERS}/Shallow_Landslide_Susceptibility/FeatureServer/0",
    },
    {
        "id": "contaminated_sites_catchment",
        "label_zh": "流域尺度污染源（不作为本户 HAIL）",
        "reason": (
            "正式 LIM 的 Site Contamination 来自议会监管记录。"
            "公开第 9 层是整个 catchment 多边形，不能当成这一户 HAIL。"
        ),
        "source_url": f"{HEALTHY_WATERS}/wm_Contaminant_Sources_Public/FeatureServer/9",
    },
    {
        "id": "wind_zone",
        "label_zh": "NZS 3604 风区",
        "reason": "正式 LIM 的 Wind Zones 来自议会记录（例如 Low 32 m/s）。没有稳定的公开风区 FeatureServer，不编造风区，也不改 E2 计分。",
        "source_url": LIM_ABOUT_URL,
    },
    {
        "id": "drainage_lir",
        "label_zh": "雨污管网与开发限制通知",
        "reason": (
            "正式 LIM 的 s44A(2)(b) 才有私有/公共雨污管和 LIR。"
            "可能写明在有足够雨水管之前不得继续开发。公开 GIS 读不到这条通知。"
        ),
        "source_url": LIM_ABOUT_URL,
    },
    {
        "id": "consents_and_notices",
        "label_zh": "建工/资源许可与通知",
        "reason": "正式 LIM 才列出建工许可、资源许可、车辆出入口和 weathertight 通知。公开区划叠加层不能代替这份清单。",
        "source_url": LIM_ABOUT_URL,
    },
]

DISCLAIMER_ZH = (
    "这不是已购买的正式 LIM PDF。公开洪水图、地面径流和填埋点只能做开发尽职调查交叉核对，"
    "不能代替议会 LIM 里的管网 LIR、许可、风区、污染监管记录与费率。"
)


def lim_fee_snapshot() -> dict[str, Any]:
    table = council_fees()["lim_report"]
    return {
        "standard_fee": table["standard_fee"],
        "urgent_fee": table["urgent_fee"],
        "standard_cancellation_fee": table["standard_cancellation_fee"],
        "card_surcharge_percent": table["card_surcharge_percent"],
        "standard_working_days": table["standard_working_days"],
        "urgent_working_days": table["urgent_working_days"],
        "source_name": table["source_name"],
        "source_url": table["source_url"],
        "about_url": table.get("about_url") or LIM_ABOUT_URL,
        "retrieved_at": table["retrieved_at"],
        "notes": table["notes"],
    }


def unavailable_lim(note: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "is_official_lim": False,
        "disclaimer_zh": DISCLAIMER_ZH,
        "order_url": LIM_ORDER_URL,
        "about_url": LIM_ABOUT_URL,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "layers": [],
        "not_queried": list(NOT_QUERIED),
        "constraints": {
            "flood": False,
            "overland_flow": False,
            "coastal_inundation": False,
            "landfill": False,
            "landslide": None,
        },
        "scheme_hints": [],
        "findings": [],
        "note": note,
        "fee": lim_fee_snapshot(),
    }


def lookup_lim(site: dict[str, Any]) -> dict[str, Any]:
    try:
        return _lookup_lim(site)
    except Exception as exc:  # noqa: BLE001
        return unavailable_lim(f"LIM 公开图层核对失败：{exc}。方案仍按区划硬规则生成，正式报告需向议会订购。")


def _lookup_lim(site: dict[str, Any]) -> dict[str, Any]:
    geo = site.get("geo") or {}
    lat = geo.get("lat")
    lon = geo.get("lon")
    if lat is None or lon is None:
        return unavailable_lim("没有坐标，无法核对公开 LIM 图层。")
    layers: list[dict[str, Any]] = []
    timeout = httpx.Timeout(LAYER_TIMEOUT_S)
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for spec in LAYERS:
            layers.append(_query_layer(client, spec, site, float(lat), float(lon)))
    constraints = _constraints(layers)
    hints = _hints(constraints)
    findings = _findings(layers, constraints)
    timed_out = [item["label_zh"] for item in layers if item.get("error") == "timeout"]
    note = DISCLAIMER_ZH
    if timed_out:
        note += " 超时未读：" + "、".join(timed_out) + "。"
    return {
        "status": "checked",
        "is_official_lim": False,
        "disclaimer_zh": DISCLAIMER_ZH,
        "order_url": LIM_ORDER_URL,
        "about_url": LIM_ABOUT_URL,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "layers": layers,
        "not_queried": list(NOT_QUERIED),
        "constraints": constraints,
        "scheme_hints": hints,
        "findings": findings,
        "note": note,
        "fee": lim_fee_snapshot(),
    }


def lim_advice(site: dict[str, Any]) -> list[dict[str, Any]]:
    lim = site.get("lim") or {}
    if not lim:
        return []
    fee = lim.get("fee") or lim_fee_snapshot()
    items: list[dict[str, Any]] = [
        {
            "id": "lim_official",
            "severity": "info",
            "title_zh": "尚未购买正式 LIM",
            "body_zh": (
                DISCLAIMER_ZH
                + f" 议会 Standard ${fee.get('standard_fee')}（最多 {fee.get('standard_working_days')} 个工作日），"
                + f"加急 ${fee.get('urgent_fee')}（最多 {fee.get('urgent_working_days')} 个工作日）。"
                + f"信用卡/借记卡另加 {fee.get('card_surcharge_percent')}%，未计入造价。"
            ),
            "source_name": fee.get("source_name"),
            "source_url": fee.get("source_url") or LIM_ORDER_URL,
        }
    ]
    constraints = lim.get("constraints") or {}
    if constraints.get("overland_flow"):
        items.append(
            {
                "id": "lim_olfp",
                "severity": "constraint",
                "title_zh": "公开地面径流与本户相交",
                "body_zh": (
                    "正式 LIM 的洪水附图使用同一套 Overland Flow Path。"
                    "路径可能随降雨淹没；Unitary Plan 对路径内或邻近工程有规则；开发可能需要洪水评估。"
                    "这不是禁建。门牌点查询会漏掉路径，必须用地块外包矩形。"
                    + _layer_evidence(lim, {"overland_flow_paths"})
                ),
                "source_name": "Auckland Council Overland Flow Paths",
                "source_url": f"{HEALTHY_WATERS}/Overland_Flow_Paths/FeatureServer/0",
            }
        )
    if constraints.get("flood") or constraints.get("coastal_inundation"):
        items.append(
            {
                "id": "lim_flood",
                "severity": "constraint",
                "title_zh": "公开洪水或沿海淹没图层命中本户",
                "body_zh": (
                    "Healthy Waters 公开洪水图或 1% AEP +1m 海平面淹没图与本户相交。"
                    "这不是禁建，也不等于正式 LIM 结论。后续造价需要洪水评估、抬高 FFL 或场地排水，这些没有公开零售单价，已标缺项。"
                    + _layer_evidence(lim, {"flood_plains", "flood_prone", "flood_sensitive", "coastal_inundation"})
                ),
                "source_name": "Auckland Council Healthy Waters 公开洪水/淹没图层",
                "source_url": f"{HEALTHY_WATERS}/Flood_Plains/FeatureServer/0",
            }
        )
    if constraints.get("landfill"):
        items.append(
            {
                "id": "lim_landfill",
                "severity": "constraint",
                "title_zh": "本户附近公开填埋点命中",
                "body_zh": (
                    "Landfill Sites 点图层在本户外包矩形（外扩后）内命中。"
                    "这不能代替 NES-CS / HAIL 调查，也不使用流域尺度污染点计数。"
                    "初步场地调查（PSI）没有公开零售单价，已标缺项。"
                    + _layer_evidence(lim, {"landfill"})
                ),
                "source_name": "Auckland Council Landfill Sites",
                "source_url": f"{HEALTHY_WATERS}/wm_Contaminant_Sources_Public/FeatureServer/12",
            }
        )
    landslide = constraints.get("landslide")
    if landslide in {"Moderate", "High"}:
        items.append(
            {
                "id": "lim_landslide",
                "severity": "constraint",
                "title_zh": f"大尺度滑坡易发性为 {landslide}",
                "body_zh": (
                    "公开大尺度滑坡分区覆盖奥克兰大部分地区；只有 Moderate / High 才按约束列出。"
                    "岩土报告没有公开零售单价，已标缺项。这不是禁建。"
                    + _layer_evidence(lim, {"landslide"})
                ),
                "source_name": "Auckland Council Large Scale Landslide Susceptibility",
                "source_url": f"{HEALTHY_WATERS}/Large_Scale_Landslide_Susceptibility/FeatureServer/0",
            }
        )
    gaps = _gap_note(lim)
    if gaps:
        items.append(
            {
                "id": "lim_gaps",
                "severity": "watch",
                "title_zh": "部分 LIM 相关图层未读到",
                "body_zh": gaps,
                "source_name": "Auckland Council 公开图层核对",
                "source_url": LIM_ABOUT_URL,
            }
        )
    return items


def _query_layer(
    client: httpx.Client,
    spec: dict[str, Any],
    site: dict[str, Any],
    lat: float,
    lon: float,
) -> dict[str, Any]:
    params = {
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": spec["out_fields"],
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 8,
    }
    if spec["id"] == "landfill":
        params["geometry"] = json.dumps(_landfill_envelope(site, lat, lon))
        params["geometryType"] = "esriGeometryEnvelope"
        note = "用地块外包矩形外扩后查填埋点，不是流域多边形。"
    elif spec.get("use_envelope") or spec.get("geometry") == "polyline":
        params["geometry"] = json.dumps(_flow_envelope(site, lat, lon))
        params["geometryType"] = "esriGeometryEnvelope"
        note = "用地块外包矩形与折线相交。门牌点会漏掉地面径流，正式 LIM 也是按地块相交。"
    elif spec.get("use_point") or not _parcel_envelope(site):
        params["geometry"] = f"{lon},{lat}"
        params["geometryType"] = "esriGeometryPoint"
        note = "地址点相交查询。"
    else:
        params["geometry"] = json.dumps(_parcel_envelope(site))
        params["geometryType"] = "esriGeometryEnvelope"
        note = "用地块外包矩形与多边形相交，比只查门牌点更接近地块级 LIM。"
    timeout = float(spec.get("timeout_s") or LAYER_TIMEOUT_S)
    try:
        response = client.get(spec["url"], params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException:
        return _layer_result(spec, present=False, error="timeout", note=note + " 查询超时，失败开放。")
    except httpx.HTTPError:
        return _layer_result(spec, present=False, error="request_failed", note=note + " 请求失败，失败开放。")
    if not isinstance(payload, dict) or payload.get("error"):
        return _layer_result(spec, present=False, error="request_failed", note=note + " 图层返回错误，失败开放。")
    features = payload.get("features") or []
    sample = _sample(features[0].get("attributes") or {}, spec.get("sample_keys") or ()) if features else None
    if spec["id"] == "overland_flow_paths" and features:
        sample = _olfp_sample(features)
    return _layer_result(
        spec,
        present=bool(features),
        count=len(features),
        sample=sample,
        note=note,
    )


def _layer_result(
    spec: dict[str, Any],
    *,
    present: bool,
    error: str | None = None,
    count: int = 0,
    sample: dict[str, Any] | None = None,
    note: str = "",
) -> dict[str, Any]:
    return {
        "id": spec["id"],
        "label_zh": spec["label_zh"],
        "group": spec["group"],
        "present": present,
        "count": count,
        "error": error,
        "sample": sample,
        "note": note,
        "source_name": spec["source_name"],
        "source_url": spec["url"].rsplit("/query", 1)[0],
    }


def _parcel_envelope(site: dict[str, Any], pad: float = 0.0) -> dict[str, Any] | None:
    box = ((site.get("parcel") or {}).get("bbox")) or None
    if not box:
        return None
    return {
        "xmin": float(box["min_lon"]) - pad,
        "ymin": float(box["min_lat"]) - pad,
        "xmax": float(box["max_lon"]) + pad,
        "ymax": float(box["max_lat"]) + pad,
        "spatialReference": {"wkid": 4326},
    }


def _flow_envelope(site: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    parcel = _parcel_envelope(site)
    if parcel:
        return parcel
    pad = OLFP_POINT_PAD_DEG
    return {
        "xmin": lon - pad,
        "ymin": lat - pad,
        "xmax": lon + pad,
        "ymax": lat + pad,
        "spatialReference": {"wkid": 4326},
    }


def _landfill_envelope(site: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    parcel = _parcel_envelope(site, LANDFILL_BBOX_PAD_DEG)
    if parcel:
        return parcel
    pad = LANDFILL_POINT_PAD_DEG
    return {
        "xmin": lon - pad,
        "ymin": lat - pad,
        "xmax": lon + pad,
        "ymax": lat + pad,
        "spatialReference": {"wkid": 4326},
    }


def _olfp_sample(features: list[dict[str, Any]]) -> dict[str, Any]:
    groups: list[int] = []
    length_m = 0.0
    for feature in features:
        attrs = feature.get("attributes") or {}
        group = attrs.get("CatchmentAreaGroup")
        if isinstance(group, (int, float)):
            groups.append(int(group))
        raw_length = attrs.get("Shape__Length")
        if isinstance(raw_length, (int, float)):
            length_m += float(raw_length)
    unique = sorted(set(groups))
    top = max(unique) if unique else None
    return {
        "CatchmentAreaGroup": top,
        "CatchmentAreaGroup_label": CATCHMENT_AREA_GROUPS.get(top or -1, ""),
        "groups": "、".join(CATCHMENT_AREA_GROUPS.get(item, str(item)) for item in unique),
        "path_count": len(features),
        "length_m": round(length_m, 1),
    }


def _sample(attrs: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    picked: dict[str, Any] = {}
    for key in keys:
        if key not in attrs or attrs[key] in (None, ""):
            continue
        value = attrs[key]
        if isinstance(value, str) and len(value) > 240:
            picked[key] = value[:240] + "…"
        elif isinstance(value, (str, int, float, bool)):
            picked[key] = value
    return picked


def _constraints(layers: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {item["id"]: item for item in layers}
    flood = any(
        (by_id.get(key) or {}).get("present") for key in ("flood_plains", "flood_prone", "flood_sensitive")
    )
    coastal = bool((by_id.get("coastal_inundation") or {}).get("present"))
    overland = bool((by_id.get("overland_flow_paths") or {}).get("present"))
    landfill = bool((by_id.get("landfill") or {}).get("present"))
    sample = ((by_id.get("landslide") or {}).get("sample") or {})
    raw = sample.get("SusceptibilityValue")
    landslide = str(raw) if raw in {"Low", "Moderate", "High"} else None
    return {
        "flood": flood,
        "overland_flow": overland,
        "coastal_inundation": coastal,
        "landfill": landfill,
        "landslide": landslide,
    }


def _hints(constraints: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if constraints.get("flood") or constraints.get("coastal_inundation"):
        hints.extend(["prefer_two_storey", "prefer_compact"])
    if constraints.get("overland_flow"):
        hints.append("prefer_compact")
    if constraints.get("landfill"):
        hints.append("prefer_compact")
    if constraints.get("landslide") in {"Moderate", "High"}:
        hints.append("prefer_compact")
    return list(dict.fromkeys(hints))


def _findings(layers: list[dict[str, Any]], constraints: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    by_id = {item["id"]: item for item in layers}
    plains = by_id.get("flood_plains") or {}
    if plains.get("present"):
        sample = plains.get("sample") or {}
        event = sample.get("RAINFALL_EVENT")
        year = sample.get("YEAR_PRODUCED")
        bits = []
        if event:
            bits.append(f"{event} 年重现期")
        if year:
            bits.append(f"图层年 {year}")
        suffix = f"（{'，'.join(bits)}）" if bits else ""
        findings.append(f"公开洪水平原与本户相交{suffix}。不是正式 LIM 结论，也不是禁建。")
    prone = by_id.get("flood_prone") or {}
    if prone.get("present"):
        depth = (prone.get("sample") or {}).get("Depth100y")
        if isinstance(depth, (int, float)):
            findings.append(f"公开易涝区命中，图层 100 年重现期水深约 {depth} m。抬高 FFL 费用未计价。")
        else:
            findings.append("公开易涝区与本户相交。抬高 FFL 费用未计价。")
    if (by_id.get("flood_sensitive") or {}).get("present"):
        findings.append("公开洪水敏感区与本户相交。")
    if (by_id.get("overland_flow_paths") or {}).get("present"):
        sample = (by_id.get("overland_flow_paths") or {}).get("sample") or {}
        groups = sample.get("groups") or sample.get("CatchmentAreaGroup_label")
        extra = f"（汇水 {groups}）" if groups else ""
        findings.append(
            f"公开地面径流与本户相交{extra}。正式 LIM 写明路径可能淹没，开发可能需要洪水评估。不是禁建。"
        )
    if constraints.get("coastal_inundation"):
        findings.append("公开沿海淹没（1% AEP +1m 海平面）与本户相交。")
    if constraints.get("landfill"):
        findings.append("本户附近公开填埋点命中。NES-CS 调查未计价。")
    landslide = constraints.get("landslide")
    if landslide in {"Moderate", "High"}:
        zone = ((by_id.get("landslide") or {}).get("sample") or {}).get("Zone")
        zone_bit = f"，分区 {zone}" if zone else ""
        if landslide in {"Moderate", "High"}:
            findings.append(f"大尺度滑坡易发性为 {landslide}{zone_bit}。岩土报告未计价。")
    misses = [
        item["label_zh"]
        for item in layers
        if item.get("id") in {"flood_plains", "flood_prone", "flood_sensitive", "coastal_inundation", "landfill"}
        and not item.get("present")
        and not item.get("error")
    ]
    if misses and not (
        constraints.get("flood")
        or constraints.get("overland_flow")
        or constraints.get("coastal_inundation")
        or constraints.get("landfill")
    ):
        findings.append("抽查的公开洪水、沿海淹没与填埋点未与本户相交。正式 LIM 仍可能有地面径流、管网 LIR 或其他记录。")
    return findings


def _layer_evidence(lim: dict[str, Any], ids: set[str]) -> str:
    bits: list[str] = []
    for item in lim.get("layers") or []:
        if item.get("id") not in ids or not item.get("present"):
            continue
        sample = item.get("sample") or {}
        detail = "，".join(f"{key}={sample[key]}" for key in list(sample)[:4])
        bits.append(f"{item['label_zh']}" + (f"（{detail}）" if detail else ""))
    return (" 命中：" + "；".join(bits) + "。") if bits else ""


def _gap_note(lim: dict[str, Any]) -> str:
    parts: list[str] = []
    timed = [item["label_zh"] for item in lim.get("layers") or [] if item.get("error")]
    if timed:
        parts.append("超时或失败：" + "、".join(timed) + "。")
    skipped = [item["label_zh"] for item in lim.get("not_queried") or []]
    if skipped:
        parts.append(
            "正式 LIM 才有、公开图层读不到："
            + "、".join(skipped)
            + "。雨污管 LIR、风区和许可清单会影响能否继续开发，但没有公开单价。"
        )
    if lim.get("status") == "unavailable":
        parts.append(lim.get("note") or "公开图层未读到。")
    return " ".join(parts)
