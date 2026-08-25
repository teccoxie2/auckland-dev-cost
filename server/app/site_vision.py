from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from .imagery import collect_imagery, lookup_building_outlines

ALLOWED_HINTS = {
    "prefer_compact",
    "prefer_two_storey",
    "avoid_terrace",
    "existing_rebuild",
    "vacant_infill",
}


def unavailable_analysis(note: str) -> dict[str, Any]:
    return {
        "imagery": [],
        "buildings": {"found": False, "note": note},
        "vision": {
            "status": "unavailable",
            "scheme_hints": [],
            "findings": [],
            "model": None,
            "note": note,
        },
    }


def analyze_site(site: dict[str, Any], rules: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return _analyze_site(site, rules or {})
    except Exception as exc:  # noqa: BLE001
        return unavailable_analysis(f"场地影像核对失败：{exc}。方案仍按区划硬规则生成。")


def _analyze_site(site: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    imagery = collect_imagery(site)
    buildings = lookup_building_outlines(site)
    hints = _hints_from_gis(site, buildings, rules)
    vision = {
        "status": "imagery_only" if imagery else "unavailable",
        "scheme_hints": hints,
        "findings": _findings(site, buildings, rules),
        "model": None,
        "note": "公开航拍不是直播。未配置视觉模型时，只用 LINZ 屋顶轮廓与地籍交叉核对，不编造看见的内容。",
    }
    if imagery:
        vision["status"] = "buildings_only" if buildings.get("found") else "imagery_only"
    model_result = _call_vision_model(imagery, site, rules) if imagery else None
    if model_result:
        extra_hints = [item for item in model_result.get("scheme_hints") or [] if item in ALLOWED_HINTS]
        extra_findings = [item for item in (model_result.get("findings") or []) if isinstance(item, str)]
        vision["scheme_hints"] = list(dict.fromkeys([*hints, *extra_hints]))
        vision["findings"] = [*vision["findings"], *extra_findings]
        vision["status"] = "model"
        vision["model"] = model_result.get("model")
        vision["note"] = (
            "视觉模型只描述航拍里能看见的场地情况，不能改地籍面积、区划或任何金额。"
            + (f" 模型：{vision['model']}。" if vision["model"] else "")
        )
        vision["observations"] = model_result.get("observations")
    return {"imagery": imagery, "buildings": buildings, "vision": vision}


def vision_advice(site: dict[str, Any]) -> list[dict[str, Any]]:
    vision = site.get("vision") or {}
    buildings = site.get("buildings") or {}
    imagery = site.get("imagery") or []
    items: list[dict[str, Any]] = []
    if imagery:
        labels = "、".join(frame.get("label_zh") or frame["id"] for frame in imagery[:3])
        items.append(
            {
                "id": "imagery",
                "severity": "info",
                "title_zh": "已读取公开航拍",
                "body_zh": f"{labels}。用来核对现有房屋和场地，不是实时摄像头。",
                "source_name": imagery[0].get("source_name"),
                "source_url": imagery[0].get("source_url"),
            }
        )
    if buildings.get("found"):
        coverage = buildings.get("parcel_coverage")
        coverage_txt = f"约占本户地块 {round(coverage * 100)}%。" if coverage is not None else ""
        items.append(
            {
                "id": "buildings",
                "severity": "watch" if (buildings.get("count") or 0) else "info",
                "title_zh": f"LINZ 屋顶轮廓 {buildings.get('count') or 0} 栋",
                "body_zh": (
                    f"相交屋顶合计约 {buildings.get('roof_area_m2') or 0} m²。{coverage_txt}"
                    f"{buildings.get('note') or ''}"
                ),
                "source_name": buildings.get("source_name"),
                "source_url": buildings.get("source_url"),
            }
        )
    elif buildings.get("note"):
        items.append(
            {
                "id": "buildings_missing",
                "severity": "watch",
                "title_zh": "屋顶轮廓未读到",
                "body_zh": str(buildings["note"]),
                "source_name": "LINZ NZ Building Outlines",
                "source_url": "https://data.linz.govt.nz/layer/101290-nz-building-outlines/",
            }
        )
    if vision.get("observations"):
        items.append(
            {
                "id": "vision_obs",
                "severity": "info",
                "title_zh": "航拍判读",
                "body_zh": str(vision["observations"]),
                "source_name": vision.get("model"),
                "source_url": imagery[0].get("source_url") if imagery else None,
            }
        )
    if vision.get("findings"):
        items.append(
            {
                "id": "vision",
                "severity": "info",
                "title_zh": "场地核对",
                "body_zh": " ".join(vision["findings"]),
                "source_name": vision.get("model") or "地籍 × 航拍 × 屋顶轮廓",
                "source_url": (imagery[0].get("source_url") if imagery else None),
            }
        )
    if vision.get("status") != "model":
        items.append(
            {
                "id": "vision_model",
                "severity": "watch",
                "title_zh": "视觉模型未运行",
                "body_zh": (
                    vision.get("note")
                    or "设置 OPENAI_API_KEY 后会把航拍送给视觉模型做补充判读；缺密钥时不编造看见的内容。"
                ),
                "source_name": None,
                "source_url": None,
            }
        )
    return items


def _hints_from_gis(site: dict[str, Any], buildings: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    slope = float(((site.get("terrain") or {}).get("slope_deg")) or 0)
    if slope >= 8:
        hints.append("prefer_two_storey")
        hints.append("prefer_compact")
    if buildings.get("found") and int(buildings.get("count") or 0) >= 1:
        hints.append("existing_rebuild")
        hints.append("prefer_compact")
        coverage = buildings.get("parcel_coverage")
        cap = float(rules.get("coverage") or 0)
        if coverage and cap and coverage >= cap * 0.8:
            hints.append("avoid_terrace")
    elif buildings.get("found") and int(buildings.get("count") or 0) == 0:
        hints.append("vacant_infill")
    return list(dict.fromkeys(hints))


def _findings(site: dict[str, Any], buildings: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    parcel = site.get("parcel") or {}
    if parcel.get("found") and parcel.get("area_m2") is not None:
        findings.append(f"地籍面积 {parcel['area_m2']} m² 保持议会读数，航拍不改这个数字。")
    if buildings.get("found"):
        count = int(buildings.get("count") or 0)
        if count:
            findings.append(f"LINZ 屋顶轮廓在外包矩形内读到 {count} 栋，按现有房屋重建路径优先考虑独栋。")
        else:
            findings.append("外包矩形内没有屋顶轮廓，加密方案仍须过区划硬规则。")
        coverage = buildings.get("parcel_coverage")
        cap = float(rules.get("coverage") or 0)
        if coverage is not None and cap:
            findings.append(
                f"屋顶合计覆盖约 {round(coverage * 100)}%，区划覆盖率上限 {int(cap * 100)}%。"
            )
    slope = (site.get("terrain") or {}).get("slope_deg")
    if slope is not None:
        findings.append(f"DEM 坡度 {slope}°，坡度数字仍以 LINZ DEM 为准，不用航拍估坡。")
    return findings


def _call_vision_model(
    imagery: list[dict[str, Any]],
    site: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any] | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    frames = [frame for frame in imagery if frame.get("url")][:2]
    if not frames:
        return None
    images: list[str] = []
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            for frame in frames:
                response = client.get(frame["url"])
                response.raise_for_status()
                if "image" not in (response.headers.get("content-type") or ""):
                    continue
                import base64

                encoded = base64.b64encode(response.content[:900_000]).decode("ascii")
                images.append(f"data:image/jpeg;base64,{encoded}")
    except Exception:
        return None
    if not images:
        return None
    parcel = site.get("parcel") or {}
    zone = site.get("zone") or {}
    terrain = site.get("terrain") or {}
    brief = {
        "address": (site.get("geo") or {}).get("display_name"),
        "zone_name": zone.get("zone_name"),
        "permitted_dwellings": rules.get("permitted_dwellings"),
        "parcel_area_m2": parcel.get("area_m2") if parcel.get("found") else None,
        "slope_deg": terrain.get("slope_deg"),
        "overlays": [item.get("key") for item in site.get("overlays") or [] if item.get("present")],
    }
    prompt = (
        "你在核对新西兰奥克兰一块住宅地的公开航拍。GIS 摘要如下，面积/区划/坡度以 GIS 为准，你不得改写这些数字，也不得给出任何价格。\n"
        f"{json.dumps(brief, ensure_ascii=False)}\n"
        "只返回 JSON："
        '{"observations":"中文简述可见场地","scheme_hints":[],"findings":["中文短句"]}'
        " scheme_hints 只能从 "
        f"{sorted(ALLOWED_HINTS)} 里选。findings 只写航拍里能看见的：现有房屋、树木、车道、空地，不要编造平方米。"
    )
    model = os.environ.get("SITE_VISION_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for url in images:
        content.append({"type": "image_url", "image_url": {"url": url}})
    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": content}],
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = payload["choices"][0]["message"]["content"]
        parsed = json.loads(text)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
    clean_findings = [str(item) for item in findings if isinstance(item, str) and item.strip()]
    observations = parsed.get("observations") if isinstance(parsed.get("observations"), str) else None
    if observations and _looks_like_price(observations):
        observations = None
    clean_findings = [item for item in clean_findings if not _looks_like_price(item)]
    hints = [item for item in parsed.get("scheme_hints") or [] if item in ALLOWED_HINTS]
    return {
        "model": model,
        "observations": observations,
        "findings": clean_findings,
        "scheme_hints": hints,
    }


def _looks_like_price(text: str) -> bool:
    return bool(re.search(r"(\$|NZD|单价|总价|报价)", text, re.I))
