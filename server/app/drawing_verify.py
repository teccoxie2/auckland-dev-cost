from __future__ import annotations

from typing import Any

from .costing import WINDOW_ITEMS, cost_option
from .data_loader import pricebook
from .drawing_flow import template_from_extract
from .drawing_llm import (
    BLOCKED_ITEM_IDS,
    ALLOWED_ZONES,
    call_drawing_llm,
    combined_drawing_text,
    evidence_in_source,
    full_drawing_text,
    ground_fields,
    ground_windows,
    llm_configured,
    llm_model_name,
    looks_like_price,
    number_in_text,
)
from .drawing_parse import merge_extracts, merge_window_lists, windows_from_charts
from .price_provider import pricebook_meta
from .pricing import line, missing_line
from .quantity import takeoff

ZONE_DEFS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("foundation", "筏板与基础", ("concrete_", "expol_", "drawing_area_unknown")),
    ("structure", "木结构", ("timber_sg8", "framing_labour")),
    ("interior", "室内衬板", ("gib_",)),
    ("envelope", "外墙保温与空腔", ("pink_batts", "cavity_")),
    ("roof", "屋面", ("roofing_",)),
    ("joinery", "门窗", ("window_", "door_", "joinery_")),
    ("kitchen", "厨房", ("kaboodle_", "sink_", "oven_", "tap_mondella", "plumber_prepipe_kitchen", "kitchen_")),
    (
        "bathroom",
        "卫生间",
        (
            "toilet_",
            "shower_",
            "tap_caroma",
            "membrane_",
            "plumber_prepipe_bathroom",
            "plumber_fitoff",
            "bathroom_",
        ),
    ),
    ("plumbing", "整栋给排水", ("plumber_prepipe_mains",)),
    ("scaffold", "外围脚手架", ("scaffolding_",)),
    ("retaining", "挡土与室外", ("retaining_", "pile_h5", "geotextile")),
)

NO_ZONING = {"status": "permitted", "needs_resource_consent": False, "reasons": []}

ITEM_QTY_KEYS = {
    "timber_sg8_90x45_h12": "timber_90_lm",
    "timber_sg8_140x45_h12": "timber_140_lm",
    "cavity_batten_h31_45x20": "batten_lm",
    "gib_std_10mm": "gib_m2",
    "pink_batts_r22_wall": "insulation_m2",
    "roofing_corrugate_colour_845": "roof_sheet_lm",
    "concrete_readymix_20mpa": "slab_m3",
    "framing_labour_gfa": "gfa_m2",
    "expol_tuffpod_1100x300": "pod_count",
    "kaboodle_base_600": "kitchen_base_600",
    "kaboodle_wall_600": "kitchen_wall_600",
    "kaboodle_door_600_seasalt": "kitchen_door_600",
    "kaboodle_benchtop_2400x600": "kitchen_bench_2400",
    "scaffolding_perimeter_erect": "external_wall_m2",
    "scaffolding_perimeter_hire_week": "external_wall_m2",
}

ITEM_COUNT_KEYS = {
    "sink_mondella_concerto": "kitchens",
    "oven_bellini_60_pack": "kitchens",
    "tap_mondella_resonance_kitchen": "kitchens",
    "plumber_prepipe_kitchen": "kitchens",
    "toilet_stein_ero": "bathrooms",
    "shower_stein_georgia_750": "bathrooms",
    "tap_caroma_luna_shower": "bathrooms",
    "tap_caroma_luna_basin": "bathrooms",
    "membrane_crommelin_4l": "bathrooms",
    "plumber_fitoff_toilet": "bathrooms",
    "plumber_fitoff_shower": "bathrooms",
    "plumber_fitoff_basin": "bathrooms",
    "plumber_prepipe_mains": "dwellings",
}

