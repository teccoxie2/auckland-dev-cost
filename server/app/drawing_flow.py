from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .costing import cost_option
from .design import wrap_typology
from .drawing_parse import extract_pdf, infer_kind, merge_extracts
from .quantity import takeoff
from .zoning import filter_template


class DrawingState(TypedDict, total=False):
    site: dict
    rules: dict
    parts: list
    extracted: dict
    template: dict
    option: dict
    explanation: str
    trace: list
    error: dict


def _trace(state: DrawingState, node: str, detail: str) -> list[dict[str, Any]]:
    items = list(state.get("trace") or [])
    items.append({"node": node, "detail": detail})
    return items


def parse_node(state: DrawingState) -> dict[str, Any]:
    merged = merge_extracts(state.get("parts") or [])
    if not merged["enough_to_cost"]:
        return {
            "extracted": merged,
            "error": {
                "code": "drawing_empty",
                "message": "图纸文字层里没有可核对的建筑面积或门窗表。扫描件无法量尺寸，请上传可选中文字的 RC/BC PDF。",
            },
            "trace": _trace(state, "parse_drawings", "no usable quantities"),
        }
    n_win = sum(int(item["count"]) for item in merged.get("windows") or [])
    gfa = (merged.get("fields") or {}).get("gfa_m2", {}).get("value")
    return {
        "extracted": merged,
        "error": None,
        "trace": _trace(state, "parse_drawings", f"gfa={gfa}; windows={n_win}"),
    }


