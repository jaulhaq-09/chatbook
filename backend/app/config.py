"""Runtime configuration. Every value can be set with a CHATBOOK_* environment variable."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _default_static_dir() -> Path | None:
    """Use the built frontend when it sits next to the backend (repo checkout)."""
    candidate = BACKEND_ROOT.parent / "frontend" / "dist"
    return candidate if (candidate / "index.html").is_file() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHATBOOK_", env_file=".env", extra="ignore")

    # Where jobs, media and exports are stored. Everything here is temporary.
    data_dir: Path = BACKEND_ROOT / "data"
    # Jobs (and their files) are deleted this long after the last activity.
    job_ttl_hours: float = Field(default=24, gt=0)
    cleanup_interval_minutes: float = Field(default=15, gt=0)

    # Upload and extraction limits.
    max_upload_mb: int = Field(default=4096, gt=0)
    max_unzipped_mb: int = Field(default=8192, gt=0)
    max_single_media_mb: int = Field(default=512, gt=0)

    # Processing.
    media_workers: int = Field(default=4, ge=1, le=16)
    preview_items_per_page: int = Field(default=250, ge=20, le=2000)

    # Allowed browser origins when the frontend runs on another port (Vite dev server).
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Folder with the built frontend. None means API only.
    static_dir: Path | None = Field(default_factory=_default_static_dir)

    # Database URL. If None, defaults to SQLite at data_dir/chatbook.db.
    # For PostgreSQL: postgresql+asyncpg://user:pass@host:5432/dbname
    database_url: str | None = None

    # Chromium needs this flag when it runs as root inside a container.
    chromium_no_sandbox: bool = False

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        self.data_dir.mkdir(parents=True, exist_ok=True)
        db_file = (self.data_dir / "chatbook.db").resolve().as_posix()
        return f"sqlite+aiosqlite:///{db_file}"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_unzipped_bytes(self) -> int:
        return self.max_unzipped_mb * 1024 * 1024

    @property
    def max_single_media_bytes(self) -> int:
        return self.max_single_media_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
