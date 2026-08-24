from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .advise import build_advice
from .design import build_template, costed_option, recommend_schemes
from .gis import GisError, geocode_address, lookup_overlays, lookup_parcel, lookup_terrain, lookup_zone
from .zoning import apply_zone_rules


class ProjectState(TypedDict, total=False):
    address: str
    spec: dict
    error: dict
    site: dict
    zone: dict
    overlays: list
    rules: dict
    advice: list
    options: list
    trace: list
    explanation: str
    pm_review: dict


def _trace(state: ProjectState, node: str, detail: str) -> list[dict[str, Any]]:
    items = list(state.get("trace") or [])
    items.append({"node": node, "detail": detail})
    return items


def geocode_node(state: ProjectState) -> dict[str, Any]:
    try:
        geo = geocode_address(state["address"])
    except GisError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}, "trace": _trace(state, "geocode", str(exc))}
    except Exception as exc:  # noqa: BLE001
        return {"error": {"code": "geocode_failed", "message": f"地理编码失败：{exc}"}, "trace": _trace(state, "geocode", str(exc))}
    site = {"geo": geo}
    return {"site": site, "error": None, "trace": _trace(state, "geocode", geo["display_name"])}


def planning_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    geo = state["site"]["geo"]
    try:
        zone = lookup_zone(geo["lat"], geo["lon"])
        overlays = lookup_overlays(geo["lat"], geo["lon"])
    except GisError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}}
    except Exception as exc:  # noqa: BLE001
        return {"error": {"code": "planning_failed", "message": f"规划图层查询失败：{exc}"}}
    site = dict(state["site"])
    site["zone"] = zone
    site["overlays"] = overlays
    present = [item["key"] for item in overlays if item.get("present")]
    return {
        "site": site,
        "zone": zone,
        "overlays": overlays,
        "trace": _trace(state, "planning", f"{zone['zone_name']}; overlays={present}"),
    }


def parcel_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    geo = state["site"]["geo"]
    try:
        parcel = lookup_parcel(geo["lat"], geo["lon"], state["address"])
    except Exception as exc:  # noqa: BLE001
        parcel = {"found": False, "note": f"地籍查询失败：{exc}"}
    site = dict(state["site"])
    site["parcel"] = parcel
    detail = (
        f"{parcel.get('formatted_address')} {parcel.get('area_m2')} m²"
        if parcel.get("found")
        else parcel.get("note") or "parcel missing"
    )
    return {"site": site, "trace": _trace(state, "parcel", str(detail))}


def terrain_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    geo = state["site"]["geo"]
    try:
        terrain = lookup_terrain(geo["lat"], geo["lon"], state["site"].get("parcel"))
    except Exception as exc:  # noqa: BLE001
        terrain = {"note": f"DEM 查询失败：{exc}"}
    site = dict(state["site"])
    site["terrain"] = terrain
    if terrain.get("slope_deg") is not None:
        detail = f"slope={terrain['slope_deg']}° rise={terrain['height_range_m']}m"
    else:
        detail = terrain.get("note") or "terrain missing"
    return {"site": site, "trace": _trace(state, "terrain", detail)}


def rules_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    rules = apply_zone_rules(state["zone"].get("zone_code"), state.get("overlays") or [])
    return {"rules": rules, "trace": _trace(state, "rules", f"permitted_dwellings={rules.get('permitted_dwellings')}")}


def advise_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    advice = build_advice(state["site"], state["rules"])
    return {"advice": advice, "trace": _trace(state, "advise", f"{len(advice)} notes")}


def options_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    options = recommend_schemes(state["rules"], state["site"])
    return {"options": options, "trace": _trace(state, "options", f"{len(options)} schemes")}


