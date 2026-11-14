from __future__ import annotations

import io
import logging
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from app.schemas import (
    BackgroundOut,
    CountsOut,
    DateRangeOut,
    InsightsOut,
    JobOut,
    JobPatch,
    PreviewOut,
    PreviewRequest,
    Progress,
    SenderOut,
    SourceOut,
)
from app.services import background
from app.services.ingest import Upload
from app.services.insights import compute_insights
from app.services.jobs import JobNotFound
from app.services.media import ffmpeg_available
from app.services.preview_pdf import section_count
from app.services.render.plan import build_plan, compute_stats
from app.services.render.view import preview_page_count, render_volume_html, section_summaries
from app.state import Services, get_services

log = logging.getLogger("chatbook")
router = APIRouter(prefix="/jobs", tags=["jobs"])
_MEDIA_FILE = re.compile(r"^m\d{6}\.(jpg|png)$")
_CHUNK = 1024 * 1024
_MAX_BACKGROUND = 25 * 1024 * 1024

Svc = Annotated[Services, Depends(get_services)]


def to_out(job: dict, svc: Services) -> JobOut:
    return JobOut(
        id=job["id"],
        status=job["status"],
        error=job["error"],
        warnings=job["warnings"],
        progress=Progress(**job["progress"]),
        created_at=job["created_at"],
        expires_at=svc.store.expires_at(job),
        date_order=job["date_order"],
        order_ambiguous=job["order_ambiguous"],
        is_sample=job["is_sample"],
        sources=[SourceOut(**s) for s in job["sources"]],
        senders=[SenderOut(**s) for s in job["senders"]],
        counts=CountsOut(**job["counts"]),
        date_range=DateRangeOut(**job["date_range"]) if job["date_range"] else None,
        suggested_title=job["suggested_title"],
        video_posters=ffmpeg_available(),
        background=BackgroundOut(**{k: job["background"][k] for k in BackgroundOut.model_fields})
        if job.get("background")
        else None,
    )


def load_job(svc: Services, job_id: str) -> dict:
    try:
        return svc.store.load(job_id)
    except JobNotFound as exc:
        raise HTTPException(404, "This job was not found. It may have expired.") from exc


def ready_job(svc: Services, job_id: str) -> dict:
    job = load_job(svc, job_id)
    if job["status"] == "processing":
        raise HTTPException(409, "The chat is still being processed.")
    if job["status"] == "failed":
        raise HTTPException(409, job["error"] or "The chat could not be read.")
    return job


def _save_uploads(files: list[UploadFile], svc: Services, job_id: str) -> list[Upload]:
    """Stream the uploads to the job folder, enforcing the size limit."""
    folder = svc.store.path(job_id) / "uploads"
    existing = len(list(folder.iterdir()))
    uploads: list[Upload] = []
    total = 0
    for i, f in enumerate(files):
        path = folder / f"{existing + i:04d}.upload"
        with path.open("wb") as out:
            while chunk := f.file.read(_CHUNK):
                total += len(chunk)
                if total > svc.settings.max_upload_bytes:
                    out.close()
                    for u in uploads:
                        u.path.unlink(missing_ok=True)
                    path.unlink(missing_ok=True)
                    raise HTTPException(413, f"The upload is larger than the {svc.settings.max_upload_mb} MB limit.")
                out.write(chunk)
        uploads.append(Upload(f.filename or "export", path))
    return uploads


@router.post("", status_code=202, response_model=JobOut)
def create_job(
    svc: Svc,
    files: Annotated[list[UploadFile], File(description="WhatsApp export .zip or chat .txt files")],
    date_order: Annotated[Literal["auto", "dmy", "mdy"], Form()] = "auto",
) -> JobOut:
    if not files:
        raise HTTPException(422, "Choose at least one export file.")
    job = svc.store.create(date_order=date_order)
    try:
        uploads = _save_uploads(files, svc, job["id"])
    except HTTPException:
        svc.store.delete(job["id"])
        raise
    svc.ingestor.submit(job["id"], uploads)
    return to_out(svc.store.load(job["id"]), svc)


@router.post("/sample", status_code=202, response_model=JobOut)
def create_sample(svc: Svc) -> JobOut:
    job = svc.store.create(is_sample=True)
    svc.ingestor.submit_sample(job["id"])
    return to_out(job, svc)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, svc: Svc) -> JobOut:
    return to_out(load_job(svc, job_id), svc)


@router.post("/{job_id}/files", status_code=202, response_model=JobOut)
def add_files(job_id: str, svc: Svc, files: Annotated[list[UploadFile], File()]) -> JobOut:
    job = ready_job(svc, job_id)
    if not files:
        raise HTTPException(422, "Choose at least one export file.")
    uploads = _save_uploads(files, svc, job_id)
    svc.store.update(job_id, status="processing", error=None)
    svc.ingestor.submit(job_id, uploads)
    return to_out(svc.store.load(job["id"]), svc)


