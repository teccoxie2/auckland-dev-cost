from __future__ import annotations

from typing import Any

from .data_loader import design_rules

OVERLAY_LABELS = {
    "significant_ecological_area": "重要生态区（SEA）",
    "notable_trees": "保护树木",
    "volcanic_viewshaft": "火山视廊",
    "historic_heritage": "历史遗产",
    "special_character": "特殊风貌",
    "height_variation": "高度变化控制",
    "coastal_inundation": "沿海淹没",
    "precinct": "Precinct 地段规则",
}


def build_advice(site: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    spec = design_rules()
    slope = spec["slope"]
    parcel = site.get("parcel") or {}
    terrain = site.get("terrain") or {}
    zone_name = (site.get("zone") or {}).get("zone_name") or "未知区划"

    items.append(
        {
            "id": "zone",
            "severity": "info",
            "title_zh": f"区划：{zone_name}",
            "body_zh": (
                f"许可套数上限 {rules.get('permitted_dwellings')} 套，高度约 {rules.get('height_m')} m，"
                f"覆盖率 {int((rules.get('coverage') or 0) * 100)}%，景观用地 {int((rules.get('landscaped') or 0) * 100)}%。"
                f"{rules.get('consent_note') or ''}"
            ),
            "source_name": (site.get("zone") or {}).get("source_name"),
            "source_url": (site.get("zone") or {}).get("source_url"),
        }
    )

    if parcel.get("found"):
        coverage_m2 = round(float(parcel["area_m2"]) * float(rules.get("coverage") or 0), 1)
        items.append(
            {
                "id": "parcel",
                "severity": "info",
                "title_zh": f"本户地块约 {parcel['area_m2']} m²",
                "body_zh": (
                    f"公开地籍「{parcel.get('formatted_address')}」"
                    f"{(' · ' + parcel['legal_description']) if parcel.get('legal_description') else ''}。"
                    f"按覆盖率，本户初版建筑占地不宜超过约 {coverage_m2} m²。"
                    f"面宽约 {parcel.get('frontage_m')} m、进深约 {parcel.get('depth_m')} m。"
                ),
                "source_name": parcel.get("source_name"),
                "source_url": parcel.get("source_url"),
            }
        )
    else:
        items.append(
            {
                "id": "parcel_missing",
                "severity": "watch",
                "title_zh": "未读到完整地块边界",
                "body_zh": parcel.get("note") or "覆盖率与挡土墙长度只能按地址点估算。",
                "source_name": None,
                "source_url": None,
            }
        )

    cluster = site.get("subdivision") or {}
    if cluster.get("found"):
        combined = cluster.get("combined_area_m2")
        coverage_combined = (
            round(float(combined) * float(rules.get("coverage") or 0), 1) if combined else None
        )
        labels = [
            (item.get("formatted_address") or item.get("legal_description") or "").strip()
            for item in cluster.get("units") or []
        ]
        labels = [item for item in labels if item]
        items.append(
            {
                "id": "subdivision",
                "severity": "watch",
                "title_zh": f"拆分后合计约 {combined} m²（{cluster.get('title_plan')}）",
                "body_zh": (
                    cluster.get("note")
                    or "开发完成后议会不再保留整宗门牌，现址是同一 DP 下的多户。"
                )
                + (f" 现址：{'；'.join(labels)}。" if labels else "")
                + (
                    f" 多套图纸按合计覆盖率约 {coverage_combined} m² 占地来校核。"
                    if coverage_combined
                    else ""
                ),
                "source_name": cluster.get("source_name"),
                "source_url": cluster.get("source_url"),
            }
        )

    if terrain.get("slope_deg") is not None:
        items.extend(_slope_advice(terrain, parcel, spec, slope))
    else:
        items.append(
            {
                "id": "terrain_missing",
                "severity": "watch",
                "title_zh": "坡度未读到",
                "body_zh": terrain.get("note") or "无法给出挡土墙与土方建议，请人工看 GeoMaps 等高线。",
                "source_name": None,
                "source_url": None,
            }
        )

    for overlay in site.get("overlays") or []:
        if not overlay.get("present"):
            continue
        key = overlay.get("key")
        label = OVERLAY_LABELS.get(key, key)
        items.append(
            {
                "id": f"overlay_{key}",
                "severity": "constraint",
                "title_zh": f"叠加层：{label}",
                "body_zh": _overlay_body(key),
                "source_name": "Auckland Council Unitary Plan overlay",
                "source_url": overlay.get("source_url"),
            }
        )

    return items


def _slope_advice(
    terrain: dict[str, Any],
    parcel: dict[str, Any],
    spec: dict[str, Any],
    slope: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    deg = float(terrain["slope_deg"])
    rise = float(terrain["height_range_m"])
    sources = {item["id"]: item for item in spec["sources"]}
    if deg < slope["gentle_deg"] and rise < 2.0:
        items.append(
            {
                "id": "slope_gentle",
                "severity": "info",
                "title_zh": f"缓坡约 {deg:.1f}°（取样高差 {rise:.1f} m）",
                "body_zh": (
                    "DEM 显示这块地比较平。取样高差小于该 8m DEM 的标称精度，初版按平地筏板/木框架考虑，不把挡土墙列为主项。"
                    "仍建议施工前做地勘，NZS 3604 只适用于 good ground。"
                ),
                "source_name": terrain.get("source_name"),
                "source_url": terrain.get("source_url"),
            }
        )
        return items

    if deg < slope["e11_steep_deg"]:
        title = f"中坡约 {deg:.1f}°（高差 {rise:.1f} m）"
        body = (
            "建议缩小占地、优先二层，用分台减少切填。"
            "若平整建筑平台，挡土墙通常会承受房屋或车道荷载（surcharge），"
            "按 MBIE/Auckland Council：有附加荷载即需建筑许可，不能因墙高不足 1.5m 就当成豁免。"
        )
        severity = "watch"
    else:
        title = f"陡坡约 {deg:.1f}°（高差 {rise:.1f} m）"
        body = (
            f"达到 Unitary Plan E11 的 10° 口径，土方与基础应按坡地专项设计，不宜直接套 NZS 3604 平地做法。"
            "初版建议：沿等高线布房、缩小筏板、分台 + 挡土墙，并预留岩土工程师。"
        )
        severity = "constraint"

    items.append(
        {
            "id": "slope",
            "severity": severity,
            "title_zh": title,
            "body_zh": body + f" {terrain.get('note') or ''}",
            "source_name": sources["e11"]["name"],
            "source_url": sources["e11"]["url"],
        }
    )

    height = min(max(rise * 0.5, slope["retaining_trigger_m"]), 3.0)
    wall_length = parcel.get("frontage_m") or terrain.get("run_m") or 12
    surcharge = True
    consent = "需要建筑许可（墙支撑建筑平台，属于 surcharge）"
    if height > slope["sleeper_max_height_m"]:
        wall_note = (
            f"初版按高差一半估一道约 {height:.1f} m、长约 {wall_length:.0f} m 的墙。"
            "超过零售枕木适用高度，材料不计价，须工程师设计混凝土或木桩墙。"
        )
    else:
        wall_note = (
            f"初版按高差一半估一道约 {height:.1f} m、长约 {wall_length:.0f} m 的矮墙，"
            "只计入 H4 枕木材料；立柱、泄水、回填和人工缺价。"
            "BRANZ 建议超过 1m 咨询特许工程师。"
        )
    items.append(
        {
            "id": "retaining",
            "severity": "constraint" if surcharge else "watch",
            "title_zh": f"挡土墙：约 {height:.1f} m · {consent}",
            "body_zh": wall_note,
            "source_name": sources["mbie_retaining"]["name"],
            "source_url": sources["mbie_retaining"]["url"],
        }
    )

    footprint_guess = min(float(parcel.get("area_m2") or 200) * 0.35, 250)
    earth_area = round(footprint_guess * 1.2, 0)
    earth_vol = round(footprint_guess * (rise / 4.0), 1)
    e12_hit = earth_area > slope["e12_permitted_area_m2"] or earth_vol > slope["e12_permitted_volume_m3"]
    items.append(
        {
            "id": "earthworks",
            "severity": "watch" if e12_hit else "info",
            "title_zh": "土方（E12）",
            "body_zh": (
                f"粗估扰动面积约 {earth_area:.0f} m²、体积约 {earth_vol:.0f} m³（占地×高差/4，不是施工图土方）。"
                + (
                    "可能超过住宅区许可活动 500m² / 250m³，需按 E12 核 Resource Consent。"
                    if e12_hit
                    else "若实际切填控制在 500m² 且 250m³ 以内，可为许可活动，仍须满足泥沙控制标准。"
                )
            ),
            "source_name": sources["e12"]["name"],
            "source_url": sources["e12"]["url"],
        }
    )
    return items


def _overlay_body(key: str) -> str:
    mapping = {
        "notable_trees": "布房、车行道和土方需避开树冠与根区，加密方案更容易触发 Resource Consent。",
        "coastal_inundation": "建筑标高、筏板和自由板需要按淹没控制核对，不建议下挖车库。",
        "historic_heritage": "拆除或外观改动通常走遗产路径，第一期住宅模板仅作对照。",
        "special_character": "街景、材料与体积受风貌规则约束，许可套数可能下降。",
        "significant_ecological_area": "植被清除与土方受限，开发应避开 SEA 范围。",
        "volcanic_viewshaft": "高度比区划表更紧，二层以上需核视廊。",
        "height_variation": "以 Height Variation Control 的高度为准，而不是区划默认高度。",
        "precinct": "地段规则可能改动后退、高度或设计控制，需读 Precinct 章节。",
    }
    return mapping.get(key, "该叠加层可能构成 qualifying matter，加密前需规划核对。")
