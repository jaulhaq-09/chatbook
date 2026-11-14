"""Parser for WhatsApp "Export chat" text files (Android and iOS, any locale)."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import PurePosixPath

from .models import MediaRef, Message, ParsedChat

_TIME = r"(\d{1,2})[:.](\d{2})(?::(\d{2}))?\s*([AaPp]\.?\s?[Mm]\.?)?"
_DATE = r"(\d{1,4})[/.\-](\d{1,2})[/.\-](\d{1,4}),?\s+"
# 12/03/2026, 9:41 am - Name: text
_HEAD_ANDROID = re.compile(rf"^{_DATE}{_TIME}\s+[-–—]\s+(.*)$", re.DOTALL)
# [12/03/2026, 9:41:05 PM] Name: text
_HEAD_IOS = re.compile(rf"^\[{_DATE}{_TIME}\]\s+(.*)$", re.DOTALL)

_ANDROID_ATTACHMENT = re.compile(r"^(.+?\.[A-Za-z0-9]{2,5})\s+\(file attached\)\s*$", re.IGNORECASE)
_IOS_ATTACHMENT = re.compile(r"<attached:\s*([^>]+?)\s*>")
_OMITTED = re.compile(
    r"^<?\s*(image|video|audio|sticker|gif|document|contact card|voice message|media)\s+omitted\s*>?$",
    re.IGNORECASE,
)
_DELETED = re.compile(r"^(this message was deleted|you deleted this message)\.?$", re.IGNORECASE)

_EXT_KIND = {
    **dict.fromkeys(("jpg", "jpeg", "png", "gif", "webp", "heic"), "image"),
    **dict.fromkeys(("mp4", "mov", "3gp", "mkv", "webm", "avi"), "video"),
    **dict.fromkeys(("opus", "ogg"), "voice"),
    **dict.fromkeys(("m4a", "aac", "mp3", "wav", "amr"), "audio"),
}
_OMITTED_KIND = {
    "image": "image",
    "gif": "image",
    "media": "image",
    "video": "video",
    "audio": "audio",
    "sticker": "sticker",
    "document": "doc",
    "contact card": "doc",
    "voice message": "voice",
}

# A sender name is the text before the first ": ", unless that is long (then it is a system line).
_MAX_SENDER_LEN = 60


def media_kind(name: str) -> str:
    """Classify an attachment by its file name."""
    ext = PurePosixPath(name).suffix.lstrip(".").lower()
    kind = _EXT_KIND.get(ext, "doc")
    if name.upper().startswith("STK-"):
        return "sticker"
    if kind == "audio" and "PTT" in name.upper():
        return "voice"
    return kind


def _split_attachment(text: str) -> tuple[MediaRef | None, str | None, str]:
    """Return (media, omitted_kind, remaining_text) for a message body."""
    first, _, rest = text.partition("\n")
    m = _ANDROID_ATTACHMENT.match(first)
    if m:
        name = m.group(1).strip()
        return MediaRef(name, media_kind(name)), None, rest.strip()
    m = _IOS_ATTACHMENT.search(text)
    if m:
        name = m.group(1).strip()
        remaining = (text[: m.start()] + text[m.end() :]).strip()
        return MediaRef(name, media_kind(name)), None, remaining
    m = _OMITTED.match(first.strip())
    if m and not rest:
        return None, _OMITTED_KIND.get(m.group(1).lower(), "image"), ""
    return None, None, text


def _make_datetime(y: int, mo: int, d: int, h: int, mi: int, s: int) -> datetime | None:
    if mo > 12 >= d:  # clearly month-first digits in a day-first reading, or vice versa
        mo, d = d, mo
    try:
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None


def parse_chat(raw: str, order: str = "auto") -> ParsedChat:
    """Parse the text of one export.

    `order` is "auto", "dmy" or "mdy". With "auto" the order is detected from any date whose
    first or second number is above 12. When every date is ambiguous the result is flagged.
    """
    text = raw.lstrip("﻿").replace("‎", "").replace("‏", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    records: list[dict] = []
    current: dict | None = None
    for line in text.split("\n"):
        m = _HEAD_ANDROID.match(line) or _HEAD_IOS.match(line)
        if m:
            current = {
                "p": (m.group(1), m.group(2), m.group(3)),
                "h": int(m.group(4)),
                "mi": int(m.group(5)),
                "s": int(m.group(6) or 0),
                "ap": m.group(7) or "",
                "body": m.group(8),
            }
            records.append(current)
        elif current is not None:
            current["body"] += "\n" + line

    saw_dmy = saw_mdy = False
    year_first_only = bool(records)
    for r in records:
        p = r["p"]
        if len(p[0]) <= 2:
            year_first_only = False
            a, b = int(p[0]), int(p[1])
            if a > 12:
                saw_dmy = True
            elif b > 12:
                saw_mdy = True

    forced = order in ("dmy", "mdy")
    if forced:
        resolved = order
    elif saw_mdy and not saw_dmy:
        resolved = "mdy"
    else:
        resolved = "dmy"
    ambiguous = bool(records) and not forced and not saw_dmy and not saw_mdy and not year_first_only

    messages: list[Message] = []
    senders: Counter[str] = Counter()
    for r in records:
        p = r["p"]
        if len(p[0]) == 4:
            y, mo, d = int(p[0]), int(p[1]), int(p[2])
        else:
            y = int(p[2])
            if y < 100:
                y += 2000
            if resolved == "mdy":
                mo, d = int(p[0]), int(p[1])
            else:
                d, mo = int(p[0]), int(p[1])
        h = r["h"]
        if r["ap"]:
            h = (h % 12) + (12 if "p" in r["ap"].lower() else 0)
        ts = _make_datetime(y, mo, d, h, r["mi"], r["s"])
        if ts is None:
            continue

        body: str = r["body"]
        sender: str | None = None
        content = body
        idx = body.find(": ")
        if 0 < idx <= _MAX_SENDER_LEN and "\n" not in body[:idx]:
            sender, content = body[:idx], body[idx + 2 :]

        msg = Message(id=len(messages), ts=ts, sender=sender)
        if sender is None:
            msg.text = body.strip()
            messages.append(msg)
            continue

        senders[sender] += 1
        content = content.rstrip()
        if _DELETED.match(content.strip()):
            msg.deleted = True
        else:
            msg.media, msg.omitted, msg.text = _split_attachment(content)
        messages.append(msg)

    return ParsedChat(messages=messages, senders=dict(senders), order=resolved, ambiguous=ambiguous)


def _message_key(m: Message) -> tuple:
    return (
        m.ts,
        m.sender or "",
        m.text,
        m.media.name if m.media else "",
        m.omitted or "",
        m.deleted,
    )


def merge_chats(chats: list[ParsedChat]) -> tuple[list[Message], dict[str, int]]:
    """Combine several exports into one timeline.

    A message that already appears in an earlier export is dropped from later ones, so
    overlapping exports do not repeat. Identical messages inside one export are all kept.
    """
    kept: list[Message] = []
    seen: Counter[tuple] = Counter()
    for index, chat in enumerate(chats):
        available = Counter(seen)
        fresh: list[Message] = []
        for m in chat.messages:
            key = _message_key(m)
            if index > 0 and available[key] > 0:
                available[key] -= 1
                continue
            fresh.append(m)
        for m in fresh:
            seen[_message_key(m)] += 1
        kept.extend(fresh)

    order = {id(m): i for i, m in enumerate(kept)}
    kept.sort(key=lambda m: (m.ts, order[id(m)]))
    senders: Counter[str] = Counter()
    for i, m in enumerate(kept):
        m.id = i
        if m.sender:
            senders[m.sender] += 1
    return kept, dict(senders)
