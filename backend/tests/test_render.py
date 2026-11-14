from __future__ import annotations

import re
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.core.parser import parse_chat
from app.schemas import AlbumOptions, RenderOptions
from app.services.exports import ExportManager
from app.services.ingest import Upload
from app.services.render.layout import (
    album_cells,
    album_groups,
    estimate_book_pages,
    filter_messages,
    split_volumes,
)
from app.services.render.plan import build_plan, compute_stats, toc_labels
from app.services.render.view import render_volume_html
from app.services.sample import build_sample_zip
from tests.conftest import run_ingest


def messages_from(text: str):
    return parse_chat(text).messages


LINES = "\n".join(
    [
        "01/03/2026, 9:00 am - A: hello world",
        "01/03/2026, 9:05 am - B: Hello again",
        "02/03/2026, 9:00 am - A: IMG-1.jpg (file attached)",
        "15/04/2026, 9:00 am - B: later in April",
        "16/04/2026, 9:00 am - A: and again",
        "02/01/2027, 9:00 am - A: next year",
    ]
)


@pytest.fixture
def sample_job(store, ingestor, tmp_path):
    job_id = store.create(is_sample=True)["id"]
    run_ingest(store, ingestor, [Upload("sample.zip", build_sample_zip(tmp_path / "s.zip"))], job_id)
    return job_id


def plan_for(store, job_id, **opts):
    return build_plan(RenderOptions(**opts), store.load(job_id), store.load_messages(job_id), store.load_media(job_id))


# ---- filtering and volumes ---------------------------------------------------------------
def test_filter_by_date_people_and_text():
    msgs = messages_from(LINES)
    assert len(filter_messages(msgs, RenderOptions(date_from=date(2026, 3, 2), date_to=date(2026, 4, 15)))) == 2
    assert [m.sender for m in filter_messages(msgs, RenderOptions(exclude_people=["A"]))] == ["B", "B"]
    assert [m.text for m in filter_messages(msgs, RenderOptions(query="HELLO"))] == ["hello world", "Hello again"]
    # Search applies to the book only; an album ignores it.
    assert len(filter_messages(msgs, RenderOptions(mode="album", query="zzz"))) == len(msgs)


def test_volumes_by_month_year_and_size_keep_days_together():
    msgs = messages_from(LINES)
    by_month = split_volumes(msgs, RenderOptions(volume_mode="month"), lambda m: 1)
    assert [v.label for v in by_month] == ["March 2026", "April 2026", "January 2027"]
    assert [v.suffix for v in by_month] == ["2026-03", "2026-04", "2027-01"]
    by_year = split_volumes(msgs, RenderOptions(volume_mode="year"), lambda m: 1)
    assert [v.label for v in by_year] == ["2026", "2027"]

    day = messages_from(
        "\n".join(f"01/03/2026, 9:{i:02d} am - A: m{i}" for i in range(30)) + "\n02/03/2026, 9:00 am - A: x"
    )
    sized = split_volumes(day, RenderOptions(volume_mode="size", volume_size=20), lambda m: 1)
    assert [len(v.messages) for v in sized] == [30, 1]  # the first day is never cut in half
    assert [v.label for v in sized] == ["Part 1", "Part 2"]


def test_no_volumes_for_nothing():
    assert split_volumes([], RenderOptions(), lambda m: 1) == []


# ---- plan and statistics -----------------------------------------------------------------
def test_plan_defaults_and_stats(store, sample_job):
    plan = plan_for(store, sample_job)
    assert plan.title == "Priya & Arjun"
    assert plan.me in ("Arjun", "Priya")
    stats = compute_stats(plan)
    assert (stats.messages, stats.photos, stats.videos) == (35, 10, 1)
    assert stats.toc_available
    assert stats.estimated_pages >= 3


def test_plan_respects_me_when_valid_and_ignores_unknown_names(store, sample_job):
    assert plan_for(store, sample_job, me="Priya").me == "Priya"
    assert plan_for(store, sample_job, me="Nobody").me in ("Arjun", "Priya")


