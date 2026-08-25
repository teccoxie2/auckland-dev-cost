from __future__ import annotations

from typing import Any

from .data_loader import council_fees
from .price_provider import get_price_provider

GST = 0.15


def get_item(item_id: str) -> dict[str, Any] | None:
    quote = get_price_provider().get_rate(item_id, 1, {"lookup": True})
    if quote is None:
        return None
    return quote["item"]


def line(
    item_id: str,
    quantity: float,
    *,
    formula: str,
    extra_notes: str = "",
    line_id: str | None = None,
    name_zh: str | None = None,
) -> dict[str, Any]:
    row_id = line_id or item_id
    quote = get_price_provider().get_rate(item_id, quantity, {"formula": formula})
    if quote is None or quantity <= 0:
        return {
            "id": row_id,
            "status": "missing" if quote is None else "zero",
            "quantity": round(quantity, 3),
            "amount_incl_gst": 0.0,
            "formula": formula,
        }
    item = quote["item"]
    amount = round(float(quote["unit_price"]) * quantity, 2)
    if not quote.get("gst_included", True) and quote["unit"] != "percent":
        amount = round(amount * (1 + GST), 2)
    return {
        "id": row_id,
        "status": "priced",
        "category": item.get("category"),
        "trade": item.get("trade"),
        "name_zh": name_zh or item.get("name_zh") or quote["label"],
        "name_en": item.get("name_en"),
        "unit": quote["unit"],
        "quantity": round(quantity, 3),
        "unit_price": quote["unit_price"],
        "gst_included": quote.get("gst_included", True),
        "amount_incl_gst": amount,
        "sku": item.get("sku") or quote["sku"],
        "pack": item.get("pack"),
        "source_name": quote["source"],
        "source_url": quote.get("source_url") or item.get("source_url"),
        "retrieved_at": quote["as_of"] or item.get("retrieved_at"),
        "pricebook_version": quote["version"],
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


def lim_report_fee() -> dict[str, Any]:
    table = council_fees()["lim_report"]
    return {
        "amount": table["standard_fee"],
        "standard_fee": table["standard_fee"],
        "urgent_fee": table["urgent_fee"],
        "card_surcharge_percent": table["card_surcharge_percent"],
        "standard_working_days": table["standard_working_days"],
        "urgent_working_days": table["urgent_working_days"],
        "source_name": table["source_name"],
        "source_url": table["source_url"],
        "about_url": table.get("about_url"),
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
