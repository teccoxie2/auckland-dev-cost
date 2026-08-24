from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "projects.sqlite"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


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
    with _connect() as connection:
        connection.execute(
            "INSERT INTO projects (id, address, created_at, status, payload) VALUES (?, ?, ?, ?, ?)",
            (project_id, address, created, status, json.dumps(record, ensure_ascii=False)),
        )
        connection.commit()
    return record


def list_projects() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, address, created_at, status FROM projects ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_project(project_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT payload FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        return None
    return json.loads(row["payload"])