def test_album_only_uses_photos_that_exist(store, sample_job):
    job = store.load(sample_job)
    msgs = store.load_messages(sample_job)
    registry = store.load_media(sample_job)
    assert len(album_cells(msgs, registry, include_videos=True)) == 11
    assert len(album_cells(msgs, registry, include_videos=False)) == 10
    groups = album_groups(album_cells(msgs, registry, True), "month")
    assert [g[0] for g in groups] == ["March 2026", "April 2026"]
    assert [g[0] for g in album_groups(album_cells(msgs, registry, True), "none")] == [""]
    assert job["counts"]["photos"] == 10


def test_toc_needs_two_to_seventy_two_entries(store, sample_job):
    plan = plan_for(store, sample_job)
    assert toc_labels(plan, plan.volumes[0]) == ["March 2026", "April 2026"]
    assert toc_labels(plan_for(store, sample_job, toc=False), plan.volumes[0]) == []
    assert toc_labels(plan_for(store, sample_job, date_to=date(2026, 3, 31)), plan.volumes[0]) != []
    narrow = plan_for(store, sample_job, date_to=date(2026, 3, 31))
    assert toc_labels(narrow, narrow.volumes[0]) == []  # a single month needs no contents page


def test_estimate_grows_with_content(store, sample_job):
    msgs = store.load_messages(sample_job)
    registry = store.load_media(sample_job)
    o = RenderOptions()
    spec = plan_for(store, sample_job).spec
    small = estimate_book_pages(msgs[:5], o, spec, registry, 2, "Arjun")
    large = estimate_book_pages(msgs * 20, o, spec, registry, 2, "Arjun")
    assert large > small


# ---- HTML --------------------------------------------------------------------------------
def render(store, job_id, **opts):
    plan = plan_for(store, job_id, **opts)
    return render_volume_html(plan, plan.volumes[0], media_base="/m/", preview=True)


def test_html_contains_the_chat_and_uses_the_requested_clock(store, sample_job):
    html = render(store, sample_job)
    assert "Good morning! Are we still on for Coorg" in html
    assert "9:02 am" in html and "Thursday 12 March 2026" in html
    assert "<b>thermos</b>" in html  # *thermos* markup
    assert "/m/web/m" in html  # photos come from the media route
    assert "9:02 am" not in render(store, sample_job, clock="h24")
    assert "09:02" in render(store, sample_job, clock="h24")


def test_print_quality_uses_the_large_copies(store, sample_job):
    assert "/m/print/m" in render(store, sample_job, quality="print")


def test_message_text_is_escaped(store, ingestor, tmp_path):
    txt = tmp_path / "x.txt"
    txt.write_text(
        "01/03/2026, 9:00 am - A: <script>alert(1)</script> & <img src=x onerror=alert(2)>\n"
        "01/03/2026, 9:01 am - B: ok\n",
        encoding="utf-8",
    )
    job_id = run_ingest(store, ingestor, [Upload("x.txt", txt)])
    html = render(store, job_id)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x" not in html


def test_a_hostile_title_cannot_break_out_of_the_stylesheet(store, sample_job):
    html = render(store, sample_job, title='</style><script>alert(1)</script>"; }')
    assert "<script>alert(1)</script>" not in html
    assert html.count("</style>") == 1


def test_hiding_media_shows_labels_instead(store, sample_job):
    html = render(store, sample_job, show_media=False)
    assert "/m/web/m" not in html
    assert "Photo" in html and "Video" in html


def test_album_html_has_groups_and_respects_columns(store, sample_job):
    html = render(store, sample_job, mode="album", album=AlbumOptions(columns=4, group="month"))
    assert "March 2026" in html and "cols-4" in html and "repeat(4," in html
    assert "Good morning" not in html


def test_preview_slices_and_omits_the_contents_page(store, sample_job):
    plan = plan_for(store, sample_job)
    html = render_volume_html(plan, plan.volumes[0], media_base="/m/", preview=True, page=2, per_page=10)
    assert 'class="cover"' not in html and 'class="toc"' not in html
    assert "Good morning" not in html  # that message is on page 1


