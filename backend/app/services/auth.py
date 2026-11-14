"""Authentication and User Data Management Service.

Handles user registration, login, secure password hashing (scrypt),
session validation, and persistence of chatbook projects to the database.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select

from app.db import Database, User, UserBook, UserSession

log = logging.getLogger("chatbook.auth")
SESSION_DAYS = 30


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    """Hash password using scrypt with a random 16-byte salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored scrypt hash using constant-time comparison."""
    try:
        scheme, salt_hex, key_hex = hashed.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False


class AuthService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def signup(self, email: str, password: str, name: str = "") -> tuple[User, str]:
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            raise ValueError("Please provide a valid email address.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        async with self.db.sessionmaker() as session:
            stmt = select(User).where(User.email == email)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                raise ValueError("An account with this email already exists.")

            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name.strip() or email.split("@")[0],
            )
            session.add(user)
            await session.flush()

            token = secrets.token_urlsafe(32)
            user_session = UserSession(
                token=token,
                user_id=user.id,
                expires_at=utcnow() + timedelta(days=SESSION_DAYS),
            )
            session.add(user_session)
            await session.commit()
            await session.refresh(user)
            return user, token

    async def login(self, email: str, password: str) -> tuple[User, str]:
        email = email.strip().lower()
        async with self.db.sessionmaker() as session:
            stmt = select(User).where(User.email == email)
            user = (await session.execute(stmt)).scalar_one_or_none()
            if not user or not verify_password(password, user.password_hash):
                raise ValueError("Invalid email or password.")

            token = secrets.token_urlsafe(32)
            user_session = UserSession(
                token=token,
                user_id=user.id,
                expires_at=utcnow() + timedelta(days=SESSION_DAYS),
            )
            session.add(user_session)
            await session.commit()
            await session.refresh(user)
            return user, token

    async def get_user_by_token(self, token: str) -> User | None:
        if not token:
            return None
        async with self.db.sessionmaker() as session:
            stmt = (
                select(User)
                .join(UserSession, UserSession.user_id == User.id)
                .where(UserSession.token == token, UserSession.expires_at > utcnow())
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def logout(self, token: str) -> None:
        if not token:
            return
        async with self.db.sessionmaker() as session:
            await session.execute(delete(UserSession).where(UserSession.token == token))
            await session.commit()

    async def claim_job(self, user_id: str, job_id: str) -> None:
        """Associate an existing job or guest book with a user."""
        async with self.db.sessionmaker() as session:
            stmt = select(UserBook).where(UserBook.id == job_id)
            book = (await session.execute(stmt)).scalar_one_or_none()
            if book:
                book.user_id = user_id
                await session.commit()
            else:
                # Create book entry linked to user
                new_book = UserBook(id=job_id, user_id=user_id)
                session.add(new_book)
                await session.commit()

    async def sync_book(
        self,
        job_id: str,
        user_id: str | None = None,
        title: str = "",
        status: str = "processing",
        message_count: int = 0,
        photo_count: int = 0,
        video_count: int = 0,
        date_range: str | None = None,
        options_json: str | None = None,
        summary_json: str | None = None,
    ) -> None:
        """Upsert a chatbook entry in the database."""
        async with self.db.sessionmaker() as session:
            stmt = select(UserBook).where(UserBook.id == job_id)
            book = (await session.execute(stmt)).scalar_one_or_none()
            if book:
                if user_id is not None:
                    book.user_id = user_id
                if title:
                    book.title = title
                book.status = status
                book.message_count = message_count
                book.photo_count = photo_count
                book.video_count = video_count
                if date_range is not None:
                    book.date_range = date_range
                if options_json is not None:
                    book.options_json = options_json
                if summary_json is not None:
                    book.summary_json = summary_json
            else:
                book = UserBook(
                    id=job_id,
                    user_id=user_id,
                    title=title,
                    status=status,
                    message_count=message_count,
                    photo_count=photo_count,
                    video_count=video_count,
                    date_range=date_range,
                    options_json=options_json,
                    summary_json=summary_json,
                )
                session.add(book)
            await session.commit()

    async def list_user_books(self, user_id: str) -> list[dict[str, Any]]:
        async with self.db.sessionmaker() as session:
            stmt = select(UserBook).where(UserBook.user_id == user_id).order_by(UserBook.updated_at.desc())
            results = (await session.execute(stmt)).scalars().all()
            return [b.to_dict() for b in results]

    async def delete_user_book(self, user_id: str, job_id: str) -> bool:
        async with self.db.sessionmaker() as session:
            stmt = select(UserBook).where(UserBook.id == job_id, UserBook.user_id == user_id)
            book = (await session.execute(stmt)).scalar_one_or_none()
            if not book:
                return False
            await session.delete(book)
            await session.commit()
            return True
