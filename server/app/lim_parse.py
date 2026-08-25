from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import DependencyError, PdfReadError

from .drawing_parse import MAX_PDF_BYTES

LIM_MARKERS = (
    "land information memorandum",
    "s44a(2)(a)",
    "lim address",
    "site contamination",
    "overland flow path",
)
STREET_KEY = re.compile(
    r"(\d+[a-z]?)\s+([a-z][a-z0-9'\-]*(?:\s+[a-z0-9'\-]+){0,3})\s+"
    r"(street|road|avenue|drive|place|lane|crescent|terrace|parade|way|close|rise|track)",
    re.IGNORECASE,
)
APP_NO = re.compile(
    r"(?:application number|application no\.?)\s*[:\s]*([A-Z]{0,3}\d{5,})",
    re.IGNORECASE,
)
APP_NO_GLUED = re.compile(r"(\d{8,})Application number", re.IGNORECASE)
ISSUED = re.compile(
    r"(?:date issued|issued)\s*[:\s]*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)
ISSUED_GLUED = re.compile(r"(\d{1,2}-[A-Za-z]{3}-\d{4})Date issued", re.IGNORECASE)
LIM_ADDRESS = re.compile(r"(.{8,120}?)LIM address", re.IGNORECASE)
LIM_ADDRESS_LINE = re.compile(r"LIM address\s*[:\s]*([^\n]{8,120})", re.IGNORECASE)
LEGAL = re.compile(r"(LOT\s+\d+\s+DP\s+\d+)", re.IGNORECASE)
LEGAL_GLUED = re.compile(r"(LOT\s+\d+\s+DP\s+\d+)Legal Description", re.IGNORECASE)
WIND = re.compile(
    r"Wind Zone\(s\) for this property:\s*(Low|Medium|High)\s+wind speed of\s*(\d+)\s*m/s",
    re.IGNORECASE,
)
EXPOSURE = re.compile(
    r"This property is classified as:\s*([^\n]{3,80})",
    re.IGNORECASE,
)
LIR = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})[^\n]{0,80}?(?P<lir>LIR_\d+)\s+Description:\s*(?P<body>.+?)(?=\n\s*\n|s44A|s44\(|\Z)",
    re.IGNORECASE | re.DOTALL,
)
LIR_LOOSE = re.compile(r"(LIR_\d+)", re.IGNORECASE)
BCO = re.compile(r"\b(BCO\d+)\b")
VXG = re.compile(r"\b(VXG\d+)\b")
OLFP_HIT = re.compile(
    r"this site \(property parcel\) spatially intersects with one or more overland flow paths",
    re.IGNORECASE,
)
OLFP_MISS = re.compile(
    r"(does not spatially intersect|no overland flow path)",
    re.IGNORECASE,
)
NO_CONTAMINATION_DATA = re.compile(
    r"no land contamination data are available in council'?s regulatory records",
    re.IGNORECASE,
)
NO_SOIL = re.compile(
    r"not aware of any soil issues in relation to this land",
    re.IGNORECASE,
)
FLOODING_ALL = re.compile(
    r'this statement entitled ["“]?flooding["”]? appears on all lims',
    re.IGNORECASE,
)
WEATHERTIGHT_NONE = re.compile(
    r"has not been notified of any information under Section 124 of the Weathertight",
    re.IGNORECASE,
)


def parse_lim_pdf(path: Path, *, filename: str) -> dict[str, Any]:
    if path.stat().st_size > MAX_PDF_BYTES:
        return _fail(filename, "PDF 超过 15MB，未解析。")
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001
                return _fail(filename, "PDF 有打开密码，无法读取文字层。请导出无密码副本后再上传。")
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                pages.append(page.extract_text() or "")
            except Exception as exc:  # noqa: BLE001
                if "cryptography" in str(exc).lower() or isinstance(exc, DependencyError):
                    return _fail(filename, "加密 PDF 需要 cryptography 才能读文字层。")
                pages.append("")
        text = "\n".join(pages)
        parsed = parse_lim_text(text, filename=filename)
        parsed["page_count"] = len(pages)
        parsed["char_count"] = len(text.strip())
        return parsed
    except DependencyError:
        return _fail(filename, "加密 PDF 需要 cryptography 才能读文字层。")
    except (PdfReadError, OSError, ValueError) as exc:
        return _fail(filename, f"无法解析 PDF：{exc}")