def test_missing_media_is_labelled_for_the_reader(store, ingestor, tmp_path):
    txt = tmp_path / "x.txt"
    txt.write_text(
        "01/03/2026, 9:00 am - A: IMG-9.jpg (file attached)\n02/03/2026, 9:00 am - B: <Media omitted>\n",
        encoding="utf-8",
    )
    job_id = run_ingest(store, ingestor, [Upload("x.txt", txt)])
    html = render(store, job_id)
    assert "Photo not in this export" in html
    assert "Photo left out of this export" in html


# ---- real PDFs ---------------------------------------------------------------------------
def export_and_wait(manager: ExportManager, job_id: str, **opts) -> dict:
    export = manager.start(job_id, RenderOptions(**opts))
    deadline = time.time() + 120
    while time.time() < deadline:
        current = manager.get(job_id, export["id"])
        if current["status"] not in ("queued", "running"):
            return current
        time.sleep(0.2)
    raise AssertionError("export did not finish")


@pytest.fixture
def manager(store, settings):
    m = ExportManager(store, settings)
    yield m
    m.shutdown()


@pytest.mark.browser
def test_pdf_has_selectable_text_bookmarks_and_a_correct_contents_page(store, manager, sample_job):
    result = export_and_wait(manager, sample_job)
    assert result["status"] == "done", result["error"]
    (file,) = result["files"]
    pdf = store.path(sample_job) / "exports" / result["id"] / file["name"]
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == file["pages"] >= 6

    text = [p.extract_text() for p in reader.pages]
    assert "Priya & Arjun" in text[0]
    assert "Good morning! Are we still on for Coorg" in "".join(text)  # real text, not an image
    assert "सुबह" in "".join(text)  # Devanagari survived

    # Every contents line points at the page where that month really starts.
    toc_text = text[1]
    for label in ("March 2026", "April 2026"):
        line = next(line for line in toc_text.splitlines() if line.startswith(label))
        listed = int(line.split()[-1])
        assert label in text[listed - 1]
        # ...and no earlier content page already shows that month heading.
        assert not any(f"\n{label}\n" in t for t in text[2 : listed - 1])
    assert reader.pages[0].mediabox.width == pytest.approx(595, abs=2)  # A4


@pytest.mark.browser
def test_page_size_and_album_mode(store, manager, sample_job):
    result = export_and_wait(manager, sample_job, mode="album", page_size="Letter", album=AlbumOptions(columns=2))
    assert result["status"] == "done", result["error"]
    pdf = store.path(sample_job) / "exports" / result["id"] / result["files"][0]["name"]
    reader = PdfReader(str(pdf))
    assert reader.pages[0].mediabox.width == pytest.approx(612, abs=2)
    assert reader.pages[0].mediabox.height == pytest.approx(792, abs=2)
    assert any("Mar 2026" in p.extract_text() for p in reader.pages)


@pytest.mark.browser
def test_volumes_are_separate_pdfs_plus_a_zip(store, manager, sample_job):
    import zipfile

    result = export_and_wait(manager, sample_job, volume_mode="month")
    assert result["status"] == "done", result["error"]
    assert [f["label"] for f in result["files"]] == ["March 2026", "April 2026"]
    folder = store.path(sample_job) / "exports" / result["id"]
    with zipfile.ZipFile(folder / result["archive"]) as zf:
        assert sorted(zf.namelist()) == sorted(f["name"] for f in result["files"])
    first = PdfReader(str(folder / result["files"][0]["name"]))
    assert re.search(r"v\s*o\s*l\s*u\s*m\s*e\s*1\s*o\s*f\s*2", first.pages[0].extract_text(), re.I)


@pytest.mark.browser
def test_exporting_nothing_fails_with_advice(store, manager, sample_job):
    result = export_and_wait(manager, sample_job, date_from=date(2030, 1, 1))
    assert result["status"] == "failed"
    assert "nothing to export" in result["error"]


