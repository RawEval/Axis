"""Repository for the `users` table.

Phase 1 only exposes `get_timezone(user_id)` — the rest of user CRUD lives
in auth-service. This repo is the read path used by capabilities that need
to localize timestamps to the user's wall-clock (activity.query, every
recent_activity capability).
"""
from __future__ import annotations

from uuid import UUID

import asyncpg


class UsersRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_timezone(self, user_id: UUID) -> str:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT timezone FROM users WHERE id = $1", user_id
            )
            return row["timezone"] if row else "UTC"
