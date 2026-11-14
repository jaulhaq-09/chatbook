"""Authentication and user library API routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.db import User
from app.state import Services, get_services

router = APIRouter(tags=["auth"])

Svc = Annotated[Services, Depends(get_services)]


class SignUpRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ClaimJobRequest(BaseModel):
    job_id: str


async def get_optional_user(
    svc: Svc,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return await svc.auth.get_user_by_token(parts[1])
    return None


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in or sign up.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


@router.post("/auth/signup")
async def signup(body: SignUpRequest, svc: Svc) -> dict[str, Any]:
    try:
        user, token = await svc.auth.signup(body.email, body.password, body.name)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return {"user": user.to_dict(), "token": token}


@router.post("/auth/login")
async def login(body: LoginRequest, svc: Svc) -> dict[str, Any]:
    try:
        user, token = await svc.auth.login(body.email, body.password)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err
    return {"user": user.to_dict(), "token": token}


@router.get("/auth/me")
async def me(user: CurrentUser) -> dict[str, Any]:
    return {"user": user.to_dict()}


@router.post("/auth/logout")
async def logout(
    svc: Svc,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            await svc.auth.logout(parts[1])
    return {"ok": True}


@router.post("/auth/claim-job/{job_id}")
async def claim_job(job_id: str, user: CurrentUser, svc: Svc) -> dict[str, bool]:
    await svc.auth.claim_job(user.id, job_id)
    return {"ok": True}


@router.get("/user/books")
async def list_user_books(user: CurrentUser, svc: Svc) -> list[dict[str, Any]]:
    return await svc.auth.list_user_books(user.id)


@router.delete("/user/books/{job_id}")
async def delete_user_book(job_id: str, user: CurrentUser, svc: Svc) -> dict[str, bool]:
    deleted = await svc.auth.delete_user_book(user.id, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found in your library.")
    try:
        svc.store.delete(job_id)
    except Exception:
        pass
    return {"ok": True}
