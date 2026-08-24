from app.gis import address_where, in_auckland, parse_address_query, search_addresses


def test_zero_coords_are_not_auckland():
    assert in_auckland(0, 0) is False
    assert in_auckland(-36.89839, 174.92383) is True


def test_parse_nelson_street():
    parsed = parse_address_query("55 Nelson Street")
    assert parsed["number"] == "55"
    assert parsed["road"] == "NELSON"
    assert parsed["locality"] == ""


def test_parse_nelson_howick():
    parsed = parse_address_query("55 Nelson Street Howick")
    assert parsed["number"] == "55"
    assert parsed["road"] == "NELSON"
    assert parsed["locality"] == "HOWICK"


def test_parse_bruce_unit_and_suburb():
    parsed = parse_address_query("115D Bruce Road, Glenfield, Auckland")
    assert parsed["number"] == "115D"
    assert parsed["road"] == "BRUCE"
    assert parsed["locality"] == "GLENFIELD"


def test_where_does_not_use_leading_wildcard_on_house_number():
    where = address_where(parse_address_query("55 Nelson Street"))
    assert where is not None
    assert "%55 NELSON%" not in where
    assert "LIKE '55 NELSON%" in where
    assert "AddressStatus='Current'" in where


def test_search_nelson_street_from_council_layer():
    hits = search_addresses("55 Nelson Street")
    labels = [item["full_address"] for item in hits]
    assert len(hits) >= 4
    assert any("HOWICK" in item.upper() for item in labels)
    assert any("AUCKLAND CENTRAL" in item.upper() for item in labels)
    assert any("55-59" in item for item in labels)
    assert any(item.upper().startswith("55A NELSON") for item in labels)
    assert not any(item.upper().startswith("155 ") for item in labels)
    for item in hits:
        assert item["lat"] < 0
        assert item["lon"] > 0
        assert item["source_url"].endswith("AC_Address_Query/FeatureServer/0")