def parse_lim_text(text: str, *, filename: str) -> dict[str, Any]:
    compact = re.sub(r"[ \t]+", " ", text or "")
    lowered = compact.lower()
    if len(compact.strip()) < 120:
        return _fail(filename, "PDF 几乎没有文字层。扫描件无法读取 LIM 正文，请上传可选中文字的议会 LIM PDF。")
    if not any(marker in lowered for marker in LIM_MARKERS):
        return _fail(
            filename,
            "这份 PDF 不像奥克兰议会正式 LIM（未读到 Land Information Memorandum / s44A 栏）。请上传客户已购买的 LIM。",
        )
    contamination = _section(compact, "Site Contamination", ("Wind Zones", "Soil Issues", "Flooding"))
    wind_text = _section(compact, "Wind Zones", ("Soil Issues", "Flooding", "Overland Flow"))
    soil_text = _section(compact, "Soil Issues", ("Flooding", "Overland Flow", "Exposure Zones"))
    flood_text = _section(compact, "Flooding", ("Overland Flow Path", "Overland Flow", "Exposure Zones", "Coastal Erosion"))
    olfp_text = _section(
        compact,
        "Overland Flow Path",
        ("Exposure Zones", "Coastal Erosion", "s44A(2)(b)", "Information on private"),
    )
    exposure_text = _section(compact, "Exposure Zones", ("Coastal Erosion", "s44A(2)(b)", "Information on private"))
    coastal_text = _section(
        compact,
        "Coastal Erosion",
        ("s44A(2)(b)", "Information on private and public stormwater", "Site Contamination"),
    )
    drain_text = _section(
        compact,
        "Information on private and public stormwater and sewerage drains",
        ("s44A(2)(ba)", "s44A(2)(c)", "Information relating to any rates", "Consents, Certificates"),
    )
    if not drain_text:
        drain_text = _section(compact, "s44A(2)(b)", ("s44A(2)(ba)", "s44A(2)(c)", "Consents, Certificates"))

    wind_match = WIND.search(wind_text or compact)
    exposure_match = EXPOSURE.search(exposure_text or compact)
    drainage = _drainage_notices(drain_text or compact)
    building = _nearby_ids(compact, BCO)
    crossings = _nearby_ids(compact, VXG)

    olfp_intersects = bool(OLFP_HIT.search(olfp_text or compact))
    olfp_absent = bool(OLFP_MISS.search(olfp_text or compact))
    no_contam = bool(NO_CONTAMINATION_DATA.search(contamination or compact))
    no_soil = bool(NO_SOIL.search(soil_text or compact))

    lim_address = _lim_address(compact)
    legal = _first(LEGAL_GLUED.search(compact), LEGAL.search(compact))
    issued_raw = _first(ISSUED_GLUED.search(compact), ISSUED.search(compact))
    app_raw = _first(APP_NO_GLUED.search(compact), APP_NO.search(compact))

    findings: list[str] = []
    if olfp_intersects:
        findings.append("正式 LIM 写明本户地块与一条或多条 Overland Flow Path 空间相交。")
    elif olfp_text and not olfp_absent:
        findings.append("正式 LIM 有 Overland Flow Path 栏，但正文未读到空间相交句。附图未做图像识别。")
    if drainage:
        first = drainage[0]
        findings.append(f"正式 LIM 管网通知 {first['lir_id']}：{first['description'][:160]}")
    if wind_match:
        findings.append(f"正式 LIM 风区 {wind_match.group(1)} {wind_match.group(2)} m/s。")
    if no_contam:
        findings.append("正式 LIM 写明议会监管记录没有场地污染数据。")
    if no_soil:
        findings.append("正式 LIM 写明议会不知本户有土壤问题。")

    return {
        "ok": True,
        "error": None,
        "filename": filename,
        "is_official_lim": True,
        "application_number": app_raw.group(1) if app_raw else None,
        "issued_at": _iso_date(issued_raw.group(1) if issued_raw else None),
        "issued_raw": issued_raw.group(1) if issued_raw else None,
        "lim_address": lim_address,
        "legal_description": _clean(legal.group(1) if legal else None),
        "site_contamination": {
            "has_regulatory_data": False if no_contam else None if not contamination else True,
            "evidence": _clip(contamination or "", 400),
        },
        "wind_zone": {
            "label": wind_match.group(1).title() if wind_match else None,
            "speed_mps": int(wind_match.group(2)) if wind_match else None,
            "evidence": _clip(wind_match.group(0) if wind_match else wind_text, 280),
        },
        "soil_issues": {
            "council_aware": False if no_soil else None if not soil_text else True,
            "evidence": _clip(soil_text or "", 400),
        },
        "flooding": {
            "all_lims_statement": bool(FLOODING_ALL.search(flood_text or compact)),
            "site_specific_plain": False,
            "evidence": _clip(flood_text or "", 500),
        },
        "overland_flow": {
            "intersects": True if olfp_intersects else False if olfp_absent or not (olfp_text or "").strip() else None,
            "evidence": _clip(olfp_text or "", 500),
        },
        "exposure_zone": {
            "label": _clean(exposure_match.group(1) if exposure_match else None),
            "evidence": _clip(exposure_text or "", 280),
        },
        "coastal_erosion": {
            "standard_text_only": "appears on all lims" in (coastal_text or compact).lower(),
            "evidence": _clip(coastal_text or "", 360),
        },
        "drainage_notices": drainage,
        "building_consents": building,
        "vehicle_crossings": crossings,
        "weathertight_notified": False if WEATHERTIGHT_NONE.search(compact) else None,
        "findings": findings,
        "warnings": [],
    }


