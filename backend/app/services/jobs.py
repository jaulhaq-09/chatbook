"""Disk-backed job store.

One folder per job:

    jobs/<id>/job.json        summary and status
    jobs/<id>/sources/*.txt   the chat text of every export that was added
    jobs/<id>/messages.jsonl  merged messages
    jobs/<id>/media.json      attachment registry (lower-case file name -> entry)
    jobs/<id>/media/web|print resized copies of photos and video poster frames
    jobs/<id>/exports/<eid>/  finished PDFs
    jobs/<id>/render/         temporary HTML handed to Chromium

Original uploads are deleted as soon as they have been processed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.models import Message

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_SUBDIRS = ("sources", "uploads", "media/web", "media/print", "exports", "render", "tmp")


class JobNotFound(Exception):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


def write_json(path: Path, data: Any) -> None:
    """Write JSON so a reader never sees a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


_write_json = write_json


class JobStore:
    def __init__(self, root: Path, ttl_hours: float) -> None:
        self.root = root
        self.ttl = timedelta(hours=ttl_hours)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._messages_cache: OrderedDict[str, tuple[tuple[int, int], list[Message]]] = OrderedDict()

    # ---- paths -------------------------------------------------------------------------
    def path(self, job_id: str) -> Path:
        """Folder of a job. Only 32-character hex ids are accepted, so no path can escape."""
        if not isinstance(job_id, str) or not _JOB_ID.match(job_id):
            raise JobNotFound(job_id)
        p = self.root / job_id
        if not (p / "job.json").is_file():
            raise JobNotFound(job_id)
        return p

    # ---- lifecycle ---------------------------------------------------------------------
    def create(self, **fields: Any) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        d = self.root / job_id
        for sub in _SUBDIRS:
            (d / sub).mkdir(parents=True, exist_ok=True)
        stamp = now().isoformat(timespec="seconds")
        job: dict[str, Any] = {
            "id": job_id,
            "created_at": stamp,
            "updated_at": stamp,
            "status": "processing",
            "error": None,
            "warnings": [],
            "progress": {"stage": "Starting", "done": 0, "total": 0},
            "date_order": "auto",
            "order_ambiguous": False,
            "is_sample": False,
            "sources": [],
            "senders": [],
            "counts": {"messages": 0, "photos": 0, "videos": 0, "missing_media": 0, "omitted_media": 0},
            "date_range": None,
            "suggested_title": "",
        }
        job.update(fields)
        _write_json(d / "job.json", job)
        return job

    def load(self, job_id: str) -> dict[str, Any]:
        p = self.path(job_id) / "job.json"
        with self._lock:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                raise JobNotFound(job_id) from exc

    def mutate(self, job_id: str, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock:
            job = self.load(job_id)
            fn(job)
            job["updated_at"] = now().isoformat(timespec="seconds")
            _write_json(self.path(job_id) / "job.json", job)
            return job

    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        return self.mutate(job_id, lambda job: job.update(changes))

    def touch(self, job_id: str) -> None:
        self.mutate(job_id, lambda job: None)

    def delete(self, job_id: str) -> None:
        d = self.path(job_id)
        with self._lock:
            self._messages_cache.pop(job_id, None)
            shutil.rmtree(d, ignore_errors=True)

    def expires_at(self, job: dict[str, Any]) -> str:
        return (datetime.fromisoformat(job["updated_at"]) + self.ttl).isoformat(timespec="seconds")

    def cleanup_expired(self) -> int:
        """Delete jobs that have been idle longer than the time-to-live. Returns how many."""
        removed = 0
        cutoff = now() - self.ttl
        for d in self.root.iterdir():
            if not d.is_dir():
                continue
            try:
                updated = datetime.fromisoformat(json.loads((d / "job.json").read_text("utf-8"))["updated_at"])
            except (OSError, ValueError, KeyError):
                updated = datetime.fromtimestamp(d.stat().st_mtime, timezone.utc)
            if updated < cutoff:
                with self._lock:
                    self._messages_cache.pop(d.name, None)
                    shutil.rmtree(d, ignore_errors=True)
                removed += 1
        return removed

    # ---- messages ----------------------------------------------------------------------
    def save_messages(self, job_id: str, messages: list[Message]) -> None:
        p = self.path(job_id) / "messages.jsonl"
        tmp = p.with_name("messages.jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for m in messages:
                fh.write(json.dumps(m.to_dict(), ensure_ascii=False))
                fh.write("\n")
        with self._lock:
            os.replace(tmp, p)
            self._messages_cache.pop(job_id, None)

    def load_messages(self, job_id: str) -> list[Message]:
        p = self.path(job_id) / "messages.jsonl"
        if not p.exists():
            return []
        st = p.stat()
        sig = (st.st_mtime_ns, st.st_size)
        with self._lock:
            hit = self._messages_cache.get(job_id)
            if hit and hit[0] == sig:
                self._messages_cache.move_to_end(job_id)
                return hit[1]
        with p.open(encoding="utf-8") as fh:
            messages = [Message.from_dict(json.loads(line)) for line in fh if line.strip()]
        with self._lock:
            self._messages_cache[job_id] = (sig, messages)
            while len(self._messages_cache) > 4:
                self._messages_cache.popitem(last=False)
        return messages

    # ---- media registry ----------------------------------------------------------------
    def load_media(self, job_id: str) -> dict[str, dict[str, Any]]:
        p = self.path(job_id) / "media.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def save_media(self, job_id: str, registry: dict[str, dict[str, Any]]) -> None:
        with self._lock:
            _write_json(self.path(job_id) / "media.json", registry)
