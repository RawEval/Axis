"""Pytest fixtures for auth-service tests.

We hit real Postgres (running in docker) — no mocks. The pool is created
fresh per test to avoid the "Future attached to a different loop" trap that
hits when sharing asyncpg pools across pytest-asyncio loops.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import db
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    await db.connect()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        await db.close()


@pytest_asyncio.fixture
async def unique_email() -> str:
    return f"test+{uuid.uuid4().hex[:12]}@raweval.com"
