"""Text formatting helpers (dates, times, WhatsApp markup)."""

from __future__ import annotations

import re
from datetime import datetime

from markupsafe import Markup, escape

_BOLD = re.compile(r"(^|[\s(])\*([^*\n]+)\*(?=$|[\s.,!?:;)])")
_ITALIC = re.compile(r"(^|[\s(])_([^_\n]+)_(?=$|[\s.,!?:;)])")
_STRIKE = re.compile(r"(^|[\s(])~([^~\n]+)~(?=$|[\s.,!?:;)])")


def fmt_text(text: str) -> Markup:
    """Escape a message and apply WhatsApp's *bold*, _italic_ and ~strike~."""
    s = str(escape(text))
    s = _BOLD.sub(r"\1<b>\2</b>", s)
    s = _ITALIC.sub(r"\1<i>\2</i>", s)
    s = _STRIKE.sub(r"\1<s>\2</s>", s)
    return Markup(s)  # noqa: S704 - the text was escaped above


def fmt_time(ts: datetime, clock: str) -> str:
    if clock == "h24":
        return f"{ts.hour:02d}:{ts.minute:02d}"
    return f"{ts.hour % 12 or 12}:{ts.minute:02d} {'am' if ts.hour < 12 else 'pm'}"


def day_label(ts: datetime) -> str:
    return f"{ts:%A} {ts.day} {ts:%B %Y}"


def month_label(ts: datetime) -> str:
    return f"{ts:%B %Y}"


def short_date(ts: datetime) -> str:
    return f"{ts.day} {ts:%b %Y}"


def range_label(a: datetime, b: datetime) -> str:
    if a.date() == b.date():
        return f"{a.day} {a:%B %Y}"
    if a.year == b.year:
        return f"{a.day} {a:%B} \u2013 {b.day} {b:%B %Y}"
    return f"{a.day} {a:%B %Y} \u2013 {b.day} {b:%B %Y}"


def duration(seconds: float | None) -> str | None:
    if not seconds:
        return None
    s = round(seconds)
    return f"{s // 60}:{s % 60:02d}"


def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def css_string(value: str) -> str:
    """A safe CSS string literal, for generated `content:` values."""
    out = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    out = out.replace("<", "\\3c ").replace(">", "\\3e ")
    return f'"{out}"'
