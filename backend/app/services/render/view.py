"""Build the view model for one volume and render it to HTML with Jinja."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.models import Message
from app.services.render.fmt import (
    css_string,
    day_label,
    duration,
    fmt_text,
    fmt_time,
    month_label,
    plural,
    range_label,
    short_date,
)
from app.services.render.fonts import font_stack
from app.services.render.layout import (
    FONT_PX,
    VolumePlan,
    album_groups,
    estimate_album_pages,
    estimate_book_pages,
    fit_dims,
)
from app.services.render.motifs import motif_svg
from app.services.render.plan import Plan, toc_labels, volume_counts

TEMPLATES = Path(__file__).resolve().parent.parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["css_str"] = css_string

_NAME_COLORS = ["#1f7aec", "#c2410c", "#7c3aed", "#0f766e", "#b91c1c", "#a16207", "#be185d", "#4d7c0f"]
_KIND_LABEL = {
    "image": "Photo",
    "video": "Video",
    "voice": "Voice message",
    "audio": "Audio",
    "doc": "Document",
    "sticker": "Sticker",
}


def _name_color(name: str) -> str:
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return _NAME_COLORS[h % len(_NAME_COLORS)]


def _wave_bars(name: str) -> list[int]:
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    bars = []
    for _ in range(30):
        h = (h * 1103515245 + 12345) & 0xFFFFFFFF
        bars.append(4 + ((h >> 16) % 17))
    return bars


def _src(plan: Plan, entry: dict[str, Any], media_base: str) -> str | None:
    return f"{media_base}{plan.variant}/{entry['file']}" if entry.get("file") else None


def _message_item(m: Message, first: bool, plan: Plan, media_base: str) -> dict[str, Any]:
    o = plan.options
    out = m.sender == plan.me
    item: dict[str, Any] = {
        "type": "msg",
        "side": "out" if out else "in",
        "first": first,
        "name": m.sender if (first and not out and plan.n_senders > 2) else None,
        "name_color": _name_color(m.sender or ""),
        "time": fmt_time(m.ts, o.clock),
        "kind": "text",
        "caption_html": fmt_text(m.text) if (m.text and (m.media or m.omitted)) else None,
        "text_html": fmt_text(m.text) if not (m.media or m.omitted) else None,
    }
    if m.deleted:
        item["kind"] = "deleted"
        return item
    if not (m.media or m.omitted):
        return item

    kind = m.media.kind if m.media else (m.omitted or "image")
    label = _KIND_LABEL.get(kind, "Media")
    if not o.show_media:
        item.update(kind="label", label=label)
        return item

    entry = plan.registry.get(m.media.name.lower()) if m.media else None
    ok = bool(entry and entry["state"] == "ok")
    if kind in ("image", "video") and ok:
        w, h = fit_dims(entry["w"], entry["h"], plan.spec)
        item.update(kind=kind, src=_src(plan, entry, media_base), w=w, h=h, dur=duration(entry.get("dur")))
    elif kind == "sticker" and ok:
        item.update(kind="sticker", src=_src(plan, entry, media_base))
    elif kind in ("voice", "audio"):
        name = m.media.name if m.media else "voice"
        item.update(kind="voice", bars=_wave_bars(name), dur=duration(entry.get("dur") if entry else None))
    elif kind == "doc" and m.media:
        item.update(kind="doc", doc_name=m.media.name, ext=(m.media.name.rsplit(".", 1)[-1][:4].upper() or "FILE"))
    else:
        if m.omitted:
            reason = f"{label} left out of this export"
        elif entry and entry["state"] == "bad":
            reason = f"{label} could not be read"
        else:
            reason = f"{label} not in this export"
        item.update(kind="missing", label=reason)
    return item


def build_book_items(msgs: list[Message], plan: Plan, media_base: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    last_day = last_month = prev_sender = None
    for m in msgs:
        day = m.ts.date()
        if day != last_day:
            month = (m.ts.year, m.ts.month)
            if month != last_month:
                items.append({"type": "month", "label": month_label(m.ts)})
                last_month = month
            items.append({"type": "day", "label": day_label(m.ts)})
            last_day, prev_sender = day, None
        if m.system:
            items.append({"type": "sys", "text": m.text})
            prev_sender = None
            continue
        items.append(_message_item(m, prev_sender != m.sender, plan, media_base))
        prev_sender = m.sender
    return items


def build_album_groups(cells: list[Message], plan: Plan, media_base: str) -> list[dict[str, Any]]:
    o = plan.options.album
    groups = []
    for label, group_cells in album_groups(cells, o.group):
        out = []
        for m in group_cells:
            entry = plan.registry[m.media.name.lower()]  # type: ignore[union-attr]
            caption = short_date(m.ts) + (f" · {m.sender}" if m.sender else "")
            out.append(
                {
                    "src": _src(plan, entry, media_base),
                    "video": m.media.kind == "video",  # type: ignore[union-attr]
                    "dur": duration(entry.get("dur")),
                    "caption": caption if o.captions else None,
                }
            )
        groups.append({"label": label, "cells": out})
    return groups


def _cover_summary(plan: Plan, vol: VolumePlan) -> str:
    msgs, photos, videos = volume_counts(plan, vol)
    if plan.options.mode == "album":
        parts = [plural(photos, "photo") if photos else "", plural(videos, "video") if videos else ""]
    else:
        parts = [
            plural(msgs, "message"),
            plural(photos, "photo") if photos else "",
            plural(videos, "video") if videos else "",
        ]
    return ", ".join(p for p in parts if p)


def _people(plan: Plan, vol: VolumePlan) -> str:
    seen: list[str] = []
    for m in vol.messages:
        if m.sender and m.sender not in seen:
            seen.append(m.sender)
    return ", ".join(seen[:6])


def preview_page_count(vol: VolumePlan, per_page: int) -> int:
    return max(1, math.ceil(len(vol.messages) / per_page))


@dataclass
class Body:
    """One slice of a long volume, rendered as its own document and joined to the others afterwards."""

    items: list[dict[str, Any]] | None = None  # book mode
    groups: list[dict[str, Any]] | None = None  # album mode
    front: bool = False  # cover and contents belong to the first slice only
    back: bool = False  # the back page belongs to the last slice only
    toc: bool = True  # False leaves the contents page out (a section preview has no real page numbers)
    page_start: int | None = None  # number of this slice's first page in the whole volume


# Chromium paginates a document in one go, and the work grows faster than the page count: 160 pages
# take 18 s but 490 pages take 130 s. Slices of about this many pages keep the total close to linear.
SLICE_WEIGHT = 1800  # a text message weighs 1, a photo or video 6; about 100 pages


def _weight(item: dict[str, Any]) -> int:
    return 6 if item.get("kind") in ("image", "video", "sticker") else 1


def split_body(plan: Plan, vol: VolumePlan, media_base: str, budget: int | None = None) -> list[Body]:
    """Cut a volume into slices at day boundaries (book) or group boundaries (album)."""
    bodies = _split_body(plan, vol, media_base, budget)
    bodies[-1].back = True
    return bodies


def _split_body(plan: Plan, vol: VolumePlan, media_base: str, budget: int | None = None) -> list[Body]:
    o = plan.options
    budget = SLICE_WEIGHT if budget is None else budget
    if o.mode == "book":
        items = build_book_items(vol.messages, plan, media_base)
        slices: list[list[dict[str, Any]]] = [[]]
        weight = 0
        for i, it in enumerate(items):
            starts_block = it["type"] in ("month", "day")
            # a month heading is followed by its first day: break before the heading, never between them
            after_month = i > 0 and items[i - 1]["type"] == "month"
            if weight >= budget and starts_block and not after_month:
                slices.append([])
                weight = 0
            slices[-1].append(it)
            weight += _weight(it)
        return [Body(items=s, front=(n == 0)) for n, s in enumerate(slices)]

    groups = build_album_groups(vol.messages, plan, media_base)
    parts: list[list[dict[str, Any]]] = [[]]
    weight = 0
    for g in groups:
        cells = g["cells"]
        label = g["label"]
        while cells:
            room = max(1, (budget - weight) // 6) if weight < budget else 0
            if room == 0:
                parts.append([])
                weight = 0
                continue
            take, cells = cells[:room], cells[room:]
            parts[-1].append({"label": label, "cells": take})
            weight += 6 * len(take)
            label = f"{g['label']} (continued)" if g["label"] else ""
    return [Body(groups=p, front=(n == 0)) for n, p in enumerate(parts) if p or n == 0]


def _page_backgrounds(plan: Plan) -> tuple[str, str]:
    """CSS `background` of the inside pages and of the cover. A picture replaces the plain paper colour.

    Chromium positions a page background against the page's content area, so the picture is moved out by
    the margins and sized to the whole sheet to reach the edges.
    """
    paper = plan.theme["page"]
    file = plan.background_file
    if not file:
        return paper, paper
    spec = plan.spec
    size = f"{spec.width:g}mm {spec.height:g}mm"
    inside = f'{paper} url("{file}") no-repeat -{spec.side:g}mm -{spec.top:g}mm / {size}'
    cover = f'{paper} url("{file}") no-repeat 0 0 / {size}'
    scope = plan.options.background.scope
    return (inside if scope in ("all", "inside") else paper), (cover if scope in ("all", "cover") else paper)


def _mix(hex_color: str, base: str, amount: float) -> str:
    """`hex_color` laid over `base` at `amount` (0..1), as a hex colour."""
    a = [int(hex_color[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * amount + y * (1 - amount)):02x}" for x, y in zip(a, b, strict=True))


def _paper_hex(plan: Plan) -> str:
    paper = plan.theme["page"]
    return paper if re.fullmatch(r"#[0-9a-fA-F]{6}", paper) else "#ffffff"


def _foot(mode: str, text: str, auto: dict[str, str]) -> str:
    """The words for one corner of the footer: an automatic value, the person's own text, or nothing."""
    if mode == "none":
        return ""
    return text.strip() if mode == "text" else auto.get(mode, "")


