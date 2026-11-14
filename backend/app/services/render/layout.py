"""Page sizes, themes, filtering, volume splitting and page-count estimates."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from app.core.models import Message
from app.schemas import RenderOptions
from app.services.render.fmt import month_label

MM = 96 / 25.4  # CSS pixels per millimetre
MAX_TOC_ENTRIES = 72


@dataclass(frozen=True)
class PageSpec:
    key: str
    width: float  # mm
    height: float
    top: float
    side: float
    bottom: float
    css_size: str

    @property
    def body_w(self) -> float:
        return (self.width - 2 * self.side) * MM

    @property
    def body_h(self) -> float:
        return (self.height - self.top - self.bottom) * MM


PAGES: dict[str, PageSpec] = {
    "A4": PageSpec("A4", 210, 297, 20, 16, 22, "A4"),
    "Letter": PageSpec("Letter", 215.9, 279.4, 20, 16, 22, "Letter"),
    "A5": PageSpec("A5", 148, 210, 16, 12, 18, "A5"),
    "Square": PageSpec("Square", 200, 200, 16, 14, 18, "200mm 200mm"),
}
FONT_PX = {"s": 12.0, "m": 13.5, "l": 15.0}

_BOOK_THEMES: dict[str, dict[str, str]] = {
    "classic": dict(
        page="#efeae2",
        text="#111b21",
        bubble_in="#ffffff",
        bubble_out="#d9fdd3",
        bubble_border="transparent",
        time="#667781",
        chip="#ffffff",
        chip_border="transparent",
        sys="#ffeecd",
        head="#54656f",
        rule="rgba(17,27,33,.16)",
        shadow="0 1px 1px rgba(11,20,26,.12)",
        tile="#c9d1d4",
    ),
    "clean": dict(
        page="#ffffff",
        text="#1b2328",
        bubble_in="#f0f2f3",
        bubble_out="#e0f4db",
        bubble_border="transparent",
        time="#6a7880",
        chip="#f0f2f3",
        chip_border="transparent",
        sys="#f6efd8",
        head="#6a7880",
        rule="#dde1e3",
        shadow="none",
        tile="#c9d1d4",
    ),
    "ink": dict(
        page="#ffffff",
        text="#111111",
        bubble_in="#ffffff",
        bubble_out="#ffffff",
        bubble_border="#a9afb3",
        time="#666666",
        chip="#ffffff",
        chip_border="#c3c8cb",
        sys="#ffffff",
        head="#555555",
        rule="#d0d4d6",
        shadow="none",
        tile="#d5d9db",
    ),
}
_PAPERS: dict[str, dict[str, str]] = {
    "white": dict(page="#ffffff", text="#111111", head="#6a6a6a", rule="#dcdcdc", tile="#dfe3e4"),
    "warm": dict(page="#f5f0e6", text="#2a241a", head="#7a705e", rule="#ded6c4", tile="#e2dac8"),
    "black": dict(page="#121212", text="#f2f2f2", head="#9b9b9b", rule="#303030", tile="#262626"),
}


def tokens(options: RenderOptions) -> dict[str, str]:
    if options.mode == "album":
        return {**_BOOK_THEMES["clean"], **_PAPERS[options.album.paper]}
    return dict(_BOOK_THEMES[options.theme])


# ---- filtering -------------------------------------------------------------------------
def filter_messages(messages: list[Message], o: RenderOptions) -> list[Message]:
    start = datetime.combine(o.date_from, time.min) if o.date_from else None
    end = datetime.combine(o.date_to, time.max) if o.date_to else None
    excluded = set(o.exclude_people)
    query = o.query.strip().lower() if o.mode == "book" else ""
    out: list[Message] = []
    for m in messages:
        if (start and m.ts < start) or (end and m.ts > end):
            continue
        if m.sender and m.sender in excluded:
            continue
        if query:
            if m.system:
                continue
            haystack = f"{m.text} {m.media.name if m.media else ''}".lower()
            if query not in haystack:
                continue
        out.append(m)
    return out


def album_cells(messages: list[Message], registry: dict[str, dict[str, Any]], include_videos: bool) -> list[Message]:
    """Messages whose photo (or video) can be shown in an album."""
    cells = []
    for m in messages:
        if not m.media or m.media.kind not in ("image", "video"):
            continue
        if m.media.kind == "video" and not include_videos:
            continue
        entry = registry.get(m.media.name.lower())
        if entry and entry["state"] == "ok":
            cells.append(m)
    return cells


# ---- volumes ---------------------------------------------------------------------------
@dataclass
class VolumePlan:
    index: int  # 1-based
    label: str
    suffix: str  # used in the file name
    messages: list[Message]  # book: shown messages, album: messages that carry a photo or video

    @property
    def start(self) -> datetime:
        return self.messages[0].ts

    @property
    def end(self) -> datetime:
        return self.messages[-1].ts


def split_volumes(msgs: list[Message], o: RenderOptions, unit: Callable[[Message], int]) -> list[VolumePlan]:
    if not msgs:
        return []
    mode = o.volume_mode
    if mode == "none":
        return [VolumePlan(1, "", "", msgs)]
    groups: list[tuple[str, str, list[Message]]] = []
    if mode in ("month", "year"):
        index: dict[tuple, int] = {}
        for m in msgs:
            key = (m.ts.year, m.ts.month) if mode == "month" else (m.ts.year,)
            i = index.get(key)
            if i is None:
                i = index[key] = len(groups)
                label = month_label(m.ts) if mode == "month" else str(m.ts.year)
                suffix = f"{m.ts:%Y-%m}" if mode == "month" else f"{m.ts.year}"
                groups.append((label, suffix, []))
            groups[i][2].append(m)
    else:  # size: close a volume at the first day change after it reaches the target
        cur: list[Message] = []
        count, last_day = 0, None
        chunks: list[list[Message]] = []
        for m in msgs:
            if count >= o.volume_size and m.ts.date() != last_day:
                chunks.append(cur)
                cur, count = [], 0
            cur.append(m)
            count += unit(m)
            last_day = m.ts.date()
        if cur:
            chunks.append(cur)
        groups = [(f"Part {i}", f"vol{i}", c) for i, c in enumerate(chunks, 1)]
    return [VolumePlan(i, label, suffix, ms) for i, (label, suffix, ms) in enumerate(groups, 1)]


def month_labels(msgs: list[Message]) -> list[str]:
    seen: list[str] = []
    for m in msgs:
        label = month_label(m.ts)
        if not seen or seen[-1] != label:
            seen.append(label)
    return seen


def album_groups(cells: list[Message], group: str) -> list[tuple[str, list[Message]]]:
    """Cells grouped for the album. With group "none" there is one unnamed group."""
    if group == "none":
        return [("", cells)] if cells else []
    out: list[tuple[str, list[Message]]] = []
    index: dict[Any, int] = {}
    for m in cells:
        if group == "month":
            key, label = (m.ts.year, m.ts.month), month_label(m.ts)
        elif group == "day":
            key, label = m.ts.date(), f"{m.ts:%A} {m.ts.day} {m.ts:%B %Y}"
        else:
            key = label = m.sender or "Unknown"
        i = index.get(key)
        if i is None:
            i = index[key] = len(out)
            out.append((label, []))
        out[i][1].append(m)
    return out


# ---- estimates -------------------------------------------------------------------------
def fit_dims(w: int, h: int, spec: PageSpec) -> tuple[int, int]:
    """Size an image bubble the way the print layout does."""
    max_w = min(320, round(spec.body_w * 0.5))
    max_h = round(min(380, spec.body_h * 0.42))
    width, height = float(max_w), max_w * h / w
    if height > max_h:
        height, width = float(max_h), max_h * w / h
    return round(max(110, width)), round(max(60, height))


def estimate_book_pages(
    msgs: list[Message], o: RenderOptions, spec: PageSpec, registry: dict[str, dict[str, Any]], n_senders: int, me: str
) -> int:
    """Cheap page-count estimate for the book body (no HTML is built)."""
    font = FONT_PX[o.text_size]
    line_h = font * 1.38
    chars = max(10, (spec.body_w * 0.76 - 17) / (font * 0.54))

    def lines(text: str) -> int:
        return sum(max(1, math.ceil(len(part) / chars)) for part in text.split("\n"))

    total = 0.0
    last_day = None
    last_month = None
    prev_sender: str | None = None
    for m in msgs:
        if m.ts.date() != last_day:
            last_day = m.ts.date()
            total += 24 + 16
            prev_sender = None
            month = (m.ts.year, m.ts.month)
            if month != last_month:
                last_month = month
                total += 56
        if m.system:
            total += lines(m.text) * line_h * 0.85 + 8 + 9
            prev_sender = None
            continue
        first = prev_sender != m.sender
        prev_sender = m.sender
        gap = 9 if first else 3
        name = 19 if (first and n_senders > 2 and m.sender != me) else 0
        caption = (lines(m.text) * line_h + 8) if m.text else 0
        entry = registry.get(m.media.name.lower()) if m.media else None
        kind = m.media.kind if m.media else m.omitted
        if m.deleted:
            total += line_h + 12 + gap + name
        elif not (m.media or m.omitted):
            total += lines(m.text) * line_h + 12 + gap + name
        elif not o.show_media:
            total += line_h + 12 + gap + name + caption
        elif m.media and kind in ("image", "video") and entry and entry["state"] == "ok":
            _, h = fit_dims(entry["w"], entry["h"], spec)
            total += h + 8 + caption + gap + name
        elif kind == "sticker" and entry and entry["state"] == "ok":
            total += 110 + gap
        elif kind in ("voice", "audio"):
            total += 46 + caption + gap + name
        elif kind == "doc":
            total += 52 + caption + gap + name
        else:
            total += 96 + 14 + caption + gap + name
    return max(1, math.ceil(total / (spec.body_h * 0.97)))


def estimate_album_pages(groups: list[tuple[str, list[Message]]], o: RenderOptions, spec: PageSpec) -> int:
    cols = o.album.columns
    cell_w = (spec.body_w - 10 * (cols - 1)) / cols
    caption = 18 if o.album.captions else 0
    row_h = (cell_w if cols > 1 else min(spec.body_w * 0.75, 215 * MM)) + caption + 10
    total = 0.0
    for label, cells in groups:
        total += (44 if label else 0) + math.ceil(len(cells) / cols) * row_h
    return max(1, math.ceil(total / (spec.body_h * 0.97)))
