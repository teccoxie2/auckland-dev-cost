from __future__ import annotations

import os
from typing import Any, Protocol, TypedDict

from .data_loader import council_fees, pricebook


class RateQuote(TypedDict):
    sku: str
    unit_price: float
    currency: str
    source: str
    source_url: str | None
    version: str
    as_of: str
    unit: str
    gst_included: bool
    label: str
    item: dict[str, Any]


class PriceProvider(Protocol):
    def get_rate(self, sku_or_element: str, qty: float, context: dict[str, Any] | None = None) -> RateQuote | None:
        """Return a sourced unit price, or None when the source has no row. Never invent a price."""


def _item_quote(item: dict[str, Any], book: dict[str, Any]) -> RateQuote | None:
    if item.get("unit_price") is None:
        return None
    return {
        "sku": str(item.get("sku") or item["id"]),
        "unit_price": float(item["unit_price"]),
        "currency": str(book.get("currency") or "NZD"),
        "source": str(item.get("source_name") or book.get("disclaimer") or "pricebook"),
        "source_url": item.get("source_url"),
        "version": str(book.get("version") or ""),
        "as_of": str(item.get("retrieved_at") or ""),
        "unit": str(item.get("unit") or ""),
        "gst_included": bool(item.get("gst_included", True)),
        "label": str(item.get("name_zh") or item["id"]),
        "item": item,
    }


class PriceBookProvider:
    """Implementation 1: versioned local JSON/CSV price book."""

    def get_rate(self, sku_or_element: str, qty: float, context: dict[str, Any] | None = None) -> RateQuote | None:
        del qty, context
        book = pricebook()
        for item in book.get("items") or []:
            if item.get("id") == sku_or_element or item.get("sku") == sku_or_element:
                return _item_quote(item, book)
        return None


class ApiPriceProvider:
    """Implementation 2 (reserved): supplier HTTP API. Unset URL or HTTP error → no rate, never invent."""

    def get_rate(self, sku_or_element: str, qty: float, context: dict[str, Any] | None = None) -> RateQuote | None:
        base = os.environ.get("PRICE_API_URL", "").strip()
        if not base:
            return None
        try:
            import httpx
        except ImportError:
            return None
        url = f"{base.rstrip('/')}/rates/{sku_or_element}"
        try:
            response = httpx.get(url, params={"qty": qty}, timeout=10.0)
        except Exception:
            return None
        if response.status_code != 200:
            return None
        try:
            data = response.json()
        except Exception:
            return None
        if not isinstance(data, dict) or data.get("unit_price") is None:
            return None
        book = pricebook()
        return {
            "sku": str(data.get("sku") or sku_or_element),
            "unit_price": float(data["unit_price"]),
            "currency": str(data.get("currency") or "NZD"),
            "source": str(data.get("source") or "supplier_api"),
            "source_url": data.get("source_url"),
            "version": str(data.get("version") or ""),
            "as_of": str(data.get("as_of") or ""),
            "unit": str(data.get("unit") or ""),
            "gst_included": bool(data.get("gst_included", True)),
            "label": str(data.get("label") or sku_or_element),
            "item": {**data, "id": sku_or_element, "name_zh": data.get("label") or sku_or_element},
        }


class CompositePriceProvider:
    """Price book first, then optional API. First sourced hit wins."""

    def __init__(self, providers: list[PriceProvider]):
        self.providers = providers

    def get_rate(self, sku_or_element: str, qty: float, context: dict[str, Any] | None = None) -> RateQuote | None:
        for provider in self.providers:
            quote = provider.get_rate(sku_or_element, qty, context)
            if quote is not None:
                return quote
        return None


_provider: CompositePriceProvider | None = None


def get_price_provider() -> CompositePriceProvider:
    global _provider
    if _provider is None:
        _provider = CompositePriceProvider([PriceBookProvider(), ApiPriceProvider()])
    return _provider


def reset_price_provider() -> None:
    global _provider
    _provider = None


def pricebook_meta() -> dict[str, Any]:
    book = pricebook()
    as_of = ""
    for item in book.get("items") or []:
        if item.get("retrieved_at"):
            as_of = str(item["retrieved_at"])
            break
    return {
        "version": book.get("version"),
        "as_of": as_of,
        "currency": book.get("currency") or "NZD",
        "item_count": len(book.get("items") or []),
        "source_name": "versioned pricebook.json",
    }


def official_fee_meta() -> dict[str, Any]:
    fees = council_fees()
    return {
        "version": fees.get("version"),
        "as_of": fees.get("retrieved_at"),
        "source_name": fees.get("source_name"),
        "source_url": fees.get("source_url"),
    }
