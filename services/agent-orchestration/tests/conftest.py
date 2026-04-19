"""Shared fixtures for agent-orchestration tests."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

from app.db import db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    await db.connect()
    yield db.raw
    await db.close()
