"""The objects shared by all requests, created once per application."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.config import Settings
from app.db import Database
from app.services.auth import AuthService
from app.services.exports import ExportManager
from app.services.ingest import Ingestor
from app.services.jobs import JobStore
from app.services.preview_pdf import PreviewRenderer


@dataclass
class Services:
    settings: Settings
    db: Database
    auth: AuthService
    store: JobStore
    ingestor: Ingestor
    exports: ExportManager
    previews: PreviewRenderer

    @classmethod
    def create(cls, settings: Settings) -> Services:
        db = Database(settings.resolved_database_url)
        auth = AuthService(db)
        store = JobStore(settings.jobs_dir, settings.job_ttl_hours)
        return cls(
            settings,
            db,
            auth,
            store,
            Ingestor(store, settings),
            ExportManager(store, settings),
            PreviewRenderer(store, settings),
        )


def get_services(request: Request) -> Services:
    return request.app.state.services