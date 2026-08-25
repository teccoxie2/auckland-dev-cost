from app.price_provider import ApiPriceProvider, PriceBookProvider, get_price_provider
from app.pricing import line


def test_pricebook_provider_returns_versioned_public_rate():
    quote = PriceBookProvider().get_rate("timber_sg8_90x45_h12", 1.0)
    assert quote is not None
    assert quote["unit_price"] == 7.41
    assert quote["version"] == "2026-08-24"
    assert quote["source_url"]
    assert quote["as_of"] == "2026-08-24"


def test_missing_sku_is_none():
    assert PriceBookProvider().get_rate("no_such_sku", 1.0) is None


def test_api_provider_without_url_does_not_invent(monkeypatch):
    monkeypatch.delenv("PRICE_API_URL", raising=False)
    assert ApiPriceProvider().get_rate("timber_sg8_90x45_h12", 1.0) is None


def test_composite_prefers_pricebook():
    quote = get_price_provider().get_rate("timber_sg8_90x45_h12", 2.0)
    assert quote is not None
    assert quote["unit_price"] == 7.41


def test_line_records_pricebook_version():
    row = line("timber_sg8_90x45_h12", 1, formula="test")
    assert row["status"] == "priced"
    assert row["pricebook_version"] == "2026-08-24"
    assert row["unit_price"] == 7.41
