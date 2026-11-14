"""HTML to PDF with headless Chromium, including a contents page that knows its page numbers."""

from __future__ import annotations

import contextlib
import threading
from pathlib import Path

from playwright.sync_api import Route, sync_playwright
from pypdf import PdfReader, PdfWriter

from app.services.render.layout import VolumePlan
from app.services.render.plan import Plan, toc_labels
from app.services.render.view import render_volume_html, split_body


class Cancelled(Exception):
    pass


def _only_local_files(route: Route) -> None:
    """The renderer never needs the network: refuse everything except local files."""
    if route.request.url.startswith("file:"):
        route.continue_()
    else:
        route.abort()


class PdfEngine:
    """One Chromium process, reused for every volume of an export. Use as a context manager."""

    def __init__(self, no_sandbox: bool = False) -> None:
        self._no_sandbox = no_sandbox
        self._pw = None
        self._browser = None

    def __enter__(self) -> PdfEngine:
        self._pw = sync_playwright().start()
        args = ["--no-sandbox"] if self._no_sandbox else []
        self._browser = self._pw.chromium.launch(args=args)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def render(self, html_path: Path, pdf_path: Path) -> None:
        assert self._browser is not None
        context = self._browser.new_context()
        context.route("**/*", _only_local_files)
        page = context.new_page()
        page.set_default_timeout(900_000)
        try:
            page.goto(html_path.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.pdf(
                path=str(pdf_path),
                prefer_css_page_size=True,
                print_background=True,
                outline=True,
                tagged=True,
            )
        finally:
            context.close()


def read_outline(pdf_path: Path) -> tuple[int, dict[str, int]]:
    """Page count and the first page of every heading (title -> 1-based page)."""
    reader = PdfReader(str(pdf_path))
    found: dict[str, int] = {}

    def walk(items: list) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            title = (item.title or "").strip()
            try:
                found.setdefault(title, reader.get_destination_page_number(item) + 1)
            except Exception:  # noqa: BLE001 - a broken bookmark only costs one contents entry
                continue

    walk(reader.outline)
    return len(reader.pages), found


def build_volume_pdf(
    engine: PdfEngine,
    plan: Plan,
    vol: VolumePlan,
    render_dir: Path,
    out_path: Path,
    cancel: threading.Event,
    on_stage=lambda text: None,
) -> int:
    """Render one volume to `out_path` and return its page count.

    A contents page needs to know where each month lands, which is only known after Chromium has
    paginated. The volume is rendered once with placeholder numbers, the real numbers are read from
    the PDF's bookmarks, and the pages holding the contents are rendered again.

    Long volumes are cut into slices (see `split_body`) that are rendered one by one and joined,
    because Chromium slows down sharply on very long documents.
    """
    slices = split_body(plan, vol, media_base="../media/")
    if len(slices) == 1:
        return _build_single(engine, plan, vol, slices[0], render_dir, out_path, cancel, on_stage)
    return _build_sliced(engine, plan, vol, slices, render_dir, out_path, cancel, on_stage)


def _render_one(engine, plan, vol, body, render_dir, pdf_path, toc_pages, cancel) -> tuple[int, dict[str, int]]:
    if cancel.is_set():
        raise Cancelled
    html_path = render_dir / f"{pdf_path.stem}.html"
    try:
        html = render_volume_html(plan, vol, media_base="../media/", toc_pages=toc_pages, body=body)
        html_path.write_text(html, encoding="utf-8")
        engine.render(html_path, pdf_path)
    finally:
        with contextlib.suppress(OSError):
            html_path.unlink(missing_ok=True)
    return read_outline(pdf_path)


def _resolve(labels: list[str], outline: dict[str, int]) -> dict[str, str]:
    # A heading Chromium did not report gets an empty number rather than a wrong one.
    return {label: str(outline[label]) if label in outline else "" for label in labels}


def _build_single(engine, plan, vol, body, render_dir, out_path, cancel, on_stage) -> int:
    labels = toc_labels(plan, vol)
    pages_map: dict[str, str] | None = None
    pages = 0
    for attempt in range(3):
        on_stage("Laying out pages" if attempt == 0 else "Adding page numbers to the contents")
        pages, outline = _render_one(engine, plan, vol, body, render_dir, out_path, pages_map, cancel)
        if not labels:
            break
        resolved = _resolve(labels, outline)
        if resolved == pages_map:
            break
        if attempt == 0 and not any(resolved.values()):
            break
        pages_map = resolved
    return pages


def _build_sliced(engine, plan, vol, slices, render_dir, out_path, cancel, on_stage) -> int:
    labels = toc_labels(plan, vol)
    n = len(slices)
    parts = [render_dir / f"{out_path.stem}.part{i:03d}.pdf" for i in range(n)]
    counts: list[int] = [0] * n
    outlines: list[dict[str, int]] = [{} for _ in range(n)]
    pages_map: dict[str, str] | None = None

    def render(i: int) -> None:
        slices[i].page_start = None if i == 0 else sum(counts[:i]) + 1
        on_stage(f"Laying out pages (part {i + 1} of {n})")
        counts[i], outlines[i] = _render_one(engine, plan, vol, slices[i], render_dir, parts[i], pages_map, cancel)

    def global_outline() -> dict[str, int]:
        merged: dict[str, int] = {}
        offset = 0
        for i in range(n):
            for title, page in outlines[i].items():
                merged.setdefault(title, offset + page)
            offset += counts[i]
        return merged

    try:
        for i in range(n):
            render(i)
        if labels:
            for _ in range(2):
                resolved = _resolve(labels, global_outline())
                if resolved == pages_map or not any(resolved.values()):
                    break
                pages_map = resolved
                on_stage("Adding page numbers to the contents")
                before = counts[0]
                render(0)
                if counts[0] != before:  # the contents grew onto another page: everything after it shifts
                    for i in range(1, n):
                        render(i)

        if cancel.is_set():
            raise Cancelled
        on_stage("Joining the parts")
        writer = PdfWriter()
        for part in parts:
            writer.append(str(part))
        for title, page in sorted(global_outline().items(), key=lambda kv: kv[1]):
            writer.add_outline_item(title, page - 1)
        writer.add_metadata({"/Title": plan.title})
        with out_path.open("wb") as fh:
            writer.write(fh)
        writer.close()
    finally:
        for part in parts:
            with contextlib.suppress(OSError):
                part.unlink(missing_ok=True)
    return sum(counts)