ITEM_FORMULAS = {
    "timber_sg8_90x45_h12": "立柱+墙板延米（含10%损耗）= (周长/间距×层数 + 8) × 层高 + 3×周长×层数",
    "timber_sg8_140x45_h12": "宽推拉门或过梁加强时增加 140×45",
    "cavity_batten_h31_45x20": "外墙面积 / 0.6m 间距",
    "gib_std_10mm": "内衬面积 × 1.15 损耗，并扣门窗洞口",
    "pink_batts_r22_wall": "外墙面积 × 1.08 损耗",
    "roofing_corrugate_colour_845": "屋面斜面积 / 0.762m 覆盖宽 × 1.10 损耗",
    "concrete_readymix_20mpa": "底层占地 × 85mm 面层 × 1.05 损耗",
    "framing_labour_gfa": "GFA × 框架安装公开区间中位",
    "expol_tuffpod_1100x300": "占地长宽按 1.2m 网格取整格子数",
    "kaboodle_base_600": "每套厨房 5 个 600mm 地柜",
    "kaboodle_wall_600": "每套厨房 5 个 600mm 吊柜",
    "kaboodle_door_600_seasalt": "每套厨房 10 扇 600mm 门板",
    "kaboodle_benchtop_2400x600": "每套厨房 2 块 2400×600 台面",
    "sink_mondella_concerto": "每套厨房 1 个水槽",
    "oven_bellini_60_pack": "每套厨房 1 套烤箱电灶包",
    "tap_mondella_resonance_kitchen": "每套厨房 1 套厨房龙头",
    "plumber_prepipe_kitchen": "每套厨房 1 个给排水点",
    "toilet_stein_ero": "卫生间数量 × 马桶套装",
    "shower_stein_georgia_750": "卫生间数量 × 淋浴房",
    "tap_caroma_luna_shower": "卫生间数量 × 淋浴混水阀",
    "tap_caroma_luna_basin": "卫生间数量 × 面盆龙头",
    "membrane_crommelin_4l": "卫生间数量 × 防水涂料",
    "plumber_prepipe_bathroom": "每间卫生间 3 个给排水点",
    "plumber_prepipe_mains": "住宅单元数 × 主进出水",
    "plumber_fitoff_toilet": "卫生间数量 × 马桶 fit-off",
    "plumber_fitoff_shower": "卫生间数量 × 淋浴 fit-off",
    "plumber_fitoff_basin": "卫生间数量 × 面盆 fit-off",
    "scaffolding_perimeter_erect": "外墙立面面积 × 搭拆运",
    "scaffolding_perimeter_hire_week": "外墙立面面积 × 最低 1 周租",
}


def zone_for_line(line_item: dict[str, Any]) -> tuple[str, str]:
    hinted = str(line_item.get("zone") or "")
    if hinted in ALLOWED_ZONES:
        label = next((name for zone_id, name, _ in ZONE_DEFS if zone_id == hinted), "未能分区")
        return hinted, label
    line_id = str(line_item.get("id") or "")
    for zone_id, label, prefixes in ZONE_DEFS:
        if any(line_id.startswith(prefix) or line_id == prefix.rstrip("_") for prefix in prefixes):
            return zone_id, label
    return "other", "未能分区"


