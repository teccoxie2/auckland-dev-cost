from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .data_loader import council_fees, pricebook
from .graph import configure_option, hydrate_legacy_result, run_address
from .store import create_project, get_project, list_projects, update_project

app = FastAPI(title="Auckland Development Cost MVP", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateProjectBody(BaseModel):
    address: str = Field(min_length=3, max_length=200)


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
    state = run_address(body.address.strip())
    public = _public_result(state)
    status = "error" if public.get("error") else "ready"
    return create_project(body.address.strip(), public, status)


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
