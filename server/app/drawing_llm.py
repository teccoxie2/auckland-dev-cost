from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from .data_loader import pricebook

BLOCKED_ITEM_IDS = {"design_fee_designer_pct"}
ALLOWED_FIELD_KEYS = {
    "gfa_m2",
    "footprint_m2",
    "roof_m2",
    "storeys",
    "wall_height_m",
    "eaves_mm",
    "bedrooms",
    "bathrooms",
    "kitchens",
    "dwellings",
    "coverage_pct",
    "retaining_height_m",
    "stud_spacing_mm",
    "cladding",
    "site_area_m2",
}
ALLOWED_ZONES = {
    "foundation",
    "structure",
    "interior",
    "envelope",
    "roof",
    "joinery",
    "kitchen",
    "bathroom",
    "plumbing",
    "scaffold",
    "retaining",
    "other",
}
PRICE_MARK = re.compile(r"(\$|NZD|单价|总价|报价|NZ\$)", re.I)
INT_FIELDS = {
    "storeys",
    "bedrooms",
    "bathrooms",
    "kitchens",
    "dwellings",
    "eaves_mm",
    "stud_spacing_mm",
}


def llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def llm_model_name() -> str:
    return (
        os.environ.get("DRAWING_LLM_MODEL", "").strip()
        or os.environ.get("SITE_VISION_MODEL", "").strip()
        or "gpt-4o-mini"
    )


def catalog_for_prompt() -> list[dict[str, Any]]:
    book = pricebook()
    rows: list[dict[str, Any]] = []
    for item in book.get("items") or []:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in BLOCKED_ITEM_IDS:
            continue
        rows.append(
            {
                "id": item_id,
                "name_zh": item.get("name_zh"),
                "unit": item.get("unit"),
                "trade": item.get("trade"),
                "notes": item.get("notes"),
            }
        )
    for item in book.get("missing_on_purpose") or []:
        rows.append(
            {
                "id": item["id"],
                "name_zh": item.get("name_zh"),
                "unit": None,
                "priced": False,
                "notes": item.get("reason"),
            }
        )
    return rows


def combined_drawing_text(parts: list[dict[str, Any]], *, limit: int = 80_000) -> str:
    chunks: list[str] = []
    remaining = limit
    for part in parts:
        text = str(part.get("text") or "").strip()
        if not text:
            continue
        header = f"===== FILE {part.get('filename')} KIND {part.get('kind')} =====\n"
        body = text[: max(remaining - len(header), 0)]
        if not body:
            break
        chunks.append(header + body)
        remaining -= len(header) + len(body)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def evidence_in_source(evidence: str, source: str) -> bool:
    ev = normalize_text(evidence)
    src = normalize_text(source)
    if len(ev) < 6 or not src:
        return False
    return ev in src


def looks_like_price(text: str) -> bool:
    return bool(PRICE_MARK.search(text or ""))


