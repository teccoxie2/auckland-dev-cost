from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .data_loader import pricebook
from .models import Base, CostEstimate, DocumentSet, PriceBookVersion, Project, SchemeOption, SiteSnapshot

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "projects.sqlite"

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    env = os.environ.get("DATABASE_URL", "").strip()
    if env:
        return env
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        kwargs: dict[str, Any] = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(_engine, expire_on_commit=False)
    assert _SessionLocal is not None
    return _engine


def session() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def create_project(address: str, payload: dict[str, Any], status: str) -> dict[str, Any]:
    project_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    record = {
        "id": project_id,
        "address": address,
        "created_at": created,
        "status": status,
        "result": payload,
    }
    with session() as db:
        db.add(
            Project(
                id=project_id,
                address=address,
                created_at=created,
                status=status,
                payload=json.dumps(record, ensure_ascii=False),
            )
        )
        db.flush()
        _sync_children(db, record)
        db.commit()
    return record


def list_projects() -> list[dict[str, Any]]:
    with session() as db:
        rows = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [
        {"id": row.id, "address": row.address, "created_at": row.created_at, "status": row.status}
        for row in rows
    ]


def get_project(project_id: str) -> dict[str, Any] | None:
    with session() as db:
        row = db.get(Project, project_id)
    if not row:
        return None
    return json.loads(row.payload)


def update_project(project_id: str, payload: dict[str, Any], status: str) -> dict[str, Any] | None:
    record = get_project(project_id)
    if not record:
        return None
    record["result"] = payload
    record["status"] = status
    with session() as db:
        row = db.get(Project, project_id)
        if not row:
            return None
        row.status = status
        row.payload = json.dumps(record, ensure_ascii=False)
        _sync_children(db, record)
        db.commit()
    return record


def _sync_children(db: Session, record: dict[str, Any]) -> None:
    project_id = record["id"]
    result = record.get("result") or {}
    db.execute(delete(CostEstimate).where(CostEstimate.project_id == project_id))
    db.execute(delete(SchemeOption).where(SchemeOption.project_id == project_id))
    db.execute(delete(SiteSnapshot).where(SiteSnapshot.project_id == project_id))
    db.execute(delete(DocumentSet).where(DocumentSet.project_id == project_id))

    site = result.get("site") or {}
    zone = site.get("zone") or {}
    parcel = site.get("parcel") or {}
    captured = (
        (site.get("snapshot") or {}).get("captured_at")
        or site.get("captured_at")
        or record.get("created_at")
        or datetime.now(timezone.utc).isoformat()
    )
    zone_code = zone.get("zone_code")
    db.add(
        SiteSnapshot(
            id=str(uuid.uuid4()),
            project_id=project_id,
            captured_at=str(captured),
            zone_code=str(zone_code) if zone_code is not None else None,
            zone_name=zone.get("zone_name"),
            area_m2=float(parcel["area_m2"]) if parcel.get("area_m2") is not None else None,
            payload=site,
            rules_payload=result.get("rules"),
        )
    )

    for option in result.get("options") or []:
        scheme_id = str(uuid.uuid4())
        template = option.get("template") or {}
        db.add(
            SchemeOption(
                id=scheme_id,
                project_id=project_id,
                option_key=str(option.get("id") or scheme_id),
                typology=template.get("kind") or option.get("origin"),
                dwellings=template.get("dwellings"),
                gfa_m2=float(template["gfa_m2"]) if template.get("gfa_m2") is not None else None,
                verdict=(option.get("verdict") or {}).get("status"),
                payload=option,
            )
        )
        totals = option.get("totals") or {}
        lines = option.get("lines")
        if totals or lines:
            db.add(
                CostEstimate(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    scheme_option_id=scheme_id,
                    version=1,
                    pricebook_version=totals.get("pricebook_version"),
                    fee_book_version=totals.get("fee_book_version"),
                    confirmed_total=totals.get("confirmed_total_incl_gst"),
                    missing_count=int(totals.get("missing_count") or 0),
                    payload={"totals": totals, "lines": lines or []},
                )
            )

    captured_docs = datetime.now(timezone.utc).isoformat()
    for document in result.get("drawings") or []:
        db.add(
            DocumentSet(
                id=str(uuid.uuid4()),
                project_id=project_id,
                kind=document.get("kind"),
                filename=document.get("filename"),
                stored_path=document.get("stored_path"),
                captured_at=captured_docs,
                payload=document,
            )
        )

    book = pricebook()
    as_of = ""
    for item in book.get("items") or []:
        if item.get("retrieved_at"):
            as_of = str(item["retrieved_at"])
            break
    db.merge(
        PriceBookVersion(
            version=str(book.get("version") or "unversioned"),
            as_of=as_of,
            source_name="server/app/data/pricebook.json",
            item_count=len(book.get("items") or []),
            payload={"currency": book.get("currency"), "region": book.get("region")},
        )
    )
