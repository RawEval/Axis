"""Auth flow tests — hit the running Postgres, not mocks."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_me(client: AsyncClient, unique_email: str) -> None:
    r = await client.post(
        "/register",
        json={"email": unique_email, "password": "PytestPassword123!", "name": "Test"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"]
    assert body["user_id"]

    me = await client.get(
        "/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == unique_email.lower()


@pytest.mark.asyncio
async def test_duplicate_register_409(client: AsyncClient, unique_email: str) -> None:
    payload = {"email": unique_email, "password": "PytestPassword123!"}
    r1 = await client.post("/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password_then_right(client: AsyncClient, unique_email: str) -> None:
    await client.post(
        "/register",
        json={"email": unique_email, "password": "PytestPassword123!", "name": "Test"},
    )
    bad = await client.post(
        "/login",
        json={"email": unique_email, "password": "NotTheRightPassword!"},
    )
    assert bad.status_code == 401
    good = await client.post(
        "/login",
        json={"email": unique_email, "password": "PytestPassword123!"},
    )
    assert good.status_code == 200
    assert good.json()["access_token"]


@pytest.mark.asyncio
async def test_me_without_token_401(client: AsyncClient) -> None:
    r = await client.get("/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_bogus_token_401(client: AsyncClient) -> None:
    r = await client.get("/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password_422(client: AsyncClient, unique_email: str) -> None:
    r = await client.post("/register", json={"email": unique_email, "password": "short"})
    assert r.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_register_invalid_email_422(client: AsyncClient) -> None:
    r = await client.post(
        "/register",
        json={"email": "not-an-email", "password": "PytestPassword123!"},
    )
    assert r.status_code == 422