def _faces(plan: Plan, vol: VolumePlan, *, show_cover: bool, show_back: bool) -> tuple[dict | None, dict | None]:
    """Text of the cover and of the back page. Blank fields fall back to automatic text."""
    o = plan.options
    ct, bk = o.cover_text, o.back
    total = len(plan.volumes)
    dates = range_label(vol.start, vol.end)
    auto = {"people": _people(plan, vol), "counts": _cover_summary(plan, vol), "dates": dates}
    volume = f"Volume {vol.index} of {total}" if total > 1 else ""
    cover = back = None
    if show_cover:
        cover = {
            "kicker": " · ".join(x for x in (ct.kicker.strip(), volume) if x),
            "title": plan.title,
            "sub": ct.subtitle.strip() or dates,
            "tag": ct.tagline.strip(),
            "sign": "",
            "foot_l": _foot(ct.left_mode, ct.footer_left, auto),
            "foot_r": _foot(ct.right_mode, ct.footer_right, auto),
        }
    if show_back:
        back = {
            "kicker": volume,
            "title": bk.heading.strip(),
            "sub": "",
            "tag": bk.message.strip() or dates,
            "sign": bk.signature.strip(),
            "foot_l": _foot(bk.left_mode, bk.footer_left, auto),
            "foot_r": _foot(bk.right_mode, bk.footer_right, auto),
        }
    return cover, back