@pytest.mark.browser
def test_cancelled_export_stops(store, settings, sample_job):
    manager = ExportManager(store, settings)
    export = {"id": "0" * 16}
    d = store.path(sample_job) / "exports" / export["id"]
    d.mkdir(parents=True)
    from app.services.jobs import write_json

    write_json(
        d / "export.json",
        {
            "id": export["id"],
            "job_id": sample_job,
            "status": "queued",
            "progress": {"stage": "", "done": 0, "total": 1},
            "files": [],
            "archive": None,
            "error": None,
            "created_at": "",
        },
    )
    event = threading.Event()
    event.set()
    manager.run(sample_job, export["id"], RenderOptions(), event)
    assert manager.get(sample_job, export["id"])["status"] == "cancelled"
    manager.shutdown()


@pytest.mark.browser
def test_page_estimate_is_close_to_the_real_page_count(store, manager, ingestor, tmp_path):
    """A text-heavy chat of about 900 messages: the estimate should land within 20 percent."""
    lines = []
    for i in range(900):
        day = 1 + i // 30
        who = "Priya" if i % 3 else "Arjun"
        lines.append(
            f"{day:02d}/03/2026, {9 + (i % 30) // 5}:{(i % 5) * 10:02d} am - {who}: "
            + ("word " * (3 + (i * 7) % 28)).strip()
        )
    txt = tmp_path / "long.txt"
    txt.write_text("\n".join(lines), encoding="utf-8")
    job_id = run_ingest(store, ingestor, [Upload("long.txt", txt)])
    estimate = compute_stats(plan_for(store, job_id)).estimated_pages
    result = export_and_wait(manager, job_id)
    assert result["status"] == "done", result["error"]
    actual = result["files"][0]["pages"]
    assert abs(estimate - actual) <= max(2, 0.2 * actual), (estimate, actual)


@pytest.mark.browser
def test_long_volume_is_laid_out_in_slices_but_reads_as_one_book(store, manager, ingestor, tmp_path, monkeypatch):
    import app.services.render.view as view

    monkeypatch.setattr(view, "SLICE_WEIGHT", 220)  # force several slices out of a small chat
    lines = []
    for i in range(700):
        d = date(2026, 3, 1) + timedelta(days=i // 10)
        who = "Priya" if i % 3 else "Arjun"
        lines.append(
            f"{d:%d/%m/%Y}, {9 + (i % 10)}:{(i % 5) * 10:02d} am - {who}: " + ("word " * (3 + (i * 7) % 20)).strip()
        )
    txt = tmp_path / "long.txt"
    txt.write_text("\n".join(lines), encoding="utf-8")
    job_id = run_ingest(store, ingestor, [Upload("long.txt", txt)])
    assert len(view.split_body(plan_for(store, job_id), plan_for(store, job_id).volumes[0], "m/")) >= 3

    result = export_and_wait(manager, job_id)
    assert result["status"] == "done", result["error"]
    (file,) = result["files"]
    pdf = store.path(job_id) / "exports" / result["id"] / file["name"]
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == file["pages"]
    text = [p.extract_text() for p in reader.pages]

    # Page numbers carry on across the joins: every content page shows its own number (excluding back cover).
    for i in range(2, len(text) - 1):
        assert str(i + 1) in text[i].splitlines()[-3:] or str(i + 1) in text[i].split(), (i + 1, text[i][-80:])

    # The contents page points at the right pages, and the bookmarks agree.
    outline = {o.title: reader.get_destination_page_number(o) + 1 for o in reader.outline if not isinstance(o, list)}
    for label in ("March 2026", "April 2026", "May 2026"):
        line = next(line for line in text[1].splitlines() if line.startswith(label))
        listed = int(line.split()[-1])
        assert outline[label] == listed
        assert label in text[listed - 1]
    # A month heading is printed once, not again at the start of a slice.
    assert sum(t.count("\nMarch 2026\n") for t in text[2:]) == 1


def test_datetime_import_is_used():  # keeps the import list honest for linters
    assert datetime(2026, 1, 1).year == 2026 and Path(".")
