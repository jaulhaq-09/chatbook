from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.services.ingest import IngestError, Upload
from app.services.jobs import JobNotFound
from app.services.sample import build_sample_zip
from tests.conftest import CHAT, jpeg_bytes, make_zip, run_ingest


def test_sample_export_is_fully_processed(store, ingestor, tmp_path):
    zip_path = build_sample_zip(tmp_path / "sample.zip")
    job_id = store.create(is_sample=True)["id"]
    run_ingest(store, ingestor, [Upload("sample.zip", zip_path)], job_id)

    job = store.load(job_id)
    assert job["status"] == "ready"
    assert job["counts"]["photos"] == 10
    assert job["counts"]["videos"] == 1
    assert job["counts"]["missing_media"] == 0
    assert job["suggested_title"] == "Priya & Arjun"
    assert [s["name"] for s in job["senders"]] == ["Arjun", "Priya"] or job["senders"][0]["count"] >= job["senders"][1][
        "count"
    ]

    registry = store.load_media(job_id)
    img = registry["img-20260312-wa0001.jpg"]
    assert img["state"] == "ok" and img["w"] <= 1000 and img["h"] <= 1000
    jd = store.path(job_id)
    assert (jd / "media" / "web" / img["file"]).is_file()
    assert (jd / "media" / "print" / img["file"]).is_file()
    assert registry["trip-plan.pdf"]["state"] == "meta"
    assert registry["ptt-20260312-wa0003.opus"]["state"] == "meta"
    # Portrait photo keeps its orientation and proportions.
    portrait = registry["img-20260315-wa0008.jpg"]
    assert portrait["h"] > portrait["w"]


def test_video_gets_a_poster_frame_when_ffmpeg_exists(store, ingestor, tmp_path):
    from app.services.media import ffmpeg_available

    zip_path = build_sample_zip(tmp_path / "sample.zip")
    job_id = run_ingest(store, ingestor, [Upload("sample.zip", zip_path)])
    video = store.load_media(job_id)["vid-20260314-wa0004.mp4"]
    assert video["state"] == "ok"
    if ffmpeg_available():
        assert video["poster"] is True and video["file"]
        assert video["dur"] == pytest.approx(2, abs=0.5)
    else:
        assert video["poster"] is False


def test_media_missing_from_the_zip_is_reported(store, ingestor, tmp_path):
    z = make_zip(tmp_path / "e.zip", {"_chat.txt": CHAT, "IMG-1.jpg": jpeg_bytes()})
    job_id = run_ingest(store, ingestor, [Upload("e.zip", z)])
    job = store.load(job_id)
    assert job["counts"]["photos"] == 1
    assert job["counts"]["missing_media"] == 1  # IMG-2.jpg is not in the zip
    assert store.load_media(job_id)["img-2.jpg"]["state"] == "missing"


def test_damaged_image_is_marked_bad_but_does_not_stop_the_job(store, ingestor, tmp_path):
    z = make_zip(tmp_path / "e.zip", {"_chat.txt": CHAT, "IMG-1.jpg": b"not an image", "IMG-2.jpg": jpeg_bytes()})
    job_id = run_ingest(store, ingestor, [Upload("e.zip", z)])
    registry = store.load_media(job_id)
    assert registry["img-1.jpg"]["state"] == "bad"
    assert registry["img-2.jpg"]["state"] == "ok"
    assert store.load(job_id)["status"] == "ready"


def test_member_paths_never_escape_the_job_folder(store, ingestor, tmp_path):
    z = make_zip(
        tmp_path / "e.zip",
        {"_chat.txt": CHAT, "../../evil/IMG-1.jpg": jpeg_bytes(), "..\\..\\IMG-2.jpg": jpeg_bytes()},
    )
    job_id = run_ingest(store, ingestor, [Upload("e.zip", z)])
    registry = store.load_media(job_id)
    assert registry["img-1.jpg"]["state"] == "ok" and registry["img-2.jpg"]["state"] == "ok"
    assert not (tmp_path / "evil").exists()
    assert not list(tmp_path.glob("**/evil"))


def test_zip_without_chat_text_fails_with_a_clear_message(store, ingestor, tmp_path):
    z = make_zip(tmp_path / "e.zip", {"IMG-1.jpg": jpeg_bytes()})
    job_id = store.create()["id"]
    with pytest.raises(IngestError, match="no chat text"):
        ingestor.ingest(job_id, [Upload("e.zip", z)])


