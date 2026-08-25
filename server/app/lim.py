from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .data_loader import council_fees

LIM_ORDER_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html"
)
LIM_ABOUT_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/"
    "about-property-files-and-lim-reports.html"
)

FLOODING_ALL_LIMS_ZH = (
    "正式 LIM 每份都有 Flooding 栏。附图与 GeoMaps 洪水图同源，并会更新。"
    "图上无洪水不排除地面径流淹没，尤其是来自邻户的路径。"
    "开发可能需要申请人提供洪水评估。本页不识别附图像素。"
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


def awaiting_lim() -> dict[str, Any]:
    report = {
        "status": "awaiting_upload",
        "source": "customer_pdf",
        "is_official_lim": False,
        "disclaimer_zh": (
            "正式 LIM 由客户上传已购买的议会 PDF。查询地址时不读取公开洪水图层冒充 LIM，"
            "也不把订购费计入造价。"
        ),
        "order_url": LIM_ORDER_URL,
        "about_url": LIM_ABOUT_URL,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "layers": [],
        "constraints": _empty_constraints(),
        "scheme_hints": [],
        "findings": [],
        "note": "请上传客户提供的正式 LIM PDF。只读文字层，扫描件无法核对。",
        "fee": lim_fee_snapshot(),
        "parsed": None,
    }
    report["sections"] = lim_sections_from_report(report)
    return report


def report_from_parsed(parsed: dict[str, Any]) -> dict[str, Any]:
    constraints = {
        "flood": False,
        "overland_flow": bool((parsed.get("overland_flow") or {}).get("intersects")),
        "coastal_inundation": False,
        "landfill": False,
        "landslide": None,
        "contamination_data": (parsed.get("site_contamination") or {}).get("has_regulatory_data"),
        "soil_issues": (parsed.get("soil_issues") or {}).get("council_aware"),
        "drainage_notices": bool(parsed.get("drainage_notices")),
    }
    hints: list[str] = []
    if constraints["overland_flow"] or constraints["flood"]:
        hints.append("prefer_compact")
        if constraints["flood"]:
            hints.append("prefer_two_storey")
    report = {
        "status": "parsed",
        "source": "customer_pdf",
        "is_official_lim": True,
        "disclaimer_zh": "以下字段来自客户上传的正式 LIM PDF 文字层，不是公开 GIS 抽查，也不是附图识别。",
        "order_url": LIM_ORDER_URL,
        "about_url": LIM_ABOUT_URL,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "layers": [],
        "constraints": constraints,
        "scheme_hints": list(dict.fromkeys(hints)),
        "findings": list(parsed.get("findings") or []),
        "note": None,
        "fee": lim_fee_snapshot(),
        "parsed": parsed,
        "filename": parsed.get("filename"),
        "application_number": parsed.get("application_number"),
        "issued_at": parsed.get("issued_at"),
        "lim_address": parsed.get("lim_address"),
        "legal_description": parsed.get("legal_description"),
    }
    report["sections"] = lim_sections_from_report(report)
    return report


def lim_sections_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = report.get("parsed") or {}
    status = report.get("status")
    if status != "parsed":
        awaiting = "请上传正式 LIM 后读取此栏。"
        return [
            _section("site_contamination", "Site Contamination", "场地污染", "s44A(2)(a)", "awaiting", awaiting),
            _section("wind_zones", "Wind Zones", "风区", "s44A(2)(a)", "awaiting", awaiting),
            _section("soil_issues", "Soil Issues", "土壤", "s44A(2)(a)", "awaiting", awaiting),
            _section("flooding", "Flooding", "洪水", "s44A(2)(a)", "awaiting", awaiting + " " + FLOODING_ALL_LIMS_ZH),
            _section("overland_flow", "Overland Flow Path", "地面径流", "s44A(2)(a)", "awaiting", awaiting),
            _section("exposure_zones", "Exposure Zones", "腐蚀分区", "s44A(2)(a)", "awaiting", awaiting),
            _section("coastal", "Coastal Erosion", "海岸侵蚀", "s44A(2)(a)", "awaiting", awaiting),
            _section("drainage", "Stormwater and sewerage drains", "雨污管网", "s44A(2)(b)", "awaiting", awaiting),
            _section("consents", "Consents, certificates and notices", "许可与通知", "s44A(2)(d)", "awaiting", awaiting),
        ]

    contamination = parsed.get("site_contamination") or {}
    if contamination.get("has_regulatory_data") is False:
        contam_state, contam_body = "recorded", "议会监管记录没有场地污染数据。"
    elif contamination.get("has_regulatory_data"):
        contam_state, contam_body = "recorded", "正文写有污染监管内容。NES-CS 调查没有公开零售单价，已标缺项。"
    else:
        contam_state, contam_body = "not_stated", "文字层未读到 Site Contamination 结论。"
    contam_body += _evidence(contamination.get("evidence"))

    wind = parsed.get("wind_zone") or {}
    if wind.get("label"):
        speed = f" {wind['speed_mps']} m/s" if wind.get("speed_mps") is not None else ""
        wind_body = f"NZS 3604 风区 {wind['label']}{speed}。未改 E2 计分（仍按中等风区假设），因为没有把议会风区映射进公开分值表。"
        wind_state = "recorded"
    else:
        wind_state, wind_body = "not_stated", "文字层未读到 Wind Zones。"
    wind_body += _evidence(wind.get("evidence"))

    soil = parsed.get("soil_issues") or {}
    if soil.get("council_aware") is False:
        soil_state, soil_body = "recorded", "议会写明不知本户有土壤问题。"
    elif soil.get("council_aware"):
        soil_state, soil_body = "recorded", "正文写有土壤问题。岩土报告没有公开零售单价，已标缺项。"
    else:
        soil_state, soil_body = "not_stated", "文字层未读到 Soil Issues 结论。"
    soil_body += _evidence(soil.get("evidence"))

    flooding = parsed.get("flooding") or {}
    flood_body = FLOODING_ALL_LIMS_ZH
    if flooding.get("evidence"):
        flood_body += _evidence(flooding.get("evidence"))
    flood_state = "recorded" if flooding.get("all_lims_statement") or flooding.get("evidence") else "not_stated"

    olfp = parsed.get("overland_flow") or {}
    if olfp.get("intersects") is True:
        olfp_state = "recorded"
        olfp_body = (
            "正文写明本户地块与一条或多条 Overland Flow Path 空间相交。"
            "路径可能随降雨淹没；Unitary Plan 对路径内或邻近工程有规则。不是禁建。附图未做图像识别。"
        )
    elif olfp.get("intersects") is False:
        olfp_state = "recorded"
        olfp_body = "正文未写明本户与 Overland Flow Path 空间相交。附图未做图像识别。"
    else:
        olfp_state = "not_stated"
        olfp_body = "未读到地面径流是否与本户相交的句子。附图未做图像识别。"
    olfp_body += _evidence(olfp.get("evidence"))

    exposure = parsed.get("exposure_zone") or {}
    if exposure.get("label"):
        exposure_state, exposure_body = "recorded", f"腐蚀分区：{exposure['label']}。"
    else:
        exposure_state, exposure_body = "not_stated", "文字层未读到 Exposure Zones。"
    exposure_body += _evidence(exposure.get("evidence"))

    coastal = parsed.get("coastal_erosion") or {}
    coastal_body = "正式 LIM 每份都有 Coastal Erosion 栏。ASCIE 线在附图上，本页不识别像素。"
    coastal_state = "recorded" if coastal.get("evidence") or coastal.get("standard_text_only") else "not_stated"
    coastal_body += _evidence(coastal.get("evidence"))

    notices = parsed.get("drainage_notices") or []
    if notices:
        drain_state = "recorded"
        bits = [f"{item.get('lir_id')}: {item.get('description')}" for item in notices[:3]]
        drain_body = "管网通知（LIR）：" + "；".join(bits)
    else:
        drain_state = "not_stated"
        drain_body = "文字层未读到 LIR 编号。私有排水接到公共管仍由业主负责。"

    consents = parsed.get("building_consents") or []
    crossings = parsed.get("vehicle_crossings") or []
    consent_bits = [item.get("id") for item in consents[:8] if item.get("id")]
    crossing_bits = [item.get("id") for item in crossings[:4] if item.get("id")]
    if consent_bits or crossing_bits:
        consent_state = "recorded"
        consent_body = ""
        if consent_bits:
            consent_body += "建工许可编号：" + "、".join(consent_bits) + "。"
        if crossing_bits:
            consent_body += "车辆出入口：" + "、".join(crossing_bits) + "。"
        if parsed.get("weathertight_notified") is False:
            consent_body += "议会写明未收到 weathertight 第 124 条通知。"
    else:
        consent_state = "not_stated"
        consent_body = "文字层未抽出建工许可编号。公开区划不能代替这份清单。"

    return [
        _section("site_contamination", "Site Contamination", "场地污染", "s44A(2)(a)", contam_state, contam_body),
        _section("wind_zones", "Wind Zones", "风区", "s44A(2)(a)", wind_state, wind_body),
        _section("soil_issues", "Soil Issues", "土壤", "s44A(2)(a)", soil_state, soil_body),
        _section("flooding", "Flooding", "洪水", "s44A(2)(a)", flood_state, flood_body),
        _section("overland_flow", "Overland Flow Path", "地面径流", "s44A(2)(a)", olfp_state, olfp_body),
        _section("exposure_zones", "Exposure Zones", "腐蚀分区", "s44A(2)(a)", exposure_state, exposure_body),
        _section("coastal", "Coastal Erosion", "海岸侵蚀", "s44A(2)(a)", coastal_state, coastal_body),
        _section("drainage", "Stormwater and sewerage drains", "雨污管网", "s44A(2)(b)", drain_state, drain_body),
        _section("consents", "Consents, certificates and notices", "许可与通知", "s44A(2)(d)", consent_state, consent_body),
    ]


def lim_advice(site: dict[str, Any]) -> list[dict[str, Any]]:
    lim = site.get("lim") or {}
    if not lim:
        return []
    fee = lim.get("fee") or lim_fee_snapshot()
    if lim.get("status") != "parsed":
        return [
            {
                "id": "lim_official",
                "severity": "watch",
                "title_zh": "请上传正式 LIM",
                "body_zh": (
                    "开发核算以客户已购买的议会 LIM PDF 为准。"
                    f"若尚未购买，议会 Standard ${fee.get('standard_fee')}（最多 {fee.get('standard_working_days')} 个工作日），"
                    f"加急 ${fee.get('urgent_fee')}。信用卡另加 {fee.get('card_surcharge_percent')}%，订购费不计入本页造价。"
                ),
                "source_name": fee.get("source_name"),
                "source_url": fee.get("source_url") or LIM_ORDER_URL,
            }
        ]
    items: list[dict[str, Any]] = [
        {
            "id": "lim_official",
            "severity": "info",
            "title_zh": "已读取客户上传的正式 LIM",
            "body_zh": (
                f"应用号 {lim.get('application_number') or '未读到'}，"
                f"签发 {lim.get('issued_at') or lim.get('parsed', {}).get('issued_raw') or '未读到'}。"
                "只使用文字层；附图、管网图和许可扫描页未识别。"
            ),
            "source_name": lim.get("filename") or "客户上传 LIM",
            "source_url": LIM_ABOUT_URL,
        }
    ]
    constraints = lim.get("constraints") or {}
    parsed = lim.get("parsed") or {}
    if constraints.get("overland_flow"):
        items.append(
            {
                "id": "lim_olfp",
                "severity": "constraint",
                "title_zh": "正式 LIM：地面径流与本户相交",
                "body_zh": (
                    "正文写明地块与 Overland Flow Path 空间相交。不是禁建。"
                    "开发可能需要洪水评估；评估没有公开零售单价，已标缺项。"
                    + _evidence((parsed.get("overland_flow") or {}).get("evidence"))
                ),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    notices = parsed.get("drainage_notices") or []
    if notices:
        first = notices[0]
        items.append(
            {
                "id": "lim_drainage",
                "severity": "constraint",
                "title_zh": f"正式 LIM：{first.get('lir_id') or '管网通知'}",
                "body_zh": first.get("description") or "读到管网 LIR，但没有公开工程单价。",
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    wind = parsed.get("wind_zone") or {}
    if wind.get("label"):
        items.append(
            {
                "id": "lim_wind",
                "severity": "info",
                "title_zh": f"正式 LIM 风区 {wind['label']}",
                "body_zh": (
                    (f"{wind['speed_mps']} m/s。" if wind.get("speed_mps") is not None else "")
                    + "E2 计分仍按中等风区假设，未把该风区写入分值表。"
                ),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    return items


def _empty_constraints() -> dict[str, Any]:
    return {
        "flood": False,
        "overland_flow": False,
        "coastal_inundation": False,
        "landfill": False,
        "landslide": None,
        "contamination_data": None,
        "soil_issues": None,
        "drainage_notices": False,
    }


def _section(id_: str, heading_en: str, heading_zh: str, s44a: str, state: str, body_zh: str) -> dict[str, Any]:
    return {
        "id": id_,
        "heading_en": heading_en,
        "heading_zh": heading_zh,
        "s44a": s44a,
        "state": state,
        "body_zh": body_zh,
        "source_url": LIM_ABOUT_URL,
    }


def _evidence(text: str | None) -> str:
    clipped = (text or "").strip()
    if not clipped:
        return ""
    return f" 原文：{clipped[:280]}"
