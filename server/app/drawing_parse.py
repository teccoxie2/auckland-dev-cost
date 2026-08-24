from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

MAX_PDF_BYTES = 15 * 1024 * 1024

WINDOW_ROW = re.compile(
    r"(?P<code>(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+)\s+"
    r"(?P<a>\d{3,4})\s*[xX×]\s*(?P<b>\d{3,4})"
    r"(?:\s*(?:mm)?)?"
    r"(?:\s*(?:qty|no\.?|×|x)\s*(?P<qty>\d{1,2}))?",
    re.IGNORECASE,
)
DIM_WH = re.compile(
    r"(?P<w>\d{3,4})\s*[Ww]\s*[xX×]\s*(?P<h>\d{3,4})\s*[Hh]",
    re.IGNORECASE,
)
DIM_HW = re.compile(
    r"(?P<h>\d{3,4})\s*[Hh]\s*[xX×]\s*(?P<w>\d{3,4})\s*[Ww]",
    re.IGNORECASE,
)
QTY_NEAR = re.compile(r"(?:qty|quantity|no\.?|数量)\s*[:=]?\s*(\d{1,2})", re.IGNORECASE)
GFA = re.compile(
    r"(?:gross\s+floor\s+area|gfa|总建筑面积|建筑面积)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²)",
    re.IGNORECASE,
)
GROUND = re.compile(
    r"(?:ground\s+floor|level\s*0|一楼|底层|占地)\s*(?:area|面积)?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²)",
    re.IGNORECASE,
)
ROOF = re.compile(
    r"(?:roof(?:ing)?\s+area|屋面面积|屋顶面积)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²)",
    re.IGNORECASE,
)
STOREYS = re.compile(r"(\d)\s*(?:storey|storeys|storeyed|层楼|层建筑)", re.IGNORECASE)
WALL_H = re.compile(
    r"(?:wall\s+height|stud\s+height|层高|墙高)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*m\b",
    re.IGNORECASE,
)
FLOOR_H = re.compile(
    r"(?:ground|first|second|一楼|二楼|三楼)\s*(?:floor\s*)?(?:height|层高)?\s*[:：]?\s*(\d\.\d{1,2})\s*m\b",
    re.IGNORECASE,
)
EAVES = re.compile(r"eaves?\s*[:：]?\s*(\d{2,4})\s*mm", re.IGNORECASE)
BEDS = re.compile(r"(\d)\s*(?:bed(?:room)?s?|房)\b", re.IGNORECASE)
BATHS = re.compile(r"(\d(?:\.\d)?)\s*(?:bath(?:room)?s?|卫)\b", re.IGNORECASE)
KITCHENS = re.compile(r"(\d)\s*(?:kitchen|厨)\b", re.IGNORECASE)
DWELLINGS = re.compile(r"(\d)\s*(?:dwelling|unit|套住宅|户)\b", re.IGNORECASE)
COVERAGE = re.compile(
    r"(?:building\s+coverage|site\s+coverage|覆盖率)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
RETAIN_H = re.compile(
    r"retaining\s+wall[^\n]{0,40}?(\d+(?:\.\d+)?)\s*m",
    re.IGNORECASE,
)
BLOCK = re.compile(r"block\s+veneer|concrete\s+block\s+cladding|砌块贴面", re.IGNORECASE)
STUD_400 = re.compile(r"(?:stud(?:s)?\s+(?:centres?|centers?|spacing)\s*[:：]?\s*400|立柱间距\s*400)", re.IGNORECASE)


def extract_pdf(path: Path, *, kind: str, filename: str) -> dict[str, Any]:
    if path.stat().st_size > MAX_PDF_BYTES:
        return {
            "kind": kind,
            "filename": filename,
            "error": "PDF 超过 15MB，未解析。",
            "char_count": 0,
            "fields": {},
            "windows": [],
            "warnings": ["file_too_large"],
        }
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append({"page": index, "text": page.extract_text() or ""})
    text = "\n".join(item["text"] for item in pages)
    parsed = extract_from_text(text, kind=kind, filename=filename)
    parsed["page_count"] = len(pages)
    parsed["char_count"] = len(text.strip())
    if parsed["char_count"] < 80 and not parsed["fields"] and not parsed["windows"]:
        parsed["warnings"].append("scanned_or_empty_text")
        parsed["error"] = parsed.get("error") or "PDF 几乎没有文字层。扫描件无法按尺寸套价，请上传可选中文字的 RC/BC 图，或提供 IFC。"
    return parsed


def extract_from_text(text: str, *, kind: str, filename: str) -> dict[str, Any]:
    compact = re.sub(r"[ \t]+", " ", text)
    fields: dict[str, Any] = {}
    warnings: list[str] = []

    _put_number(fields, "gfa_m2", GFA, compact, filename)
    _put_number(fields, "footprint_m2", GROUND, compact, filename)
    _put_number(fields, "roof_m2", ROOF, compact, filename)
    _put_int(fields, "storeys", STOREYS, compact, filename, lo=1, hi=5)
    _put_number(fields, "wall_height_m", WALL_H, compact, filename, lo=2.1, hi=4.0)
    heights = [float(m.group(1)) for m in FLOOR_H.finditer(compact) if 2.1 <= float(m.group(1)) <= 4.0]
    if heights:
        fields["storey_heights_m"] = {
            "value": heights[:5],
            "evidence": "；".join(m.group(0) for m in list(FLOOR_H.finditer(compact))[:5]),
            "source_file": filename,
        }
        if "storeys" not in fields:
            fields["storeys"] = {"value": len(heights), "evidence": "按读到的层高条数", "source_file": filename}
        if "wall_height_m" not in fields:
            fields["wall_height_m"] = {
                "value": round(sum(heights) / len(heights), 2),
                "evidence": "层高平均值",
                "source_file": filename,
            }
    eaves = EAVES.search(compact)
    if eaves:
        fields["eaves_mm"] = {"value": int(eaves.group(1)), "evidence": eaves.group(0), "source_file": filename}
    _put_int(fields, "bedrooms", BEDS, compact, filename, lo=1, hi=8)
    baths = BATHS.search(compact)
    if baths:
        value = float(baths.group(1))
        fields["bathrooms"] = {
            "value": int(round(value)),
            "evidence": baths.group(0),
            "source_file": filename,
        }
    _put_int(fields, "kitchens", KITCHENS, compact, filename, lo=1, hi=6)
    _put_int(fields, "dwellings", DWELLINGS, compact, filename, lo=1, hi=12)
    coverage = COVERAGE.search(compact)
    if coverage:
        fields["coverage_pct"] = {
            "value": float(coverage.group(1)),
            "evidence": coverage.group(0),
            "source_file": filename,
        }
    retain = RETAIN_H.search(compact)
    if retain:
        fields["retaining_height_m"] = {
            "value": float(retain.group(1)),
            "evidence": retain.group(0),
            "source_file": filename,
        }
    if BLOCK.search(compact) or STUD_400.search(compact):
        evidence = (BLOCK.search(compact) or STUD_400.search(compact)).group(0)
        fields["stud_spacing_mm"] = {"value": 400, "evidence": evidence, "source_file": filename}
        fields["cladding"] = {"value": "block_veneer", "evidence": evidence, "source_file": filename}

    windows = _windows(compact, filename)
    if not windows:
        warnings.append("no_window_schedule")

    return {
        "kind": kind,
        "filename": filename,
        "error": None,
        "fields": fields,
        "windows": windows,
        "warnings": warnings,
    }


AREA_FIELD_KEYS = {
    "gfa_m2",
    "footprint_m2",
    "roof_m2",
    "coverage_pct",
    "storeys",
    "wall_height_m",
    "storey_heights_m",
    "eaves_mm",
    "retaining_height_m",
    "bedrooms",
    "bathrooms",
    "kitchens",
    "dwellings",
}


def merge_extracts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    windows_bc: list[dict[str, Any]] = []
    windows_other: list[dict[str, Any]] = []
    warnings: list[str] = []
    documents = []
    errors = []
    for part in parts:
        documents.append(
            {
                "kind": part.get("kind"),
                "filename": part.get("filename"),
                "page_count": part.get("page_count"),
                "char_count": part.get("char_count"),
                "error": part.get("error"),
            }
        )
        if part.get("error") and part.get("char_count", 0) < 80:
            errors.append(part["error"])
        warnings.extend(part.get("warnings") or [])
        kind = part.get("kind")
        for key, value in (part.get("fields") or {}).items():
            if key not in fields:
                fields[key] = value
            elif kind == "rc" and key in AREA_FIELD_KEYS:
                fields[key] = value
        if part.get("windows"):
            if kind == "bc":
                windows_bc = list(part["windows"])
            elif not windows_other:
                windows_other = list(part["windows"])
    windows = windows_bc or windows_other
    return {
        "documents": documents,
        "fields": fields,
        "windows": windows,
        "warnings": list(dict.fromkeys(warnings)),
        "errors": errors,
        "enough_to_cost": bool(fields.get("gfa_m2") or fields.get("footprint_m2") or windows),
    }


def infer_kind(filename: str, declared: str | None = None) -> str:
    if declared in {"rc", "bc"}:
        return declared
    lower = filename.lower()
    if "bco" in lower or "bc " in lower or "architectural" in lower or "approved" in lower:
        return "bc"
    if re.search(r"\brc\b", lower) or "resource" in lower:
        return "rc"
    return "unknown"


def _windows(text: str, filename: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for match in WINDOW_ROW.finditer(text):
        code = re.sub(r"\s+", "", match.group("code")).upper()
        a = int(match.group("a"))
        b = int(match.group("b"))
        width, height = _orient(code, a, b)
        qty = int(match.group("qty") or 1)
        key = f"{code}-{width}x{height}"
        if key in found:
            found[key]["count"] += qty
        else:
            found[key] = {
                "code": code,
                "w_mm": width,
                "h_mm": height,
                "count": qty,
                "evidence": match.group(0).strip(),
                "source_file": filename,
            }
    if found:
        return list(found.values())
    loose: list[dict[str, Any]] = []
    for match in list(DIM_WH.finditer(text)) + list(DIM_HW.finditer(text)):
        width = int(match.group("w"))
        height = int(match.group("h"))
        if width < 400 or height < 400:
            continue
        snippet = text[max(match.start() - 40, 0) : match.end() + 40]
        qty_match = QTY_NEAR.search(snippet)
        qty = int(qty_match.group(1)) if qty_match else 1
        loose.append(
            {
                "code": f"W{len(loose)+1}",
                "w_mm": width,
                "h_mm": height,
                "count": qty,
                "evidence": match.group(0),
                "source_file": filename,
            }
        )
    return _collapse(loose)


def _orient(code: str, a: int, b: int) -> tuple[int, int]:
    if code.startswith("ED") or code.startswith("D"):
        return (min(a, b), max(a, b)) if max(a, b) >= 1800 else (a, b)
    return (max(a, b), min(a, b)) if max(a, b) >= 1500 and min(a, b) <= 1500 else (a, b)


def _collapse(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    for item in items:
        key = (item["w_mm"], item["h_mm"])
        if key in grouped:
            grouped[key]["count"] += item["count"]
        else:
            grouped[key] = item
    return list(grouped.values())


def _put_number(fields: dict[str, Any], key: str, pattern: re.Pattern, text: str, filename: str, lo: float = 0, hi: float = 1e9) -> None:
    match = pattern.search(text)
    if not match:
        return
    value = float(match.group(1))
    if value < lo or value > hi:
        return
    fields[key] = {"value": value, "evidence": match.group(0), "source_file": filename}


def _put_int(fields: dict[str, Any], key: str, pattern: re.Pattern, text: str, filename: str, lo: int, hi: int) -> None:
    match = pattern.search(text)
    if not match:
        return
    value = int(float(match.group(1)))
    if value < lo or value > hi:
        return
    fields[key] = {"value": value, "evidence": match.group(0), "source_file": filename}