def address_matches_project(lim_address: str | None, project_address: str) -> tuple[bool, str]:
    if not (lim_address or "").strip():
        return False, "这份 LIM 的文字层没有 LIM address，无法确认是否为本户。"
    lim_key = _street_key(lim_address)
    project_key = _street_key(project_address)
    if not lim_key or not project_key or lim_key != project_key:
        return False, f"这份 LIM 的地址是 {lim_address.strip()}，与当前项目 {project_address} 不一致。"
    lim_local = _locality_hint(lim_address)
    project_local = _locality_hint(project_address)
    if lim_local and project_local and lim_local != project_local:
        return False, (
            f"这份 LIM 是 {lim_address.strip()}，当前项目是 {project_address}。"
            "同一门牌号在不同郊区不算同一户。"
        )
    return True, ""


def _fail(filename: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "filename": filename,
        "is_official_lim": False,
        "char_count": 0,
        "page_count": 0,
        "findings": [],
        "warnings": [],
        "drainage_notices": [],
        "building_consents": [],
        "vehicle_crossings": [],
    }


def _section(text: str, start: str, ends: tuple[str, ...]) -> str:
    start_re = re.compile(re.escape(start), re.IGNORECASE)
    match = start_re.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    end_positions = []
    for heading in ends:
        found = re.search(re.escape(heading), rest, re.IGNORECASE)
        if found:
            end_positions.append(found.start())
    cut = min(end_positions) if end_positions else min(len(rest), 2500)
    return rest[:cut].strip()


def _drainage_notices(text: str) -> list[dict[str, str]]:
    notices: list[dict[str, str]] = []
    for match in LIR.finditer(text):
        body = re.sub(r"\s+", " ", match.group("body")).strip()
        notices.append(
            {
                "date": match.group("date"),
                "lir_id": match.group("lir"),
                "description": body[:400],
            }
        )
    if notices:
        return notices
    for match in LIR_LOOSE.finditer(text):
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 240)
        window = re.sub(r"\s+", " ", text[start:end]).strip()
        notices.append({"date": "", "lir_id": match.group(1), "description": window[:400]})
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in notices:
        if item["lir_id"] in seen:
            continue
        seen.add(item["lir_id"])
        unique.append(item)
    return unique


def _nearby_ids(text: str, pattern: re.Pattern[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        ident = match.group(1)
        if ident in seen:
            continue
        seen.add(ident)
        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 180)
        items.append({"id": ident, "evidence": re.sub(r"\s+", " ", text[start:end]).strip()[:280]})
    return items


def _lim_address(text: str) -> str | None:
    glued = LIM_ADDRESS.search(text)
    if glued:
        candidate = glued.group(1).strip().split("\n")[-1].strip()
        if len(candidate) >= 8:
            return re.sub(r"\s+", " ", candidate)
    lined = LIM_ADDRESS_LINE.search(text)
    if lined:
        return re.sub(r"\s+", " ", lined.group(1)).strip()
    return None


def _street_key(value: str) -> str | None:
    match = STREET_KEY.search(value or "")
    if not match:
        return None
    return f"{match.group(1).lower()} {match.group(2).lower()} {match.group(3).lower()}"


def _locality_hint(value: str) -> str | None:
    text = f" {re.sub(r'[^a-z0-9]+', ' ', (value or '').lower())} "
    if " howick " in text:
        return "howick"
    if " auckland central " in text or " city centre " in text or " cbd " in text:
        return "auckland-central"
    return None


def _iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _first(*matches: re.Match[str] | None) -> re.Match[str] | None:
    for item in matches:
        if item:
            return item
    return None


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", value).strip() or None


def _clip(value: str | None, limit: int) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
