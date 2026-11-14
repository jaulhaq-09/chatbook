from __future__ import annotations

import os
from functools import lru_cache

from fastapi import APIRouter

from app import __version__
from app.schemas import HealthOut
from app.services.media import ffmpeg_available

router = APIRouter(tags=["health"])


@lru_cache(maxsize=1)
def chromium_installed() -> bool:
    """True when Playwright can find its Chromium. Checked once; it can take a moment."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return os.path.exists(p.chromium.executable_path)
    except Exception:  # noqa: BLE001
        return False


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__, ffmpeg=ffmpeg_available(), chromium=chromium_installed())
