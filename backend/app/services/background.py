"""A picture behind every page.

The uploaded picture is stored once, tidied (rotated upright, shrunk, saved as JPEG). When a PDF is made,
it is combined with the paper colour into one page-sized image, already faded to the chosen strength.
Chromium then only has to paint that image as the page background, which also means the fade is exact in
every PDF viewer and printer.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from PIL import Image, ImageColor, ImageOps

from app.schemas import BackgroundOptions
from app.services.render.layout import PageSpec

MAX_SIDE = 3000  # longest side kept for the stored picture, in pixels
THUMB_SIDE = 480
TILE_FRACTION = 0.34  # width of one tile, as a share of the page width
KEEP = 6  # composed page images kept per job
MM_PER_INCH = 25.4
Image.MAX_IMAGE_PIXELS = 120_000_000  # refuse decompression bombs


class BackgroundError(Exception):
    """The file is not a picture that can be used."""


def folder(job_dir: Path) -> Path:
    path = job_dir / "background"
    path.mkdir(parents=True, exist_ok=True)
    return path


def original_path(job_dir: Path) -> Path:
    return job_dir / "background" / "picture.jpg"


def thumb_path(job_dir: Path) -> Path:
    return job_dir / "background" / "thumb.jpg"


def store_picture(job_dir: Path, source: BinaryIO, filename: str) -> dict[str, Any]:
    """Validate and save an uploaded picture. Returns what is kept in job.json."""
    try:
        image = Image.open(source)
        image.load()
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA", "P"):
            rgba = image.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
            image = flat
        else:
            image = image.convert("RGB")
    except Exception as exc:  # noqa: BLE001 - Pillow raises many kinds of error for a bad file
        raise BackgroundError("That file is not a picture that can be used. Choose a JPG, PNG or WebP image.") from exc
    if min(image.size) < 2:
        raise BackgroundError("That picture is too small to use.")
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    folder(job_dir)
    image.save(original_path(job_dir), "JPEG", quality=92, optimize=True)
    thumb = image.copy()
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.Resampling.LANCZOS)
    thumb.save(thumb_path(job_dir), "JPEG", quality=82)
    return {
        "name": (filename or "picture")[:120],
        "width": image.width,
        "height": image.height,
        "version": uuid.uuid4().hex[:10],
    }


def clear(job_dir: Path) -> None:
    for path in (original_path(job_dir), thumb_path(job_dir)):
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _page_pixels(spec: PageSpec, quality: str) -> tuple[int, int]:
    dpi = 200 if quality == "print" else 120
    return round(spec.width / MM_PER_INCH * dpi), round(spec.height / MM_PER_INCH * dpi)


def compose(picture: Image.Image, size: tuple[int, int], paper: str, fit: str, strength: float) -> Image.Image:
    """The picture laid onto a page-sized sheet of the paper colour, faded to `strength` (0..1)."""
    w, h = size
    sheet = Image.new("RGB", size, ImageColor.getrgb(paper))
    if fit == "cover":
        layer = ImageOps.fit(picture, size, Image.Resampling.LANCZOS)
        layer_mask = None
        sheet_layer = layer
    elif fit == "contain":
        fitted = ImageOps.contain(picture, size, Image.Resampling.LANCZOS)
        sheet_layer = sheet.copy()
        sheet_layer.paste(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
        # only the area the picture covers is faded; the rest stays plain paper
        layer_mask = Image.new("L", size, 0)
        layer_mask.paste(
            255, ((w - fitted.width) // 2, (h - fitted.height) // 2, (w + fitted.width) // 2, (h + fitted.height) // 2)
        )
    else:  # tile
        tile_w = max(32, round(w * TILE_FRACTION))
        tile_h = max(32, round(tile_w * picture.height / picture.width))
        tile = picture.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet_layer = sheet.copy()
        for y in range(0, h, tile_h):
            for x in range(0, w, tile_w):
                sheet_layer.paste(tile, (x, y))
        layer_mask = None
    faded = Image.blend(sheet, sheet_layer, max(0.0, min(1.0, strength)))
    if layer_mask is not None:
        faded = Image.composite(faded, sheet, layer_mask)
    return faded


def prepare(
    job_dir: Path, job: dict[str, Any], spec: PageSpec, paper: str, quality: str, opts: BackgroundOptions
) -> str | None:
    """Make the page-sized image for these settings and return its file name inside `render/`.

    Returns None when there is no picture or it is switched off.
    """
    info = job.get("background")
    source = original_path(job_dir)
    if not info or not opts.enabled or not source.is_file():
        return None
    size = _page_pixels(spec, quality)
    signature = f"{info['version']}|{size}|{paper}|{opts.fit}|{round(opts.opacity, 3)}"
    name = f"bg-{hashlib.sha1(signature.encode()).hexdigest()[:16]}.jpg"
    render_dir = job_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    target = render_dir / name
    if not target.is_file():
        with Image.open(source) as picture:
            picture.load()
            result = compose(picture, size, paper, opts.fit, opts.opacity)
        buffer = io.BytesIO()
        result.save(buffer, "JPEG", quality=90 if quality == "print" else 85, optimize=True)
        tmp = target.with_name(f"{target.stem}-{uuid.uuid4().hex[:8]}.tmp")
        try:
            tmp.write_bytes(buffer.getvalue())
            try:
                tmp.replace(target)
            except OSError:
                if not target.is_file():
                    raise
            _prune(render_dir, keep=name)
        finally:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)
    else:
        target.touch()
    return name


def _prune(render_dir: Path, keep: str) -> None:
    try:
        files = sorted(render_dir.glob("bg-*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[KEEP:]:
            if old.name != keep:
                with contextlib.suppress(OSError):
                    old.unlink(missing_ok=True)
    except Exception:
        pass