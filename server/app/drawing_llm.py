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
CHAT_TIMEOUT = httpx.Timeout(connect=8.0, read=120.0, write=30.0, pool=8.0)
PROBE_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=8.0, pool=5.0)
PAGE_CHUNK = 3_500
FIRST_PAGE_CAP = 6_000
HINT_RE = re.compile(
    r"schedule|window|door|joinery|gfa|gross\s*floor|floor\s*area|m²|m2|"
    r"kitchen|bath|ensuite|\bens\b|bedroom|coverage|eaves|retain|cladding|stud|"
    r"qty|quantity|roof|slab|foundation|insulation|gib|timber|plumb|"
    r"area|dwelling|storey|lintel|joist|\b(?:ew|ed|dw|sl|rs|w|d)[-\s]?\d+",
    re.I,
)


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


def _iter_pages(part: dict[str, Any]) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    raw_pages = part.get("pages")
    if isinstance(raw_pages, list) and raw_pages:
        for item in raw_pages:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "")
            try:
                page = int(item.get("page") or 0)
            except (TypeError, ValueError):
                page = 0
            rows.append((page or len(rows) + 1, text))
        if rows:
            return rows
    text = str(part.get("text") or "")
    if not text:
        return []
    index = 1
    for start in range(0, len(text), PAGE_CHUNK):
        rows.append((index, text[start : start + PAGE_CHUNK]))
        index += 1
    return rows


def _chunk_score(text: str) -> int:
    if not str(text).strip():
        return -1
    return len(HINT_RE.findall(text))


def combined_drawing_text(parts: list[dict[str, Any]], *, limit: int = 120_000) -> str:
    first_pages: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    for part in parts:
        pages = _iter_pages(part)
        for offset, (page, text) in enumerate(pages):
            row = {
                "filename": part.get("filename"),
                "kind": part.get("kind"),
                "page": page,
                "text": text,
                "score": _chunk_score(text),
                "first": offset == 0,
            }
            if offset == 0:
                first_pages.append(row)
            ranked.append(row)
    ranked.sort(key=lambda item: (-int(item["score"]), str(item["filename"] or ""), int(item["page"] or 0)))
    ordered: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in [*first_pages, *ranked]:
        key = (row["filename"], row["page"], str(row.get("text") or "")[:24])
        if key in seen:
            continue
        seen.add(key)
        ordered.append(row)
    chunks: list[str] = []
    remaining = limit
    for row in ordered:
        text = str(row.get("text") or "").strip()
        if not text or remaining <= 80:
            continue
        header = f"===== FILE {row.get('filename')} KIND {row.get('kind')} PAGE {row.get('page')} =====\n"
        is_schedule = int(row.get("score") or 0) >= 2
        cap = remaining - len(header)
        if row.get("first") and not is_schedule:
            cap = min(cap, FIRST_PAGE_CAP)
        body = text[: max(cap, 0)]
        if not body:
            break
        chunks.append(header + body)
        remaining -= len(header) + len(body)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)


