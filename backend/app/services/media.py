"""Image and video helpers: resized copies for the preview and the print."""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 120_000_000

WEB_MAX = 1000  # preview and "standard" quality
PRINT_MAX = 2000  # "print" quality
STICKER_MAX = 512


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def process_image(data: bytes, kind: str, web_dir: Path, print_dir: Path, stem: str) -> dict[str, Any]:
    """Write web and print copies of one image and return its registry entry."""
    sticker = kind == "sticker"
    with Image.open(io.BytesIO(data)) as im:
        if im.format == "JPEG":
            im.draft("RGB", (PRINT_MAX, PRINT_MAX))
        im = ImageOps.exif_transpose(im)
        if sticker:
            im = im.convert("RGBA")
        elif im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
            im = flat
        else:
            im = im.convert("RGB")

        ext = "png" if sticker else "jpg"
        file = f"{stem}.{ext}"
        size = (0, 0)
        for variant, directory, limit, quality in (
            ("web", web_dir, STICKER_MAX if sticker else WEB_MAX, 82),
            ("print", print_dir, STICKER_MAX if sticker else PRINT_MAX, 88),
        ):
            copy = im.copy()
            copy.thumbnail((limit, limit), Image.Resampling.LANCZOS)
            if sticker:
                copy.save(directory / file, "PNG", optimize=True)
            else:
                copy.save(directory / file, "JPEG", quality=quality, optimize=True)
            if variant == "web":
                size = copy.size
    return {"file": file, "w": size[0], "h": size[1]}


def probe_duration(path: Path) -> float | None:
    if not ffmpeg_available():
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout.strip()
        value = float(out)
        return value if value > 0 else None
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def process_video(path: Path, web_dir: Path, print_dir: Path, stem: str, work_dir: Path) -> dict[str, Any]:
    """Pull a poster frame from a video. Without ffmpeg the entry has no picture."""
    entry: dict[str, Any] = {"file": None, "w": 640, "h": 360, "dur": None, "poster": False}
    if not ffmpeg_available():
        return entry
    duration = probe_duration(path)
    entry["dur"] = duration
    frame = work_dir / f"{stem}-frame.jpg"
    at = min(0.5, duration / 2) if duration else 0
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{at:.2f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(1600,iw)':-2",
                "-q:v",
                "3",
                str(frame),
            ],
            capture_output=True,
            timeout=90,
            check=True,
        )
        info = process_image(frame.read_bytes(), "image", web_dir, print_dir, stem)
        entry.update(info, poster=True)
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        frame.unlink(missing_ok=True)
    return entry
