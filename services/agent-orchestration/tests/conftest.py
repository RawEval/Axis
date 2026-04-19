"""Shared fixtures for agent-orchestration tests.

`db_pool` is a session-scoped asyncpg pool opened directly by the test session
(NOT via app.db.connect — that sets a module-level global which collides with
any code path that also calls connect()). Tests that need DB access use this
pool directly via `await db_pool.acquire() as conn`.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import asyncpg
import pytest
import pytest_asyncio

from app.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(settings.postgres_url, min_size=1, max_size=2)
    try:
        yield pool
    finally:
        await pool.close()
