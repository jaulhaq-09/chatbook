from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_file = tmp_path / "test_auth.db"
    settings = Settings(
        data_dir=tmp_path / "data",
        database_url=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_signup_and_login_flow(client: TestClient) -> None:
    # 1. Sign up a new user
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@example.com", "password": "supersecretpassword", "name": "Alice"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["name"] == "Alice"
    token = data["token"]

    # 2. Prevent duplicate signup
    dup = client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@example.com", "password": "anotherpassword"},
    )
    assert dup.status_code == 400
    assert "already exists" in dup.json()["detail"]

    # 3. Verify /auth/me with Bearer token
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "alice@example.com"

    # 4. /auth/me without token fails with 401
    anon = client.get("/api/v1/auth/me")
    assert anon.status_code == 401

    # 5. Log in with wrong password fails
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert wrong.status_code == 401

    # 6. Log in with correct password succeeds
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "supersecretpassword"},
    )
    assert login.status_code == 200
    assert "token" in login.json()

    # 7. Logout revokes token
    logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    revoked = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked.status_code == 401


def test_user_books_and_claiming(client: TestClient) -> None:
    # Sign up user
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "bob@example.com", "password": "password123", "name": "Bob"},
    )
    token = signup_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start sample chat
    sample_res = client.post("/api/v1/jobs/sample")
    assert sample_res.status_code == 202
    job_id = sample_res.json()["id"]

    # Claim the sample chat into Bob's account
    claim_res = client.post(f"/api/v1/auth/claim-job/{job_id}", headers=headers)
    assert claim_res.status_code == 200

    # List Bob's books
    books_res = client.get("/api/v1/user/books", headers=headers)
    assert books_res.status_code == 200
    books = books_res.json()
    assert len(books) == 1
    assert books[0]["id"] == job_id

    # Delete Bob's book
    del_res = client.delete(f"/api/v1/user/books/{job_id}", headers=headers)
    assert del_res.status_code == 200
    assert len(client.get("/api/v1/user/books", headers=headers).json()) == 0
