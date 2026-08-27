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


DEFAULT_DRAWING_MODEL = "gpt-5.6-luna"
CHAT_TIMEOUT = httpx.Timeout(connect=8.0, read=90.0, write=30.0, pool=8.0)
PROBE_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=8.0, pool=5.0)


def llm_api_key() -> str:
    return (os.environ.get("CPA_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()


def llm_configured() -> bool:
    return bool(llm_api_key())


def llm_base_url() -> str:
    raw = (os.environ.get("CPA_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip()
    if not raw:
        return "https://api.openai.com/v1"
    raw = re.sub(r"/management\.html.*$", "", raw, flags=re.I)
    raw = re.sub(r"/chat/completions/?$", "", raw, flags=re.I).rstrip("/")
    if raw.endswith("/v1"):
        return raw
    return f"{raw}/v1"


def llm_model_name(available: list[str] | None = None) -> str:
    requested = (
        os.environ.get("DRAWING_LLM_MODEL", "").strip()
        or os.environ.get("SITE_VISION_MODEL", "").strip()
        or DEFAULT_DRAWING_MODEL
    )
    lookup = {item.lower(): item for item in (available or [])}
    if requested.lower() in lookup:
        return lookup[requested.lower()]
    return requested


def llm_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {llm_api_key()}", "Content-Type": "application/json"}


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


def list_llm_models() -> tuple[list[str], str | None, int | None]:
    if not llm_configured():
        return [], "未配置 CPA_API_KEY / OPENAI_API_KEY。", None
    base = llm_base_url()
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT) as client:
            response = client.get(f"{base}/models", headers=llm_headers())
        if response.status_code in {401, 403}:
            return [], f"HTTP {response.status_code} 密钥无效或无权限", response.status_code
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        return [], str(exc), None
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return [], "模型列表格式无法解析。", None
    names: list[str] = []
    for item in rows:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            name = str(item.get("id") or item.get("name") or "").strip()
            if name:
                names.append(name)
    return list(dict.fromkeys(names)), None, 200


def probe_llm(*, ping_chat: bool = False) -> dict[str, Any]:
    if not llm_configured():
        return {
            "configured": False,
            "reachable": False,
            "authorized": False,
            "base_url": None,
            "model": None,
            "models": [],
            "note": "未配置 CPA_API_KEY 或 OPENAI_API_KEY，无法调用本地 CPA / 大模型，也不会编造材料清单。",
        }
    base = llm_base_url()
    models, list_error, status = list_llm_models()
    model = llm_model_name(models)
    result: dict[str, Any] = {
        "configured": True,
        "reachable": status is not None or list_error is None,
        "authorized": list_error is None,
        "base_url": base,
        "model": model,
        "models": models[:24],
        "note": "",
    }
    if status in {401, 403}:
        result["reachable"] = True
        result["authorized"] = False
        result["note"] = (
            f"已连上 {base}，但密钥被 CPA 拒绝（HTTP {status}）。"
            "请在本机管理页复制「API Keys / 客户端密钥」，不要用管理密钥或之前那串无效的 cpa- 值。"
        )
        return result
    if list_error:
        result["reachable"] = False
        result["authorized"] = False
        result["note"] = f"已配置密钥，但连不上 {base}：{list_error}"
        return result
    result["reachable"] = True
    result["authorized"] = True
    if not ping_chat:
        result["note"] = f"已连上 {base}，模型 {model}。本页用它读文字层选 SKU，数量按公式或门窗表重算，单价只走价库。"
        return result
    try:
        raw, used_model = _chat_completion(
            model,
            [{"role": "user", "content": '只返回 JSON：{"ok":true}'}],
            timeout=PROBE_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        result["reachable"] = False
        result["note"] = f"模型列表可读，但 chat/completions 失败：{exc}"
        return result
    parsed = parse_llm_json(raw)
    result["model"] = used_model
    result["chat_ok"] = bool(parsed)
    result["note"] = (
        f"已用 {used_model} 完成一次 CPA 试调用。"
        if parsed
        else f"已连上 CPA，但试调用没有返回 JSON：{(raw or '')[:180]}"
    )
    return result


def _chat_completion(
    model: str,
    messages: list[dict[str, Any]],
    *,
    timeout: httpx.Timeout = CHAT_TIMEOUT,
) -> tuple[str, str]:
    base = llm_base_url()
    body = {
        "model": model,
        "temperature": 0,
        "messages": messages,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{base}/chat/completions",
            headers=llm_headers(),
            json={**body, "response_format": {"type": "json_object"}},
        )
        if response.status_code >= 400:
            retry = client.post(f"{base}/chat/completions", headers=llm_headers(), json=body)
            retry.raise_for_status()
            payload = retry.json()
        else:
            response.raise_for_status()
            payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(str(part.get("text") or part) if isinstance(part, dict) else str(part) for part in content)
    return str(content or ""), str(payload.get("model") or model)


def call_drawing_llm(source_text: str) -> dict[str, Any]:
    if not llm_configured():
        return {
            "ok": False,
            "error": {
                "code": "llm_unavailable",
                "message": "未配置 CPA_API_KEY / OPENAI_API_KEY，无法用大模型读图纸文字层。数量与金额都不会编造；请设置密钥后再验证。",
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
    models, _list_error, _status = list_llm_models()
    model = llm_model_name(models)
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
        raw, used_model = _chat_completion(model, [{"role": "user", "content": prompt}])
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
    return {"ok": True, "model": used_model, "payload": parsed}


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
