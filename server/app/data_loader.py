from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_json(name: str) -> dict:
    path = DATA_DIR / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=8)
def pricebook() -> dict:
    return load_json("pricebook.json")


@lru_cache(maxsize=8)
def council_fees() -> dict:
    return load_json("council_fees.json")


@lru_cache(maxsize=8)
def zone_rules() -> dict:
    return load_json("zone_rules.json")


@lru_cache(maxsize=8)
def typologies() -> dict:
    return load_json("typologies.json")
