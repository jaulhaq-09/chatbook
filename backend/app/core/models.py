"""Plain data types shared by the parser, the job store and the renderer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# What an attachment is, as far as printing is concerned.
MEDIA_KINDS = ("image", "video", "voice", "audio", "doc", "sticker")


@dataclass(slots=True)
class MediaRef:
    """An attachment named in the chat text (the file itself may or may not be present)."""

    name: str
    kind: str


@dataclass(slots=True)
class Message:
    id: int
    ts: datetime  # local time exactly as written in the export; WhatsApp stores no time zone
    sender: str | None  # None for system lines such as "Messages are end-to-end encrypted"
    text: str = ""
    media: MediaRef | None = None
    omitted: str | None = None  # kind of a "<Media omitted>" placeholder
    deleted: bool = False

    @property
    def system(self) -> bool:
        return self.sender is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts.isoformat(),
            "sender": self.sender,
            "text": self.text,
            "media": {"name": self.media.name, "kind": self.media.kind} if self.media else None,
            "omitted": self.omitted,
            "deleted": self.deleted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Message:
        media = d.get("media")
        return cls(
            id=d["id"],
            ts=datetime.fromisoformat(d["ts"]),
            sender=d.get("sender"),
            text=d.get("text", ""),
            media=MediaRef(media["name"], media["kind"]) if media else None,
            omitted=d.get("omitted"),
            deleted=bool(d.get("deleted", False)),
        )


@dataclass(slots=True)
class ParsedChat:
    messages: list[Message]
    senders: dict[str, int]
    order: str  # "dmy" or "mdy": how day and month were read
    ambiguous: bool  # True when every date reads the same both ways, so the order was a guess