def render_volume_html(
    plan: Plan,
    vol: VolumePlan,
    *,
    media_base: str,
    preview: bool = False,
    page: int = 1,
    per_page: int = 250,
    toc_pages: dict[str, str] | None = None,
    body: Body | None = None,
) -> str:
    """HTML of one volume. A preview renders only one slice of it and leaves out the contents page.

    With `body` the document holds just that slice of the volume (see `split_body`).
    """
    o = plan.options
    msgs = vol.messages
    if preview:
        page = min(max(1, page), preview_page_count(vol, per_page))
        msgs = msgs[(page - 1) * per_page : page * per_page]
    total = len(plan.volumes)

    front = body.front if body else True
    toc = None
    labels = [] if (preview or not front or (body is not None and not body.toc)) else toc_labels(plan, vol)
    if labels:
        toc = [{"label": label, "page": (toc_pages or {}).get(label, "000")} for label in labels]

    auto_header = plan.title + (f" · {vol.label}" if total > 1 and vol.label else "")
    header_left = o.header_left.strip() or auto_header
    show_cover = bool(o.cover and front and (not preview or page == 1))
    last = (body.back if body else True) if not preview else page >= preview_page_count(vol, per_page)
    show_back = bool(o.back.enabled and last)
    cover_face, back_face = _faces(plan, vol, show_cover=show_cover, show_back=show_back)
    paper = _paper_hex(plan)
    c1, c2 = o.design.color1, o.design.color2
    title_pt = 40 if len(plan.title) <= 22 else 32 if len(plan.title) <= 40 else 26
    spec = plan.spec
    page_bg, cover_bg = _page_backgrounds(plan)
    css = _env.get_template("style.css").render(
        spec=spec,
        page_bg=page_bg,
        cover_bg=cover_bg,
        cover_picture=cover_bg != plan.theme["page"],
        t=plan.theme,
        fs=FONT_PX[o.text_size],
        font=font_stack(o.chat_font),
        serif=font_stack(o.design.heading_font),
        c1=c1,
        c2=c2,
        c1_soft=_mix(c1, paper, 0.12),
        c2_soft=_mix(c2, paper, 0.25),
        cover_style=o.design.cover_style,
        title_pt=title_pt,
        header_left=header_left,
        header_right=o.header_right.strip() or range_label(vol.start, vol.end),
        footer_left=f"Volume {vol.index} of {total}" if total > 1 else "",
        page_numbers=o.page_numbers,
        cols=o.album.columns,
        page_start=body.page_start if body else None,
    )
    html = _env.get_template("document.html").render(
        css=css,
        mode=o.mode,
        preview=preview,
        doc_title=plan.title,
        title=plan.title,
        cover=cover_face,
        back=back_face,
        cover_style=o.design.cover_style,
        motif=motif_svg(o.design.motif, c1, c2),
        toc=toc,
        items=(body.items if body else build_book_items(msgs, plan, media_base)) if o.mode == "book" else None,
        groups=(body.groups if body else build_album_groups(msgs, plan, media_base)) if o.mode == "album" else None,
        preload=plan.background_file if (page_bg != plan.theme["page"] or cover_bg != plan.theme["page"]) else None,
        fit_class="fit" if (o.album.fit == "fit") else "fill",
        cols=o.album.columns,
    )
    return html


