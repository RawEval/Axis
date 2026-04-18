"""User repository — all SQL for the users table lives here."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None,
        plan: str = "free",
    ) -> dict[str, Any]:
        """Atomic signup: user + personal org + owner membership + default project.

        Every new user owns their own personal organization (ADR 010). The
        default project sits inside that org. This means a brand-new user
        can immediately invite a teammate without migrating their data.
        """
        display_name = name or "Personal"
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, name, plan, password_hash, settings, usage)
                VALUES ($1, $2, $3, $4, '{}'::jsonb, '{}'::jsonb)
                RETURNING id, email, name, plan, created_at
                """,
                email.lower(),
                name,
                plan,
                password_hash,
            )

            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (name, is_personal)
                VALUES ($1, TRUE)
                RETURNING id
                """,
                display_name,
            )

            await conn.execute(
                """
                INSERT INTO organization_members (org_id, user_id, role)
                VALUES ($1, $2, 'owner')
                """,
                org_id,
                row["id"],
            )

            await conn.execute(
                """
                INSERT INTO projects (user_id, org_id, name, description, is_default)
                VALUES ($1, $2, 'Personal', 'Your default workspace', TRUE)
                """,
                row["id"],
                org_id,
            )
        return dict(row)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, name, plan, password_hash, failed_login_attempts,
                       locked_until, created_at
                FROM users
                WHERE LOWER(email) = LOWER($1)
                """,
                email,
            )
        return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, name, plan, created_at
                FROM users
                WHERE id = $1::uuid
                """,
                user_id,
            )
        return dict(row) if row else None

    async def mark_login_success(self, user_id: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET last_login_at = NOW(), failed_login_attempts = 0, locked_until = NULL
                WHERE id = $1::uuid
                """,
                user_id,
            )

    async def mark_login_failure(self, user_id: str, lock_if_exceeded: int) -> int:
        """Increment failed attempts, lock if exceeded. Returns new count."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1,
                    locked_until = CASE
                        WHEN failed_login_attempts + 1 >= $2
                        THEN NOW() + INTERVAL '30 minutes'
                        ELSE locked_until
                    END
                WHERE id = $1::uuid
                RETURNING failed_login_attempts
                """,
                user_id,
                lock_if_exceeded,
            )
        return int(row["failed_login_attempts"])

    async def email_exists(self, email: str) -> bool:
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT 1 FROM users WHERE LOWER(email) = LOWER($1)",
                email,
            )
        return val is not None

    async def log_login_event(
        self,
        *,
        user_id: str | None,
        email: str,
        event_type: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO login_events (user_id, email, event_type, ip_address, user_agent)
                VALUES ($1::uuid, $2, $3, $4::inet, $5)
                """,
                user_id,
                email,
                event_type,
                ip,
                user_agent,
            )

    @staticmethod
    def is_locked(user: dict[str, Any]) -> bool:
        locked_until: datetime | None = user.get("locked_until")
        if locked_until is None:
            return False
        return locked_until > datetime.now(tz=locked_until.tzinfo)
