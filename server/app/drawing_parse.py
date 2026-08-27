from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import DependencyError, PdfReadError

MAX_PDF_BYTES = 15 * 1024 * 1024

WINDOW_ROW = re.compile(
    r"(?P<code>(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+)\s+"
    r"(?P<a>\d{3,4})\s*[xX×]\s*(?P<b>\d{3,4})"
    r"(?:\s*(?:mm)?)?"
    r"(?:\s*(?:qty|no\.?|×|x)\s*(?P<qty>\d{1,2}))?",
    re.IGNORECASE,
)
COLUMN_WINDOW = re.compile(
    r"(?P<code>(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+)\s+"
    r"(?P<a>\d{3,4})(?:\s*mm)?\s+"
    r"(?P<b>\d{3,4})(?:\s*mm)?"
    r"(?:\s+(?P<qty>\d{1,2}))?"
    r"(?:\s+(?P<kind>[A-Za-z][A-Za-z +/.-]{1,24}))?",
    re.IGNORECASE,
)
HW_THEN_CODE = re.compile(
    r"(?P<h>\d{3,4})\s*[Hh]\s*[xX×]\s*(?P<w>\d{3,4})\s*[Ww]\s+"
    r"(?P<code>(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+)",
    re.IGNORECASE,
)
SIZE_THEN_CODE = re.compile(
    r"(?P<a>\d{3,4})\s*[xX×]\s*(?P<b>\d{3,4})\s+"
    r"(?P<code>(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+)",
    re.IGNORECASE,
)
WIDTH_THEN_ED = re.compile(
    r"(?P<w>\d{3,4})\s*[Ww]\s+(?P<code>ED[-\s]?\d+)",
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
    r"(?:gross\s+floor\s+area|total\s+gfa|gfa\s+total|gfa|总建筑面积|建筑面积)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²)?",
    re.IGNORECASE,
)
FLOOR_AREA = re.compile(
    r"(?P<label>ground\s+floor(?:\s+area)?|first\s+floor(?:\s+area)?|second\s+floor(?:\s+area)?|"
    r"level\s+\d(?:\s+area)?|total\s+gfa|gross\s+floor\s+area|gfa|roof(?:ing)?\s+area|"
    r"底层面积|一楼面积|二楼面积|屋面面积)\s*[:：]?\s*(?P<val>\d+(?:\.\d+)?)\s*(?:m2|m²)?",
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
    r"retaining\s+wall[^\d]{0,40}?(\d+(?:\.\d+)?)\s*m",
    re.IGNORECASE,
)
PROPOSED_COVERAGE = re.compile(
    r"Proposed Coverage\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
GROSS_SITE = re.compile(r"Gross Site Area\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
SECOND_FLOOR = re.compile(r"second\s+floor", re.IGNORECASE)
FIRST_FLOOR = re.compile(r"first\s+floor", re.IGNORECASE)
LOT_FFL = re.compile(r"\bLOT\s+([1-9])\s+FFL", re.IGNORECASE)
STREET_ADDRESS = re.compile(r"Street Address\s+([^,\n]{5,80})", re.IGNORECASE)
ROAD_ADDRESS = re.compile(
    r"(\d+[A-Za-z]?\s+[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z'-]+)?\s+(?:Road|Street|Avenue|Drive|Place|Lane|Crescent))",
    re.IGNORECASE,
)
BED_RM = re.compile(r"(?:MASTER\s+BR|BED\s*RM)\s*(\d)", re.IGNORECASE)
BLOCK = re.compile(r"block\s+veneer|concrete\s+block\s+cladding|砌块贴面", re.IGNORECASE)
STUD_400 = re.compile(r"(?:stud(?:s)?\s+(?:centres?|centers?|spacing)\s*[:：]?\s*400|立柱间距\s*400)", re.IGNORECASE)


def _empty_parse(kind: str, filename: str, error: str, warning: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "filename": filename,
        "error": error,
        "char_count": 0,
        "page_count": 0,
        "text": "",
        "fields": {},
        "windows": [],
        "charts": [],
        "page_debug": [],
        "pages": [],
        "warnings": [warning],
        "address_hint": None,
    }


def group_text_items(items: list[tuple[float, float, str]], y_tol: float = 3.0) -> str:
    pieces = [(float(y), float(x), str(text or "").replace("\n", " ").strip()) for y, x, text in items]
    pieces = [item for item in pieces if item[2]]
    if not pieces:
        return ""
    ordered = sorted(pieces, key=lambda item: (-item[0], item[1]))
    lines: list[str] = []
    bucket: list[tuple[float, str]] = []
    current_y = ordered[0][0]
    for y, x, text in ordered:
        if bucket and abs(y - current_y) > y_tol:
            bucket.sort(key=lambda item: item[0])
            lines.append(" ".join(item[1] for item in bucket))
            bucket = [(x, text)]
            current_y = y
        else:
            bucket.append((x, text))
            if not lines and not bucket[1:]:
                current_y = y
    if bucket:
        bucket.sort(key=lambda item: item[0])
        lines.append(" ".join(item[1] for item in bucket))
    return "\n".join(lines)


def _schedule_hits(text: str) -> int:
    blob = text or ""
    return len(re.findall(r"\b(?:EW|ED|DW|SL|RS|W|D)[-\s]?\d+\b", blob, re.I)) + len(
        re.findall(r"schedule|gfa|qty|m2|m²|window|door", blob, re.I)
    )


def extract_page_layers(page) -> dict[str, str]:
    glyphs: list[tuple[float, float, str]] = []

    def visitor(text, _cm, tm, _font_dict, _font_size) -> None:
        if not text:
            return
        try:
            glyphs.append((float(tm[5]), float(tm[4]), str(text)))
        except (TypeError, ValueError, IndexError):
            return

    plain = ""
    try:
        plain = page.extract_text(visitor_text=visitor) or ""
    except TypeError:
        try:
            plain = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            plain = ""
    except Exception:  # noqa: BLE001
        plain = ""
    rows = group_text_items(glyphs)
    layout = ""
    try:
        layout = page.extract_text(extraction_mode="layout") or ""
    except Exception:  # noqa: BLE001
        layout = ""
    candidates = [item for item in (layout, rows, plain) if item and str(item).strip()]
    if not candidates:
        return {"plain": plain, "layout": layout, "rows": rows, "text": ""}
    best = max(candidates, key=lambda text: (_schedule_hits(text), len(text)))
    merged = "\n".join(dict.fromkeys(candidates))
    return {"plain": plain, "layout": layout, "rows": rows, "text": merged or best}


def page_role(text: str, table_rows: int) -> str:
    n = len((text or "").strip())
    if n < 40:
        return "drawing_no_text"
    if table_rows or re.search(r"schedule|window|door|gfa|qty", text or "", re.I):
        return "schedule"
    return "notes"


def extract_charts(text: str, *, filename: str, page: int | None = None) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    seen_lines: set[str] = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if len(line) < 4 or line in seen_lines:
            continue
        match = WINDOW_ROW.search(line) or COLUMN_WINDOW.search(line) or HW_THEN_CODE.search(line) or SIZE_THEN_CODE.search(line)
        if not match:
            continue
        groups = match.groupdict()
        width = int(groups.get("w") or groups.get("a") or 0)
        height = int(groups.get("h") or groups.get("b") or 0)
        if groups.get("w") and groups.get("h"):
            width, height = int(groups["w"]), int(groups["h"])
        elif groups.get("a") and groups.get("b"):
            width, height = _orient(str(groups.get("code") or "W"), int(groups["a"]), int(groups["b"]))
        if not _plausible_opening(width, height):
            continue
        seen_lines.add(line)
        window_rows.append(
            {
                "line": line,
                "code": re.sub(r"\s+", "", str(groups.get("code") or "")).upper(),
                "w_mm": width,
                "h_mm": height,
                "count": int(groups.get("qty") or 1),
                "kind": (groups.get("kind") or "").strip() or None,
                "evidence": match.group(0).strip(),
            }
        )
    if window_rows:
        charts.append(
            {
                "id": "window_schedule",
                "name_zh": "门窗表",
                "source_file": filename,
                "page": page,
                "rows": window_rows,
            }
        )
    area_rows: list[dict[str, Any]] = []
    seen_area: set[str] = set()
    for match in FLOOR_AREA.finditer(text or ""):
        evidence = match.group(0).strip()
        if evidence in seen_area:
            continue
        seen_area.add(evidence)
        area_rows.append(
            {
                "line": evidence,
                "label": match.group("label"),
                "value": match.group("val"),
                "evidence": evidence,
            }
        )
    if area_rows:
        charts.append(
            {
                "id": "area_schedule",
                "name_zh": "面积表",
                "source_file": filename,
                "page": page,
                "rows": area_rows,
            }
        )
    coverage_rows: list[dict[str, Any]] = []
    seen_cov: set[str] = set()
    for match in PROPOSED_COVERAGE.finditer(text or ""):
        evidence = match.group(0).strip()
        if evidence in seen_cov:
            continue
        seen_cov.add(evidence)
        coverage_rows.append(
            {
                "line": evidence,
                "label": "Proposed Coverage",
                "pct": match.group(1),
                "area_m2": match.group(2),
                "evidence": evidence,
            }
        )
    for match in GROSS_SITE.finditer(text or ""):
        evidence = match.group(0).strip()
        if evidence in seen_cov:
            continue
        seen_cov.add(evidence)
        coverage_rows.append(
            {
                "line": evidence,
                "label": "Gross Site Area",
                "value": match.group(1),
                "evidence": evidence,
            }
        )
    if coverage_rows:
        charts.append(
            {
                "id": "coverage_schedule",
                "name_zh": "覆盖率 / 地块面积表",
                "source_file": filename,
                "page": page,
                "rows": coverage_rows,
            }
        )
    return charts


def extract_pdf(path: Path, *, kind: str, filename: str) -> dict[str, Any]:
    if path.stat().st_size > MAX_PDF_BYTES:
        return _empty_parse(kind, filename, "PDF 超过 15MB，未解析。", "file_too_large")
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001
                return _empty_parse(
                    kind,
                    filename,
                    "PDF 有打开密码，无法读取文字层。请导出无密码副本后再上传。",
                    "encrypted_password",
                )
        pages = []
        page_warnings: list[str] = []
        page_debug: list[dict[str, Any]] = []
        charts: list[dict[str, Any]] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                layers = extract_page_layers(page)
                text = layers.get("text") or ""
            except Exception as exc:  # noqa: BLE001
                page_warnings.append(f"page_{index}_unreadable")
                text = ""
                layers = {"plain": "", "layout": "", "rows": "", "text": ""}
                if "cryptography" in str(exc).lower() or isinstance(exc, DependencyError):
                    return _empty_parse(
                        kind,
                        filename,
                        "加密 PDF 需要 cryptography 才能读文字层。服务已缺少该依赖时请重试。",
                        "aes_dependency",
                    )
            page_charts = extract_charts(text, filename=filename, page=index)
            table_rows = sum(len(item.get("rows") or []) for item in page_charts)
            role = page_role(text, table_rows)
            if role == "drawing_no_text":
                page_warnings.append(f"page_{index}_drawing_no_text")
            pages.append({"page": index, "text": text, "plain": layers.get("plain"), "layout": layers.get("layout")})
            page_debug.append(
                {
                    "page": index,
                    "filename": filename,
                    "kind": kind,
                    "char_count": len(text.strip()),
                    "role": role,
                    "table_rows": table_rows,
                    "preview": re.sub(r"\s+", " ", text).strip()[:280],
                }
            )
            charts.extend(page_charts)
        text = "\n".join(item["text"] for item in pages)
        parsed = extract_from_text(text, kind=kind, filename=filename)
        parsed["page_count"] = len(pages)
        parsed["char_count"] = len(text.strip())
        parsed["text"] = text
        parsed["pages"] = [{"page": item["page"], "text": item["text"]} for item in pages]
        parsed["page_debug"] = page_debug
        if charts:
            parsed["charts"] = charts
        parsed["warnings"] = list(dict.fromkeys([*(parsed.get("warnings") or []), *page_warnings]))
        if parsed["char_count"] < 80 and not parsed["fields"] and not parsed["windows"]:
            parsed["warnings"].append("scanned_or_empty_text")
            parsed["error"] = parsed.get("error") or "PDF 几乎没有文字层。扫描件无法按尺寸套价，请上传可选中文字的 RC/BC 图，或提供 IFC。"
        no_text = sum(1 for item in page_debug if item.get("role") == "drawing_no_text")
        if no_text:
            parsed["warnings"].append(f"有 {no_text} 页几乎无文字层，图里的尺寸和线型未读取，也不做图像识别。")
        return parsed
    except DependencyError:
        return _empty_parse(
            kind,
            filename,
            "加密 PDF 需要 cryptography 才能读文字层。",
            "aes_dependency",
        )
    except (PdfReadError, OSError, ValueError) as exc:
        return _empty_parse(kind, filename, f"无法解析 PDF：{exc}", "pdf_unreadable")


def extract_from_text(text: str, *, kind: str, filename: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", " ", text)
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
    _put_int(fields, "kitchens", KITCHENS, compact, filename, lo=1, hi=12)
    _put_int(fields, "dwellings", DWELLINGS, compact, filename, lo=1, hi=12)
    coverage = COVERAGE.search(compact)
    if coverage:
        fields["coverage_pct"] = {
            "value": float(coverage.group(1)),
            "evidence": coverage.group(0),
            "source_file": filename,
        }
    proposed = PROPOSED_COVERAGE.search(compact)
    if proposed:
        fields["coverage_pct"] = {
            "value": float(proposed.group(1)),
            "evidence": proposed.group(0),
            "source_file": filename,
        }
        fields["footprint_m2"] = {
            "value": float(proposed.group(2)),
            "evidence": proposed.group(0),
            "source_file": filename,
        }
    site_area = GROSS_SITE.search(compact)
    if site_area:
        fields["site_area_m2"] = {
            "value": float(site_area.group(1)),
            "evidence": site_area.group(0),
            "source_file": filename,
        }
    retain = RETAIN_H.search(compact)
    if retain:
        fields["retaining_height_m"] = {
            "value": float(retain.group(1)),
            "evidence": retain.group(0),
            "source_file": filename,
        }
    lots = sorted({int(item) for item in LOT_FFL.findall(compact)})
    if len(lots) >= 2:
        fields["dwellings"] = {
            "value": len(lots),
            "evidence": "、".join(f"LOT {item} FFL" for item in lots),
            "source_file": filename,
        }
        fields["kind_guess"] = {
            "value": "terrace" if len(lots) >= 3 else "duplex",
            "evidence": fields["dwellings"]["evidence"],
            "source_file": filename,
        }
    if SECOND_FLOOR.search(compact) and int(_value(fields, "storeys") or 1) < 3:
        fields["storeys"] = {"value": 3, "evidence": "图纸含 Second Floor", "source_file": filename}
    elif FIRST_FLOOR.search(compact) and "storeys" not in fields:
        fields["storeys"] = {"value": 2, "evidence": "图纸含 First Floor", "source_file": filename}
    bed_nos = [int(item) for item in BED_RM.findall(compact)]
    if bed_nos and int(_value(fields, "bedrooms") or 0) < max(bed_nos):
        fields["bedrooms"] = {
            "value": max(bed_nos),
            "evidence": f"MASTER BR / BED RM 最大 {max(bed_nos)}",
            "source_file": filename,
        }
    dwellings = int(_value(fields, "dwellings") or 0)
    if dwellings and re.search(r"\bKITCHEN\b", compact, re.I) and int(_value(fields, "kitchens") or 0) < dwellings:
        fields["kitchens"] = {
            "value": dwellings,
            "evidence": f"每套有 Kitchen 标注，按 {dwellings} 套计",
            "source_file": filename,
        }
    wet = 0
    wet_bits = []
    if re.search(r"\bENS\s*1\b", compact, re.I):
        wet += 1
        wet_bits.append("ENS 1")
    if re.search(r"\bENS\s*2\b", compact, re.I):
        wet += 1
        wet_bits.append("ENS 2")
    if re.search(r"\bBATH\b", compact, re.I):
        wet += 1
        wet_bits.append("BATH")
    if dwellings and wet and int(_value(fields, "bathrooms") or 0) < wet * dwellings:
        fields["bathrooms"] = {
            "value": wet * dwellings,
            "evidence": f"每套 {'+'.join(wet_bits)}，×{dwellings} 套",
            "source_file": filename,
        }
    if BLOCK.search(compact) or STUD_400.search(compact):
        evidence = (BLOCK.search(compact) or STUD_400.search(compact)).group(0)
        fields["stud_spacing_mm"] = {"value": 400, "evidence": evidence, "source_file": filename}
        fields["cladding"] = {"value": "block_veneer", "evidence": evidence, "source_file": filename}

    charts = extract_charts(text, filename=filename)
    apply_chart_fields(fields, charts, filename)
    windows = merge_window_lists(_windows(f"{text}\n{compact}", filename), windows_from_charts(charts))
    if not windows:
        warnings.append("no_window_schedule")

    return {
        "kind": kind,
        "filename": filename,
        "error": None,
        "text": text,
        "char_count": len(text.strip()),
        "fields": fields,
        "windows": windows,
        "charts": charts,
        "page_debug": [],
        "warnings": warnings,
        "address_hint": _address_hint(compact),
    }


def windows_from_charts(charts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for chart in charts or []:
        if chart.get("id") != "window_schedule":
            continue
        filename = str(chart.get("source_file") or "")
        for row in chart.get("rows") or []:
            code = re.sub(r"\s+", "", str(row.get("code") or "")).upper()
            if not code:
                continue
            try:
                width = int(row.get("w_mm") or 0)
                height = int(row.get("h_mm") or 0)
                count = int(row.get("count") or 1)
            except (TypeError, ValueError):
                continue
            if not _plausible_opening(width, height) or count < 1:
                continue
            previous = found.get(code)
            if previous is not None and int(previous.get("count") or 1) >= count:
                continue
            found[code] = {
                "code": code,
                "w_mm": width,
                "h_mm": height,
                "count": count,
                "evidence": str(row.get("evidence") or row.get("line") or ""),
                "source_file": filename,
                "kind": row.get("kind"),
            }
    return list(found.values())


def merge_window_lists(
    primary: list[dict[str, Any]] | None,
    extra: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    for item in primary or []:
        code = re.sub(r"\s+", "", str(item.get("code") or "")).upper()
        if code:
            by_code[code] = item
    for item in extra or []:
        code = re.sub(r"\s+", "", str(item.get("code") or "")).upper()
        if not code:
            continue
        previous = by_code.get(code)
        if previous is None:
            by_code[code] = item
            continue
        extra_count = int(item.get("count") or 0)
        previous_count = int(previous.get("count") or 0)
        if extra_count > previous_count:
            by_code[code] = {**item, "source_file": item.get("source_file") or previous.get("source_file")}
        elif item.get("kind") and not previous.get("kind"):
            previous["kind"] = item.get("kind")
    return list(by_code.values())


def apply_chart_fields(fields: dict[str, Any], charts: list[dict[str, Any]] | None, filename: str) -> None:
    for chart in charts or []:
        source = str(chart.get("source_file") or filename)
        if chart.get("id") == "area_schedule":
            for row in chart.get("rows") or []:
                label = str(row.get("label") or "").lower()
                try:
                    value = float(row.get("value"))
                except (TypeError, ValueError):
                    continue
                evidence = str(row.get("evidence") or row.get("line") or "")
                key = None
                if "total" in label or "gross" in label or label.strip() in {"gfa"} or "总建筑" in label or "建筑面积" in label:
                    key = "gfa_m2"
                elif "ground" in label or "底层" in label or "占地" in label:
                    key = "footprint_m2"
                elif "roof" in label or "屋面" in label:
                    key = "roof_m2"
                if not key or key in fields:
                    continue
                fields[key] = {"value": value, "evidence": evidence, "source_file": source}
        elif chart.get("id") == "coverage_schedule":
            for row in chart.get("rows") or []:
                evidence = str(row.get("evidence") or row.get("line") or "")
                if row.get("pct") and "coverage_pct" not in fields:
                    try:
                        fields["coverage_pct"] = {
                            "value": float(row["pct"]),
                            "evidence": evidence,
                            "source_file": source,
                        }
                    except (TypeError, ValueError):
                        pass
                if row.get("area_m2") and "footprint_m2" not in fields:
                    try:
                        fields["footprint_m2"] = {
                            "value": float(row["area_m2"]),
                            "evidence": evidence,
                            "source_file": source,
                        }
                    except (TypeError, ValueError):
                        pass
                if str(row.get("label") or "").lower().startswith("gross site") and "site_area_m2" not in fields:
                    try:
                        fields["site_area_m2"] = {
                            "value": float(row.get("value")),
                            "evidence": evidence,
                            "source_file": source,
                        }
                    except (TypeError, ValueError):
                        pass


def _value(fields: dict[str, Any], key: str):
    item = fields.get(key)
    if item is None:
        return None
    if isinstance(item, dict) and "value" in item:
        return item["value"]
    return item


def _address_hint(text: str) -> str | None:
    street = STREET_ADDRESS.search(text)
    if street:
        return street.group(1).strip()
    road = ROAD_ADDRESS.search(text)
    if road:
        return road.group(1).strip()
    return None


def _road_key(hint: str | None) -> str:
    if not hint:
        return ""
    match = re.search(r"([a-z]+)\s+(?:road|street|avenue|drive|place|lane|crescent)", hint.lower())
    return match.group(1) if match else re.sub(r"[^a-z]+", "", hint.lower())


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
    charts: list[dict[str, Any]] = []
    page_debug: list[dict[str, Any]] = []
    rc_road = next((_road_key(part.get("address_hint")) for part in parts if part.get("kind") == "rc" and part.get("address_hint")), "")
    for part in parts:
        documents.append(
            {
                "kind": part.get("kind"),
                "filename": part.get("filename"),
                "page_count": part.get("page_count"),
                "char_count": part.get("char_count"),
                "error": part.get("error"),
                "address_hint": part.get("address_hint"),
            }
        )
        if part.get("error") and part.get("char_count", 0) < 80:
            errors.append(part["error"])
        warnings.extend(part.get("warnings") or [])
        part_road = _road_key(part.get("address_hint"))
        if rc_road and part.get("kind") != "rc" and part_road and part_road != rc_road:
            warnings.append(
                f"{part.get('filename')} 文字层地址是「{part.get('address_hint')}」，"
                f"与 RC 的道路「{rc_road}」不一致，这份图的面积和门窗表未并入。"
            )
            continue
        kind = part.get("kind")
        charts.extend(part.get("charts") or [])
        page_debug.extend(part.get("page_debug") or [])
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
        "charts": charts,
        "page_debug": page_debug,
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

    def add(code: str, width: int, height: int, evidence: str, qty: int = 1) -> None:
        if not _plausible_opening(width, height):
            return
        key = re.sub(r"\s+", "", code).upper()
        if key in found:
            if qty > int(found[key].get("count") or 1):
                found[key]["count"] = qty
                found[key]["evidence"] = evidence.strip()
            return
        found[key] = {
            "code": key,
            "w_mm": width,
            "h_mm": height,
            "count": qty,
            "evidence": evidence.strip(),
            "source_file": filename,
        }

    for match in HW_THEN_CODE.finditer(text):
        add(match.group("code"), int(match.group("w")), int(match.group("h")), match.group(0))
    for match in WINDOW_ROW.finditer(text):
        width, height = _orient(match.group("code"), int(match.group("a")), int(match.group("b")))
        add(match.group("code"), width, height, match.group(0), int(match.group("qty") or 1))
    for match in COLUMN_WINDOW.finditer(text):
        width, height = _orient(match.group("code"), int(match.group("a")), int(match.group("b")))
        add(match.group("code"), width, height, match.group(0), int(match.group("qty") or 1))
    for match in SIZE_THEN_CODE.finditer(text):
        width, height = _orient(match.group("code"), int(match.group("a")), int(match.group("b")))
        add(match.group("code"), width, height, match.group(0))
    door_heights = [item["h_mm"] for item in found.values() if str(item["code"]).startswith("ED")]
    default_h = 2100 if any(1960 <= item <= 2100 for item in door_heights) else None
    if default_h:
        for match in WIDTH_THEN_ED.finditer(text):
            code = match.group("code")
            width = int(match.group("w"))
            add(code, width, default_h, f"{match.group(0)}（高度未标，同图 ED 为 {default_h}H）")
    if found:
        return list(found.values())
    loose: list[dict[str, Any]] = []
    for match in list(DIM_WH.finditer(text)) + list(DIM_HW.finditer(text)):
        width = int(match.group("w"))
        height = int(match.group("h"))
        if not _plausible_opening(width, height):
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


def _plausible_opening(width: int, height: int) -> bool:
    if width < 400 or height < 350:
        return False
    if width > 7000 or height > 4000:
        return False
    return True


def _orient(code: str, a: int, b: int) -> tuple[int, int]:
    code_u = re.sub(r"\s+", "", code).upper()
    if max(a, b) >= 2400:
        return max(a, b), min(a, b)
    if code_u.startswith("ED") or code_u.startswith("D"):
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