def explain_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {"explanation": state["error"]["message"]}
    zone = state["zone"]
    rules = state["rules"]
    parcel = (state.get("site") or {}).get("parcel") or {}
    terrain = (state.get("site") or {}).get("terrain") or {}
    overlays = [item["key"] for item in state.get("overlays") or [] if item.get("present")]
    feasible = [opt for opt in state.get("options") or [] if opt["verdict"]["status"] != "infeasible"]
    parts = [
        f"这块地公开区划为「{zone.get('zone_name')}」。",
        f"规则表中许可住宅套数上限为 {rules.get('permitted_dwellings')} 套，高度约 {rules.get('height_m')} m，覆盖率 {int((rules.get('coverage') or 0)*100)}%。",
    ]
    if parcel.get("found"):
        parts.append(f"地块面积约 {parcel['area_m2']} m²（{parcel.get('formatted_address')}）。")
    if terrain.get("slope_deg") is not None:
        parts.append(f"DEM 坡度约 {terrain['slope_deg']}°、高差 {terrain['height_range_m']} m。")
    if overlays:
        parts.append("命中叠加层：" + "、".join(overlays) + "。加密方案更可能需要 Resource Consent。")
    else:
        parts.append("未在抽查的叠加层上命中遗产/特殊风貌/SEA/淹没控制（不代表没有其他约束）。")
    parts.append(
        f"下面给出 {len(feasible)} 个按这块地筛过的初版方案。你可以改套数、层数、户型大小、厨房和卫生间后再核算。"
        "金额只来自价库与官方费率，缺项单独列出。"
    )
    return {"explanation": "".join(parts), "trace": _trace(state, "explain", "site-brief")}


def pm_gate_node(state: ProjectState) -> dict[str, Any]:
    review = {
        "status": "auto_passed_mvp",
        "note": "第一期屋主展示自动通过。项目经理面板将使用 LangGraph interrupt() 在此挂起。",
    }
    return {"pm_review": review, "trace": _trace(state, "pm_gate", review["status"])}


def build_graph():
    graph = StateGraph(ProjectState)
    graph.add_node("geocode", geocode_node)
    graph.add_node("planning", planning_node)
    graph.add_node("parcel", parcel_node)
    graph.add_node("terrain", terrain_node)
    graph.add_node("rules", rules_node)
    graph.add_node("advise", advise_node)
    graph.add_node("options", options_node)
    graph.add_node("explain", explain_node)
    graph.add_node("pm_gate", pm_gate_node)
    graph.add_edge(START, "geocode")
    graph.add_edge("geocode", "planning")
    graph.add_edge("planning", "parcel")
    graph.add_edge("parcel", "terrain")
    graph.add_edge("terrain", "rules")
    graph.add_edge("rules", "advise")
    graph.add_edge("advise", "options")
    graph.add_edge("options", "explain")
    graph.add_edge("explain", "pm_gate")
    graph.add_edge("pm_gate", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_address(address: str) -> ProjectState:
    return WORKFLOW.invoke({"address": address, "trace": []})


def configure_option(site: dict[str, Any], rules: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    template = build_template(spec)
    why = [
        "客户选装方案：按你选的套数、层数、户型、厨房和卫生间重新套价。",
        "坡度、挡土墙和覆盖率仍用这块地已读到的公开数据，不重新编数。",
    ]
    return costed_option(template, rules, site, why=why, recommended=True, origin="custom")


def hydrate_legacy_result(address: str, result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("error"):
        return None
    site = dict(result.get("site") or {})
    geo = site.get("geo") or {}
    if geo.get("lat") is None or geo.get("lon") is None:
        return None
    parcel = site.get("parcel") or {}
    terrain = site.get("terrain") or {}
    needs_parcel = not parcel.get("found")
    needs_terrain = terrain.get("slope_deg") is None
    if not needs_parcel and not needs_terrain and result.get("advice"):
        return None
    changed = False
    if needs_parcel:
        try:
            site["parcel"] = lookup_parcel(float(geo["lat"]), float(geo["lon"]), address)
            changed = True
        except Exception:  # noqa: BLE001
            site["parcel"] = {"found": False, "note": "地籍补读失败"}
    if needs_terrain:
        try:
            site["terrain"] = lookup_terrain(float(geo["lat"]), float(geo["lon"]), site.get("parcel"))
            changed = True
        except Exception:  # noqa: BLE001
            site["terrain"] = {"note": "DEM 补读失败"}
            changed = True
    if not changed and result.get("advice"):
        return None
    result = dict(result)
    result["site"] = site
    if result.get("rules"):
        result["advice"] = build_advice(site, result["rules"])
    return result