def full_drawing_text(parts: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for part in parts:
        for page, text in _iter_pages(part):
            blob = str(text or "").strip()
            if not blob:
                continue
            chunks.append(f"===== FILE {part.get('filename')} KIND {part.get('kind')} PAGE {page} =====\n{blob}")
    return "\n\n".join(chunks)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def fold_alnum(value: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "", normalize_text(value))


def number_in_text(number: float | int, text: str) -> bool:
    raw = str(text or "").replace(",", "")
    if isinstance(number, float) and not number.is_integer():
        token = f"{number:g}"
        return token in raw.replace(" ", "") or str(number) in raw
    token = str(int(round(float(number))))
    return re.search(rf"(?<!\d){re.escape(token)}(?!\d)", raw) is not None


def evidence_in_source(evidence: str, source: str) -> bool:
    ev = normalize_text(evidence)
    src = normalize_text(source)
    if not ev or not src:
        return False
    if len(ev) >= 6 and ev in src:
        return True
    folded_ev = fold_alnum(evidence)
    folded_src = fold_alnum(source)
    if len(folded_ev) >= 8 and folded_ev in folded_src:
        return True
    numbers = re.findall(r"\d+(?:\.\d+)?", ev)
    words = re.findall(r"[a-z]{3,}", ev)
    if len(ev) >= 10 and numbers and all(item in src.replace(" ", "") or item in src for item in numbers):
        if not words or any(word in src for word in words):
            return True
    return False


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


def charts_prompt_block(charts: list[dict[str, Any]] | None) -> str:
    compact: list[dict[str, Any]] = []
    for chart in charts or []:
        if not isinstance(chart, dict):
            continue
        compact.append(
            {
                "id": chart.get("id"),
                "name_zh": chart.get("name_zh"),
                "source_file": chart.get("source_file"),
                "page": chart.get("page"),
                "rows": chart.get("rows") or [],
            }
        )
    if not compact:
        return "服务器未从文字层抽出可识别的表格行。仍须逐页读正文，不要猜扫描图上的毫米。"
    blob = json.dumps(compact, ensure_ascii=False)
    if len(blob) > 40_000:
        blob = blob[:40_000]
    return blob


def call_drawing_llm(source_text: str, charts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
        "正文按 FILE/PAGE 分段，门窗表、面积表、厨卫标注可能在靠后的 PAGE，必须逐段读完，不要只看封面。"
        "只根据图纸正文和服务器抽出的表格行做穷尽抽取：每一行门窗表、每一处面积/覆盖率/层数/厨卫/卧室、以及正文提到的材料。"
        "服务器抽出的图表 JSON 里每一行都必须进入 windows 或 fields，不得合并、跳过或改数字。"
        "evidence 必须从 PAGE 正文或图表 line 逐字抄录（可去掉换行），数字必须与原文一致。"
        "不要发明正文里没有的毫米、面积或件数。禁止输出任何价格、单价、总价、NZD 或 $。"
        "几乎无文字的图页不要猜尺寸，也不要做图像识别。"
        "门窗只能从文字层的门窗表或尺寸标注读取，每一樘都要列出，Qty 写在 count。"
        "材料行的 item_id 必须来自给定价库目录；目录不含单价，你也不许写单价。"
        "价库能对上的都写入 lines；对不上的写入 unmapped，不要省略。"
        "结构/屋面/保温等可按读到的 GFA 或厨卫套数点名对应 SKU，服务器会用公式重算数量，不采用你写的金额。"
        "没有公式的科目，quantity 必须是原文里出现的件数。\n"
        "只返回 JSON："
        '{"summary_zh":"中文简述读到的户型与表",'
        '"fields":[{"key":"gfa_m2","value":186.4,"evidence":"原文短句"}],'
        '"windows":[{"code":"W1","w_mm":1800,"h_mm":1200,"count":4,"evidence":"原文短句"}],'
        '"lines":[{"item_id":"kaboodle_base_600","quantity":5,"zone":"kitchen",'
        '"evidence":"原文短句","reason_zh":"为何计入此 SKU"}],'
        '"unmapped":[{"name_zh":"说明","quantity":1,"unit":"ea","evidence":"原文","reason_zh":"价库没有对应 SKU"}]}\n'
        f"fields.key 只能是 {sorted(ALLOWED_FIELD_KEYS)}。zone 只能是 {sorted(ALLOWED_ZONES)}。\n"
        f"价库目录：{json.dumps(catalog, ensure_ascii=False)}\n"
        f"文字层图表：\n{charts_prompt_block(charts)}\n"
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
        if not number_in_text(number, evidence):
            rejected.append({"item_id": key, "reason_zh": "字段数字未出现在证据句中，已丢弃。"})
            continue
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
        if not number_in_text(width, evidence) or not number_in_text(height, evidence):
            rejected.append({"item_id": code, "reason_zh": "门窗尺寸未出现在证据句中，已丢弃。"})
            continue
        if count != 1 and not number_in_text(count, evidence):
            rejected.append({"item_id": code, "reason_zh": "门窗数量未出现在证据句中，已丢弃。"})
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