@router.patch("/{job_id}", response_model=JobOut)
def patch_job(job_id: str, body: JobPatch, svc: Svc) -> JobOut:
    ready_job(svc, job_id)
    svc.store.update(job_id, date_order=body.date_order)
    svc.ingestor.remerge(job_id)
    return to_out(svc.store.load(job_id), svc)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, svc: Svc) -> Response:
    load_job(svc, job_id)
    svc.store.delete(job_id)
    return Response(status_code=204)


@router.get("/{job_id}/media/{variant}/{file}")
def get_media(job_id: str, variant: Literal["web", "print"], file: str, svc: Svc) -> FileResponse:
    if not _MEDIA_FILE.match(file):
        raise HTTPException(404, "Not found.")
    try:
        path = svc.store.path(job_id) / "media" / variant / file
    except JobNotFound as exc:
        raise HTTPException(404, "Not found.") from exc
    if not path.is_file():
        raise HTTPException(404, "Not found.")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})


@router.post("/{job_id}/background", response_model=JobOut)
def set_background(
    job_id: str, svc: Svc, file: Annotated[UploadFile, File(description="JPG, PNG or WebP picture")]
) -> JobOut:
    """Keep a picture to print behind the pages. Replaces the one uploaded before."""
    ready_job(svc, job_id)
    data = file.file.read(_MAX_BACKGROUND + 1)
    if len(data) > _MAX_BACKGROUND:
        raise HTTPException(413, "That picture is larger than 25 MB. Choose a smaller one.")
    try:
        info = background.store_picture(svc.store.path(job_id), io.BytesIO(data), file.filename or "picture")
    except background.BackgroundError as exc:
        raise HTTPException(422, str(exc)) from exc
    return to_out(svc.store.update(job_id, background=info), svc)


@router.delete("/{job_id}/background", response_model=JobOut)
def remove_background(job_id: str, svc: Svc) -> JobOut:
    ready_job(svc, job_id)
    background.clear(svc.store.path(job_id))
    return to_out(svc.store.update(job_id, background=None), svc)


@router.get("/{job_id}/background")
def get_background(job_id: str, svc: Svc) -> FileResponse:
    """Small copy of the picture, for the thumbnail in the settings."""
    job = load_job(svc, job_id)
    path = background.thumb_path(svc.store.path(job_id))
    if not job.get("background") or not path.is_file():
        raise HTTPException(404, "Not found.")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/{job_id}/insights", response_model=InsightsOut)
def insights(job_id: str, svc: Svc) -> InsightsOut:
    ready_job(svc, job_id)
    svc.store.touch(job_id)
    return InsightsOut(**compute_insights(svc.store.load_messages(job_id)))


@router.post("/{job_id}/preview-pdf")
def preview_pdf(job_id: str, body: PreviewRequest, svc: Svc) -> FileResponse:
    """The pages of one section as a real PDF, for the page viewer."""
    job = ready_job(svc, job_id)
    svc.store.touch(job_id)
    plan = build_plan(body.options, job, svc.store.load_messages(job_id), svc.store.load_media(job_id))
    if not plan.volumes:
        raise HTTPException(422, "Nothing matches these filters.")
    volume = min(body.volume, len(plan.volumes))
    page = min(body.page, section_count(plan, volume, svc.settings.preview_items_per_page))
    try:
        path = svc.previews.render(job_id, job, plan, volume, page)
    except Exception as exc:  # noqa: BLE001 - Chromium problems should read as one clear message
        log.exception("preview pdf failed")
        raise HTTPException(500, "The preview pages could not be made. Please try again.") from exc
    return FileResponse(path, media_type="application/pdf", headers={"Cache-Control": "no-store"})


@router.post("/{job_id}/preview", response_model=PreviewOut)
def preview(job_id: str, body: PreviewRequest, svc: Svc) -> PreviewOut:
    job = ready_job(svc, job_id)
    svc.store.touch(job_id)
    plan = build_plan(body.options, job, svc.store.load_messages(job_id), svc.store.load_media(job_id))
    stats = compute_stats(plan)
    if not plan.volumes:
        return PreviewOut(html="", page=1, page_count=1, volume=1, stats=stats)
    volume = min(body.volume, len(plan.volumes))
    vol = plan.volumes[volume - 1]
    per_page = svc.settings.preview_items_per_page
    page = min(body.page, preview_page_count(vol, per_page))
    html = render_volume_html(
        plan, vol, media_base=f"/api/v1/jobs/{job_id}/media/", preview=True, page=page, per_page=per_page
    )
    return PreviewOut(
        html=html,
        page=page,
        page_count=preview_page_count(vol, per_page),
        volume=volume,
        stats=stats,
        sections=section_summaries(plan, vol, per_page),
    )