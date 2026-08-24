from app.gis import (
    address_where,
    deposited_plan_id,
    in_auckland,
    lookup_parcel,
    lookup_unit_cluster,
    parse_address_query,
    search_addresses,
    split_estate_note,
)


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


def test_split_note_only_when_all_hits_are_unit_titles():
    hits = [
        {"full_number": "115A", "full_address": "115A Bruce Road Glenfield"},
        {"full_number": "115B", "full_address": "115B Bruce Road Glenfield"},
        {"full_number": "115C", "full_address": "115C Bruce Road Glenfield"},
        {"full_number": "115D", "full_address": "115D Bruce Road Glenfield"},
        {"full_number": "115E", "full_address": "115E Bruce Road Glenfield"},
        {"full_number": "115F", "full_address": "115F Bruce Road Glenfield"},
    ]
    note = split_estate_note("115 Bruce Road Glenfield", hits)
    assert note is not None
    assert "115A" in note
    assert "115F" in note
    assert "整宗" in note
    mixed = [*hits, {"full_number": "115", "full_address": "115 Bruce Road Glenfield"}]
    assert split_estate_note("115 Bruce Road Glenfield", mixed) is None
    assert split_estate_note("115A Bruce Road Glenfield", hits) is None


def test_deposited_plan_id():
    assert deposited_plan_id("LOT 1 DP 580591") == "580591"
    assert deposited_plan_id("Lot 6 DP 580591") == "580591"
    assert deposited_plan_id("FEE SIMPLE") is None


def test_search_bruce_glenfield_has_no_parent_115():
    hits = search_addresses("115 Bruce Road Glenfield")
    numbers = [(item.get("full_number") or "").upper().replace(" ", "") for item in hits]
    assert any(item.startswith("115A") for item in numbers)
    assert any(item.startswith("115F") for item in numbers)
    assert not any(item == "115" for item in numbers)
    note = split_estate_note("115 Bruce Road Glenfield", hits)
    assert note is not None
    assert "115A" in note


def test_unit_cluster_for_115a_bruce():
    hits = search_addresses("115A Bruce Road Glenfield")
    assert hits
    hit = hits[0]
    parcel = lookup_parcel(hit["lat"], hit["lon"], hit["full_address"])
    assert parcel.get("found")
    cluster = lookup_unit_cluster(hit["lat"], hit["lon"], hit["full_address"], parcel)
    assert cluster["found"] is True
    assert cluster["title_plan"] == "DP 580591"
    assert cluster["unit_count"] == 6
    assert cluster["combined_area_m2"] is not None
    assert 700 < float(cluster["combined_area_m2"]) < 800
    labels = " ".join(item.get("formatted_address") or "" for item in cluster["units"])
    assert "115A" in labels
    assert "115F" in labels
    assert "只显示并核算" in cluster["note"]
