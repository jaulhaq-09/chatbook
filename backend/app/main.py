"""Application factory.

Run for development:   uvicorn app.main:app --reload
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import exports, health, jobs
from app.config import Settings, get_settings
from app.state import Services

log = logging.getLogger("chatbook")


async def _cleanup_loop(services: Services) -> None:
    interval = services.settings.cleanup_interval_minutes * 60
    while True:
        try:
            removed = await asyncio.to_thread(services.store.cleanup_expired)
            if removed:
                log.info("removed %d expired jobs", removed)
        except Exception:  # noqa: BLE001
            log.exception("cleanup failed")
        await asyncio.sleep(interval)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    services = Services.create(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(_cleanup_loop(services))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            services.ingestor.shutdown()
            services.exports.shutdown()
            services.previews.shutdown()

    app = FastAPI(title="Chatbook API", version=__version__, lifespan=lifespan)
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    for router in (health.router, jobs.router, exports.router):
        app.include_router(router, prefix="/api/v1")

    if settings.static_dir:  # serve the built frontend from the same origin
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")
    return app


app = create_app()