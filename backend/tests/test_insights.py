from datetime import datetime

from app.core.models import MediaRef, Message
from app.services.insights import compute_insights


def msg(i, ts, sender, text="", **kw):
    return Message(id=i, ts=datetime.fromisoformat(ts), sender=sender, text=text, **kw)


def sample():
    return [
        msg(1, "2026-03-02T09:00", None, "Messages are end-to-end encrypted"),
        msg(2, "2026-03-02T09:05", "Priya", "good morning 😀😀"),
        msg(3, "2026-03-02T09:06", "Arjun", "hi there"),
        msg(4, "2026-03-03T21:00", "Arjun", "", media=MediaRef("a.jpg", "image")),
        msg(5, "2026-03-04T21:10", "Priya", "", media=MediaRef("v.mp4", "video")),
        msg(6, "2026-03-04T21:11", "Priya", "", deleted=True),
        msg(7, "2026-03-07T08:00", "Priya", "later 😀"),
        msg(8, "2026-04-01T00:30", "Arjun", "", omitted="voice"),
    ]


def test_totals_ignore_system_lines_and_count_quiet_days():
    r = compute_insights(sample())
    assert r["total_messages"] == 7
    assert r["active_days"] == 5
    assert r["total_days"] == 31  # 2 March to 1 April
    assert len(r["daily"]) == 31 and r["daily"][3]["count"] == 0  # 5 March is quiet
    assert r["busiest_day"] == {"date": "2026-03-04", "count": 2}  # ties go to the later day


def test_streak_hours_weekdays_months():
    r = compute_insights(sample())
    assert r["longest_streak"] == 3  # 2, 3, 4 March
    assert r["by_hour"][21] == 3 and r["by_hour"][9] == 2 and sum(r["by_hour"]) == 7
    assert sum(w["count"] for w in r["by_weekday"]) == 7
    assert [m["label"] for m in r["by_month"]] == ["Mar 2026", "Apr 2026"]


def test_per_sender_numbers():
    r = compute_insights(sample())
    by = {s["name"]: s for s in r["senders"]}
    assert r["senders"][0]["name"] == "Priya"  # most messages first
    assert by["Priya"]["messages"] == 4 and by["Priya"]["videos"] == 1 and by["Priya"]["deleted"] == 1
    assert by["Arjun"]["photos"] == 1 and by["Arjun"]["voice"] == 1
    assert by["Priya"]["starts"] == 3 and by["Arjun"]["starts"] == 2  # 5 active days
    assert by["Priya"]["words"] == 3  # "good morning" and "later"; emoji are not words
    assert r["emojis"][0] == {"emoji": "😀", "count": 3}


def test_empty_chat_is_safe():
    r = compute_insights([msg(1, "2026-03-02T09:00", None, "system only")])
    assert r["total_messages"] == 0 and r["daily"] == [] and r["busiest_day"] is None