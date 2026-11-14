"""Plain statistics about a chat, for the Insights tab. Pure functions, no I/O."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from typing import Any

from app.core.models import Message

_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿⭐⭕]")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _streak(days: list[date]) -> int:
    """Longest run of consecutive calendar days that have at least one message."""
    best = run = 0
    prev: date | None = None
    for d in days:
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    return best


def compute_insights(messages: list[Message]) -> dict[str, Any]:
    chat = [m for m in messages if not m.system]
    if not chat:
        return {
            "total_messages": 0, "total_days": 0, "active_days": 0, "avg_per_active_day": 0.0,
            "busiest_day": None, "longest_streak": 0, "by_hour": [0] * 24,
            "by_weekday": [{"label": w, "count": 0} for w in WEEKDAYS], "by_month": [], "daily": [],
            "senders": [], "emojis": [],
        }  # fmt: skip

    per_day: Counter[date] = Counter()
    per_hour: Counter[int] = Counter()
    per_weekday: Counter[int] = Counter()
    per_month: Counter[tuple[int, int]] = Counter()
    emojis: Counter[str] = Counter()
    stats: dict[str, dict[str, int]] = {}
    starters: Counter[str] = Counter()
    last_day: date | None = None

    for m in chat:
        d = m.ts.date()
        per_day[d] += 1
        per_hour[m.ts.hour] += 1
        per_weekday[m.ts.weekday()] += 1
        per_month[(m.ts.year, m.ts.month)] += 1
        s = stats.setdefault(
            m.sender or "Unknown",
            {"messages": 0, "words": 0, "photos": 0, "videos": 0, "voice": 0, "deleted": 0},
        )
        s["messages"] += 1
        if d != last_day:
            starters[m.sender or "Unknown"] += 1
            last_day = d
        if m.deleted:
            s["deleted"] += 1
            continue
        kind = m.media.kind if m.media else m.omitted
        if kind == "image":
            s["photos"] += 1
        elif kind == "video":
            s["videos"] += 1
        elif kind in ("voice", "audio"):
            s["voice"] += 1
        if m.text:
            s["words"] += len(_WORD.findall(m.text))
            emojis.update(_EMOJI.findall(m.text))

    days = sorted(per_day)
    first, last = days[0], days[-1]
    busiest_day, busiest_count = max(per_day.items(), key=lambda kv: (kv[1], kv[0]))

    # One entry per calendar day from first to last, including quiet days, so charts show the gaps.
    daily = []
    d = first
    while d <= last:
        daily.append({"date": d.isoformat(), "count": per_day.get(d, 0)})
        d += timedelta(days=1)

    months = sorted(per_month)
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    senders = [
        {"name": name, "starts": starters[name], **vals}
        for name, vals in sorted(stats.items(), key=lambda kv: -kv[1]["messages"])
    ]
    return {
        "total_messages": len(chat),
        "total_days": (last - first).days + 1,
        "active_days": len(days),
        "avg_per_active_day": round(len(chat) / len(days), 1),
        "busiest_day": {"date": busiest_day.isoformat(), "count": busiest_count},
        "longest_streak": _streak(days),
        "by_hour": [per_hour.get(h, 0) for h in range(24)],
        "by_weekday": [{"label": w, "count": per_weekday.get(i, 0)} for i, w in enumerate(WEEKDAYS)],
        "by_month": [{"label": f"{names[m - 1]} {y}", "count": per_month[(y, m)]} for y, m in months],
        "daily": daily,
        "senders": senders,
        "emojis": [{"emoji": e, "count": c} for e, c in emojis.most_common(8)],
    }