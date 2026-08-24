from __future__ import annotations

from typing import Any

from .data_loader import pricebook
from .pricing import GST, building_consent_deposit, dc_amount, igc_amount, line, missing_line, resource_consent_deposit
from .quantity import takeoff

PRELIM_PCT = 0.10
CONTINGENCY_PCT = 0.08

WINDOW_ITEMS = {
    (1800, 1200): "window_alu_1800x1200_dg",
    (1200, 1200): "window_alu_1200x1200_dg",
}


def cost_option(
    template: dict[str, Any],
    filter_result: dict[str, Any],
    existing_dwellings: int = 1,
    site: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qty = takeoff(template, site)
    lines: list[dict[str, Any]] = []

    lines.append(
        line(
            "timber_sg8_90x45_h12",
            qty["timber_90_lm"],
            formula="立柱+墙板延米（含10%损耗）= (周长/间距×层数 + 8) × 层高 + 3×周长×层数",
        )
    )
    lines.append(
        line(
            "timber_sg8_140x45_h12",
            qty["timber_140_lm"],
            formula="宽推拉门或过梁加强时增加 140×45，否则仅少量过梁备料",
            extra_notes="窗表最大宽≥3000mm 时增加过梁木料。",
        )
    )
    if qty["cavity_required"]:
        lines.append(
            line(
                "cavity_batten_h31_45x20",
                qty["batten_lm"],
                formula="外墙面积 / 0.6m 间距，E2 得分≥7 或二层及以上计入空腔",
            )
        )
    lines.append(line("gib_std_10mm", qty["gib_m2"], formula="内衬面积 × 1.15 损耗，并扣门窗洞口"))
    lines.append(line("pink_batts_r22_wall", qty["insulation_m2"], formula="外墙面积 × 1.08 损耗"))
    lines.append(
        line(
            "roofing_corrugate_colour_845",
            qty["roof_sheet_lm"],
            formula="屋面斜面积 / 0.762m 覆盖宽 × 1.10 损耗",
        )
    )
    lines.append(
        line(
            "concrete_readymix_20mpa",
            qty["slab_m3"],
            formula="底层占地 × 85mm 面层（Rib-raft 表层口径）× 1.05 损耗",
            extra_notes="EPS 垫块本身未计价。",
        )
    )
    lines.append(
        line(
            "framing_labour_gfa",
            qty["gfa_m2"],
            formula="GFA × 框架安装公开区间中位",
        )
    )

    for opening in qty["window_schedule"]:
        code = opening["code"]
        count = int(opening["count"])
        width = int(opening["w_mm"])
        height = int(opening["h_mm"])
        if code == "ED":
            lines.append(
                line(
                    "door_hume_nexus15_860",
                    count,
                    formula="户型表 ED 数量 × Hume Nexus 15 门扇零售价",
                    extra_notes="门扇 1980×860，不是 2040 整樘含框。",
                )
            )
            continue
        item_id = WINDOW_ITEMS.get((width, height))
        if item_id:
            lines.append(
                line(
                    item_id,
                    count,
                    formula=f"{code} {width}×{height}mm 公开新窗标价 × {count}",
                )
            )
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
    kitchens = int(qty.get("kitchens") or 1)
    bathrooms = int(qty.get("bathrooms") or 1)
    lines.append(
        line(
            "kaboodle_base_600",
            qty["kitchen_base_600"],
            formula="每套厨房 5 个 600mm 地柜",
        )
    )
    lines.append(
        line(
            "kaboodle_wall_600",
            qty["kitchen_wall_600"],
            formula="每套厨房 5 个 600mm 吊柜",
        )
    )
    lines.append(
        line(
            "kaboodle_door_600_seasalt",
            qty["kitchen_door_600"],
            formula="每套厨房 10 扇 600mm 门板",
        )
    )
    lines.append(
        line(
            "kaboodle_benchtop_2400x600",
            qty["kitchen_bench_2400"],
            formula="每套厨房 2 块 2400×600 台面",
        )
    )
    lines.append(
        missing_line(
            "kitchen_appliances_install",
            "厨房电器、水槽与安装",
            "柜体/门板/台面已按 Kaboodle SKU 计价；电器和水槽安装无公开总价。",
            quantity=kitchens,
            unit="套",
        )
    )
    lines.append(
        line(
            "toilet_stein_ero",
            bathrooms,
            formula="卫生间数量 × 公开马桶套装零售价",
            extra_notes="安装未含。",
        )
    )
    lines.append(
        line(
            "shower_stein_georgia_750",
            bathrooms,
            formula="卫生间数量 × 750mm 整体淋浴房零售价",
            extra_notes="龙头花洒未含；贴砖淋浴不套用此 SKU。",
        )
    )
    lines.append(
        line(
            "tap_caroma_luna_shower",
            bathrooms,
            formula="卫生间数量 × Caroma Luna 淋浴混水阀零售价",
        )
    )
    lines.append(
        line(
            "tap_caroma_luna_basin",
            bathrooms,
            formula="卫生间数量 × Caroma Luna 面盆龙头 RRP",
        )
    )
    lines.append(
        line(
            "membrane_crommelin_4l",
            bathrooms,
            formula="卫生间数量 × Crommelin 4L 防水涂料",
        )
    )
    lines.append(
        missing_line(
            "bathroom_plumber_labour",
            "卫生间水管安装工时",
            "龙头和防水材料已按 SKU 计价；持牌水管工工时无本项目可核对数量。",
            quantity=bathrooms,
            unit="间",
        )
    )
    retaining = qty.get("retaining")
    if retaining:
        if retaining.get("sleeper_ok"):
            lines.append(
                line(
                    "retaining_sleeper_h4_200x50",
                    retaining["timber_lm"],
                    formula=retaining["formula"],
                    extra_notes=retaining["note"],
                )
            )
            lines.append(
                line(
                    "pile_h5_125_2400",
                    retaining["posts"],
                    formula="挡土墙长度 / 1.2m 间距，向上取整",
                )
            )
            lines.append(
                line(
                    "geotextile_strol_50m",
                    retaining["geotextile_rolls"],
                    formula="墙面面积 / 50m² 每卷，向上取整",
                )
            )
        else:
            lines.append(
                missing_line(
                    "retaining_engineer_wall",
                    f"工程师挡土墙约 {retaining['height_m']} m × {retaining['length_m']} m",
                    retaining["note"],
                    quantity=retaining["length_m"],
                    unit="m",
                )
            )
        lines.append(
            missing_line(
                "retaining_posts_drainage_labour",
                "挡土墙开挖、级配碎石与安装",
                "立柱和土工布材料已按 SKU 计价（仅≤1.2m 枕木墙）。碎石无全国标价，人工无公开工时。",
            )
        )
    lines.append(
        line(
            "expol_tuffpod_1100x300",
            qty["pod_count"],
            formula="占地长宽按 1.2m 网格取整格子数（1.1m 垫块 + 0.1m 肋）",
        )
    )
    scaffold_item = "scaffolding_mobile_3m_week" if int(template["storeys"]) <= 1 else "scaffolding_mobile_5m_week"
    lines.append(
        line(
            scaffold_item,
            1,
            formula="Metroscaff 官网最低租期 1 周",
        )
    )
    lines.append(
        line(
            "scaffolding_delivery",
            1,
            formula="官网送装收回一口价 × 1 次",
        )
    )
    lines.append(
        missing_line(
            "scaffolding_perimeter",
            "整栋外围脚手架",
            "已计入移动塔最低一周，不能代替满堂脚手架。",
        )
    )

    construction = _sum_priced(lines, categories={"materials", "labour"})
    prelim = round(construction * PRELIM_PCT, 2)
    lines.append(
        {
            "id": "preliminaries",
            "status": "rule",
            "category": "preliminaries",
            "name_zh": "施工预备费（P&G）",
            "unit": "percent",
            "quantity": PRELIM_PCT,
            "amount_incl_gst": prelim,
            "source_name": "项目经理第一期规则：已确认施工费的 10%",
            "source_url": None,
            "notes": "不是供应商报价。脚手架等缺项未包含在基数中。",
            "formula": "已确认材料+人工 × 10%",
        }
    )

    design_item = next(item for item in pricebook()["items"] if item["id"] == "design_fee_designer_pct")
    design_base = construction + prelim
    design_ex = round(design_base / (1 + GST) * float(design_item["unit_price"]), 2)
    design_incl = round(design_ex * (1 + GST), 2)
    lines.append(
        {
            "id": "design_fee_designer_pct",
            "status": "priced",
            "category": "design",
            "name_zh": design_item["name_zh"],
            "unit": "percent",
            "quantity": design_item["unit_price"],
            "amount_incl_gst": design_incl,
            "source_name": design_item["source_name"],
            "source_url": design_item["source_url"],
            "retrieved_at": design_item["retrieved_at"],
            "notes": design_item["notes"],
            "formula": "（已确认施工+预备）不含 GST × 5% + GST",
        }
    )

    new_units = max(int(template["dwellings"]) - existing_dwellings, 0)
    if template["kind"] == "standalone" and existing_dwellings >= 1:
        rebuild_new_units = 0
        igc_units = 0
        dc_units = 0
        intensity_note = "按拆一建一、套数不增加假设：IGC/DC 不计新增单元。实际以 Council/Watercare 评估为准。"
    else:
        rebuild_new_units = new_units
        igc_units = new_units
        dc_units = new_units
        intensity_note = f"按相对现有 {existing_dwellings} 套净增 {new_units} 套计 IGC/DC。"

    if template["kind"] in {"duplex", "terrace", "minor_dwelling"}:
        igc_units = int(template["dwellings"]) - existing_dwellings
        dc_units = max(igc_units, 0)
        rebuild_new_units = dc_units
        intensity_note = f"加密方案按净增 {max(igc_units, 0)} 个住宅单元计 IGC 与 DC。"

    igc = igc_amount(max(igc_units, 0), template.get("gfa_per_unit_m2") or template.get("minor_gfa_m2"))
    dc = dc_amount(max(dc_units, 0))
    lines.append(
        {
            "id": "watercare_igc",
            "status": "priced" if igc["amount_incl_gst"] else "zero",
            "category": "statutory",
            "name_zh": "Watercare 基础设施增长费（都市区水+污）",
            "quantity": max(igc_units, 0),
            "unit": "unit",
            "unit_price": igc["rate_incl_gst"],
            "amount_incl_gst": igc["amount_incl_gst"],
            "source_name": igc["source_name"],
            "source_url": igc["source_url"],
            "retrieved_at": igc["retrieved_at"],
            "notes": f"{igc['notes']} {intensity_note}",
            "formula": "净增单元 × $29,348.46（≤65m² 单元按 2/3）",
        }
    )
    lines.append(
        {
            "id": "development_contributions",
            "status": "priced" if dc["amount_incl_gst"] else "zero",
            "category": "statutory",
            "name_zh": "Auckland Council 开发贡献金（Rest of Auckland 假设）",
            "quantity": max(dc_units, 0),
            "unit": "HUE",
            "unit_price": dc["rate_per_hue"],
            "amount_incl_gst": dc["amount_incl_gst"],
            "source_name": dc["source_name"],
            "source_url": dc["source_url"],
            "retrieved_at": dc["retrieved_at"],
            "notes": dc["notes"] + " " + intensity_note,
            "formula": "2025/26 $20,000 × 1.02 × 净增 HUE",
        }
    )

    construction_plus = construction + prelim
    statutory_before_bc = igc["amount_incl_gst"] + dc["amount_incl_gst"]
    project_value_for_bc = construction_plus + design_incl
    bc = building_consent_deposit(project_value_for_bc)
    lines.append(
        {
            "id": "building_consent_deposit",
            "status": "priced",
            "category": "statutory",
            "name_zh": "建筑许可押金（按估算工程价值分档）",
            "amount_incl_gst": bc["deposit"],
            "source_name": bc["source_name"],
            "source_url": bc["source_url"],
            "retrieved_at": bc["retrieved_at"],
            "notes": "押金按实际工时多退少补，不是最终账单。",
            "formula": f"工程价值约 ${project_value_for_bc:,.0f} 对应官方分档押金",
        }
    )
    lines.append(_levy("branz_levy", "BRANZ 建筑研究征费 0.1%", bc["branz"], bc, "造价>$20,000 时 0.1%"))
    lines.append(_levy("mbie_levy", "MBIE 建工征费 $1.75/千元", bc["mbie"], bc, "造价>$64,999 时 $1.75 / $1,000"))
    lines.append(_levy("bca_accreditation_levy", "BCA 认证征费 $0.58/千元", bc["accreditation"], bc, "全部建工许可 58c / $1,000"))

    rc_deposit = 0.0
    if filter_result.get("needs_resource_consent"):
        rc = resource_consent_deposit()
        rc_deposit = rc["deposit"]
        lines.append(
            {
                "id": "resource_consent_deposit",
                "status": "priced",
                "category": "statutory",
                "name_zh": "资源许可押金（住宅土地使用 lodgement）",
                "quantity": 1,
                "unit": "deposit",
                "unit_price": rc["deposit"],
                "amount_incl_gst": rc["deposit"],
                "source_name": rc["source_name"],
                "source_url": rc["source_url"],
                "retrieved_at": rc["retrieved_at"],
                "notes": f"{rc['notes']} 原因：{'；'.join(filter_result.get('reasons') or [])}",
                "formula": "官方 Land use — Residential 押金 $6,500（多数案子会超出，超出未计价）",
            }
        )

    contingency_base = construction_plus + design_incl
    contingency = round(contingency_base * CONTINGENCY_PCT, 2)
    lines.append(
        {
            "id": "contingency",
            "status": "rule",
            "category": "contingency",
            "name_zh": "预备费",
            "quantity": CONTINGENCY_PCT,
            "amount_incl_gst": contingency,
            "source_name": "项目经理第一期规则：已确认施工+设计的 8%",
            "source_url": None,
            "notes": "用于现场与涨价，不是价库条目。",
            "formula": "（已确认施工+预备+设计）× 8%",
        }
    )

    priced_total = round(sum(item.get("amount_incl_gst") or 0 for item in lines if item.get("status") in {"priced", "rule", "zero"}), 2)
    missing = [item for item in lines if item.get("status") == "missing"]
    gfa = float(template["gfa_m2"])
    return {
        "quantities": qty,
        "lines": lines,
        "totals": {
            "construction_confirmed_incl_gst": construction,
            "preliminaries_incl_gst": prelim,
            "design_incl_gst": design_incl,
            "statutory_incl_gst": round(
                statutory_before_bc + bc["deposit"] + bc["branz"] + bc["mbie"] + bc["accreditation"] + rc_deposit,
                2,
            ),
            "contingency_incl_gst": contingency,
            "confirmed_total_incl_gst": priced_total,
            "missing_count": len(missing),
            "rlb_benchmark_low": round(gfa * 2500, 0),
            "rlb_benchmark_high": round(gfa * 3800, 0),
            "rlb_source_name": "RLB Riders Digest New Zealand 2025：Auckland custom dwellings $2,500–$3,800/m² GFA（Q4 2024）",
            "rlb_source_url": "https://www.rlb.com/oceania/wp-content/uploads/sites/1/2025/02/2025_New-Zealand_RLB-Rider-Digest.pdf",
        },
        "rebuild_new_units": rebuild_new_units,
        "intensity_note": intensity_note,
        "project_value_for_bc": round(project_value_for_bc, 2),
    }


def _sum_priced(lines: list[dict[str, Any]], categories: set[str]) -> float:
    total = 0.0
    for item in lines:
        if item.get("status") == "priced" and item.get("category") in categories:
            total += item.get("amount_incl_gst") or 0
    return round(total, 2)


def _levy(item_id: str, name: str, amount: float, bc: dict[str, Any], formula: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "status": "priced" if amount else "zero",
        "category": "statutory",
        "name_zh": name,
        "amount_incl_gst": amount,
        "source_name": bc["source_name"],
        "source_url": bc["source_url"],
        "retrieved_at": bc["retrieved_at"],
        "formula": formula,
    }