def parse_llm_json(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for item in candidates:
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def call_drawing_llm(source_text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "ok": False,
            "error": {
                "code": "llm_unavailable",
                "message": "未配置 OPENAI_API_KEY，无法用大模型读图纸文字层。数量与金额都不会编造；请设置密钥后再验证。",
            },
        }
    if not source_text.strip():
        return {
            "ok": False,
            "error": {
                "code": "drawing_empty",
                "message": "图纸没有可送给模型的文字层。",
            },
        }
    catalog = catalog_for_prompt()
    model = llm_model_name()
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    prompt = (
        "你在读新西兰奥克兰住宅 Resource Consent / Building Consent PDF 的文字层。"
        "只根据下面图纸正文做结构化抽取，不要发明正文里没有的毫米、面积或件数。"
        "禁止输出任何价格、单价、总价、NZD 或 $。"
        "门窗只能从文字层的门窗表读取。"
        "材料行的 item_id 必须来自给定价库目录；目录不含单价，你也不许写单价。"
        "数量可以按常识配比填写，服务器会用公式或门窗表重算，不会采用你写的金额。\n"
        "只返回 JSON："
        '{"summary_zh":"中文简述读到的户型",'
        '"fields":[{"key":"gfa_m2","value":186.4,"evidence":"原文短句"}],'
        '"windows":[{"code":"W1","w_mm":1800,"h_mm":1200,"count":4,"evidence":"原文短句"}],'
        '"lines":[{"item_id":"kaboodle_base_600","quantity":5,"zone":"kitchen",'
        '"evidence":"原文短句","reason_zh":"为何计入此 SKU"}],'
        '"unmapped":[{"name_zh":"说明","quantity":1,"unit":"ea","evidence":"原文","reason_zh":"价库没有对应 SKU"}]}\n'
        f"fields.key 只能是 {sorted(ALLOWED_FIELD_KEYS)}。zone 只能是 {sorted(ALLOWED_ZONES)}。\n"
        f"价库目录：{json.dumps(catalog, ensure_ascii=False)}\n"
        f"图纸文字：\n{source_text}"
    )
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
        raw = payload["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": {
                "code": "llm_failed",
                "message": f"大模型读取图纸失败：{exc}。未编造材料或金额。",
            },
        }
    parsed = parse_llm_json(raw)
    if not parsed:
        return {
            "ok": False,
            "error": {
                "code": "llm_failed",
                "message": "大模型没有返回可解析的 JSON。未编造材料或金额。",
            },
        }
    return {"ok": True, "model": model, "payload": parsed}


def ground_fields(raw_fields: Any, source_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fields: dict[str, Any] = {}
    rejected: list[dict[str, Any]] = []
    if not isinstance(raw_fields, list):
        return fields, rejected
    for item in raw_fields:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if key not in ALLOWED_FIELD_KEYS:
            rejected.append({"item_id": key or "field", "reason_zh": "字段名不在允许列表。"})
            continue
        if not evidence_in_source(evidence, source_text):
            rejected.append({"item_id": key, "reason_zh": "字段证据未出现在图纸文字层，已丢弃。"})
            continue
        value = item.get("value")
        if key == "cladding":
            text = str(value or "").strip()
            if not text:
                rejected.append({"item_id": key, "reason_zh": "外墙做法没有可读值。"})
                continue
            fields[key] = {"value": text, "evidence": evidence, "source_file": "llm"}
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            rejected.append({"item_id": key, "reason_zh": "字段值不是数字。"})
            continue
        if key in INT_FIELDS:
            number = int(round(number))
        fields[key] = {"value": number, "evidence": evidence, "source_file": "llm"}
    return fields, rejected


def ground_windows(raw_windows: Any, source_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    windows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    if not isinstance(raw_windows, list):
        return windows, rejected
    seen: set[str] = set()
    for item in raw_windows:
        if not isinstance(item, dict):
            continue
        evidence = str(item.get("evidence") or "").strip()
        code = re.sub(r"\s+", "", str(item.get("code") or "")).upper()
        if not code:
            rejected.append({"item_id": "window", "reason_zh": "门窗缺少代码。"})
            continue
        if not evidence_in_source(evidence, source_text):
            rejected.append({"item_id": code, "reason_zh": "门窗证据未出现在图纸文字层，已丢弃。"})
            continue
        try:
            width = int(item.get("w_mm"))
            height = int(item.get("h_mm"))
            count = int(item.get("count") or 1)
        except (TypeError, ValueError):
            rejected.append({"item_id": code, "reason_zh": "门窗尺寸或数量不是整数。"})
            continue
        if width < 400 or height < 350 or width > 7000 or height > 4000 or count < 1:
            rejected.append({"item_id": code, "reason_zh": "门窗尺寸或数量超出可信范围。"})
            continue
        if code in seen:
            continue
        seen.add(code)
        windows.append(
            {
                "code": code,
                "w_mm": width,
                "h_mm": height,
                "count": count,
                "evidence": evidence,
                "source_file": "llm",
            }
        )
    return windows, rejected