def section_summaries(plan: Plan, vol: VolumePlan, per_page: int) -> list[dict[str, Any]]:
    """For every preview section of a volume: the dates it covers and how many photos and videos it holds."""
    out: list[dict[str, Any]] = []
    for i in range(0, len(vol.messages), per_page):
        chunk = vol.messages[i : i + per_page]
        photos = videos = 0
        for m in chunk:
            if not m.media or m.deleted:
                continue
            entry = plan.registry.get(m.media.name.lower())
            if not (entry and entry["state"] == "ok"):
                continue
            if m.media.kind == "image":
                photos += 1
            elif m.media.kind == "video":
                videos += 1
        if plan.options.mode == "album":
            pages = estimate_album_pages(album_groups(chunk, plan.options.album.group), plan.options, plan.spec)
        else:
            pages = estimate_book_pages(chunk, plan.options, plan.spec, plan.registry, plan.n_senders, plan.me)
        out.append(
            {
                "pages": pages,
                "start": chunk[0].ts.date().isoformat(),
                "end": chunk[-1].ts.date().isoformat(),
                "photos": photos,
                "videos": videos,
            }
        )
    return out


def render_section_html(plan: Plan, vol: VolumePlan, *, page: int, per_page: int, media_base: str) -> str:
    """Print-layout HTML of one section of a volume, for the page preview.

    A section is the same slice of messages the HTML preview uses. It has no contents page, because
    its page numbers would mean nothing. The first section carries the cover.
    """
    count = preview_page_count(vol, per_page)
    page = min(max(1, page), count)
    chunk = vol.messages[(page - 1) * per_page : page * per_page]
    front, back = page == 1, page == count  # the cover opens the first section, the back page closes the last
    if plan.options.mode == "book":
        body = Body(items=build_book_items(chunk, plan, media_base), front=front, back=back, toc=False)
    else:
        body = Body(groups=build_album_groups(chunk, plan, media_base), front=front, back=back, toc=False)
    return render_volume_html(plan, vol, media_base=media_base, body=body)