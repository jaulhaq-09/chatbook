from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from app.api.jobs import ready_job
from app.schemas import ExportFile, ExportOut, Progress, RenderOptions
from app.services.jobs import JobNotFound
from app.state import Services, get_services

router = APIRouter(prefix="/jobs/{job_id}/exports", tags=["exports"])
Svc = Annotated[Services, Depends(get_services)]


def to_out(data: dict) -> ExportOut:
    return ExportOut(
        id=data["id"],
        job_id=data["job_id"],
        status=data["status"],
        progress=Progress(**data["progress"]),
        files=[ExportFile(**f) for f in data["files"]],
        archive=data["archive"],
        error=data["error"],
        created_at=data["created_at"],
    )


def _get(svc: Services, job_id: str, export_id: str) -> dict:
    try:
        return svc.exports.get(job_id, export_id)
    except JobNotFound as exc:
        raise HTTPException(404, "This export was not found. It may have expired.") from exc


@router.post("", status_code=202, response_model=ExportOut)
def start_export(job_id: str, options: RenderOptions, svc: Svc) -> ExportOut:
    ready_job(svc, job_id)
    return to_out(svc.exports.start(job_id, options))


@router.get("/{export_id}", response_model=ExportOut)
def get_export(job_id: str, export_id: str, svc: Svc) -> ExportOut:
    return to_out(_get(svc, job_id, export_id))


@router.delete("/{export_id}", status_code=204)
def cancel_export(job_id: str, export_id: str, svc: Svc) -> Response:
    _get(svc, job_id, export_id)
    svc.exports.cancel(job_id, export_id)
    return Response(status_code=204)


@router.get("/{export_id}/files/{name}")
def download(job_id: str, export_id: str, name: str, svc: Svc, inline: bool = False) -> FileResponse:
    _get(svc, job_id, export_id)
    try:
        path = svc.exports.file_path(job_id, export_id, name)
    except JobNotFound as exc:
        raise HTTPException(404, "File not found.") from exc
    if not path.is_file():
        raise HTTPException(404, "File not found.")
    media = "application/pdf" if name.endswith(".pdf") else "application/zip"
    return FileResponse(
        path, media_type=media, filename=name, content_disposition_type="inline" if inline else "attachment"
    )