def group_lines_by_zone(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in lines:
        zone_id, label = zone_for_line(row)
        if zone_id not in buckets:
            buckets[zone_id] = {
                "id": zone_id,
                "name_zh": label,
                "lines": [],
                "priced_incl_gst": 0.0,
                "missing_count": 0,
            }
            order.append(zone_id)
        bucket = buckets[zone_id]
        item = {**row, "zone": zone_id, "zone_name_zh": label}
        bucket["lines"].append(item)
        if item.get("status") == "missing":
            bucket["missing_count"] += 1
        elif item.get("status") in {"priced", "rule", "zero"}:
            bucket["priced_incl_gst"] = round(
                float(bucket["priced_incl_gst"]) + float(item.get("amount_incl_gst") or 0),
                2,
            )
    preferred = [zone_id for zone_id, _, _ in ZONE_DEFS if zone_id in buckets]
    rest = [zone_id for zone_id in order if zone_id not in preferred]
    return [buckets[zone_id] for zone_id in [*preferred, *rest]]


def field_values(fields: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, item in fields.items():
        if not isinstance(item, dict) or "value" not in item:
            continue
        rows.append(
            {
                "key": key,
                "value": item["value"],
                "evidence": item.get("evidence"),
                "source_file": item.get("source_file"),
            }
        )
    return rows


def merge_field_maps(regex_fields: dict[str, Any] | None, llm_fields: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(regex_fields or {})
    merged.update(llm_fields or {})
    return merged


def item_name_zh(item_id: str) -> str:
    book = pricebook()
    for item in book.get("items") or []:
        if item.get("id") == item_id:
            return str(item.get("name_zh") or item_id)
    for item in book.get("missing_on_purpose") or []:
        if item.get("id") == item_id:
            return str(item.get("name_zh") or item_id)
    return item_id


def totals_from_lines(lines: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [item for item in lines if item.get("status") == "missing"]
    construction = round(
        sum(
            float(item.get("amount_incl_gst") or 0)
            for item in lines
            if item.get("status") in {"priced", "rule", "zero"}
        ),
        2,
    )
    meta = pricebook_meta()
    return {
        "construction_confirmed_incl_gst": construction,
        "confirmed_total_incl_gst": construction,
        "missing_count": len(missing),
        "pricebook_version": meta.get("version"),
        "price_as_of": meta.get("as_of"),
    }


def known_item_ids() -> set[str]:
    book = pricebook()
    ids = {str(item["id"]) for item in book.get("items") or []}
    ids.update(str(item["id"]) for item in book.get("missing_on_purpose") or [])
    return ids


def missing_reason(item_id: str) -> str:
    for item in pricebook().get("missing_on_purpose") or []:
        if item.get("id") == item_id:
            return str(item.get("reason") or "价库将该科目标为缺项。")
    return "公开零售没有这一条目的单价，工程量已列出但不计价。"


def text_layer_ok(parts: list[dict[str, Any]]) -> bool:
    return any(int(part.get("char_count") or 0) >= 80 or len(str(part.get("text") or "").strip()) >= 80 for part in parts)


def documents_public(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for part in parts:
        rows.append(
            {
                "kind": part.get("kind"),
                "filename": part.get("filename"),
                "page_count": part.get("page_count"),
                "char_count": part.get("char_count"),
                "error": part.get("error"),
            }
        )
    return rows


def drawing_audit(
    parts: list[dict[str, Any]],
    merged: dict[str, Any],
    packed_text: str,
    full_text: str,
    windows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    page_debug = merged.get("page_debug") or []
    charts = merged.get("charts") or []
    window_rows = [
        row
        for chart in charts
        if chart.get("id") == "window_schedule"
        for row in (chart.get("rows") or [])
    ]
    openings = windows if windows is not None else (merged.get("windows") or [])
    return {
        "page_count": sum(int(part.get("page_count") or 0) for part in parts) or len(page_debug),
        "char_count": sum(int(part.get("char_count") or 0) for part in parts),
        "full_chars": len(full_text or ""),
        "sent_chars": len(packed_text or ""),
        "no_text_pages": sum(1 for item in page_debug if item.get("role") == "drawing_no_text"),
        "schedule_pages": sum(1 for item in page_debug if item.get("role") == "schedule"),
        "chart_count": len(charts),
        "chart_rows": sum(len(chart.get("rows") or []) for chart in charts),
        "window_schedule_rows": len(window_rows),
        "window_count": sum(int(item.get("count") or 0) for item in openings),
    }


def coverage_from_audit(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "page_count": audit.get("page_count"),
        "char_count": audit.get("char_count"),
        "sent_chars": audit.get("sent_chars"),
        "full_chars": audit.get("full_chars"),
        "no_text_pages": audit.get("no_text_pages"),
        "chart_rows": audit.get("chart_rows"),
        "note": (
            "只读文字层。图表按行列抽出，不依赖模型才看见表行。"
            "送给模型的字符数可能少于全文，优先保留门窗表和面积页。"
            "几乎无文字的图页不做图像识别，也不猜毫米。"
        ),
    }


def verify_drawing_parts_rules(parts: list[dict[str, Any]]) -> dict[str, Any]:
    merged = merge_extracts(parts)
    packed = combined_drawing_text(parts)
    full_text = full_drawing_text(parts) or packed
    if not merged["enough_to_cost"]:
        return {
            "error": {
                "code": "drawing_empty",
                "message": "图纸文字层里没有可核对的建筑面积或门窗表。扫描件无法量尺寸，请上传可选中文字的 RC/BC PDF。",
            },
            "extracted": merged,
            "charts": merged.get("charts") or [],
            "page_debug": merged.get("page_debug") or [],
            "audit": drawing_audit(parts, merged, packed, full_text),
        }
    template = template_from_extract(merged, {})
    cost = cost_option(template, NO_ZONING, site={}, include_overheads=False)
    zones = group_lines_by_zone(cost["lines"])
    n_win = sum(int(item["count"]) for item in merged.get("windows") or [])
    fields = merged.get("fields") or {}
    bits = ["对照路径：正则读文字层图表每一行，再按固定公式展开材料，不含议会法定费用。"]
    if fields.get("gfa_m2"):
        bits.append(f"建筑面积 {fields['gfa_m2']['value']} m²。")
    elif fields.get("footprint_m2"):
        bits.append(f"占地 {fields['footprint_m2']['value']} m²。")
    if n_win:
        bits.append(f"门窗表 {n_win} 樘。")
    bits.append("对不上公开 SKU 的科目标缺项，不编单价。")
    audit = drawing_audit(parts, merged, packed, full_text, merged.get("windows") or [])
    return {
        "error": None,
        "explanation": "".join(bits),
        "documents": merged.get("documents") or [],
        "fields": field_values(fields),
        "windows": merged.get("windows") or [],
        "charts": merged.get("charts") or [],
        "page_debug": merged.get("page_debug") or [],
        "audit": audit,
        "coverage": coverage_from_audit(audit),
        "warnings": merged.get("warnings") or [],
        "quantities": cost["quantities"],
        "zones": zones,
        "totals": cost["totals"],
        "template": {
            "name_zh": template.get("name_zh"),
            "gfa_m2": template.get("gfa_m2"),
            "gfa_missing": template.get("gfa_missing"),
            "storeys": template.get("storeys"),
            "kitchens": template.get("kitchens"),
            "bathrooms": template.get("bathrooms"),
            "dwellings": template.get("dwellings"),
        },
    }


def verify_drawing_parts(parts: list[dict[str, Any]], *, llm_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    rule_compare = verify_drawing_parts_rules(parts)
    merged = merge_extracts(parts)
    packed = combined_drawing_text(parts)
    source_text = full_drawing_text(parts) or packed
    if not text_layer_ok(parts):
        return {
            "error": {
                "code": "drawing_empty",
                "message": "图纸文字层里没有可核对的正文。扫描件无法量尺寸，也不会送给大模型猜毫米。",
            },
            "documents": documents_public(parts),
            "derivation": "llm",
            "charts": merged.get("charts") or [],
            "page_debug": merged.get("page_debug") or [],
            "audit": drawing_audit(parts, merged, packed, source_text),
        }
    if llm_payload is None:
        if not llm_configured():
            return {
                "error": {
                    "code": "llm_unavailable",
                    "message": "未配置 CPA_API_KEY / OPENAI_API_KEY，无法用大模型做本页材料推导。设置密钥后重试；金额仍只走价库。",
                },
                "documents": documents_public(parts),
                "derivation": "llm",
                "charts": merged.get("charts") or [],
                "page_debug": merged.get("page_debug") or [],
                "audit": drawing_audit(parts, merged, packed, source_text),
                "llm": {"status": "unavailable", "model": None, "note": "缺密钥时不编造材料清单。"},
            }
        called = call_drawing_llm(packed, charts=merged.get("charts") or [])
        if not called.get("ok"):
            return {
                "error": called.get("error")
                or {"code": "llm_failed", "message": "大模型读取图纸失败。"},
                "documents": documents_public(parts),
                "derivation": "llm",
                "charts": merged.get("charts") or [],
                "page_debug": merged.get("page_debug") or [],
                "audit": drawing_audit(parts, merged, packed, source_text),
                "llm": {"status": "failed", "model": llm_model_name(), "note": "模型调用失败，未编造材料或金额。"},
            }
        model = called.get("model")
        llm_payload = called.get("payload") or {}
    else:
        model = llm_model_name()
    built = build_llm_result(parts, source_text, llm_payload, model=model, packed_text=packed)
    if built.get("error"):
        return built
    if rule_compare.get("error") is None:
        built["rule_compare"] = {
            "explanation": rule_compare.get("explanation"),
            "fields": rule_compare.get("fields"),
            "windows": rule_compare.get("windows"),
            "zones": rule_compare.get("zones"),
            "totals": rule_compare.get("totals"),
            "template": rule_compare.get("template"),
        }
    else:
        built["rule_compare"] = {"error": rule_compare["error"]}
    return built


def build_llm_result(
    parts: list[dict[str, Any]],
    source_text: str,
    payload: dict[str, Any],
    *,
    model: str | None,
    packed_text: str | None = None,
) -> dict[str, Any]:
    rejected: list[dict[str, Any]] = []
    regex = merge_extracts(parts)
    packed = packed_text if packed_text is not None else combined_drawing_text(parts)
    fields, field_rejected = ground_fields(payload.get("fields"), source_text)
    windows, window_rejected = ground_windows(payload.get("windows"), source_text)
    rejected.extend(field_rejected)
    rejected.extend(window_rejected)
    fields = merge_field_maps(regex.get("fields"), fields)
    windows = merge_window_lists(regex.get("windows"), windows)
    window_sources = {item.get("source_file") for item in (regex.get("windows") or []) if item.get("source_file")}
    chart_windows = [
        item
        for item in windows_from_charts(regex.get("charts"))
        if not window_sources or item.get("source_file") in window_sources
    ]
    windows = merge_window_lists(windows, chart_windows)
    warnings = [item for item in (regex.get("warnings") or []) if item and item != "no_window_schedule"]
    audit = drawing_audit(parts, regex, packed, source_text, windows)
    debug = {
        "charts": regex.get("charts") or [],
        "page_debug": regex.get("page_debug") or [],
        "audit": audit,
        "coverage": coverage_from_audit(audit),
    }
    if not fields and not windows:
        return {
            "error": {
                "code": "llm_ungrounded",
                "message": "大模型与正则都没有在图纸文字层对上面积、户型或门窗表。未编造材料。",
            },
            "documents": documents_public(parts),
            "derivation": "llm",
            **debug,
            "llm": {
                "status": "ungrounded",
                "model": model,
                "rejected": rejected,
                "note": "证据句必须能在 PDF 文字层找到。扫描件没有文字层时无法读表。",
            },
        }
    extracted = {"fields": fields, "windows": windows}
    template = template_from_extract(extracted, {})
    qty = takeoff(template, {})
    qty["dwellings"] = int(template.get("dwellings") or 1)
    priced_lines, line_rejected, line_warnings = price_llm_selection(
        payload,
        source_text,
        qty,
        windows,
        template,
    )
    rejected.extend(line_rejected)
    warnings.extend(line_warnings)
    if not priced_lines:
        return {
            "error": {
                "code": "llm_ungrounded",
                "message": "大模型选出的材料无法对应价库或原文证据。未编造清单。",
            },
            "documents": documents_public(parts),
            "derivation": "llm",
            **debug,
            "llm": {"status": "ungrounded", "model": model, "rejected": rejected},
        }
    summary = payload.get("summary_zh") if isinstance(payload.get("summary_zh"), str) else ""
    if looks_like_price(summary):
        summary = ""
    n_win = sum(int(item["count"]) for item in windows)
    bits = [
        "本页用大模型读 PDF 文字层，并与正则全文及图表行抽取合并。送给模型的是门窗表/面积页优先，接地核对应全文。",
        "数量由服务器按公式、门窗表或原文件数重算，单价只走公开价库，模型不得定价。",
        "模型未点名但已读到面积/厨卫/门窗的科目，会按价库公式补全，不会用图像识别猜毫米。",
    ]
    if fields.get("gfa_m2"):
        bits.append(f"读到建筑面积 {fields['gfa_m2']['value']} m²。")
    elif fields.get("footprint_m2"):
        bits.append(f"读到占地 {fields['footprint_m2']['value']} m²。")
    if n_win:
        bits.append(f"门窗表 {n_win} 樘。")
    if audit.get("no_text_pages"):
        bits.append(f"有 {audit['no_text_pages']} 页几乎无文字层，图面尺寸未读取。")
    if summary:
        bits.append(summary.strip())
    return {
        "error": None,
        "derivation": "llm",
        "explanation": "".join(bits),
        "documents": documents_public(parts),
        "coverage": debug["coverage"],
        "charts": debug["charts"],
        "page_debug": debug["page_debug"],
        "audit": audit,
        "fields": field_values(fields),
        "windows": windows,
        "warnings": list(dict.fromkeys(warnings)),
        "quantities": qty,
        "zones": group_lines_by_zone(priced_lines),
        "totals": totals_from_lines(priced_lines),
        "template": {
            "name_zh": template.get("name_zh"),
            "gfa_m2": template.get("gfa_m2"),
            "gfa_missing": template.get("gfa_missing"),
            "storeys": template.get("storeys"),
            "kitchens": template.get("kitchens"),
            "bathrooms": template.get("bathrooms"),
            "dwellings": template.get("dwellings"),
        },
        "llm": {
            "status": "ok",
            "model": model,
            "summary_zh": summary.strip() or None,
            "rejected": rejected,
            "note": "模型金额已丢弃。门窗表与面积已和正则全文、图表行合并；公式科目会补上模型没点名的行。",
        },
    }


def price_llm_selection(
    payload: dict[str, Any],
    source_text: str,
    qty: dict[str, Any],
    windows: list[dict[str, Any]],
    template: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []
    known = known_item_ids()
    raw_lines = payload.get("lines") if isinstance(payload.get("lines"), list) else []
    priced: list[dict[str, Any]] = []
    seen: set[str] = set()

    joinery_lines = joinery_from_windows(windows)
    priced.extend(joinery_lines)
    seen.update(str(item["id"]) for item in joinery_lines)

    if not raw_lines:
        warnings.append("模型没有列出 SKU 行，面积/厨卫/门窗科目改由价库公式补全。")

    aliases = {
        "plumber_prepipe_kitchen": ("plumber_prepipe_fixture", "kitchen"),
        "plumber_prepipe_bathroom": ("plumber_prepipe_fixture", "bathroom"),
    }
    for raw in raw_lines:
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("item_id") or "").strip()
        evidence = str(raw.get("evidence") or "").strip()
        reason = str(raw.get("reason_zh") or "").strip()
        zone = str(raw.get("zone") or "").strip()
        if item_id in aliases:
            item_id, alias_zone = aliases[item_id]
            zone = zone or alias_zone
        if zone not in ALLOWED_ZONES:
            zone = ""
        if looks_like_price(reason):
            reason = ""
        if not item_id:
            rejected.append({"item_id": "line", "reason_zh": "材料行缺少 item_id。"})
            continue
        if item_id in BLOCKED_ITEM_IDS:
            rejected.append({"item_id": item_id, "reason_zh": "设计费/法定费用不在本页材料验证范围。"})
            continue
        if item_id not in known:
            rejected.append({"item_id": item_id, "reason_zh": "item_id 不在价库目录，已丢弃。"})
            continue
        if item_id.startswith("window_") or item_id.startswith("door_") or item_id.startswith("joinery_"):
            continue
        if not evidence_in_source(evidence, source_text):
            rejected.append({"item_id": item_id, "reason_zh": "材料证据未出现在图纸文字层，已丢弃。"})
            continue
        resolved = resolve_quantity(item_id, zone, raw.get("quantity"), qty, evidence, source_text)
        line_id = line_id_for(item_id, zone)
        if line_id in seen:
            continue
        if resolved is None:
            row = missing_line(
                line_id,
                item_name_zh(item_id),
                "图纸提到该科目，但没有可重算件数，也没有原文中的件数，故标缺项。",
            )
            row["zone"] = zone or None
            row["llm_reason_zh"] = reason or None
            priced.append(row)
            seen.add(line_id)
            continue
        quantity, formula, note = resolved
        if quantity <= 0:
            rejected.append({"item_id": item_id, "reason_zh": "按公式重算后数量为 0，未计价。"})
            continue
        extra = "数量已按公式、门窗表或原文件数由服务器重算，未采用无依据配比。"
        if reason:
            extra = f"{reason} {extra}"
        if note:
            extra = f"{extra} {note}"
        if item_id in {item["id"] for item in pricebook().get("missing_on_purpose") or []}:
            row = missing_line(line_id, item_name_zh(item_id), missing_reason(item_id), quantity=quantity)
            row["formula"] = formula
            row["zone"] = zone or None
            row["llm_reason_zh"] = reason or None
            priced.append(row)
            seen.add(line_id)
            continue
        row = line(item_id, quantity, formula=formula, extra_notes=extra, line_id=line_id)
        row["zone"] = zone or None
        row["llm_reason_zh"] = reason or None
        priced.append(row)
        seen.add(line_id)

    filled = 0
    fallback = cost_option(template, NO_ZONING, site={}, include_overheads=False)
    for item in fallback["lines"]:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in seen:
            continue
        item = {**item, "llm_reason_zh": "模型未点名，已按读到的面积/厨卫/门窗表用价库公式补全。"}
        priced.append(item)
        seen.add(item_id)
        filled += 1
    if filled:
        warnings.append(f"已按价库公式补全 {filled} 项模型未点名的面积/厨卫/门窗科目。")

    for raw in payload.get("unmapped") or []:
        if not isinstance(raw, dict):
            continue
        evidence = str(raw.get("evidence") or "").strip()
        name_zh = str(raw.get("name_zh") or "未列入价库的材料").strip()
        if not evidence:
            rejected.append({"item_id": name_zh, "reason_zh": "未映射项没有原文证据，未列入清单。"})
            continue
        if not evidence_in_source(evidence, source_text):
            rejected.append({"item_id": name_zh, "reason_zh": "未映射项的证据不在文字层。"})
            continue
        try:
            quantity = float(raw.get("quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        if quantity and not number_in_text(quantity, evidence):
            quantity = 0
        reason = str(raw.get("reason_zh") or missing_reason("window_joinery_unmatched"))
        if looks_like_price(reason):
            reason = "价库没有对应 SKU，标缺项。"
        priced.append(
            missing_line(
                f"unmapped_{len(priced)}",
                name_zh,
                reason,
                quantity=quantity,
                unit=str(raw.get("unit") or ""),
            )
        )

    if qty.get("cavity_required") and "cavity_closers_flashings" not in seen:
        priced.append(
            missing_line(
                "cavity_closers_flashings",
                "空腔防虫网与门窗泛水",
                "E2 空腔系统需要 cavity closer 和 flashing tape；检索当日无稳定公开 SKU。",
            )
        )
    return priced, rejected, warnings


def line_id_for(item_id: str, zone: str) -> str:
    if item_id == "plumber_prepipe_fixture" and zone == "kitchen":
        return "plumber_prepipe_kitchen"
    if item_id == "plumber_prepipe_fixture" and zone == "bathroom":
        return "plumber_prepipe_bathroom"
    return item_id


def resolve_quantity(
    item_id: str,
    zone: str,
    raw_quantity: Any,
    qty: dict[str, Any],
    evidence: str = "",
    source_text: str = "",
) -> tuple[float, str, str] | None:
    mapped_id = line_id_for(item_id, zone)
    if mapped_id == "plumber_prepipe_bathroom":
        bathrooms = int(qty.get("bathrooms") or 0)
        return float(bathrooms * 3), ITEM_FORMULAS["plumber_prepipe_bathroom"], ""
    if mapped_id == "plumber_prepipe_kitchen":
        return float(qty.get("kitchens") or 0), ITEM_FORMULAS["plumber_prepipe_kitchen"], ""
    if item_id in ITEM_QTY_KEYS:
        if item_id == "cavity_batten_h31_45x20" and not qty.get("cavity_required"):
            return None
        if qty.get("gfa_missing") and item_id in {
            "timber_sg8_90x45_h12",
            "timber_sg8_140x45_h12",
            "gib_std_10mm",
            "pink_batts_r22_wall",
            "roofing_corrugate_colour_845",
            "concrete_readymix_20mpa",
            "framing_labour_gfa",
            "expol_tuffpod_1100x300",
            "scaffolding_perimeter_erect",
            "scaffolding_perimeter_hire_week",
            "cavity_batten_h31_45x20",
        }:
            return None
        value = float(qty.get(ITEM_QTY_KEYS[item_id]) or 0)
        return value, ITEM_FORMULAS.get(item_id, "按图纸字段套价库公式"), "未采用模型填写的数量。"
    if mapped_id in ITEM_COUNT_KEYS:
        value = float(qty.get(ITEM_COUNT_KEYS[mapped_id]) or 0)
        return value, ITEM_FORMULAS.get(mapped_id, "按厨卫或套数计"), ""
    if item_id in ITEM_COUNT_KEYS:
        value = float(qty.get(ITEM_COUNT_KEYS[item_id]) or 0)
        return value, ITEM_FORMULAS.get(item_id, "按厨卫或套数计"), ""
    if item_id == "retaining_sleeper_h4_200x50":
        retaining = qty.get("retaining") or {}
        if not retaining.get("sleeper_ok"):
            return None
        return float(retaining.get("timber_lm") or 0), str(retaining.get("formula") or "挡土枕木"), ""
    if item_id == "pile_h5_125_2400":
        retaining = qty.get("retaining") or {}
        return float(retaining.get("posts") or 0), "挡土墙长度 / 1.2m 间距", ""
    if item_id == "geotextile_strol_50m":
        retaining = qty.get("retaining") or {}
        return float(retaining.get("geotextile_rolls") or 0), "墙面面积 / 50m² 每卷", ""
    return quantity_from_evidence(raw_quantity, evidence, source_text)


def quantity_from_evidence(
    raw_quantity: Any,
    evidence: str,
    source_text: str,
) -> tuple[float, str, str] | None:
    try:
        quantity = float(raw_quantity)
    except (TypeError, ValueError):
        return None
    if quantity <= 0 or quantity > 10_000:
        return None
    if not evidence_in_source(evidence, source_text):
        return None
    if not number_in_text(quantity, evidence):
        return None
    return quantity, "按文字层证据中的件数计，未编造数量。", "件数来自图纸原文，不是面积公式。"


def joinery_from_windows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    buckets: dict[str, dict[str, Any]] = {}
    for opening in windows:
        code = str(opening["code"])
        count = int(opening["count"])
        width = int(opening["w_mm"])
        height = int(opening["h_mm"])
        code_u = code.upper()
        is_hume_leaf = (
            800 <= width <= 920
            and 1960 <= height <= 2100
            and (code_u.startswith("ED") or code_u.startswith("D"))
        )
        if is_hume_leaf:
            item_id = "door_hume_nexus15_860"
            bucket = buckets.setdefault(
                item_id,
                {
                    "item_id": item_id,
                    "count": 0,
                    "codes": [],
                    "formula": "门扇宽 800–920、高 1960–2100 × Hume Nexus 15 门扇零售价",
                },
            )
            bucket["count"] += count
            bucket["codes"].append(code)
            continue
        item_id = WINDOW_ITEMS.get((width, height))
        if item_id:
            bucket = buckets.setdefault(
                item_id,
                {
                    "item_id": item_id,
                    "count": 0,
                    "codes": [],
                    "formula": f"{width}×{height}mm 公开新窗标价",
                },
            )
            bucket["count"] += count
            bucket["codes"].append(code)
        else:
            lines.append(
                missing_line(
                    f"joinery_{code}_{width}x{height}",
                    f"门窗 {code} {width}×{height}mm × {count}",
                    "公开零售没有这一精确尺寸的新窗/推拉门标价，工程量已列出但不计价。",
                    quantity=count,
                    unit="樘",
                )
            )
    for bucket in buckets.values():
        extra = "、".join(bucket["codes"][:8])
        if bucket["item_id"] == "door_hume_nexus15_860":
            extra_notes = f"门扇 1980×860，不是整樘含框。代码：{extra}"
        else:
            extra_notes = f"代码：{extra}"
        lines.append(
            line(
                bucket["item_id"],
                bucket["count"],
                formula=f"{bucket['formula']} × {bucket['count']}",
                extra_notes=extra_notes,
            )
        )
    return lines
