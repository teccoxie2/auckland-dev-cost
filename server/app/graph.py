from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .costing import cost_option
from .data_loader import typologies
from .gis import GisError, geocode_address, lookup_overlays, lookup_zone
from .quantity import takeoff
from .zoning import apply_zone_rules, filter_template


class ProjectState(TypedDict, total=False):
    address: str
    error: dict
    site: dict
    zone: dict
    overlays: list
    rules: dict
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


def rules_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    rules = apply_zone_rules(state["zone"].get("zone_code"), state.get("overlays") or [])
    return {"rules": rules, "trace": _trace(state, "rules", f"permitted_dwellings={rules.get('permitted_dwellings')}")}


def options_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    rules = state["rules"]
    options = []
    for template in typologies()["templates"]:
        verdict = filter_template(template, rules)
        option: dict[str, Any] = {
            "id": template["id"],
            "template": {
                "id": template["id"],
                "name_zh": template["name_zh"],
                "kind": template["kind"],
                "dwellings": template["dwellings"],
                "bedrooms": template["bedrooms"],
                "bathrooms": template["bathrooms"],
                "storeys": template["storeys"],
                "gfa_m2": template["gfa_m2"],
            },
            "verdict": verdict,
        }
        if verdict["status"] != "infeasible":
            option["quantities"] = takeoff(template)
            option["cost"] = cost_option(template, verdict, existing_dwellings=1)
        options.append(option)
    return {"options": options, "trace": _trace(state, "options", f"{len(options)} schemes")}


def explain_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {"explanation": state["error"]["message"]}
    zone = state["zone"]
    rules = state["rules"]
    overlays = [item["key"] for item in state.get("overlays") or [] if item.get("present")]
    feasible = [opt for opt in state.get("options") or [] if opt["verdict"]["status"] != "infeasible"]
    parts = [
        f"这块地公开区划为「{zone.get('zone_name')}」。",
        f"规则表中许可住宅套数上限为 {rules.get('permitted_dwellings')} 套，高度约 {rules.get('height_m')} m，覆盖率 {int((rules.get('coverage') or 0)*100)}%。",
    ]
    if overlays:
        parts.append("命中叠加层：" + "、".join(overlays) + "。加密方案更可能需要 Resource Consent。")
    else:
        parts.append("未在抽查的叠加层上命中遗产/特殊风貌/SEA/淹没控制（不代表没有其他约束）。")
    parts.append(f"系统生成 {len(feasible)} 个可继续核算的开发选项。金额只来自价库与官方费率，缺项单独列出。")
    return {"explanation": "".join(parts), "trace": _trace(state, "explain", "template-zh")}


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
    graph.add_node("rules", rules_node)
    graph.add_node("options", options_node)
    graph.add_node("explain", explain_node)
    graph.add_node("pm_gate", pm_gate_node)
    graph.add_edge(START, "geocode")
    graph.add_edge("geocode", "planning")
    graph.add_edge("planning", "rules")
    graph.add_edge("rules", "options")
    graph.add_edge("options", "explain")
    graph.add_edge("explain", "pm_gate")
    graph.add_edge("pm_gate", END)
    return graph.compile()


WORKFLOW = build_graph()


def run_address(address: str) -> ProjectState:
    return WORKFLOW.invoke({"address": address, "trace": []})
