"""Background PDF exports."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.config import Settings
from app.schemas import RenderOptions
from app.services import background
from app.services.jobs import JobNotFound, JobStore, now, write_json
from app.services.render.pdf import Cancelled, PdfEngine, build_volume_pdf
from app.services.render.plan import build_plan

log = logging.getLogger(__name__)
_EXPORT_ID = re.compile(r"^[0-9a-f]{16}$")


class ExportError(Exception):
    """A problem the user can act on. The message is shown to them."""


def slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE).strip("-_").lower()
    return cleaned[:60] or "chat"


class ExportManager:
    def __init__(self, store: JobStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="export")  # one Chromium at a time
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._recover_orphaned()

    def _recover_orphaned(self) -> None:
        """Mark any unfinished exports from previous server runs as failed."""
        try:
            for p in self.store.root.glob("*/exports/*/export.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if data.get("status") in ("running", "queued"):
                        data["status"] = "failed"
                        data["error"] = "The export was interrupted because the server was restarted."
                        write_json(p, data)
                except Exception:
                    pass
        except Exception:
            pass

    # ---- storage -----------------------------------------------------------------------
    def _dir(self, job_id: str, export_id: str):
        if not _EXPORT_ID.match(export_id or ""):
            raise JobNotFound(export_id)
        d = self.store.path(job_id) / "exports" / export_id
        if not (d / "export.json").is_file():
            raise JobNotFound(export_id)
        return d

    def get(self, job_id: str, export_id: str) -> dict[str, Any]:
        return json.loads((self._dir(job_id, export_id) / "export.json").read_text(encoding="utf-8"))

    def file_path(self, job_id: str, export_id: str, name: str):
        export = self.get(job_id, export_id)
        allowed = {f["name"] for f in export["files"]} | ({export["archive"]} if export["archive"] else set())
        if name not in allowed:
            raise JobNotFound(name)
        return self._dir(job_id, export_id) / name

    def _update(self, job_id: str, export_id: str, **changes: Any) -> None:
        with self._lock:
            try:
                d = self._dir(job_id, export_id)
            except JobNotFound:  # the job was deleted while exporting
                return
            current = self.get(job_id, export_id)
            current.update(changes)
            write_json(d / "export.json", current)

    # ---- control -----------------------------------------------------------------------
    def start(self, job_id: str, options: RenderOptions) -> dict[str, Any]:
        jd = self.store.path(job_id)
        export_id = uuid.uuid4().hex[:16]
        d = jd / "exports" / export_id
        d.mkdir(parents=True)
        export = {
            "id": export_id,
            "job_id": job_id,
            "status": "queued",
            "progress": {"stage": "Waiting to start", "done": 0, "total": 1},
            "files": [],
            "archive": None,
            "error": None,
            "created_at": now().isoformat(timespec="seconds"),
        }
        write_json(d / "export.json", export)
        self.store.touch(job_id)
        event = threading.Event()
        self._cancel[export_id] = event
        self._pool.submit(self.run, job_id, export_id, options, event)
        return export

    def cancel(self, job_id: str, export_id: str) -> None:
        self._dir(job_id, export_id)
        event = self._cancel.get(export_id)
        if event:
            event.set()

    def shutdown(self) -> None:
        for event in self._cancel.values():
            event.set()
        self._pool.shutdown(wait=False, cancel_futures=True)

    # ---- the work ----------------------------------------------------------------------
    def run(self, job_id: str, export_id: str, options: RenderOptions, cancel: threading.Event) -> None:
        try:
            self._render(job_id, export_id, options, cancel)
        except Cancelled:
            self._update(job_id, export_id, status="cancelled", progress={"stage": "Cancelled", "done": 0, "total": 1})
        except Exception as exc:  # noqa: BLE001
            log.exception("export %s failed", export_id)
            message = str(exc) if isinstance(exc, ExportError) else "The PDF could not be created."
            self._update(job_id, export_id, status="failed", error=message)
        finally:
            self._cancel.pop(export_id, None)

    def _render(self, job_id: str, export_id: str, options: RenderOptions, cancel: threading.Event) -> None:
        store = self.store
        job = store.load(job_id)
        plan = build_plan(options, job, store.load_messages(job_id), store.load_media(job_id))
        if not plan.volumes:
            raise ExportError("There is nothing to export with these settings. Widen the date range or people filter.")

        jd = store.path(job_id)
        out_dir = jd / "exports" / export_id
        total = len(plan.volumes)
        base = slug(plan.title)
        files: list[dict[str, Any]] = []
        self._update(job_id, export_id, status="running")

        with PdfEngine(self.settings.chromium_no_sandbox) as engine:
            for vol in plan.volumes:
                if cancel.is_set():
                    raise Cancelled

                def stage(text: str, vol_index: int = vol.index) -> None:
                    label = f"Volume {vol_index} of {total}: {text}" if total > 1 else text
                    self._update(job_id, export_id, progress={"stage": label, "done": vol_index - 1, "total": total})

                name = f"{base}-{vol.suffix}.pdf" if total > 1 else f"{base}.pdf"
                plan.background_file = background.prepare(
                    jd, job, plan.spec, plan.theme["page"], options.quality, options.background
                )
                pages = build_volume_pdf(engine, plan, vol, jd / "render", out_dir / name, cancel, stage)
                files.append(
                    {
                        "name": name,
                        "size": (out_dir / name).stat().st_size,
                        "pages": pages,
                        "volume": vol.index,
                        "label": vol.label,
                    }
                )
                self._update(
                    job_id,
                    export_id,
                    progress={"stage": "Rendered", "done": vol.index, "total": total},
                    files=list(files),
                )

        archive = None
        if total > 1:
            archive = f"{base}-volumes.zip"
            with zipfile.ZipFile(out_dir / archive, "w", zipfile.ZIP_STORED) as zf:
                for f in files:
                    zf.write(out_dir / f["name"], f["name"])
        self._update(
            job_id,
            export_id,
            status="done",
            files=files,
            archive=archive,
            progress={"stage": "Done", "done": total, "total": total},
        )