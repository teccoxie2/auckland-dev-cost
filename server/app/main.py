from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .data_loader import council_fees, pricebook
from .graph import run_address
from .store import create_project, get_project, list_projects

app = FastAPI(title="Auckland Development Cost MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateProjectBody(BaseModel):
    address: str = Field(min_length=3, max_length=200)


def _public_result(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("error"):
        return {"error": state["error"], "trace": state.get("trace") or []}
    options = []
    for option in state.get("options") or []:
        cost = option.get("cost")
        options.append(
            {
                "id": option["id"],
                "template": option["template"],
                "verdict": option["verdict"],
                "quantities": (cost or {}).get("quantities") or option.get("quantities"),
                "totals": (cost or {}).get("totals"),
                "lines": (cost or {}).get("lines"),
                "intensity_note": (cost or {}).get("intensity_note"),
            }
        )
    return {
        "site": state.get("site"),
        "rules": state.get("rules"),
        "explanation": state.get("explanation"),
        "pm_review": state.get("pm_review"),
        "options": options,
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
    return record


@app.post("/projects")
def post_project(body: CreateProjectBody) -> dict[str, Any]:
    state = run_address(body.address.strip())
    public = _public_result(state)
    status = "error" if public.get("error") else "ready"
    return create_project(body.address.strip(), public, status)
