from __future__ import annotations

from typing import Any

from .data_loader import council_fees, pricebook

GST = 0.15


def get_item(item_id: str) -> dict[str, Any] | None:
    for item in pricebook()["items"]:
        if item["id"] == item_id:
            return item
    return None


def line(
    item_id: str,
    quantity: float,
    *,
    formula: str,
    extra_notes: str = "",
    line_id: str | None = None,
) -> dict[str, Any]:
    row_id = line_id or item_id
    item = get_item(item_id)
    if item is None or quantity <= 0:
        return {
            "id": row_id,
            "status": "missing" if item is None else "zero",
            "quantity": round(quantity, 3),
            "amount_incl_gst": 0.0,
            "formula": formula,
        }
    amount = round(float(item["unit_price"]) * quantity, 2)
    if not item.get("gst_included", True) and item["unit"] != "percent":
        amount = round(amount * (1 + GST), 2)
    return {
        "id": row_id,
        "status": "priced",
        "category": item["category"],
        "trade": item["trade"],
        "name_zh": item["name_zh"],
        "name_en": item["name_en"],
        "unit": item["unit"],
        "quantity": round(quantity, 3),
        "unit_price": item["unit_price"],
        "gst_included": item.get("gst_included", True),
        "amount_incl_gst": amount,
        "sku": item.get("sku"),
        "pack": item.get("pack"),
        "source_name": item["source_name"],
        "source_url": item["source_url"],
        "retrieved_at": item["retrieved_at"],
        "notes": " ".join(part for part in [item.get("notes"), extra_notes] if part),
        "formula": formula,
    }


def missing_line(item_id: str, name_zh: str, reason: str, quantity: float = 0, unit: str = "") -> dict[str, Any]:
    return {
        "id": item_id,
        "status": "missing",
        "name_zh": name_zh,
        "quantity": quantity,
        "unit": unit,
        "amount_incl_gst": 0.0,
        "notes": reason,
        "source_name": "未采用公开可核对单价，故不计金额",
        "source_url": None,
    }


def building_consent_deposit(project_value_incl: float) -> dict[str, Any]:
    fees = council_fees()
    deposit = fees["building_consent_deposits"][-1]["total"]
    for band in fees["building_consent_deposits"]:
        ceiling = band["max_value"]
        if ceiling is None or project_value_incl <= ceiling:
            deposit = band["total"]
            break
    levies = fees["levies"]
    branz = round(project_value_incl * levies["branz_rate"], 2) if project_value_incl > levies["branz_threshold"] else 0.0
    mbie = (
        round((project_value_incl / 1000.0) * levies["mbie_per_1000"], 2)
        if project_value_incl > levies["mbie_threshold"]
        else 0.0
    )
    accreditation = round((project_value_incl / 1000.0) * levies["accreditation_per_1000"], 2)
    return {
        "deposit": deposit,
        "branz": branz,
        "mbie": mbie,
        "accreditation": accreditation,
        "source_name": fees["source_name"],
        "source_url": fees["source_url"],
        "retrieved_at": fees["retrieved_at"],
        "hourly": fees["hourly"],
    }


def igc_amount(new_units: int, gfa_per_unit: float | None) -> dict[str, Any]:
    fees = council_fees()["igc"]
    rate = float(fees["metro_combined_incl_gst"])
    amount = 0.0
    for _ in range(max(new_units, 0)):
        factor = fees["small_dwelling_factor"] if gfa_per_unit and gfa_per_unit <= fees["small_dwelling_gfa_m2"] else 1.0
        amount += rate * factor
    return {
        "amount_incl_gst": round(amount, 2),
        "rate_incl_gst": rate,
        "new_units": new_units,
        **{k: fees[k] for k in ("source_name", "source_url", "secondary_source_url", "retrieved_at", "notes")},
    }


def resource_consent_deposit() -> dict[str, Any]:
    table = council_fees()["resource_consent"]
    return {
        "deposit": table["residential_land_use_deposit"],
        "source_name": table["source_name"],
        "source_url": table["source_url"],
        "retrieved_at": table["retrieved_at"],
        "notes": table["notes"],
    }


def dc_amount(new_units: int) -> dict[str, Any]:
    table = council_fees()["development_contributions"]
    base = table["areas_fy2025_26_per_hue"]["rest_of_auckland"]
    rate = round(base * (1 + table["annual_increase"]), 2)
    return {
        "amount_incl_gst": round(rate * max(new_units, 0), 2),
        "rate_per_hue": rate,
        "area_assumption": "rest_of_auckland",
        "new_units": new_units,
        "source_name": table["source_name"],
        "source_url": table["source_url"],
        "increase_notice_url": table["increase_notice_url"],
        "retrieved_at": table["retrieved_at"],
        "notes": table["notes"] + " 已按 2026-07-01 起 2% 上调。",
    }
