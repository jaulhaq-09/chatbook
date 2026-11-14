"""Real printed pages for the on-screen preview.

The browser shows these pages with pdf.js, so the preview is exactly what Chromium will print.
Results are cached in the job folder, because moving a slider back and forth asks for the same
pages again and again.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app import __version__
from app.config import Settings
from app.schemas import RenderOptions
from app.services import background
from app.services.jobs import JobStore
from app.services.render.pdf import PdfEngine
from app.services.render.plan import Plan
from app.services.render.view import preview_page_count, render_section_html

log = logging.getLogger("chatbook")
KEEP = 12  # preview files kept per job; older ones are deleted


class PreviewRenderer:
    def __init__(self, store: JobStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        # One Chromium at a time for previews, so a burst of slider moves cannot starve the machine.
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="preview")

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _key(self, job: dict[str, Any], options: RenderOptions, volume: int, page: int) -> str:
        signature = json.dumps(
            [
                __version__,
                job["sources"],
                job["date_order"],
                job.get("background"),
                options.model_dump(mode="json"),
                volume,
                page,
                self.settings.preview_items_per_page,
            ],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha1(signature.encode()).hexdigest()[:20]

    def render(self, job_id: str, job: dict[str, Any], plan: Plan, volume: int, page: int) -> Path:
        """Path of the PDF for this section, making it when it is not cached yet."""
        folder = self.store.path(job_id) / "render"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"preview-{self._key(job, plan.options, volume, page)}.pdf"
        if path.is_file():
            path.touch()
            return path
        self._pool.submit(self._build, job, plan, volume, page, path, folder).result()
        self._prune(folder)
        return path

    def _build(self, job: dict[str, Any], plan: Plan, volume: int, page: int, path: Path, folder: Path) -> None:
        if path.is_file():  # another request made it while this one waited
            return
        vol = plan.volumes[volume - 1]
        plan.background_file = background.prepare(
            folder.parent, job, plan.spec, plan.theme["page"], plan.options.quality, plan.options.background
        )
        html = render_section_html(
            plan, vol, page=page, per_page=self.settings.preview_items_per_page, media_base="../media/"
        )
        html_path = folder / f"{path.stem}-{uuid.uuid4().hex[:8]}.html"
        tmp = folder / f"{path.stem}-{uuid.uuid4().hex[:8]}.tmp"
        try:
            html_path.write_text(html, encoding="utf-8")
            with PdfEngine(self.settings.chromium_no_sandbox) as engine:
                engine.render(html_path, tmp)
            try:
                tmp.replace(path)
            except OSError:
                if not path.is_file():
                    raise
        finally:
            with contextlib.suppress(OSError):
                html_path.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

    @staticmethod
    def _prune(folder: Path) -> None:
        try:
            files = sorted(folder.glob("preview-*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[KEEP:]:
                with contextlib.suppress(OSError):
                    old.unlink(missing_ok=True)
        except Exception:
            pass


def section_count(plan: Plan, volume: int, per_page: int) -> int:
    return preview_page_count(plan.volumes[volume - 1], per_page)