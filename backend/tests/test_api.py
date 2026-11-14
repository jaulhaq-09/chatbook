from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.sample import build_sample_zip
from tests.conftest import CHAT, jpeg_bytes, make_zip

API = "/api/v1"


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


def wait_for(client: TestClient, job_id: str, timeout: float = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"{API}/jobs/{job_id}").json()
        if job["status"] != "processing":
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


@pytest.fixture
def sample_id(client: TestClient) -> str:
    res = client.post(f"{API}/jobs/sample")
    assert res.status_code == 202
    job_id = res.json()["id"]
    assert wait_for(client, job_id)["status"] == "ready"
    return job_id


def upload(client: TestClient, path: Path, name: str | None = None, **form):
    with path.open("rb") as fh:
        return client.post(f"{API}/jobs", files=[("files", (name or path.name, fh, "application/zip"))], data=form)


# ---- health and jobs ---------------------------------------------------------------------
def test_health(client):
    body = client.get(f"{API}/health").json()
    assert body["status"] == "ok" and body["chromium"] is True
    assert isinstance(body["ffmpeg"], bool)


def test_sample_job_summary(client, sample_id):
    job = client.get(f"{API}/jobs/{sample_id}").json()
    assert job["status"] == "ready" and job["is_sample"]
    assert job["counts"] == {"messages": 35, "photos": 10, "videos": 1, "missing_media": 0, "omitted_media": 0}
    assert job["suggested_title"] == "Priya & Arjun"
    assert {s["name"] for s in job["senders"]} == {"Priya", "Arjun"}
    assert job["date_range"]["start"].startswith("2026-03-12")
    assert job["expires_at"] > job["created_at"]
    assert job["progress"]["stage"] == "Ready"


@pytest.mark.parametrize("bad", ["0" * 32, "not-a-job", "../etc/passwd"])
def test_unknown_or_malformed_job_ids_are_404(client, bad):
    assert client.get(f"{API}/jobs/{bad}").status_code == 404


def test_upload_a_real_zip(client, tmp_path):
    z = make_zip(
        tmp_path / "WhatsApp Chat with Maya.zip",
        {"_chat.txt": CHAT, "IMG-1.jpg": jpeg_bytes(), "IMG-2.jpg": jpeg_bytes()},
    )
    res = upload(client, z)
    assert res.status_code == 202
    job = wait_for(client, res.json()["id"])
    assert job["status"] == "ready"
    assert job["suggested_title"] == "Maya"
    assert job["counts"]["photos"] == 2
    assert job["sources"][0]["name"] == "WhatsApp Chat with Maya.zip"


def test_upload_of_something_else_fails_with_a_readable_error(client, tmp_path):
    bad = tmp_path / "holiday.png"
    bad.write_bytes(jpeg_bytes())
    job = wait_for(client, upload(client, bad).json()["id"])
    assert job["status"] == "failed"
    assert "not a chat export" in job["error"]
    # A failed job cannot be previewed or exported.
    assert client.post(f"{API}/jobs/{job['id']}/preview", json={"options": {}}).status_code == 409
    assert client.post(f"{API}/jobs/{job['id']}/exports", json={}).status_code == 409


def test_upload_larger_than_the_limit_is_rejected_and_cleaned_up(settings, tmp_path):
    settings.max_upload_mb = 1
    with TestClient(create_app(settings)) as client:
        big = tmp_path / "big.zip"
        big.write_bytes(b"0" * (2 * 1024 * 1024))
        res = upload(client, big)
        assert res.status_code == 413
        assert "limit" in res.json()["detail"]
    assert not any(settings.jobs_dir.iterdir())


