"""Reader for Instagram and Facebook chats from "Download your information" (JSON format).

Meta stores one folder per conversation, holding message_1.json, message_2.json ... and the pictures,
videos and voice notes. The reader turns a conversation into the same plain text a WhatsApp export
uses, so everything after it (merging, media, layout) works without change.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

MESSAGE_FILE = re.compile(r"^message_\d+\.json$", re.IGNORECASE)
_HEADER_LOOK = re.compile(r"^\[?\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4},?\s")
_AUTO_TEXT = re.compile(r"\bsent an attachment\.?$|\bsent a (photo|video|voice message)\.?$", re.IGNORECASE)
_NAME_LIMIT = 60


@dataclass
class MetaThread:
    """One conversation folder inside a download."""

    folder: str
    files: list[str]
    size: int = 0


@dataclass
class MetaChat:
    text: str
    media: dict[str, str] = field(default_factory=dict)  # lower-case attachment name -> member path
    title: str = ""
    platform: str = "Instagram or Facebook"
    messages: int = 0


def find_threads(entries: list[tuple[str, int]]) -> list[MetaThread]:
    """Group the message_N.json files of a download into conversations. `entries` are (path, size)."""
    found: dict[str, MetaThread] = {}
    for path, size in entries:
        norm = path.replace("\\", "/")
        if norm.startswith("__MACOSX/") or not MESSAGE_FILE.match(PurePosixPath(norm).name):
            continue
        folder = str(PurePosixPath(norm).parent)
        thread = found.setdefault(folder, MetaThread(folder, []))
        thread.files.append(path)
        thread.size += size
    return sorted(found.values(), key=lambda t: -t.size)


def _platform(path: str) -> str:
    low = path.lower()
    if "instagram" in low:
        return "Instagram"
    if "facebook" in low or "messenger" in low:
        return "Facebook"
    return "Instagram or Facebook"


def fix_text(value: Any) -> str:
    """Meta writes UTF-8 bytes as if they were Latin-1 letters, so "é" arrives as "Ã©". Undo that."""
    if not isinstance(value, str):
        return ""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _clean_name(name: str) -> str:
    name = " ".join(name.split()).replace(": ", " - ").replace(":", "")
    return (name or "Unknown")[:_NAME_LIMIT]


def _stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d, %H:%M:%S")


def _safe_body(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join((" " + ln) if _HEADER_LOOK.match(ln) else ln for ln in lines)


def _with_ext(name: str, fallback: str) -> str:
    return name if re.search(r"\.[A-Za-z0-9]{2,5}$", name) else f"{name}.{fallback}"


def _media_of(msg: dict[str, Any], serial: list[int]) -> list[tuple[str, str]]:
    """The attachments of one message as (file name shown, member basename to look up)."""
    out: list[tuple[str, str]] = []
    for key in ("photos", "videos", "gifs"):
        for item in msg.get(key) or []:
            uri = str(item.get("uri", ""))
            if uri:
                base = PurePosixPath(uri).name
                out.append((_with_ext(base, "jpg" if key != "videos" else "mp4"), base))
    for item in msg.get("audio_files") or []:
        uri = str(item.get("uri", ""))
        if uri:
            serial[0] += 1
            # voice notes are .mp4 files; a new name keeps them from being treated as video
            out.append((f"voice_{serial[0]:05d}.m4a", PurePosixPath(uri).name))
    for item in msg.get("files") or []:
        uri = str(item.get("uri", ""))
        if uri:
            base = PurePosixPath(uri).name
            out.append((_with_ext(base, "bin"), base))
    sticker = msg.get("sticker")
    if isinstance(sticker, dict) and sticker.get("uri"):
        base = PurePosixPath(str(sticker["uri"])).name
        out.append(("STK-" + _with_ext(base, "webp"), base))
    return out


def convert(read: Callable[[str], bytes], thread: MetaThread, members: dict[str, str]) -> MetaChat:
    """Turn one conversation into chat text. `members` maps lower-case file names to zip paths."""
    records: list[tuple[int, int, str, dict[str, Any]]] = []
    title = ""
    seq = 0
    for path in thread.files:
        try:
            data = json.loads(read(path).decode("utf-8", errors="replace"))
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        title = title or fix_text(data.get("title"))
        for msg in data.get("messages") or []:
            if isinstance(msg, dict) and isinstance(msg.get("timestamp_ms"), int):
                seq += 1
                records.append((msg["timestamp_ms"], -seq, _clean_name(fix_text(msg.get("sender_name"))), msg))
    # each file lists its messages newest first; -seq keeps that order reversed for equal times
    records.sort(key=lambda r: (r[0], r[1]))

    lines: list[str] = []
    media: dict[str, str] = {}
    serial = [0]
    count = 0
    for ts, _, sender, msg in records:
        stamp = _stamp(ts)
        content = fix_text(msg.get("content"))
        attachments = _media_of(msg, serial)
        if msg.get("is_unsent"):
            lines.append(f"{stamp} - {sender}: This message was deleted")
            count += 1
            continue
        share = msg.get("share")
        if isinstance(share, dict) and share.get("link") and not attachments:
            link = fix_text(share.get("link"))
            note = fix_text(share.get("share_text"))
            content = "\n".join(part for part in (content, note, link) if part)
        if attachments and _AUTO_TEXT.search(content.strip()):
            content = ""
        if not attachments:
            if not content.strip():
                continue
            lines.append(f"{stamp} - {sender}: {_safe_body(content)}")
            count += 1
            continue
        for index, (name, base) in enumerate(attachments):
            member = members.get(base.lower())
            if member:
                media[name.lower()] = member
            head = f"{stamp} - {sender}: {name} (file attached)"
            if index == 0 and content.strip():
                head += "\n" + _safe_body(content)
            lines.append(head)
            count += 1
    return MetaChat("\n".join(lines) + "\n", media, title, _platform(thread.files[0]), count)