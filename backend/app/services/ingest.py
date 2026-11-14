"""Turn uploaded exports into a ready job: parse, merge, and prepare the media."""

from __future__ import annotations

import logging
import re
import shutil
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import Settings
from app.core import meta
from app.core.models import MediaRef, Message
from app.core.parser import merge_chats, parse_chat
from app.services.jobs import JobStore
from app.services.media import probe_duration, process_image, process_video

log = logging.getLogger(__name__)

_MAX_CHAT_TEXT_BYTES = 1024 * 1024 * 1024
_TITLE_FROM_NAME = re.compile(r"WhatsApp Chat (?:with|-)\s*(.+?)\.(?:txt|zip)$", re.IGNORECASE)


class IngestError(Exception):
    """A problem with one uploaded file. The message is shown to the user."""


@dataclass
class Upload:
    name: str
    path: Path


def _basename(member: str) -> str:
    return PurePosixPath(member.replace("\\", "/")).name


def _decode(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


class _ZipCache:
    """One open ZipFile per worker thread, so a large archive is not re-indexed for every file."""

    def __init__(self) -> None:
        self._local = threading.local()
        self._all: list[zipfile.ZipFile] = []
        self._lock = threading.Lock()

    def get(self, path: Path) -> zipfile.ZipFile:
        opened = getattr(self._local, "opened", None)
        if opened is None:
            opened = self._local.opened = {}
        zf = opened.get(path)
        if zf is None:
            zf = opened[path] = zipfile.ZipFile(path)
            with self._lock:
                self._all.append(zf)
        return zf

    def close(self) -> None:
        for zf in self._all:
            zf.close()
        self._all.clear()


class Ingestor:
    def __init__(self, store: JobStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")

    # ---- public ------------------------------------------------------------------------
    def submit(self, job_id: str, uploads: list[Upload]) -> None:
        self._pool.submit(self._run, job_id, uploads)

    def submit_sample(self, job_id: str) -> None:
        """Build the generated example export inside the job, then process it like an upload."""

        def work() -> None:
            from app.services.sample import build_sample_zip

            try:
                path = build_sample_zip(self.store.path(job_id) / "uploads" / "sample.zip")
            except Exception:  # noqa: BLE001
                log.exception("could not build the sample")
                self.store.update(job_id, status="failed", error="The example chat could not be created.")
                return
            self._run(job_id, [Upload("sample.zip", path)])

        self._pool.submit(work)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _run(self, job_id: str, uploads: list[Upload]) -> None:
        try:
            self.ingest(job_id, uploads)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user through the job
            log.exception("ingest failed for %s", job_id)
            message = str(exc) if isinstance(exc, IngestError) else "Something went wrong while reading the files."
            try:
                self.store.update(job_id, status="failed", error=message)
            except Exception:  # noqa: BLE001 - the job may have been deleted meanwhile
                pass
        finally:
            for up in uploads:
                up.path.unlink(missing_ok=True)

    def ingest(self, job_id: str, uploads: list[Upload]) -> None:
        store = self.store
        jd = store.path(job_id)
        store.update(
            job_id, status="processing", error=None, progress={"stage": "Reading files", "done": 0, "total": 0}
        )

        warnings: list[str] = []
        members: dict[str, tuple[Path, str]] = {}  # lower-case attachment name -> (zip path, member)
        added = 0
        for up in uploads:
            try:
                text, found = self._read_upload(up, warnings)
            except IngestError as exc:
                warnings.append(str(exc))
                continue
            if not parse_chat(text).messages:
                head = text.strip()[:60].replace("\n", " ")
                warnings.append(f'No messages found in "{up.name}". It starts with: {head!r}')
                continue

            def add_source(job: dict[str, Any], _name: str = up.name, _text: str = text) -> None:
                sid = max((s["id"] for s in job["sources"]), default=0) + 1
                job["sources"].append({"id": sid, "name": _name, "messages": 0})
                (jd / "sources" / f"{sid:04d}.txt").write_text(_text, encoding="utf-8")

            store.mutate(job_id, add_source)
            for key, member in found.items():
                members.setdefault(key, (up.path, member))
            added += 1

        job = store.load(job_id)
        if not job["sources"]:
            raise IngestError(" ".join(warnings) or "No chat text was found in the uploaded files.")
        store.update(job_id, warnings=job.get("warnings", []) + warnings)

        messages = self._remerge(job_id)
        self._prepare_media(job_id, messages, members)
        self._finalize(job_id)

    # ---- merging -----------------------------------------------------------------------
    def remerge(self, job_id: str) -> None:
        """Re-read every stored export, for example after the date order was changed."""
        self._remerge(job_id)
        self._finalize(job_id)

    def _remerge(self, job_id: str) -> list[Message]:
        store = self.store
        jd = store.path(job_id)
        job = store.load(job_id)
        chats = []
        for src in job["sources"]:
            text = (jd / "sources" / f"{src['id']:04d}.txt").read_text(encoding="utf-8")
            chats.append(parse_chat(text, job["date_order"]))
        messages, senders = merge_chats(chats)
        store.save_messages(job_id, messages)

        def apply(j: dict[str, Any]) -> None:
            for src, chat in zip(j["sources"], chats, strict=False):
                src["messages"] = len(chat.messages)
            j["order_ambiguous"] = any(c.ambiguous for c in chats)
            j["senders"] = [{"name": n, "count": c} for n, c in sorted(senders.items(), key=lambda kv: (-kv[1], kv[0]))]
            j["date_range"] = (
                {"start": messages[0].ts.isoformat(), "end": messages[-1].ts.isoformat()} if messages else None
            )

        store.mutate(job_id, apply)
        return messages

    # ---- upload reading ----------------------------------------------------------------
    def _read_upload(self, up: Upload, notes: list[str] | None = None) -> tuple[str, dict[str, str]]:
        notes = notes if notes is not None else []
        lower = up.name.lower()
        if zipfile.is_zipfile(up.path):
            try:
                with zipfile.ZipFile(up.path) as zf:
                    infos = [i for i in zf.infolist() if not i.is_dir()]
                    if sum(i.file_size for i in infos) > self.settings.max_unzipped_bytes:
                        raise IngestError(
                            f'"{up.name}" is larger than the {self.settings.max_unzipped_mb} MB limit when unpacked.'
                        )
                    threads = meta.find_threads([(i.filename, i.file_size) for i in infos])
                    if threads:
                        return self._read_meta_zip(up, zf, infos, threads, notes)
                    texts = [
                        i
                        for i in infos
                        if i.filename.lower().endswith(".txt")
                        and not i.filename.startswith("__MACOSX/")
                        and not _basename(i.filename).startswith("._")
                    ]
                    if not texts:
                        raise IngestError(
                            f'"{up.name}" has no chat text file. Export again from WhatsApp using Export chat.'
                        )
                    chat = next((i for i in texts if _basename(i.filename).lower() == "_chat.txt"), None)
                    chat = chat or max(texts, key=lambda i: i.file_size)
                    if chat.file_size > _MAX_CHAT_TEXT_BYTES:
                        raise IngestError(f'The chat text in "{up.name}" is too large.')
                    text = _decode(zf.read(chat))
                    found: dict[str, str] = {}
                    for i in infos:
                        base = _basename(i.filename)
                        if not base or base.startswith(".") or i.filename.startswith("__MACOSX/") or i is chat:
                            continue
                        found.setdefault(base.lower(), i.filename)
            except zipfile.BadZipFile as exc:
                raise IngestError(f'"{up.name}" is not a valid ZIP file.') from exc
            return text, found
        if lower.endswith(".json"):
            if up.path.stat().st_size > _MAX_CHAT_TEXT_BYTES:
                raise IngestError(f'"{up.name}" is too large.')
            thread = meta.MetaThread(up.name, [up.name], up.path.stat().st_size)
            chat = meta.convert(lambda _p: up.path.read_bytes(), thread, {})
            if not chat.messages:
                raise IngestError(f'"{up.name}" is not an Instagram or Facebook chat file (message_1.json).')
            if chat.media and notes is not None:
                notes.append(
                    f'"{up.name}" mentions photos or videos, but a single .json file does not include media. '
                    "To include photos and videos, upload the full .zip export from Instagram or Facebook."
                )
            return chat.text, {}
        if lower.endswith(".txt"):
            if up.path.stat().st_size > _MAX_CHAT_TEXT_BYTES:
                raise IngestError(f'"{up.name}" is too large.')
            return _decode(up.path.read_bytes()), {}
        raise IngestError(
            f'"{up.name}" is not a chat export. Choose a .zip, a WhatsApp .txt, '
            "or an Instagram or Facebook message_1.json."
        )

    def _read_meta_zip(
        self,
        up: Upload,
        zf: zipfile.ZipFile,
        infos: list[zipfile.ZipInfo],
        threads: list[meta.MetaThread],
        notes: list[str],
    ) -> tuple[str, dict[str, str]]:
        """An Instagram or Facebook download: use the biggest conversation and say so."""
        thread = threads[0]
        if thread.size > _MAX_CHAT_TEXT_BYTES:
            raise IngestError(f'The chat in "{up.name}" is too large.')
        prefix = thread.folder.rstrip("/") + "/" if thread.folder not in ("", ".") else ""
        members = {}
        for i in infos:
            name = i.filename.replace("\\", "/")
            base = _basename(i.filename)
            if base and not base.startswith(".") and not name.startswith("__MACOSX/") and name.startswith(prefix):
                members.setdefault(base.lower(), i.filename)
        chat = meta.convert(zf.read, thread, members)
        if not chat.messages:
            raise IngestError(f'No messages were found in "{up.name}".')
        if len(threads) > 1:
            who = chat.title or PurePosixPath(thread.folder).name
            notes.append(
                f'"{up.name}" holds {len(threads)} chats. Used the biggest one, "{who}" ({chat.messages:,} items). '
                "To use another, zip just that chat's folder and upload it."
            )
        return chat.text, chat.media

    # ---- media -------------------------------------------------------------------------
    def _prepare_media(self, job_id: str, messages: list[Message], members: dict[str, tuple[Path, str]]) -> None:
        store = self.store
        jd = store.path(job_id)
        registry = store.load_media(job_id)
        counter = max((int(e["file"][1:7]) for e in registry.values() if e.get("file")), default=0)

        referenced: dict[str, MediaRef] = {}
        for m in messages:
            if m.media:
                referenced.setdefault(m.media.name.lower(), m.media)

        todo: list[tuple[str, MediaRef, str, tuple[Path, str]]] = []
        for key, ref in referenced.items():
            existing = registry.get(key)
            if existing and existing["state"] in ("ok", "meta"):
                continue
            source = members.get(key)
            if ref.kind == "doc":
                registry[key] = {"name": ref.name, "kind": ref.kind, "state": "meta", "file": None}
            elif source is None:
                registry[key] = {"name": ref.name, "kind": ref.kind, "state": "missing", "file": None}
            else:
                counter += 1
                todo.append((key, ref, f"m{counter:06d}", source))

        cache = _ZipCache()
        total = len(todo)
        store.update(job_id, progress={"stage": "Preparing photos and video", "done": 0, "total": total})
        done = 0
        last = 0.0
        try:
            with ThreadPoolExecutor(max_workers=self.settings.media_workers, thread_name_prefix="media") as pool:
                futures = {
                    pool.submit(self._process_one, jd, cache, ref, stem, source): (key, ref)
                    for key, ref, stem, source in todo
                }
                for fut in as_completed(futures):
                    key, ref = futures[fut]
                    registry[key] = fut.result()
                    done += 1
                    if time.monotonic() - last > 0.4 or done == total:
                        last = time.monotonic()
                        store.update(
                            job_id, progress={"stage": "Preparing photos and video", "done": done, "total": total}
                        )
        finally:
            cache.close()
        store.save_media(job_id, registry)

    def _process_one(
        self, jd: Path, cache: _ZipCache, ref: MediaRef, stem: str, source: tuple[Path, str]
    ) -> dict[str, Any]:
        base: dict[str, Any] = {"name": ref.name, "kind": ref.kind}
        zip_path, member = source
        try:
            zf = cache.get(zip_path)
            info = zf.getinfo(member)
            if info.file_size > self.settings.max_single_media_bytes:
                return {**base, "state": "bad", "file": None}
            web, prt = jd / "media" / "web", jd / "media" / "print"
            if ref.kind in ("image", "sticker"):
                entry = process_image(zf.read(member), ref.kind, web, prt, stem)
                return {**base, "state": "ok", "dur": None, "poster": True, **entry}
            tmp = jd / "tmp" / f"{stem}{PurePosixPath(member).suffix}"
            try:
                with zf.open(member) as src, tmp.open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                if ref.kind == "video":
                    entry = process_video(tmp, web, prt, stem, jd / "tmp")
                    return {**base, "state": "ok", **entry}
                return {**base, "state": "meta", "file": None, "dur": probe_duration(tmp)}
            finally:
                tmp.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - a damaged file must not stop the whole job
            log.warning("could not process %s", ref.name, exc_info=True)
            return {**base, "state": "bad", "file": None}

    # ---- summary -----------------------------------------------------------------------
    def _finalize(self, job_id: str) -> None:
        store = self.store
        messages = store.load_messages(job_id)
        registry = store.load_media(job_id)
        photos = videos = missing = omitted = 0
        for m in messages:
            if m.omitted:
                omitted += 1
            if not m.media:
                continue
            entry = registry.get(m.media.name.lower())
            ok = bool(entry and entry["state"] == "ok")
            if m.media.kind == "image" and ok:
                photos += 1
            elif m.media.kind == "video" and ok:
                videos += 1
            elif m.media.kind in ("image", "video", "sticker") and not ok:
                missing += 1
        job = store.load(job_id)
        counts = {
            "messages": sum(1 for m in messages if not m.system),
            "photos": photos,
            "videos": videos,
            "missing_media": missing,
            "omitted_media": omitted,
        }
        title = job.get("suggested_title") or self._guess_title(job)
        store.update(
            job_id,
            status="ready",
            error=None,
            counts=counts,
            suggested_title=title,
            progress={"stage": "Ready", "done": 1, "total": 1},
        )

    @staticmethod
    def _guess_title(job: dict[str, Any]) -> str:
        if job.get("is_sample"):
            return "Priya & Arjun"
        for src in job["sources"]:
            m = _TITLE_FROM_NAME.search(src["name"])
            if m:
                return m.group(1)
        names = [s["name"] for s in job["senders"]]
        return " & ".join(names) if 0 < len(names) <= 2 else "Our chat"