def test_adding_files_merges_into_the_same_job(client, tmp_path):
    first = make_zip(tmp_path / "a.zip", {"_chat.txt": CHAT, "IMG-1.jpg": jpeg_bytes(), "IMG-2.jpg": jpeg_bytes()})
    job_id = upload(client, first).json()["id"]
    assert wait_for(client, job_id)["status"] == "ready"
    more = make_zip(
        tmp_path / "b.zip", {"_chat.txt": CHAT.split("13/03")[0] + "14/03/2026, 8:00 am - Arjun: new day\n"}
    )
    with more.open("rb") as fh:
        res = client.post(f"{API}/jobs/{job_id}/files", files=[("files", ("b.zip", fh, "application/zip"))])
    assert res.status_code == 202
    job = wait_for(client, job_id)
    assert len(job["sources"]) == 2 and job["counts"]["messages"] == 4


def test_date_order_patch_rereads_the_dates(client, tmp_path):
    txt = tmp_path / "c.txt"
    txt.write_text("03/04/2026, 9:30 am - A: x\n05/06/2026, 9:30 am - B: y\n", encoding="utf-8")
    with txt.open("rb") as fh:
        job_id = client.post(f"{API}/jobs", files=[("files", ("c.txt", fh, "text/plain"))]).json()["id"]
    job = wait_for(client, job_id)
    assert job["order_ambiguous"] and job["date_range"]["start"].startswith("2026-04-03")
    patched = client.patch(f"{API}/jobs/{job_id}", json={"date_order": "mdy"}).json()
    assert patched["date_range"]["start"].startswith("2026-03-04") and not patched["order_ambiguous"]
    assert client.patch(f"{API}/jobs/{job_id}", json={"date_order": "ymd"}).status_code == 422


def test_delete_removes_the_job_and_its_files(client, sample_id, settings):
    assert client.delete(f"{API}/jobs/{sample_id}").status_code == 204
    assert client.get(f"{API}/jobs/{sample_id}").status_code == 404
    assert not (settings.jobs_dir / sample_id).exists()
    assert client.delete(f"{API}/jobs/{sample_id}").status_code == 404


# ---- media ---------------------------------------------------------------------------------
def test_media_route_serves_images_and_nothing_else(client, sample_id):
    res = client.get(f"{API}/jobs/{sample_id}/media/web/m000001.jpg")
    assert res.status_code == 200 and res.headers["content-type"] == "image/jpeg"
    assert res.content[:2] == b"\xff\xd8"
    assert client.get(f"{API}/jobs/{sample_id}/media/print/m000001.jpg").status_code == 200
    assert client.get(f"{API}/jobs/{sample_id}/media/huge/m000001.jpg").status_code == 422
    for name in ("job.json", "..%2Fjob.json", "m1.jpg", "m000001.gif"):
        assert client.get(f"{API}/jobs/{sample_id}/media/web/{name}").status_code in (404, 422)
    assert client.get(f"{API}/jobs/{sample_id}/media/web/m999999.jpg").status_code == 404


# ---- preview -------------------------------------------------------------------------------
def test_insights_for_the_sample_chat(client, sample_id):
    body = client.get(f"{API}/jobs/{sample_id}/insights").json()
    assert body["total_messages"] > 30
    assert {s["name"] for s in body["senders"]} == {"Priya", "Arjun"}
    assert len(body["by_hour"]) == 24 and len(body["by_weekday"]) == 7
    assert sum(s["photos"] for s in body["senders"]) == 10
    assert client.get(f"{API}/jobs/{'0' * 32}/insights").status_code == 404


def test_preview_returns_html_and_statistics(client, sample_id):
    res = client.post(f"{API}/jobs/{sample_id}/preview", json={"options": {}})
    assert res.status_code == 200
    body = res.json()
    assert "Good morning! Are we still on for Coorg" in body["html"]
    assert f"/api/v1/jobs/{sample_id}/media/web/m" in body["html"]
    assert body["page"] == 1 and body["page_count"] == 1 and body["volume"] == 1
    assert body["stats"]["messages"] == 35 and body["stats"]["photos"] == 10
    assert body["stats"]["estimated_pages"] >= 3


def test_preview_pages_and_volumes_are_clamped(client, sample_id):
    body = client.post(
        f"{API}/jobs/{sample_id}/preview", json={"options": {"volume_mode": "month"}, "page": 99, "volume": 99}
    ).json()
    assert body["volume"] == 2 and body["page"] == 1
    assert len(body["stats"]["volumes"]) == 2


