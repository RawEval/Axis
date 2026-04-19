"""Tests for UsersRepository.get_timezone()."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.repositories.users import UsersRepository


async def test_get_timezone_returns_default_when_user_missing(db_pool):
    repo = UsersRepository(db_pool)
    tz = await repo.get_timezone(uuid4())
    assert tz == "UTC"


async def test_get_timezone_returns_stored_value(db_pool):
    repo = UsersRepository(db_pool)
    user_id = uuid4()
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, timezone)
               VALUES ($1, $2, 'placeholder-not-validated-here', $3)""",
            user_id, f"tz-{user_id}@test.local", "Asia/Kolkata",
        )
    try:
        tz = await repo.get_timezone(user_id)
        assert tz == "Asia/Kolkata"
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
