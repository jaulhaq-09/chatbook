"""A render plan: the filtered messages, split into volumes, plus statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.models import Message
from app.schemas import RenderOptions, Stats, VolumeStat
from app.services.render.layout import (
    MAX_TOC_ENTRIES,
    PAGES,
    PageSpec,
    VolumePlan,
    album_cells,
    album_groups,
    estimate_album_pages,
    estimate_book_pages,
    filter_messages,
    month_labels,
    split_volumes,
    tokens,
)


@dataclass
class Plan:
    options: RenderOptions
    spec: PageSpec
    title: str
    me: str
    n_senders: int
    registry: dict[str, dict[str, Any]]
    volumes: list[VolumePlan]
    theme: dict[str, str]
    background_file: str | None = None  # page-sized picture in the render folder, set just before rendering

    @property
    def variant(self) -> str:
        return "print" if self.options.quality == "print" else "web"


def build_plan(
    options: RenderOptions, job: dict[str, Any], messages: list[Message], registry: dict[str, dict[str, Any]]
) -> Plan:
    names = [s["name"] for s in job["senders"]]
    if options.me in names:
        me = options.me or ""
    else:  # WhatsApp does not say who "you" are; the second most active person is a reasonable guess
        me = names[1] if len(names) > 1 else (names[0] if names else "")
    shown = filter_messages(messages, options)
    if options.mode == "album":
        volumes = split_volumes(album_cells(shown, registry, options.album.include_videos), options, lambda m: 1)
    else:
        volumes = split_volumes(shown, options, lambda m: 0 if m.system else 1)
    return Plan(
        options=options,
        spec=PAGES[options.page_size],
        title=options.title.strip() or job.get("suggested_title") or "Chat",
        me=me,
        n_senders=len(names),
        registry=registry,
        volumes=volumes,
        theme=tokens(options),
    )


def toc_labels(plan: Plan, vol: VolumePlan) -> list[str]:
    """Entries of the contents page for one volume (empty when a contents page would not help)."""
    o = plan.options
    if not o.toc:
        return []
    if o.mode == "book":
        labels = month_labels(vol.messages)
    else:
        labels = [label for label, _ in album_groups(vol.messages, o.album.group) if label]
    return labels if 2 <= len(labels) <= MAX_TOC_ENTRIES else []


def _counts(plan: Plan, msgs: list[Message]) -> tuple[int, int, int]:
    photos = videos = 0
    for m in msgs:
        if not m.media:
            continue
        entry = plan.registry.get(m.media.name.lower())
        if entry and entry["state"] == "ok":
            if m.media.kind == "image":
                photos += 1
            elif m.media.kind == "video":
                videos += 1
    return sum(1 for m in msgs if not m.system), photos, videos


def volume_counts(plan: Plan, vol: VolumePlan) -> tuple[int, int, int]:
    return _counts(plan, vol.messages)


def compute_stats(plan: Plan) -> Stats:
    o = plan.options
    stats: list[VolumeStat] = []
    for vol in plan.volumes:
        msgs, photos, videos = _counts(plan, vol.messages)
        if o.mode == "album":
            body = estimate_album_pages(album_groups(vol.messages, o.album.group), o, plan.spec)
        else:
            body = estimate_book_pages(vol.messages, o, plan.spec, plan.registry, plan.n_senders, plan.me)
        front = (1 if o.cover else 0) + (1 if toc_labels(plan, vol) else 0) + (1 if o.back.enabled else 0)
        stats.append(
            VolumeStat(
                index=vol.index,
                label=vol.label,
                messages=msgs,
                photos=photos,
                videos=videos,
                start=vol.start.isoformat(),
                end=vol.end.isoformat(),
                estimated_pages=body + front,
            )
        )
    return Stats(
        messages=sum(v.messages for v in stats),
        photos=sum(v.photos for v in stats),
        videos=sum(v.videos for v in stats),
        estimated_pages=sum(v.estimated_pages for v in stats),
        toc_available=any(toc_labels(plan, v) for v in plan.volumes),
        volumes=stats,
    )