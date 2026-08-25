from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .advise import build_advice
from .data_loader import council_fees, pricebook
from .drawing_flow import parse_files, run_drawings
from .drawing_parse import MAX_PDF_BYTES
from .gis import (
    ADDRESS_SOURCE_NAME,
    ADDRESS_SOURCE_URL,
    GisError,
    attach_subdivision,
    in_auckland,
    search_addresses,
    split_estate_note,
)
from .graph import (
    apply_customer_lim,
    configure_option,
    hydrate_legacy_result,
    hydrate_lim,
    hydrate_site_analysis,
    merge_advice,
    run_address,
)
from .lim import lim_advice
from .lim_parse import parse_lim_pdf
from .site_vision import vision_advice
from .store import create_project, get_project, list_projects, update_project

DRAWINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "drawings"
LIM_DIR = Path(__file__).resolve().parent.parent / "data" / "lim"

app = FastAPI(title="Auckland Development Cost MVP", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateProjectBody(BaseModel):
    address: str = Field(min_length=3, max_length=200)
    lat: float | None = None
    lon: float | None = None
    full_address: str | None = None
    sap_address_id: str | None = None
    sap_site_id: str | None = None


class ConfigureBody(BaseModel):
    kind: str = "standalone"
    dwellings: int = Field(default=1, ge=1, le=6)
    storeys: int = Field(default=2, ge=1, le=5)
    bedrooms: int = Field(default=3, ge=1, le=6)
    bathrooms: int = Field(default=2, ge=1, le=6)
    kitchens: int = Field(default=1, ge=1, le=4)
    gfa_m2: float | None = Field(default=None, ge=60, le=450)


def _public_option(option: dict[str, Any]) -> dict[str, Any]:
    cost = option.get("cost")
    return {
        "id": option["id"],
        "template": option["template"],
        "verdict": option["verdict"],
        "why": option.get("why") or [],
        "recommended": bool(option.get("recommended")),
        "origin": option.get("origin") or "typology",
        "drawing_extract": option.get("drawing_extract"),
        "quantities": (cost or {}).get("quantities") or option.get("quantities"),
        "totals": (cost or {}).get("totals"),
        "lines": (cost or {}).get("lines"),
        "intensity_note": (cost or {}).get("intensity_note"),
        "building_rules": option.get("building_rules"),
    }


def _public_result(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("error"):
        return {"error": state["error"], "trace": state.get("trace") or []}
    return {
        "site": state.get("site"),
        "rules": state.get("rules"),
        "advice": state.get("advice") or [],
        "explanation": state.get("explanation"),
        "pm_review": state.get("pm_review"),
        "options": [_public_option(option) for option in state.get("options") or []],
        "scheme_filter": state.get("scheme_filter"),
        "trace": state.get("trace") or [],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/addresses")
def get_addresses(q: str = "") -> dict[str, Any]:
    try:
        hits = search_addresses(q)
    except GisError as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": exc.code, "message": str(exc)}}) from exc
    return {
        "query": q.strip(),
        "addresses": hits,
        "split_note": split_estate_note(q, hits),
        "source_name": ADDRESS_SOURCE_NAME,
        "source_url": ADDRESS_SOURCE_URL,
    }


@app.get("/pricebook")
def get_pricebook() -> dict[str, Any]:
    return {"pricebook": pricebook(), "council_fees": council_fees()}


@app.get("/projects")
def get_projects() -> dict[str, Any]:
    return {"projects": list_projects()}


@app.get("/projects/{project_id}")
def get_one_project(project_id: str) -> dict[str, Any]:
    record = get_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = record.get("result") or {}
    limed = hydrate_lim(result)
    if limed:
        result = limed
    hydrated = hydrate_legacy_result(record.get("address") or "", result)
    if hydrated:
        result = hydrated
    visioned = hydrate_site_analysis(result)
    if visioned:
        result = visioned
    if limed or hydrated or visioned:
        updated = update_project(project_id, result, record.get("status") or "ready")
        if updated:
            return updated
    return record


@app.post("/projects")
def post_project(body: CreateProjectBody) -> dict[str, Any]:
    address = body.address.strip()
    selected: dict[str, Any] | None = None
    if body.lat is not None and body.lon is not None:
        if not in_auckland(body.lat, body.lon):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "invalid_selection",
                        "message": "请从下拉列表选择一条奥克兰议会地址。同一门牌可能对应多条记录。",
                    }
                },
            )
        selected = {
            "lat": body.lat,
            "lon": body.lon,
            "full_address": (body.full_address or address).strip(),
            "sap_address_id": body.sap_address_id,
            "sap_site_id": body.sap_site_id,
        }
    else:
        try:
            hits = search_addresses(address)
        except GisError as exc:
            raise HTTPException(status_code=502, detail={"error": {"code": exc.code, "message": str(exc)}}) from exc
        if len(hits) > 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "ambiguous_address",
                        "message": f"议会地址库有 {len(hits)} 条匹配，请从下拉列表选择一条。",
                    },
                    "addresses": hits,
                },
            )
        if len(hits) == 1:
            selected = hits[0]
    label = ((selected or {}).get("full_address") or address).strip()
    record = create_project(label, {"trace": [], "graph_thread_id": None}, "running")
    state = run_address(address, selected, thread_id=record["id"])
    public = _public_result(state)
    public["graph_thread_id"] = record["id"]
    status = "error" if public.get("error") else "ready"
    updated = update_project(record["id"], public, status)
    return updated or {**record, "result": public, "status": status}