def test_preview_with_no_matches_is_empty_not_an_error(client, sample_id):
    body = client.post(f"{API}/jobs/{sample_id}/preview", json={"options": {"query": "no such words"}}).json()
    assert body["html"] == "" and body["stats"]["messages"] == 0 and body["stats"]["volumes"] == []


def test_preview_filters_apply(client, sample_id):
    body = client.post(f"{API}/jobs/{sample_id}/preview", json={"options": {"exclude_people": ["Priya"]}}).json()
    assert "Good morning! Are we still on for Coorg" not in body["html"]
    assert "Yes! Booked the homestay" in body["html"]


@pytest.mark.parametrize(
    "options",
    [{"page_size": "B5"}, {"theme": "neon"}, {"album": {"columns": 9}}, {"volume_size": 1}, {"title": "x" * 500}],
)
def test_invalid_options_are_422(client, sample_id, options):
    assert client.post(f"{API}/jobs/{sample_id}/preview", json={"options": options}).status_code == 422


# ---- exports -------------------------------------------------------------------------------
def wait_export(client: TestClient, job_id: str, export_id: str, timeout: float = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get(f"{API}/jobs/{job_id}/exports/{export_id}").json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(0.2)
    raise AssertionError("export did not finish")


@pytest.mark.browser
def test_export_and_download(client, sample_id):
    res = client.post(f"{API}/jobs/{sample_id}/exports", json={"title": "Coorg trip"})
    assert res.status_code == 202
    export = wait_export(client, sample_id, res.json()["id"])
    assert export["status"] == "done", export["error"]
    (file,) = export["files"]
    assert file["name"] == "coorg-trip.pdf" and file["pages"] >= 6 and export["archive"] is None

    url = f"{API}/jobs/{sample_id}/exports/{export['id']}/files/{file['name']}"
    pdf = client.get(url)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers["content-disposition"]
    assert "inline" in client.get(url + "?inline=true").headers["content-disposition"]

    assert client.get(f"{API}/jobs/{sample_id}/exports/{export['id']}/files/job.json").status_code == 404
    assert client.get(f"{API}/jobs/{sample_id}/exports/{export['id']}/files/..%2F..%2Fjob.json").status_code == 404
    assert client.get(f"{API}/jobs/{sample_id}/exports/{'f' * 16}").status_code == 404
    assert client.get(f"{API}/jobs/{sample_id}/exports/not-valid").status_code == 404


@pytest.mark.browser
def test_export_of_volumes_offers_a_zip(client, sample_id):
    res = client.post(f"{API}/jobs/{sample_id}/exports", json={"volume_mode": "month", "mode": "album"})
    export = wait_export(client, sample_id, res.json()["id"])
    assert export["status"] == "done", export["error"]
    assert len(export["files"]) == 2 and export["archive"].endswith("-volumes.zip")
    zipped = client.get(f"{API}/jobs/{sample_id}/exports/{export['id']}/files/{export['archive']}")
    assert zipped.status_code == 200 and zipped.content[:2] == b"PK"


@pytest.mark.browser
def test_export_with_nothing_to_print_reports_why(client, sample_id):
    res = client.post(f"{API}/jobs/{sample_id}/exports", json={"query": "zzzz"})
    export = wait_export(client, sample_id, res.json()["id"])
    assert export["status"] == "failed" and "nothing to export" in export["error"]


def test_cancelling_an_unknown_export_is_404(client, sample_id):
    assert client.delete(f"{API}/jobs/{sample_id}/exports/{'a' * 16}").status_code == 404


def test_frontend_is_served_when_a_build_exists(settings, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Chatbook</title>")
    settings.static_dir = dist
    with TestClient(create_app(settings)) as client:
        assert "Chatbook" in client.get("/").text
        assert client.get(f"{API}/health").status_code == 200  # the API still wins on its own prefix


def test_sample_zip_builder_is_reusable(tmp_path):
    assert build_sample_zip(tmp_path / "again.zip").stat().st_size > 10_000