def test_run_records_failure_on_the_job_and_removes_the_upload(store, ingestor, tmp_path):
    bad = tmp_path / "broken.zip"
    bad.write_bytes(b"PK\x03\x04 garbage")
    job_id = store.create()["id"]
    ingestor._run(job_id, [Upload("broken.zip", bad)])
    job = store.load(job_id)
    assert job["status"] == "failed"
    assert "broken.zip" in job["error"]
    assert not bad.exists()


def test_unzipped_size_limit_is_enforced(store, ingestor, settings, tmp_path):
    settings.max_unzipped_mb = 1
    z = make_zip(tmp_path / "e.zip", {"_chat.txt": CHAT, "big.bin": b"0" * (2 * 1024 * 1024)})
    job_id = store.create()["id"]
    with pytest.raises(IngestError, match="limit"):
        ingestor.ingest(job_id, [Upload("e.zip", z)])


def test_plain_text_export_works_without_media(store, ingestor, tmp_path):
    txt = tmp_path / "WhatsApp Chat with Maya.txt"
    txt.write_text(CHAT, encoding="utf-8")
    job_id = run_ingest(store, ingestor, [Upload(txt.name, txt)])
    job = store.load(job_id)
    assert job["status"] == "ready"
    assert job["suggested_title"] == "Maya"
    assert job["counts"]["missing_media"] == 2


def test_unsupported_file_type_is_rejected(store, ingestor, tmp_path):
    f = tmp_path / "photo.png"
    f.write_bytes(jpeg_bytes())
    job_id = store.create()["id"]
    with pytest.raises(IngestError, match="not a chat export"):
        ingestor.ingest(job_id, [Upload("photo.png", f)])


def test_adding_a_second_export_merges_and_removes_overlap(store, ingestor, tmp_path):
    first = make_zip(tmp_path / "a.zip", {"_chat.txt": CHAT, "IMG-1.jpg": jpeg_bytes(), "IMG-2.jpg": jpeg_bytes()})
    job_id = run_ingest(store, ingestor, [Upload("a.zip", first)])
    second_chat = CHAT.split("13/03")[0] + "14/03/2026, 8:00 am - Arjun: new day\n"
    second = make_zip(tmp_path / "b.zip", {"_chat.txt": second_chat})
    run_ingest(store, ingestor, [Upload("b.zip", second)], job_id)

    messages = store.load_messages(job_id)
    assert [m.text for m in messages if m.sender][-1] == "new day"
    assert sum(1 for m in messages if m.media) == 2  # the overlapping photo lines were not repeated
    job = store.load(job_id)
    assert len(job["sources"]) == 2
    assert job["counts"]["photos"] == 2  # still available from the first export


def test_date_order_can_be_changed_afterwards(store, ingestor, tmp_path):
    txt = tmp_path / "c.txt"
    txt.write_text("03/04/2026, 9:30 am - A: x\n05/06/2026, 9:30 am - B: y\n", encoding="utf-8")
    job_id = run_ingest(store, ingestor, [Upload("c.txt", txt)])
    assert store.load(job_id)["order_ambiguous"] is True
    assert store.load_messages(job_id)[0].ts.month == 4

    store.update(job_id, date_order="mdy")
    ingestor.remerge(job_id)
    assert store.load_messages(job_id)[0].ts.month == 3
    assert store.load(job_id)["order_ambiguous"] is False


def test_job_ids_that_are_not_hex_are_rejected(store):
    for bad in ("../etc", "x" * 32, "", "a" * 31):
        with pytest.raises(JobNotFound):
            store.path(bad)


def test_expired_jobs_are_deleted(store, tmp_path):
    old = store.create()["id"]
    fresh = store.create()["id"]
    store.mutate(old, lambda j: None)  # bump, then back-date by rewriting the file
    p = store.path(old) / "job.json"
    import json

    data = json.loads(p.read_text())
    data["updated_at"] = "2020-01-01T00:00:00+00:00"
    p.write_text(json.dumps(data))
    assert store.cleanup_expired() == 1
    with pytest.raises(JobNotFound):
        store.path(old)
    assert store.path(fresh)


def test_messages_are_cached_and_refreshed_when_rewritten(store, ingestor, tmp_path):
    txt = tmp_path / "c.txt"
    txt.write_text("13/03/2026, 9:30 am - A: one\n", encoding="utf-8")
    job_id = run_ingest(store, ingestor, [Upload("c.txt", txt)])
    first = store.load_messages(job_id)
    assert store.load_messages(job_id) is first
    store.save_messages(job_id, first[:0])
    assert store.load_messages(job_id) == []


def test_zipfile_module_sanity_for_test_helpers(tmp_path: Path):
    z = make_zip(tmp_path / "x.zip", {"a.txt": "hi"})
    assert zipfile.is_zipfile(z)
