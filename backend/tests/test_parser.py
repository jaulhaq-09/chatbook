from datetime import datetime

from app.core.parser import media_kind, merge_chats, parse_chat


def test_android_12h_day_first_detected_from_day_above_12():
    r = parse_chat(
        "12/03/2026, 9:41 am - Messages and calls are end-to-end encrypted.\n14/03/2026, 6:05 pm - Arjun: Leaving now"
    )
    assert r.order == "dmy"
    assert len(r.messages) == 2
    assert r.messages[0].system
    assert r.messages[1].ts == datetime(2026, 3, 14, 18, 5)


def test_android_24h_month_first_detected():
    r = parse_chat("3/25/24, 21:45 - Sam: hi\n3/26/24, 08:05 - Lee: yo")
    assert r.order == "mdy"
    assert r.messages[0].ts == datetime(2024, 3, 25, 21, 45)


def test_ios_bracket_format_with_seconds_narrow_nbsp_and_lrm():
    r = parse_chat("[12/03/2026, 9:41:05 PM] Priya: ‎hello\n[13/03/2026, 12:00:00 AM] Arjun: midnight")
    assert len(r.messages) == 2
    assert r.messages[0].ts == datetime(2026, 3, 12, 21, 41, 5)
    assert r.messages[0].text == "hello"
    assert r.messages[1].ts.hour == 0


def test_noon_is_12():
    r = parse_chat("13/03/2026, 12:10 pm - A: noon")
    assert r.messages[0].ts.hour == 12


def test_multiline_message_is_joined():
    r = parse_chat(
        "13/03/2026, 9:09 am - Arjun: Plan:\n- 6:00 leave\n- 9:30 breakfast\n13/03/2026, 9:11 am - Priya: ok"
    )
    assert len(r.messages) == 2
    assert r.messages[0].text == "Plan:\n- 6:00 leave\n- 9:30 breakfast"


def test_android_attachments_caption_voice_doc_sticker_video():
    r = parse_chat(
        "\n".join(
            [
                "13/03/2026, 9:30 am - Priya: IMG-20260312-WA0001.jpg (file attached)",
                "the view",
                "13/03/2026, 9:31 am - Priya: PTT-20260312-WA0003.opus (file attached)",
                "13/03/2026, 9:32 am - Priya: Trip plan.pdf (file attached)",
                "13/03/2026, 9:33 am - Priya: STK-20260312-WA0004.webp (file attached)",
                "13/03/2026, 9:34 am - Priya: VID-20260312-WA0005.mp4 (file attached)",
            ]
        )
    )
    assert [m.media.kind for m in r.messages] == ["image", "voice", "doc", "sticker", "video"]
    assert r.messages[0].text == "the view"
    assert r.messages[2].media.name == "Trip plan.pdf"


def test_ios_attached_marker_and_omitted_media():
    r = parse_chat(
        "\n".join(
            [
                "[13/03/2026, 9:30:00 AM] Priya: <attached: 00000012-PHOTO-2026-03-13-09-30-00.jpg>",
                "[13/03/2026, 9:31:00 AM] Priya: image omitted",
                "[13/03/2026, 9:32:00 AM] Priya: <Media omitted>",
            ]
        )
    )
    assert r.messages[0].media.name == "00000012-PHOTO-2026-03-13-09-30-00.jpg"
    assert r.messages[1].omitted == "image"
    assert r.messages[2].omitted == "image"


def test_deleted_messages_and_unicode_text():
    r = parse_chat("13/03/2026, 9:30 am - Priya: This message was deleted\n13/03/2026, 9:31 am - Arjun: सुबह की चाय ☕")
    assert r.messages[0].deleted
    assert r.messages[1].text.startswith("सुबह")


def test_ambiguous_dates_are_flagged_and_can_be_forced():
    raw = "03/04/2026, 9:30 am - A: x\n05/06/2026, 9:30 am - B: y"
    auto = parse_chat(raw)
    assert auto.ambiguous
    assert auto.messages[0].ts.month == 4  # day first by default
    forced = parse_chat(raw, order="mdy")
    assert forced.messages[0].ts.month == 3
    assert not forced.ambiguous


def test_year_first_dates_are_never_ambiguous():
    r = parse_chat("2026-03-04, 09:30 - A: x")
    assert not r.ambiguous
    assert r.messages[0].ts == datetime(2026, 3, 4, 9, 30)


def test_text_before_first_header_is_ignored():
    r = parse_chat("junk\n13/03/2026, 9:30 am - A: hello")
    assert len(r.messages) == 1


def test_invalid_dates_are_skipped_not_fatal():
    r = parse_chat("31/02/2026, 9:30 am - A: nope\n01/03/2026, 9:30 am - A: ok")
    assert [m.text for m in r.messages] == ["ok"]


def test_senders_are_counted_and_long_prefixes_are_system_lines():
    long_line = "13/03/2026, 9:30 am - " + "x" * 70 + ": not a name"
    r = parse_chat("13/03/2026, 9:29 am - A: hi\n13/03/2026, 9:29 am - A: again\n" + long_line)
    assert r.senders == {"A": 2}
    assert r.messages[2].system


def test_merge_removes_overlap_but_keeps_repeats_inside_one_export():
    a = parse_chat("01/03/2026, 9:00 am - A: ok\n01/03/2026, 9:00 am - A: ok\n02/03/2026, 9:00 am - B: hi")
    b = parse_chat("02/03/2026, 9:00 am - B: hi\n03/03/2026, 9:00 am - A: later")
    msgs, senders = merge_chats([a, b])
    assert [m.text for m in msgs] == ["ok", "ok", "hi", "later"]
    assert [m.id for m in msgs] == [0, 1, 2, 3]
    assert senders == {"A": 3, "B": 1}


def test_merge_orders_by_time_across_files():
    later = parse_chat("05/03/2026, 9:00 am - A: later")
    earlier = parse_chat("01/03/2026, 9:00 am - A: earlier")
    msgs, _ = merge_chats([later, earlier])
    assert [m.text for m in msgs] == ["earlier", "later"]


def test_media_kind_rules():
    assert media_kind("IMG-1.JPG") == "image"
    assert media_kind("STK-1.webp") == "sticker"
    assert media_kind("PTT-1.m4a") == "voice"
    assert media_kind("song.mp3") == "audio"
    assert media_kind("clip.MOV") == "video"
    assert media_kind("notes.pdf") == "doc"


def test_message_dict_round_trip():
    r = parse_chat("13/03/2026, 9:30 am - Priya: a.jpg (file attached)\ncap")
    from app.core.models import Message

    back = Message.from_dict(r.messages[0].to_dict())
    assert back == r.messages[0]
