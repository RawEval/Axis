"""Shared fixtures for connector-manager tests.

Two distinct DB-access patterns coexist:

1. **Direct repo tests** use `db_pool` — a session-scoped asyncpg pool opened
   by the test session itself (NOT the app's global `db.raw`). This keeps the
   pool's event loop separate from any TestClient-managed loop.

2. **Route tests** use `client` — a function-scoped FastAPI TestClient that
   runs the full app lifespan (which opens its own `db.raw` pool in its own
   loop). The two pools never share state.

Mixing the two used to crash with "connection was closed in the middle of
operation" because the session-scoped `db.connect()` pool was overwritten by
the lifespan's `db.connect()` call. Keeping them separate fixes that.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


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


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
