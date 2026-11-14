from __future__ import annotations

import json

from app.core import meta


def test_fix_text_undoes_mojibake():
    # Meta exports often encode UTF-8 bytes as Latin-1 chars
    mojibake = "CafÃ©"
    assert meta.fix_text(mojibake) == "Café"
    assert meta.fix_text("Plain text") == "Plain text"
    assert meta.fix_text(123) == ""


def test_find_threads_groups_and_sorts():
    entries = [
        ("messages/inbox/small/message_1.json", 100),
        ("messages/inbox/big/message_1.json", 500),
        ("messages/inbox/big/message_2.json", 300),
        ("__MACOSX/messages/inbox/big/message_1.json", 500),
        ("messages/inbox/other/photo.jpg", 1000),
    ]
    threads = meta.find_threads(entries)
    assert len(threads) == 2
    assert threads[0].folder == "messages/inbox/big"
    assert threads[0].size == 800
    assert len(threads[0].files) == 2
    assert threads[1].folder == "messages/inbox/small"


def test_convert_creates_valid_timeline_and_attachments():
    data = {
        "title": "Friends Chat",
        "messages": [
            {
                "sender_name": "Arjun",
                "timestamp_ms": 1700000060000,
                "content": "Nice picture!",
            },
            {
                "sender_name": "Priya",
                "timestamp_ms": 1700000000000,
                "content": "Look at this",
                "photos": [{"uri": "photos/view.jpg"}],
            },
            {
                "sender_name": "Priya",
                "timestamp_ms": 1700000070000,
                "is_unsent": True,
            },
        ],
    }
    thread = meta.MetaThread("messages/inbox/chat", ["messages/inbox/chat/message_1.json"], 500)
    members = {"view.jpg": "messages/inbox/chat/photos/view.jpg"}

    chat = meta.convert(lambda p: json.dumps(data).encode("utf-8"), thread, members)
    assert chat.title == "Friends Chat"
    assert chat.messages == 3
    assert "view.jpg" in chat.media
    lines = [ln for ln in chat.text.strip().split("\n") if ln.strip()]
    assert len(lines) == 4  # photo header + caption line + Arjun msg + Priya deleted msg
    assert "This message was deleted" in lines[-1]