@app.post("/projects/{project_id}/configure")
def post_configure(project_id: str, body: ConfigureBody) -> dict[str, Any]:
    record = get_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = record.get("result") or {}
    if result.get("error") or not result.get("site") or not result.get("rules"):
        raise HTTPException(status_code=400, detail="项目还没有完整地块数据，无法选装")
    custom = configure_option(result["site"], result["rules"], body.model_dump())
    options = [item for item in result.get("options") or [] if item.get("id") != "custom"]
    public_custom = _public_option(custom)
    result["options"] = [public_custom, *options]
    result["selected_id"] = "custom"
    updated = update_project(project_id, result, record.get("status") or "ready")
    if not updated:
        raise HTTPException(status_code=404, detail="项目不存在")
    return updated


def _http_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        error = detail.get("error") or detail
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        return str(detail.get("message") or detail)
    return str(detail)


@app.post("/projects/{project_id}/drawings")
async def post_drawings(
    project_id: str,
    files: list[UploadFile] = File(...),
    kinds: str | None = Form(default=None),
) -> dict[str, Any]:
    record = get_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = record.get("result") or {}
    if result.get("error") or not result.get("site") or not result.get("rules"):
        raise HTTPException(status_code=400, detail="项目还没有完整地块数据，无法按图纸套价")
    site = attach_subdivision(dict(result["site"]), record.get("address") or "")
    result["site"] = site
    if result.get("rules"):
        result["advice"] = merge_advice(build_advice(site, result["rules"]), vision_advice(site), lim_advice(site))
    uploads = [item for item in files if item.filename]
    if not uploads:
        raise HTTPException(status_code=400, detail="请至少上传一份 PDF")
    if len(uploads) > 6:
        raise HTTPException(status_code=400, detail="一次最多上传 6 份 PDF")
    kind_list = [item.strip().lower() for item in (kinds or "").split(",") if item.strip()]
    dest = DRAWINGS_DIR / project_id
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[dict[str, Any]] = []
    for index, upload in enumerate(uploads):
        name = Path(upload.filename or f"drawing-{index}.pdf").name
        if not name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{name} 不是 PDF")
        blob = await upload.read()
        if not blob:
            raise HTTPException(status_code=400, detail=f"{name} 是空文件")
        if len(blob) > MAX_PDF_BYTES:
            raise HTTPException(status_code=400, detail=f"{name} 超过 15MB")
        path = dest / f"{index}-{name}"
        path.write_bytes(blob)
        saved.append(
            {
                "path": str(path),
                "filename": name,
                "kind": kind_list[index] if index < len(kind_list) else None,
            }
        )
    try:
        parts = parse_files(saved)
        drawing_state = run_drawings(site, result["rules"], parts)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"图纸解析失败：{exc}") from exc
    if drawing_state.get("error"):
        raise HTTPException(status_code=400, detail=_http_detail(drawing_state["error"]))
    option = drawing_state.get("option")
    if not option:
        raise HTTPException(status_code=400, detail="图纸未能生成核算方案")
    public = _public_option(option)
    others = [item for item in result.get("options") or [] if item.get("id") != "drawings"]
    result["options"] = [public, *others]
    result["selected_id"] = "drawings"
    extracted = drawing_state.get("extracted") or {}
    documents = []
    for index, document in enumerate(extracted.get("documents") or []):
        extra = saved[index] if index < len(saved) else {}
        documents.append(
            {
                **document,
                "kind": extra.get("kind") or document.get("kind"),
                "stored_path": extra.get("path"),
            }
        )
    result["drawings"] = documents
    result["drawing_explanation"] = drawing_state.get("explanation")
    result["drawing_trace"] = drawing_state.get("trace") or []
    updated = update_project(project_id, result, record.get("status") or "ready")
    if not updated:
        raise HTTPException(status_code=404, detail="项目不存在")
    return updated


@app.post("/projects/{project_id}/lim")
async def post_lim(
    project_id: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    record = get_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = record.get("result") or {}
    if result.get("error") or not result.get("site"):
        raise HTTPException(status_code=400, detail="项目还没有完整地块数据，无法核对 LIM")
    filename = Path(file.filename or "lim.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{filename} 不是 PDF")
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="LIM 文件是空的")
    if len(blob) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="LIM PDF 超过 15MB")
    dest = LIM_DIR / project_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / filename
    path.write_bytes(blob)
    parsed = parse_lim_pdf(path, filename=filename)
    if not parsed.get("ok"):
        raise HTTPException(status_code=400, detail=parsed.get("error") or "无法读取这份 LIM")
    updated_result, error = apply_customer_lim(result, parsed, record.get("address") or "")
    if error:
        raise HTTPException(status_code=400, detail=error)
    updated_result["lim_document"] = {
        "kind": "lim",
        "filename": filename,
        "stored_path": str(path),
        "page_count": parsed.get("page_count"),
        "char_count": parsed.get("char_count"),
        "application_number": parsed.get("application_number"),
        "issued_at": parsed.get("issued_at"),
        "lim_address": parsed.get("lim_address"),
    }
    saved = update_project(project_id, updated_result, record.get("status") or "ready")
    if not saved:
        raise HTTPException(status_code=404, detail="项目不存在")
    return saved
