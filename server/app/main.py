from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .data_loader import council_fees, pricebook
from .drawing_flow import parse_files, run_drawings
from .drawing_parse import MAX_PDF_BYTES
from .gis import ADDRESS_SOURCE_NAME, ADDRESS_SOURCE_URL, GisError, in_auckland, search_addresses
from .graph import configure_option, hydrate_legacy_result, run_address
from .store import create_project, get_project, list_projects, update_project

DRAWINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "drawings"

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
    hydrated = hydrate_legacy_result(record.get("address") or "", record.get("result") or {})
    if hydrated:
        updated = update_project(project_id, hydrated, record.get("status") or "ready")
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
    state = run_address(address, selected)
    public = _public_result(state)
    status = "error" if public.get("error") else "ready"
    return create_project(label, public, status)


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
        drawing_state = run_drawings(result["site"], result["rules"], parts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    result["drawings"] = extracted.get("documents") or []
    result["drawing_explanation"] = drawing_state.get("explanation")
    result["drawing_trace"] = drawing_state.get("trace") or []
    updated = update_project(project_id, result, record.get("status") or "ready")
    if not updated:
        raise HTTPException(status_code=404, detail="项目不存在")
    return updated