def template_node(state: DrawingState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    template = template_from_extract(state["extracted"], state.get("site") or {})
    return {"template": template, "trace": _trace(state, "drawing_template", template["name_zh"])}


def cost_node(state: DrawingState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    template = state["template"]
    rules = state["rules"]
    site = state["site"]
    verdict = filter_template(template, rules, site)
    option: dict[str, Any] = {
        "id": "drawings",
        "template": wrap_typology(template),
        "verdict": verdict,
        "why": template.get("why") or [],
        "recommended": verdict["status"] != "infeasible",
        "origin": "drawings",
        "drawing_extract": {
            "documents": state["extracted"].get("documents") or [],
            "fields": state["extracted"].get("fields") or {},
            "windows": state["extracted"].get("windows") or [],
            "warnings": state["extracted"].get("warnings") or [],
        },
    }
    if verdict["status"] != "infeasible":
        option["quantities"] = takeoff(template, site)
        option["cost"] = cost_option(template, verdict, existing_dwellings=1, site=site)
    return {"option": option, "trace": _trace(state, "drawing_cost", verdict["status"])}


def explain_node(state: DrawingState) -> dict[str, Any]:
    if state.get("error"):
        return {"explanation": state["error"]["message"]}
    extracted = state.get("extracted") or {}
    fields = extracted.get("fields") or {}
    windows = extracted.get("windows") or []
    n_win = sum(int(item["count"]) for item in windows)
    bits = ["第二阶段按 RC/BC 图纸文字层套价，不是户型模板估算，也没有用 YOLO 猜毫米。"]
    if fields.get("gfa_m2"):
        bits.append(f"建筑面积 {fields['gfa_m2']['value']} m²（{fields['gfa_m2']['evidence']}）。")
    elif fields.get("footprint_m2"):
        bits.append(f"占地 {fields['footprint_m2']['value']} m²（{fields['footprint_m2']['evidence']}）。")
    if n_win:
        bits.append(f"门窗表 {n_win} 樘。")
    if fields.get("stud_spacing_mm"):
        bits.append(f"立柱间距按图纸改为 {fields['stud_spacing_mm']['value']} mm。")
    mismatch = [item for item in extracted.get("warnings") or [] if "不一致" in item]
    bits.extend(mismatch)
    bits.append("金额仍只来自价库与官方费率，读不到的尺寸标缺项。")
    return {"explanation": "".join(bits), "trace": _trace(state, "drawing_explain", "drawing-brief")}


def build_drawing_graph():
    graph = StateGraph(DrawingState)
    graph.add_node("parse_drawings", parse_node)
    graph.add_node("drawing_template", template_node)
    graph.add_node("drawing_cost", cost_node)
    graph.add_node("drawing_explain", explain_node)
    graph.add_edge(START, "parse_drawings")
    graph.add_edge("parse_drawings", "drawing_template")
    graph.add_edge("drawing_template", "drawing_cost")
    graph.add_edge("drawing_cost", "drawing_explain")
    graph.add_edge("drawing_explain", END)
    return graph.compile()


DRAWING_WORKFLOW = build_drawing_graph()


def run_drawings(site: dict[str, Any], rules: dict[str, Any], parts: list[dict[str, Any]]) -> DrawingState:
    return DRAWING_WORKFLOW.invoke({"site": site, "rules": rules, "parts": parts, "trace": []})


def parse_files(saved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from pathlib import Path

    parts = []
    for item in saved:
        path = Path(item["path"])
        filename = item["filename"]
        kind = infer_kind(filename, item.get("kind"))
        parts.append(extract_pdf(path, kind=kind, filename=filename))
    return parts


def template_from_extract(extracted: dict[str, Any], site: dict[str, Any]) -> dict[str, Any]:
    fields = extracted.get("fields") or {}
    windows = [
        {"code": item["code"], "w_mm": int(item["w_mm"]), "h_mm": int(item["h_mm"]), "count": int(item["count"])}
        for item in extracted.get("windows") or []
    ]
    storeys = int(_value(fields, "storeys") or (len(_value(fields, "storey_heights_m") or []) or 1))
    footprint = _value(fields, "footprint_m2")
    gfa = _value(fields, "gfa_m2")
    gfa_missing = gfa is None and footprint is None
    gfa_derived = False
    if gfa is None and footprint:
        gfa = round(float(footprint) * storeys, 1)
        gfa_missing = False
        gfa_derived = True
    if gfa is None:
        gfa = 0.0
    dwellings = int(_value(fields, "dwellings") or 1)
    bathrooms = int(_value(fields, "bathrooms") or 0)
    kitchens = int(_value(fields, "kitchens") or 0)
    bedrooms = int(_value(fields, "bedrooms") or 0)
    wall_height = float(_value(fields, "wall_height_m") or 2.55)
    eaves = int(_value(fields, "eaves_mm") or 0)
    stud = int(_value(fields, "stud_spacing_mm") or 600)
    why = ["工程量来自上传图纸的文字层（门窗表/面积/层高），不是户型模板。"]
    for key in ("gfa_m2", "footprint_m2", "roof_m2", "wall_height_m", "eaves_mm", "stud_spacing_mm", "retaining_height_m"):
        item = fields.get(key)
        if item:
            why.append(f"{key}={item['value']} ← {item.get('evidence')}")
    if gfa_derived:
        why.append(f"GFA {gfa} m² ← 占地 {footprint} × {storeys} 层（图纸未写 GFA）。")
    if _value(fields, "cladding") == "block_veneer":
        why.append("图纸写明砌块贴面或 400mm 立柱间距，木材按 400mm 间距计。")
    parcel = site.get("parcel") or {}
    coverage = _value(fields, "coverage_pct")
    if coverage is not None and parcel.get("found") and parcel.get("area_m2") and footprint:
        cap = float(parcel["area_m2"]) * (float(coverage) / 100.0)
        why.append(f"RC 覆盖率 {coverage}%：地块 {parcel['area_m2']} m² 对应占地上限约 {cap:.0f} m²。")
    return {
        "id": "drawings",
        "name_zh": f"图纸核算 · {int(gfa)}m² · {storeys}层 · {len(windows)}种门窗",
        "name_en": "Drawing-based takeoff",
        "kind": "standalone" if dwellings == 1 else "terrace" if dwellings >= 3 else "duplex",
        "dwellings": dwellings,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "kitchens": kitchens,
        "storeys": storeys,
        "gfa_m2": float(gfa),
        "gfa_per_unit_m2": round(float(gfa) / max(dwellings, 1), 1),
        "gfa_missing": gfa_missing,
        "gfa_note": (
            "图纸未读到建筑面积，木材/屋面/筏板按面积计的科目不套模板数。"
            if gfa_missing
            else "GFA 由图纸占地×层数推算，文字层未写 GFA。"
            if gfa_derived
            else None
        ),
        "aspect": 1.4,
        "eaves_mm": eaves,
        "wall_height_m": wall_height,
        "storey_heights_m": _value(fields, "storey_heights_m"),
        "roof_pitch_deg": 25,
        "roof_m2_drawn": _value(fields, "roof_m2"),
        "footprint_m2_drawn": footprint,
        "stud_spacing_mm": stud,
        "stud_section": "timber_sg8_140x45_h12" if stud <= 400 else "timber_sg8_90x45_h12",
        "windows": windows,
        "quantity_source": "drawing",
        "cladding": _value(fields, "cladding"),
        "retaining_height_m": _value(fields, "retaining_height_m"),
        "why": why,
    }


def _value(fields: dict[str, Any], key: str):
    item = fields.get(key)
    if item is None:
        return None
    if isinstance(item, dict) and "value" in item:
        return item["value"]
    return item
