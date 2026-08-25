from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .data_loader import council_fees
from .lim_parse import decorate_parsed

LIM_ORDER_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html"
)
LIM_ABOUT_URL = (
    "https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/"
    "about-property-files-and-lim-reports.html"
)

FLOODING_ALL_LIMS_ZH = (
    "Flooding 栏是每份 LIM 都会印的套话：附图上没有洪水，也不排除被地面径流淹没，尤其来自邻户。"
    "这段话本身不能证明本户已划进洪水平原，也不能证明不会淹。"
    "开发申请仍可能被要求交洪水评估。本页不识别附图，所以不知道淹没范围。"
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
    parsed = decorate_parsed(parsed)
    constraints = {
        "flood": False,
        "overland_flow": bool((parsed.get("overland_flow") or {}).get("intersects")),
        "coastal_inundation": False,
        "landfill": False,
        "landslide": None,
        "contamination_data": (parsed.get("site_contamination") or {}).get("has_regulatory_data"),
        "soil_issues": (parsed.get("soil_issues") or {}).get("council_aware"),
        "drainage_notices": bool(parsed.get("drainage_notices")),
        "blocks_further_development": any(
            item.get("blocks_further_development") for item in (parsed.get("drainage_notices") or [])
        ),
        "public_drain_clash": any(
            item.get("over_public_drainage") or item.get("bridging_public_drains")
            for item in (parsed.get("building_consents") or [])
        ),
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
        "disclaimer_zh": (
            "以下是按这份 LIM 文字层字段写出的开发影响，不是英文摘录。"
            "附图、管网图和许可扫描页未识别。"
        ),
        "order_url": LIM_ORDER_URL,
        "about_url": LIM_ABOUT_URL,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "layers": [],
        "constraints": constraints,
        "scheme_hints": list(dict.fromkeys(hints)),
        "findings": analyse_findings(parsed),
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


def analyse_findings(parsed: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    notices = parsed.get("drainage_notices") or []
    blocking = [item for item in notices if item.get("blocks_further_development")]
    if blocking:
        first = blocking[0]
        year = _year(first.get("date"))
        when = f"{year} 年的管网通知" if year else "管网通知"
        pipe = "公共雨水管容量不够时，" if first.get("stormwater_capacity") else ""
        findings.append(
            f"{when} {first.get('lir_id') or ''} 限制继续开发：{pipe}"
            "继续加密、再细分或新接驳很可能被开发工程师拦住。"
            "原址按现状重建算不算继续开发，要以议会当场意见为准；本页不把整块地标成禁建。"
        )
    elif notices:
        findings.append(
            "读到管网通知，后续接驳或开挖前要问开发工程师。相关工程没有公开单价。"
        )
    if (parsed.get("overland_flow") or {}).get("intersects"):
        findings.append(
            "地块与地面径流路径相交，不是禁建。"
            "路径上或紧邻的填挖、建房可能触发规划规则，开发申请常要交洪水评估；评估没有公开单价。"
        )
    subs = parsed.get("subdivision_consents") or []
    if subs:
        findings.append(_subdivision_impact(subs[0], parsed))
    consents = parsed.get("building_consents") or []
    clash = [item for item in consents if item.get("bridging_public_drains") or item.get("over_public_drainage")]
    if clash:
        ids = "、".join(item.get("id") or "" for item in clash if item.get("id"))
        findings.append(
            f"已有挡土或排水工程跨越公共雨污管（{ids}）。"
            "以后开挖、加高挡土或改车道要核管位，可能再办许可。"
        )
    wind = parsed.get("wind_zone") or {}
    label = (wind.get("label") or "").lower()
    if label == "low":
        findings.append("风区偏低，抗风不是主要加价点；外墙防水计分仍按中等风区假设，未改分值表。")
    elif label == "high":
        findings.append("风区偏高；外墙防水计分仍按中等风区假设，未改分值表，也不编抗风加价。")
    if (parsed.get("site_contamination") or {}).get("has_regulatory_data") is False:
        findings.append("监管记录没有污染数据，不等于场地已清洁，本页不因此加污染调查费。")
    if parsed.get("engineering_approvals_recorded") is False:
        findings.append("没有读到工程批准记录，不能把场地管网工程当成已经议会签过。")
    return findings


def lim_sections_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = decorate_parsed(report.get("parsed") or {})
    status = report.get("status")
    if status != "parsed":
        awaiting = "请上传正式 LIM 后分析此栏对开发的影响。"
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
        contam_state = "recorded"
        contam_body = (
            "监管记录没有污染数据。这只说明议会档案里没有登记，不能写成这块地已清洁，"
            "也不能当成已做 HAIL 评估。本页不因此加污染场地调查费。"
        )
    elif contamination.get("has_regulatory_data"):
        contam_state = "recorded"
        contam_body = (
            "监管记录写有污染相关内容。后续开发可能要走土壤污染条例；"
            "初步场地调查没有公开零售单价，已标缺项。本页不根据这段文字判断污染等级。"
        )
    else:
        contam_state, contam_body = "not_stated", "文字层没有读到场地污染结论，不能按无污染核算。"

    wind = parsed.get("wind_zone") or {}
    label = wind.get("label")
    if label:
        speed = f"（{wind['speed_mps']} m/s）" if wind.get("speed_mps") is not None else ""
        wind_state = "recorded"
        lowered = str(label).lower()
        if lowered == "low":
            wind_body = (
                f"议会按 NZS 3604 把本户划为低风区{speed}。抗风加固通常不是本户主要加价点。"
                "外墙防水计分仍按中等风区假设，可能偏保守；没有把议会风区写进公开分值表，所以不改金额。"
            )
        elif lowered == "high":
            wind_body = (
                f"议会按 NZS 3604 把本户划为高风区{speed}。"
                "外墙防水计分仍按中等风区假设，可能偏松；没有把议会风区写进公开分值表，所以不改金额，也不编抗风加价。"
            )
        else:
            wind_body = (
                f"议会按 NZS 3604 把本户划为{label}风区{speed}。"
                "外墙防水计分也按中等风区假设，仍不改分值表。"
            )
    else:
        wind_state, wind_body = "not_stated", "文字层没有读到风区，不能据此调整抗风或外墙防水假设。"

    soil = parsed.get("soil_issues") or {}
    if soil.get("council_aware") is False:
        soil_state = "recorded"
        soil_body = (
            "议会不知本户有土壤问题。这不能代替地勘，开挖时仍可能遇到填土或软弱层。"
            "本页不因此加岩土报告费。"
        )
    elif soil.get("council_aware"):
        soil_state = "recorded"
        soil_body = "议会写有土壤问题。岩土报告没有公开零售单价，已标缺项。本页不根据这段文字判断要挖多深。"
    else:
        soil_state, soil_body = "not_stated", "文字层没有读到土壤结论，不能省略地勘。"

    flooding = parsed.get("flooding") or {}
    flood_body = FLOODING_ALL_LIMS_ZH
    flood_state = "recorded" if flooding.get("all_lims_statement") or flooding.get("evidence") else "not_stated"

    olfp = parsed.get("overland_flow") or {}
    if olfp.get("intersects") is True:
        olfp_state = "recorded"
        olfp_body = (
            "地块与地面径流路径空间相交，不是禁建。"
            "路径上或紧邻的填挖、建房可能触发 Unitary Plan；开发申请常要交洪水评估。"
            "评估没有公开零售单价，已标缺项。本页不识别附图，所以不知道路径从哪一侧穿过、宽度多少。"
        )
    elif olfp.get("intersects") is False:
        olfp_state = "recorded"
        olfp_body = "正文没有写明本户与地面径流路径相交。不等于场地不会积水。附图未读。"
    else:
        olfp_state = "not_stated"
        olfp_body = "没有读到地面径流是否与本户相交。附图未读，不能用公开图层代替。"

    exposure = parsed.get("exposure_zone") or {}
    if exposure.get("unassessed") or (
        exposure.get("label") and re.search(r"unknown|unassessed", str(exposure.get("label")), re.I)
    ):
        exposure_state = "recorded"
        exposure_body = "腐蚀分区未评定。不能据此提高或降低耐久性加价，也不编更高腐蚀区材料费。"
    elif exposure.get("label"):
        exposure_state = "recorded"
        exposure_body = (
            f"腐蚀分区为 {exposure['label']}。本页没有把腐蚀区写进公开价表，所以不改金额。"
        )
    else:
        exposure_state, exposure_body = "not_stated", "文字层没有读到腐蚀分区，不能据此改材料假设。"

    coastal = parsed.get("coastal_erosion") or {}
    coastal_body = (
        "海岸侵蚀说明每份 LIM 都有。侵蚀线在附图上，本页不识别像素，"
        "因此不把本户当成已划入侵蚀风险区，也不因此禁建。"
    )
    coastal_state = "recorded" if coastal.get("evidence") or coastal.get("standard_text_only") else "not_stated"

    notices = parsed.get("drainage_notices") or []
    if notices:
        drain_state = "recorded"
        drain_body = " ".join(_drainage_impact(item) for item in notices[:3])
        if parsed.get("engineering_approvals_recorded") is False:
            drain_body += " 没有读到工程批准记录，不能把管网工程当成已经议会签过。"
    else:
        drain_state = "not_stated"
        drain_body = "没有读到管网通知编号。私有排水接到公共管仍由业主负责，不等于管网没有限制。"

    consent_body = _consents_impact(parsed)
    consent_state = "recorded" if consent_body else "not_stated"
    if not consent_body:
        consent_body = "文字层没有抽出建工许可或细分记录。公开区划不能代替这份清单。"

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
            "title_zh": "已按正式 LIM 分析开发影响",
            "body_zh": (
                f"应用号 {lim.get('application_number') or '未读到'}，"
                f"签发 {lim.get('issued_at') or lim.get('parsed', {}).get('issued_raw') or '未读到'}。"
                "下面各条是字段推导，不是 LIM 英文摘录。附图、管网图和许可扫描页未识别。"
            ),
            "source_name": lim.get("filename") or "客户上传 LIM",
            "source_url": LIM_ABOUT_URL,
        }
    ]
    parsed = decorate_parsed(lim.get("parsed") or {})
    constraints = lim.get("constraints") or {}
    notices = parsed.get("drainage_notices") or []
    blocking = [item for item in notices if item.get("blocks_further_development")]
    if blocking:
        items.append(
            {
                "id": "lim_drainage",
                "severity": "constraint",
                "title_zh": "雨水管可能卡住继续开发",
                "body_zh": _drainage_impact(blocking[0]),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    elif notices:
        items.append(
            {
                "id": "lim_drainage",
                "severity": "constraint",
                "title_zh": "读到管网通知",
                "body_zh": _drainage_impact(notices[0]),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    if constraints.get("overland_flow"):
        items.append(
            {
                "id": "lim_olfp",
                "severity": "constraint",
                "title_zh": "地面径流穿过本户，不是禁建",
                "body_zh": (
                    "路径上或紧邻的填挖、建房可能触发规划规则，开发申请常要交洪水评估。"
                    "评估没有公开零售单价，已标缺项。附图未读，所以不知道路径从哪一侧穿过。"
                ),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    subs = parsed.get("subdivision_consents") or []
    if subs:
        items.append(
            {
                "id": "lim_subdivision",
                "severity": "watch",
                "title_zh": "本址已经拆过户",
                "body_zh": _subdivision_impact(subs[0], parsed),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    clash = [
        item
        for item in (parsed.get("building_consents") or [])
        if item.get("bridging_public_drains") or item.get("over_public_drainage")
    ]
    if clash:
        items.append(
            {
                "id": "lim_public_drains",
                "severity": "watch",
                "title_zh": "挡土或排水工程压着公共管",
                "body_zh": _consent_impact(clash[0]),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    wind = parsed.get("wind_zone") or {}
    if (wind.get("label") or "").lower() == "low":
        items.append(
            {
                "id": "lim_wind",
                "severity": "info",
                "title_zh": "风区偏低，不是主要加价点",
                "body_zh": (
                    f"议会划为低风区{('（' + str(wind['speed_mps']) + ' m/s）') if wind.get('speed_mps') is not None else ''}。"
                    "外墙防水计分仍按中等风区假设，可能偏保守，未改分值表。"
                ),
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    elif wind.get("label"):
        items.append(
            {
                "id": "lim_wind",
                "severity": "info",
                "title_zh": f"风区 {wind['label']}",
                "body_zh": "外墙防水计分仍按中等风区假设，没有把议会风区写进公开分值表，所以不改金额。",
                "source_name": lim.get("filename"),
                "source_url": LIM_ABOUT_URL,
            }
        )
    return items


def _drainage_impact(item: dict[str, Any]) -> str:
    lir = item.get("lir_id") or "管网通知"
    year = _year(item.get("date"))
    age = f"{year} 年留下的 {lir}" if year else lir
    if item.get("blocks_further_development") and item.get("stormwater_capacity"):
        return (
            f"{age} 指向公共雨水管容量不足时不得继续开发。"
            "继续加密、再细分或新接驳很可能被开发工程师拦住。"
            "原址按现状重建算不算「继续开发」，要以议会当场意见为准；本页不把整块地标成禁建。"
            "雨水管升级没有公开工程单价，已标缺项。"
        )
    if item.get("blocks_further_development"):
        return (
            f"{age} 限制继续开发。继续加密或再细分可能被拦住；"
            "本页不把整块地标成禁建。相关工程没有公开单价，已标缺项。"
        )
    if item.get("refer_development_engineer"):
        return f"{age} 要求先问开发工程师。接驳或改管没有公开工程单价，已标缺项。"
    return f"读到{age}。后续接驳或开挖前要核议会档案；没有公开工程单价，已标缺项。"


def _consent_impact(item: dict[str, Any]) -> str:
    ident = item.get("id") or "建工许可"
    facts: list[str] = []
    if item.get("retaining_wall"):
        facts.append("车道旁有挡土墙" if item.get("adjacent_driveway") else "有挡土墙")
    if item.get("timber_pole_retaining"):
        facts.append("另有木桩挡土")
    if item.get("bridging_public_drains") or item.get("over_public_drainage"):
        facts.append("跨越公共雨污管")
    if item.get("private_drainage_redirection"):
        facts.append("改过私有排水")
    lead = "、".join(facts) if facts else "有建工许可记录"
    if item.get("bridging_public_drains") or item.get("over_public_drainage"):
        return (
            f"读到建工许可 {ident}：{lead}。"
            "以后开挖、加高挡土或改车道要核公共管位，可能再办许可。"
            "管线改迁没有公开单价，已标缺项。"
        )
    extra = "已发完工证明。" if item.get("completion_issued") else ""
    return f"读到建工许可 {ident}：{lead}。{extra}改扩建要核原许可范围。"


def _crossing_impact(item: dict[str, Any]) -> str:
    ident = item.get("id") or "车辆出入口"
    done = "已发完工证明。" if item.get("completion_issued") else ""
    return (
        f"读到车辆出入口 {ident}。{done}"
        "改位置或宽度可能再向 Auckland Transport 申请；现有出入口不保证能服务加密后的车位。"
    )


def _subdivision_impact(item: dict[str, Any], parsed: dict[str, Any]) -> str:
    ident = item.get("id") or ""
    lots = item.get("lot_count")
    tenure = "独立产权" if item.get("tenure") == "freehold" else ""
    if lots:
        phrase = f" {lots} 户{tenure}"
    elif tenure:
        phrase = tenure
    else:
        phrase = ""
    done = "并已发 224C 完工证明。" if item.get("s224c") else "已获批。"
    legal = parsed.get("legal_description")
    title = f"当前地籍是 {legal}，是拆完后的其中一户，不是整宗再加总。" if legal else "当前核算的是拆完后的这一户，不是整宗再加总。"
    eng = ""
    if parsed.get("engineering_approvals_recorded") is False:
        eng = "没有读到工程批准记录；结合雨水管通知，继续加密或再细分仍可能卡在管网。"
    return f"本址已完成{phrase}细分（申请号 {ident}），{done}{title}{eng}"


def _consents_impact(parsed: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in parsed.get("subdivision_consents") or []:
        parts.append(_subdivision_impact(item, parsed))
    for item in (parsed.get("building_consents") or [])[:6]:
        parts.append(_consent_impact(item))
    for item in (parsed.get("vehicle_crossings") or [])[:4]:
        parts.append(_crossing_impact(item))
    if parsed.get("weathertight_notified") is False:
        parts.append("议会未收到渗漏住宅法第 124 条通知。这不排除隐性渗漏，也不能当成房屋完好证明。")
    return " ".join(part for part in parts if part)


def _year(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", value)
    return match.group(0) if match else None


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
        "blocks_further_development": False,
        "public_drain_clash": False,
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
