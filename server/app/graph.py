from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .advise import build_advice
from .checkpoint import get_checkpointer
from .costing import ensure_lim_cost_on_options
from .design import (
    CURRENT_TITLE_FILTER_COPY,
    apply_building_rules_to_options,
    attach_costs,
    attach_quantities,
    build_template,
    costed_option,
    generate_typology_options,
    recommend_schemes,
    scheme_filter_meta,
)
from .gis import (
    GisError,
    attach_subdivision,
    display_note_for_cluster,
    geocode_address,
    lookup_overlays,
    lookup_parcel,
    lookup_terrain,
    lookup_zone,
)
from .lim import awaiting_lim, lim_advice
from .site_vision import analyze_site, unavailable_analysis, vision_advice
from .zoning import apply_zone_rules, filter_template, is_existing_unit_title


class ProjectState(TypedDict, total=False):
    address: str
    selected_address: dict
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
    scheme_filter: dict
    vision: dict
    lim: dict
    material_elements: Annotated[list, add]


def _trace(state: ProjectState, node: str, detail: str) -> list[dict[str, Any]]:
    items = list(state.get("trace") or [])
    items.append({"node": node, "detail": detail})
    return items


def geocode_node(state: ProjectState) -> dict[str, Any]:
    selected = state.get("selected_address") or {}
    try:
        geo = geocode_address(
            state["address"],
            lat=selected.get("lat"),
            lon=selected.get("lon"),
            full_address=selected.get("full_address"),
            sap_address_id=selected.get("sap_address_id"),
            sap_site_id=selected.get("sap_site_id"),
        )
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
    site = attach_subdivision(site, state.get("address") or geo.get("display_name") or "")
    cluster = site.get("subdivision") or {}
    if cluster.get("found"):
        detail = (
            f"{parcel.get('formatted_address')} {parcel.get('area_m2')} m²; "
            f"current title {cluster.get('selected_unit')} among {cluster.get('unit_count')}"
        )
    elif parcel.get("found"):
        detail = f"{parcel.get('formatted_address')} {parcel.get('area_m2')} m²"
    else:
        detail = parcel.get("note") or "parcel missing"
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


