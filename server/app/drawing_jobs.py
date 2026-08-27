from __future__ import annotations

import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from fastapi import HTTPException

from .drawing_flow import parse_files
from .drawing_verify import verify_drawing_parts

JOB_TTL_SEC = 30 * 60
_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="drawing-verify")


def _http_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        error = detail.get("error") or detail
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        return str(detail.get("message") or detail)
    return str(detail)


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    out = {
        "job_id": job["id"],
        "status": job["status"],
        "note": job.get("note"),
    }
    if job["status"] == "ok":
        out["result"] = job.get("result")
    if job["status"] == "error":
        out["detail"] = job.get("detail")
    return out


def get_verify_job(job_id: str) -> dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="核对任务不存在或已过期，请重新上传。")
        if time.time() - float(job.get("created_at") or 0) > JOB_TTL_SEC:
            _JOBS.pop(job_id, None)
            raise HTTPException(status_code=404, detail="核对任务不存在或已过期，请重新上传。")
        return _public_job(job)


def _set_job(job_id: str, **fields: Any) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job.update(fields)


def _run_job(job_id: str, saved: list[dict[str, Any]], workdir: Path) -> None:
    try:
        _set_job(job_id, status="running", note="正在读取 PDF 文字层…")
        parts = parse_files(saved)
        _set_job(job_id, note="正在调用大模型读文字层，可能需要几分钟…")
        payload = verify_drawing_parts(parts)
        if payload.get("error"):
            _set_job(
                job_id,
                status="error",
                detail=_http_detail(payload["error"]),
                note="核对失败，未编造材料或金额。",
            )
            return
        _set_job(job_id, status="ok", result=payload, note="核对完成。")
    except HTTPException as exc:
        _set_job(job_id, status="error", detail=_http_detail(exc.detail), note="核对失败。")
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="error", detail=f"图纸解析失败：{exc}", note="核对失败。")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def submit_verify_job(saved: list[dict[str, Any]], workdir: Path) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "status": "pending",
        "note": "已排队，正在读取文字层。",
        "created_at": time.time(),
        "result": None,
        "detail": None,
    }
    with _LOCK:
        stale = [
            key
            for key, item in _JOBS.items()
            if time.time() - float(item.get("created_at") or 0) > JOB_TTL_SEC
        ]
        for key in stale:
            _JOBS.pop(key, None)
        _JOBS[job_id] = job
    _EXECUTOR.submit(_run_job, job_id, saved, workdir)
    return _public_job(job)


def save_upload_dir() -> Path:
    return Path(mkdtemp(prefix="drawing-verify-"))
