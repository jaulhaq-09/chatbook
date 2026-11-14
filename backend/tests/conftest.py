from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from app.config import Settings
from app.services.ingest import Ingestor, Upload
from app.services.jobs import JobStore


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        static_dir=None,
        chromium_no_sandbox=True,  # the test container runs as root
        _env_file=None,
    )


@pytest.fixture
def store(settings: Settings) -> JobStore:
    return JobStore(settings.jobs_dir, settings.job_ttl_hours)


@pytest.fixture
def ingestor(store: JobStore, settings: Settings) -> Ingestor:
    return Ingestor(store, settings)


def jpeg_bytes(w: int = 640, h: int = 480, color=(90, 140, 110)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


def make_zip(path: Path, files: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return path


def run_ingest(store: JobStore, ingestor: Ingestor, uploads: list[Upload], job_id: str | None = None) -> str:
    if job_id is None:
        job_id = store.create()["id"]
    ingestor.ingest(job_id, uploads)
    return job_id


CHAT = (
    "12/03/2026, 9:30 am - Priya: IMG-1.jpg (file attached)\nthe view\n"
    "12/03/2026, 9:31 am - Arjun: IMG-2.jpg (file attached)\n"
    "13/03/2026, 7:00 pm - Priya: hello there\n"
)