def merge_advice(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group or []:
            key = str(item.get("id") or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            merged.append(item)
    if any(item.get("id") == "buildings" for item in merged):
        merged = [item for item in merged if item.get("id") != "buildings_missing"]
    return merged


def _apply_site_analysis(site: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    updated = dict(site)
    updated["imagery"] = analysis.get("imagery") or []
    updated["buildings"] = analysis.get("buildings") or {"found": False}
    updated["vision"] = analysis.get("vision") or {}
    snapshot = dict(updated.get("snapshot") or {})
    frames = updated["imagery"]
    if frames:
        snapshot["imagery_source"] = frames[0].get("source_url")
    if updated["buildings"].get("source_url"):
        snapshot["buildings_source"] = updated["buildings"]["source_url"]
    if snapshot:
        updated["snapshot"] = snapshot
    return updated


def site_vision_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    try:
        analysis = analyze_site(state.get("site") or {}, state.get("rules") or {})
    except Exception as exc:  # noqa: BLE001
        analysis = unavailable_analysis(f"场地影像核对失败：{exc}。方案仍按区划硬规则生成。")
    site = _apply_site_analysis(state.get("site") or {}, analysis)
    status = (site.get("vision") or {}).get("status") or "unavailable"
    n_img = len(site.get("imagery") or [])
    return {
        "site": site,
        "vision": site.get("vision"),
        "trace": _trace(state, "site_vision", f"{status}; images={n_img}"),
    }


def _apply_lim(site: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    updated = dict(site)
    updated["lim"] = report
    snapshot = dict(updated.get("snapshot") or {})
    snapshot["lim_order_url"] = report.get("order_url")
    snapshot["lim_source"] = report.get("filename") or report.get("source")
    if snapshot:
        updated["snapshot"] = snapshot
    return updated


def lim_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    report = awaiting_lim()
    site = _apply_lim(state.get("site") or {}, report)
    return {
        "site": site,
        "lim": report,
        "trace": _trace(state, "lim", "awaiting_customer_pdf"),
    }


def land_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    planning = planning_node(state)
    merged: ProjectState = {**state, **planning}
    if planning.get("error"):
        return planning
    parcel = parcel_node(merged)
    merged = {**merged, **parcel}
    terrain = terrain_node(merged)
    site = dict(terrain.get("site") or parcel.get("site") or planning.get("site") or {})
    captured = datetime.now(timezone.utc).isoformat()
    site["captured_at"] = captured
    site["snapshot"] = {
        "captured_at": captured,
        "region": "Auckland",
        "geo_source": (site.get("geo") or {}).get("source_url"),
        "zone_source": (site.get("zone") or {}).get("source_url"),
        "parcel_source": (site.get("parcel") or {}).get("source_url"),
        "terrain_source": (site.get("terrain") or {}).get("source_url"),
    }
    land_state: ProjectState = {**merged, **terrain, "site": site}
    return {
        **planning,
        **parcel,
        **terrain,
        "site": site,
        "trace": _trace(land_state, "land", f"snapshot@{captured}"),
    }


def typology_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    advice = merge_advice(
        build_advice(state["site"], state["rules"]),
        vision_advice(state["site"]),
        lim_advice(state["site"]),
    )
    options, skipped = generate_typology_options(state["rules"], state["site"])
    meta = scheme_filter_meta(state["site"], skipped)
    payload: dict[str, Any] = {
        "advice": advice,
        "options": options,
        "trace": _trace(state, "typology", meta["note"] if meta else f"{len(options)} schemes"),
    }
    if meta:
        payload["scheme_filter"] = meta
    return payload


def quantity_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    options = attach_quantities(state.get("options") or [], state.get("site") or {})
    counted = sum(1 for item in options if item.get("quantities"))
    return {"options": options, "trace": _trace(state, "quantity", f"{counted} template takeoffs")}


def building_rules_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    options = apply_building_rules_to_options(state.get("options") or [])
    pending = sum(1 for item in options if (item.get("building_rules") or {}).get("pending_detail_drawing"))
    return {
        "options": options,
        "trace": _trace(state, "building_rules", f"E2/NZS3604 on templates; pending_detail={pending}"),
    }


def cost_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    options = attach_costs(state.get("options") or [], state.get("site") or {})
    priced = sum(1 for item in options if item.get("cost"))
    return {"options": options, "trace": _trace(state, "cost", f"{priced} PriceProvider estimates")}


def advise_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    advice = build_advice(state["site"], state["rules"])
    return {"advice": advice, "trace": _trace(state, "advise", f"{len(advice)} notes")}


def options_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    options, skipped = recommend_schemes(state["rules"], state["site"])
    meta = scheme_filter_meta(state["site"], skipped)
    payload: dict[str, Any] = {
        "options": options,
        "trace": _trace(state, "options", meta["note"] if meta else f"{len(options)} schemes"),
    }
    if meta:
        payload["scheme_filter"] = meta
    return payload


def explain_node(state: ProjectState) -> dict[str, Any]:
    if state.get("error"):
        return {"explanation": state["error"]["message"]}
    zone = state["zone"]
    rules = state["rules"]
    parcel = (state.get("site") or {}).get("parcel") or {}
    cluster = (state.get("site") or {}).get("subdivision") or {}
    terrain = (state.get("site") or {}).get("terrain") or {}
    overlays = [item["key"] for item in state.get("overlays") or [] if item.get("present")]
    feasible = [opt for opt in state.get("options") or [] if opt["verdict"]["status"] != "infeasible"]
    parts = [
        f"这块地公开区划为「{zone.get('zone_name')}」。",
        f"规则表中许可住宅套数上限为 {rules.get('permitted_dwellings')} 套，高度约 {rules.get('height_m')} m，覆盖率 {int((rules.get('coverage') or 0)*100)}%。",
    ]
    if cluster.get("found"):
        parts.append(cluster.get("note") or "开发完成后只按当前议会门牌核算。")
    elif parcel.get("found"):
        parts.append(f"地块面积约 {parcel['area_m2']} m²（{parcel.get('formatted_address')}）。")
    if terrain.get("slope_deg") is not None:
        parts.append(f"DEM 坡度约 {terrain['slope_deg']}°、高差 {terrain['height_range_m']} m。")
    if overlays:
        parts.append("命中叠加层：" + "、".join(overlays) + "。加密方案更可能需要 Resource Consent。")
    else:
        parts.append("未在抽查的叠加层上命中遗产/特殊风貌/SEA/淹没控制（不代表没有其他约束）。")
    vision = (state.get("site") or {}).get("vision") or {}
    findings = [item for item in (vision.get("findings") or []) if isinstance(item, str) and item.strip()]
    if findings:
        parts.append("场地核对：" + " ".join(findings[:3]))
    lim = (state.get("site") or {}).get("lim") or {}
    if lim.get("status") == "parsed":
        findings = [item for item in (lim.get("findings") or []) if isinstance(item, str) and item.strip()]
        parts.append("正式 LIM：" + (" ".join(findings[:3]) if findings else "已读取客户上传的 PDF 文字层。"))
    else:
        parts.append("尚未上传客户提供的正式 LIM PDF。污染、风区、地面径流和管网 LIR 以该 PDF 文字层为准。")
    parts.append(
        f"下面给出 {len(feasible)} 个按这块地筛过的初版方案。你可以改套数、层数、户型大小、厨房和卫生间后再核算。"
        "金额只来自价库与官方费率，缺项单独列出。"
    )
    return {"explanation": "".join(parts), "trace": _trace(state, "explain", "site-brief")}


def pm_gate_node(state: ProjectState) -> dict[str, Any]:
    hitl = os.environ.get("PM_HITL", "").strip().lower() in {"1", "true", "yes"}
    if hitl:
        decision = interrupt(
            {
                "message": "项目经理核定：可处理缺项，不可改写价表单价。",
                "option_ids": [item.get("id") for item in state.get("options") or []],
                "missing_counts": {
                    item["id"]: ((item.get("cost") or {}).get("totals") or {}).get("missing_count")
                    for item in state.get("options") or []
                    if item.get("id")
                },
            }
        )
        review = {
            "status": "human_resume",
            "decision": decision,
            "note": "已从项目经理 interrupt() 恢复。第一期屋主界面不展示审核面板。",
        }
    else:
        review = {
            "status": "auto_passed_mvp",
            "note": "第一期屋主展示自动通过。设置 PM_HITL=1 时，此节点会 interrupt() 把最终定价权交给项目经理。",
        }
    return {"pm_review": review, "trace": _trace(state, "pm_gate", review["status"])}


def build_graph():
    graph = StateGraph(ProjectState)
    graph.add_node("geocode", geocode_node)
    graph.add_node("land", land_node)
    graph.add_node("rules", rules_node)
    graph.add_node("lim", lim_node)
    graph.add_node("site_vision", site_vision_node)
    graph.add_node("typology", typology_node)
    graph.add_node("quantity", quantity_node)
    graph.add_node("building_rules", building_rules_node)
    graph.add_node("cost", cost_node)
    graph.add_node("explain", explain_node)
    graph.add_node("pm_gate", pm_gate_node)
    graph.add_edge(START, "geocode")
    graph.add_edge("geocode", "land")
    graph.add_edge("land", "rules")
    graph.add_edge("rules", "lim")
    graph.add_edge("lim", "site_vision")
    graph.add_edge("site_vision", "typology")
    graph.add_edge("typology", "quantity")
    graph.add_edge("quantity", "building_rules")
    graph.add_edge("building_rules", "cost")
    graph.add_edge("cost", "explain")
    graph.add_edge("explain", "pm_gate")
    graph.add_edge("pm_gate", END)
    return graph.compile(checkpointer=get_checkpointer())


WORKFLOW = build_graph()


def run_address(
    address: str,
    selected_address: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> ProjectState:
    payload: ProjectState = {"address": address, "trace": []}
    if selected_address:
        payload["selected_address"] = selected_address
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    return WORKFLOW.invoke(payload, config)


def apply_customer_lim(result: dict[str, Any], parsed: dict[str, Any], project_address: str) -> tuple[dict[str, Any] | None, str | None]:
    from .lim import report_from_parsed
    from .lim_parse import address_matches_project

    ok, message = address_matches_project(parsed.get("lim_address"), project_address)
    if not ok:
        return None, message
    site = _apply_lim(dict(result.get("site") or {}), report_from_parsed(parsed))
    updated = dict(result)
    updated["site"] = site
    kept = [item for item in (updated.get("advice") or []) if not str(item.get("id") or "").startswith("lim_")]
    updated["advice"] = merge_advice(kept, lim_advice(site))
    _append_lim_explanation(updated, site)
    options, _changed = ensure_lim_cost_on_options(updated.get("options") or [], site)
    updated["options"] = options
    return updated, None


def configure_option(site: dict[str, Any], rules: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    template = build_template(spec)
    why = [
        "客户选装方案：按你选的套数、层数、户型、厨房和卫生间重新套价。",
        "坡度、挡土墙和覆盖率仍用这块地已读到的公开数据，不重新编数。",
    ]
    return costed_option(template, rules, site, why=why, recommended=True, origin="custom")


def _needs_site_analysis(site: dict[str, Any]) -> bool:
    if not site.get("imagery") or not site.get("vision"):
        return True
    buildings = site.get("buildings") or {}
    note = str(buildings.get("note") or "").lower()
    if "timed out" in note or "超时" in note:
        return True
    parcel = site.get("parcel") or {}
    area = parcel.get("area_m2") if parcel.get("found") else None
    if buildings.get("found") and area and area < 250 and int(buildings.get("count") or 0) >= 3:
        return True
    if buildings.get("found"):
        return False
    return False


def hydrate_site_analysis(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("error"):
        return None
    site = dict(result.get("site") or {})
    geo = site.get("geo") or {}
    if geo.get("lat") is None or geo.get("lon") is None:
        return None
    if not _needs_site_analysis(site):
        return None
    try:
        analysis = analyze_site(site, result.get("rules") or {})
    except Exception as exc:  # noqa: BLE001
        analysis = unavailable_analysis(f"场地影像核对失败：{exc}。方案仍按区划硬规则生成。")
    site = _apply_site_analysis(site, analysis)
    updated = dict(result)
    updated["site"] = site
    updated["advice"] = merge_advice(updated.get("advice") or [], vision_advice(site), lim_advice(site))
    findings = [item for item in ((site.get("vision") or {}).get("findings") or []) if isinstance(item, str) and item.strip()]
    if findings:
        extra = "场地核对：" + " ".join(findings[:3])
        explanation = updated.get("explanation") or ""
        if extra not in explanation:
            updated["explanation"] = explanation + extra
    return updated


def _needs_lim(site: dict[str, Any]) -> bool:
    lim = site.get("lim") or {}
    if not lim:
        return True
    if lim.get("source") == "customer_pdf" and lim.get("status") in {"parsed", "awaiting_upload"}:
        return False
    return True


def _lim_explanation(site: dict[str, Any]) -> str:
    lim = site.get("lim") or {}
    if lim.get("status") == "parsed":
        findings = [item for item in (lim.get("findings") or []) if isinstance(item, str) and item.strip()]
        return "正式 LIM：" + (" ".join(findings[:3]) if findings else "已读取客户上传的 PDF 文字层。")
    return "尚未上传客户提供的正式 LIM PDF。污染、风区、地面径流和管网 LIR 以该 PDF 文字层为准。"


def _append_lim_explanation(result: dict[str, Any], site: dict[str, Any]) -> None:
    extra = _lim_explanation(site)
    explanation = result.get("explanation") or ""
    explanation = explanation.replace("LIM 公开图层已核对，这不是已购买的正式 LIM PDF。", "")
    if "LIM 公开核对：" in explanation:
        prefix, _, rest = explanation.partition("LIM 公开核对：")
        cut = rest.find("下面给出")
        explanation = prefix + (rest[cut:] if cut >= 0 else "")
    if extra not in explanation:
        result["explanation"] = explanation + extra
    else:
        result["explanation"] = explanation


def hydrate_lim(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("error"):
        return None
    site = dict(result.get("site") or {})
    changed = False
    lim = site.get("lim") or {}
    if _needs_lim(site):
        site = _apply_lim(site, awaiting_lim())
        changed = True
    elif lim.get("status") == "parsed":
        from pathlib import Path

        from .lim import report_from_parsed
        from .lim_parse import parse_lim_pdf

        parsed = lim.get("parsed")
        stored = (result.get("lim_document") or {}).get("stored_path")
        needs_extract = not isinstance(parsed, dict) or "subdivision_consents" not in parsed
        if needs_extract and stored and Path(stored).is_file():
            fresh = parse_lim_pdf(Path(stored), filename=(parsed or {}).get("filename") or Path(stored).name)
            if fresh.get("ok"):
                parsed = fresh
        if parsed:
            refreshed = report_from_parsed(parsed)
            refreshed["queried_at"] = lim.get("queried_at") or refreshed["queried_at"]
            if (
                refreshed.get("sections") != lim.get("sections")
                or refreshed.get("findings") != lim.get("findings")
                or refreshed.get("disclaimer_zh") != lim.get("disclaimer_zh")
            ):
                site = _apply_lim(site, refreshed)
                changed = True
    if not site.get("lim"):
        return None
    updated = dict(result)
    updated["site"] = site
    kept = [item for item in (updated.get("advice") or []) if not str(item.get("id") or "").startswith("lim_")]
    updated["advice"] = merge_advice(kept, lim_advice(site))
    _append_lim_explanation(updated, site)
    options, cost_changed = ensure_lim_cost_on_options(updated.get("options") or [], site)
    if cost_changed:
        updated["options"] = options
        changed = True
    if updated["advice"] != (result.get("advice") or []):
        changed = True
    if (updated.get("explanation") or "") != (result.get("explanation") or ""):
        changed = True
    return updated if changed else None


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
    needs_cluster = "subdivision" not in site or (site.get("subdivision") or {}).get("reason") == "cluster_lookup_failed"
    needs_title_filter = is_existing_unit_title(site) and (result.get("scheme_filter") or {}).get("copy") != CURRENT_TITLE_FILTER_COPY
    if not needs_parcel and not needs_terrain and not needs_cluster and not needs_title_filter and result.get("advice"):
        return None
    changed = False
    if needs_parcel:
        try:
            site["parcel"] = lookup_parcel(float(geo["lat"]), float(geo["lon"]), address)
            changed = True
        except Exception:  # noqa: BLE001
            site["parcel"] = {"found": False, "note": "地籍补读失败"}
    if needs_cluster:
        before = site.get("subdivision")
        site = attach_subdivision(site, address)
        if site.get("subdivision") != before:
            changed = True
        needs_title_filter = is_existing_unit_title(site) and (result.get("scheme_filter") or {}).get("copy") != CURRENT_TITLE_FILTER_COPY
    if needs_title_filter:
        changed = True
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
    if is_existing_unit_title(site):
        cluster = dict(site.get("subdivision") or {})
        cluster["note"] = display_note_for_cluster(cluster)
        site = dict(site)
        site["subdivision"] = cluster
        result["site"] = site
    if result.get("rules"):
        result["advice"] = merge_advice(build_advice(site, result["rules"]), vision_advice(site), lim_advice(site))
    if is_existing_unit_title(site):
        _apply_current_title_filter(result, site)
    else:
        _refresh_drawing_verdicts(result, site)
    cluster = site.get("subdivision") or {}
    if cluster.get("found") and cluster.get("note"):
        explanation = result.get("explanation") or ""
        if cluster["note"] not in explanation:
            result["explanation"] = explanation + cluster["note"]
    return result


def _apply_current_title_filter(result: dict[str, Any], site: dict[str, Any]) -> None:
    rules = result.get("rules") or {}
    preserved = [
        option
        for option in result.get("options") or []
        if option.get("origin") in {"drawings", "custom"} or option.get("id") in {"drawings", "custom"}
    ]
    fresh: list[dict[str, Any]] = []
    skipped = 0
    if rules:
        fresh, skipped = recommend_schemes(rules, site)
    kept_ids = {option["id"] for option in preserved}
    result["options"] = preserved + [option for option in fresh if option["id"] not in kept_ids]
    meta = scheme_filter_meta(site, skipped)
    if meta:
        result["scheme_filter"] = meta
    _refresh_drawing_verdicts(result, site)


def _refresh_drawing_verdicts(result: dict[str, Any], site: dict[str, Any]) -> None:
    rules = result.get("rules") or {}
    if not rules:
        return
    options = []
    changed = False
    for option in result.get("options") or []:
        origin = option.get("origin") or ""
        if origin != "drawings" and option.get("id") != "drawings":
            options.append(option)
            continue
        template = dict(option.get("template") or {})
        if template.get("footprint_m2_drawn") is None:
            fields = (option.get("drawing_extract") or {}).get("fields") or {}
            raw = fields.get("footprint_m2")
            if isinstance(raw, dict) and raw.get("value") is not None:
                template["footprint_m2_drawn"] = raw["value"]
            elif (option.get("quantities") or {}).get("footprint_m2"):
                template["footprint_m2_drawn"] = option["quantities"]["footprint_m2"]
        verdict = filter_template(template, rules, site)
        if verdict != option.get("verdict"):
            option = {**option, "verdict": verdict, "recommended": verdict["status"] != "infeasible"}
            changed = True
        options.append(option)
    if changed:
        result["options"] = options
