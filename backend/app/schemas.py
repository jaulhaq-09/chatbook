"""Request and response shapes of the REST API."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

DateOrder = Literal["auto", "dmy", "mdy"]
FontKey = Literal["sans", "humanist", "friendly", "wide", "serif", "book", "mono", "hand", "script"]
CoverStyle = Literal["classic", "centered", "bold", "minimal", "frame"]
Motif = Literal["none", "bubbles", "dots", "waves", "rings", "hearts", "sparkles"]
LeftFooter = Literal["people", "text", "none"]
RightFooter = Literal["counts", "dates", "text", "none"]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]


class AlbumOptions(BaseModel):
    group: Literal["month", "day", "sender", "none"] = "month"
    columns: int = Field(3, ge=1, le=4)
    fit: Literal["fill", "fit"] = "fill"
    paper: Literal["white", "warm", "black"] = "white"
    captions: bool = True
    include_videos: bool = True


class BackgroundOptions(BaseModel):
    """A picture printed behind the pages. The picture itself is uploaded to the job."""

    enabled: bool = True
    fit: Literal["cover", "contain", "tile"] = "cover"
    opacity: float = Field(0.3, ge=0.05, le=1.0)  # how strongly the picture shows; 1 is full strength
    scope: Literal["all", "inside", "cover"] = "all"


class DesignOptions(BaseModel):
    """How the cover and the back page look."""

    cover_style: CoverStyle = "classic"
    color1: HexColor = "#0a7556"
    color2: HexColor = "#d9a441"
    heading_font: FontKey = "serif"
    motif: Motif = "bubbles"  # a small drawing in the empty space


class CoverText(BaseModel):
    """Words on the cover. A blank field uses the automatic text."""

    kicker: str = Field("", max_length=80)  # small line above the title
    subtitle: str = Field("", max_length=120)  # automatic: the dates
    tagline: str = Field("", max_length=200)
    left_mode: LeftFooter = "people"  # what the bottom-left corner shows
    right_mode: RightFooter = "counts"  # what the bottom-right corner shows
    footer_left: str = Field("", max_length=120)  # used when the mode is "text"
    footer_right: str = Field("", max_length=120)


class BackOptions(BaseModel):
    """The last page of the book."""

    enabled: bool = True
    heading: str = Field("The end", max_length=80)
    message: str = Field("", max_length=400)  # automatic: the dates
    signature: str = Field("", max_length=120)
    left_mode: LeftFooter = "people"
    right_mode: RightFooter = "dates"
    footer_left: str = Field("", max_length=120)
    footer_right: str = Field("", max_length=120)


class RenderOptions(BaseModel):
    """Everything that decides how a chat is laid out. Used by the preview and by the export."""

    mode: Literal["book", "album"] = "book"
    title: str = Field("", max_length=120)
    me: str | None = Field(None, max_length=200)  # whose messages sit on the right
    page_size: Literal["A4", "Letter", "A5", "Square"] = "A4"
    theme: Literal["classic", "clean", "ink"] = "classic"
    text_size: Literal["s", "m", "l"] = "m"
    clock: Literal["h12", "h24"] = "h12"
    show_media: bool = True
    cover: bool = True
    toc: bool = True
    page_numbers: bool = True
    date_from: date | None = None
    date_to: date | None = None
    exclude_people: list[str] = Field(default_factory=list, max_length=500)
    query: str = Field("", max_length=200)
    album: AlbumOptions = Field(default_factory=AlbumOptions)
    background: BackgroundOptions = Field(default_factory=BackgroundOptions)
    chat_font: FontKey = "sans"
    design: DesignOptions = Field(default_factory=DesignOptions)
    cover_text: CoverText = Field(default_factory=CoverText)
    back: BackOptions = Field(default_factory=BackOptions)
    header_left: str = Field("", max_length=120)  # running header on every page; automatic: the title
    header_right: str = Field("", max_length=120)  # automatic: the dates
    quality: Literal["standard", "print"] = "standard"
    volume_mode: Literal["none", "month", "year", "size"] = "none"
    volume_size: int = Field(1000, ge=20, le=20000)  # messages (book) or photos (album) per volume


class Progress(BaseModel):
    stage: str
    done: int
    total: int


class SourceOut(BaseModel):
    id: int
    name: str
    messages: int


class SenderOut(BaseModel):
    name: str
    count: int


class CountsOut(BaseModel):
    messages: int
    photos: int
    videos: int
    missing_media: int
    omitted_media: int


class DateRangeOut(BaseModel):
    start: str
    end: str


class BackgroundOut(BaseModel):
    name: str
    width: int
    height: int
    version: str


class JobOut(BaseModel):
    id: str
    status: Literal["processing", "ready", "failed"]
    error: str | None
    warnings: list[str]
    progress: Progress
    created_at: str
    expires_at: str
    date_order: DateOrder
    order_ambiguous: bool
    is_sample: bool
    sources: list[SourceOut]
    senders: list[SenderOut]
    counts: CountsOut
    date_range: DateRangeOut | None
    suggested_title: str
    video_posters: bool  # False when ffmpeg is missing, so videos print as a plain tile
    background: BackgroundOut | None = None


class JobPatch(BaseModel):
    date_order: DateOrder


class PreviewRequest(BaseModel):
    options: RenderOptions
    page: int = Field(1, ge=1)
    volume: int = Field(1, ge=1)


class VolumeStat(BaseModel):
    index: int
    label: str
    messages: int
    photos: int
    videos: int
    start: str
    end: str
    estimated_pages: int


class Stats(BaseModel):
    messages: int
    photos: int
    videos: int
    estimated_pages: int
    toc_available: bool
    volumes: list[VolumeStat]


class SectionInfo(BaseModel):
    """One section of the page preview: which days it covers and what media it holds."""

    start: str
    end: str
    photos: int
    videos: int
    pages: int = 1  # rough number of printed pages in this section


class PreviewOut(BaseModel):
    html: str
    page: int
    page_count: int
    volume: int
    stats: Stats
    sections: list[SectionInfo] = Field(default_factory=list)


class ExportFile(BaseModel):
    name: str
    size: int
    pages: int
    volume: int
    label: str


class ExportOut(BaseModel):
    id: str
    job_id: str
    status: Literal["queued", "running", "done", "failed", "cancelled"]
    progress: Progress
    files: list[ExportFile]
    archive: str | None
    error: str | None
    created_at: str


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    ffmpeg: bool
    chromium: bool


class CountItem(BaseModel):
    label: str
    count: int


class DayCount(BaseModel):
    date: str
    count: int


class SenderInsight(BaseModel):
    name: str
    messages: int
    words: int
    photos: int
    videos: int
    voice: int
    deleted: int
    starts: int  # days on which this person sent the first message


class EmojiCount(BaseModel):
    emoji: str
    count: int


class InsightsOut(BaseModel):
    total_messages: int
    total_days: int
    active_days: int
    avg_per_active_day: float
    busiest_day: DayCount | None
    longest_streak: int
    by_hour: list[int]
    by_weekday: list[CountItem]
    by_month: list[CountItem]
    daily: list[DayCount]
    senders: list[SenderInsight]
    emojis: list[EmojiCount]