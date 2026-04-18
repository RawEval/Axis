"""Projects repository — per-user workspace containers (ADR 002)."""
from __future__ import annotations

from typing import Any

import asyncpg


class ProjectsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, is_default, settings, created_at, updated_at
                FROM projects
                WHERE user_id = $1::uuid
                ORDER BY is_default DESC, created_at ASC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def get(self, user_id: str, project_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, is_default, settings, created_at, updated_at
                FROM projects
                WHERE user_id = $1::uuid AND id = $2::uuid
                """,
                user_id,
                project_id,
            )
        return dict(row) if row else None

    async def get_default(self, user_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, is_default, settings, created_at, updated_at
                FROM projects
                WHERE user_id = $1::uuid AND is_default = TRUE
                LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None

    async def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO projects (user_id, name, description)
                    VALUES ($1::uuid, $2, $3)
                    RETURNING id, name, description, is_default, settings, created_at, updated_at
                    """,
                    user_id,
                    name,
                    description,
                )
            except asyncpg.UniqueViolationError as e:
                raise ValueError("project name already exists") from e
        return dict(row)

    async def rename(
        self,
        *,
        user_id: str,
        project_id: str,
        name: str,
        description: str | None,
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    UPDATE projects
                    SET name = $3, description = COALESCE($4, description), updated_at = NOW()
                    WHERE user_id = $1::uuid AND id = $2::uuid
                    RETURNING id, name, description, is_default, settings, created_at, updated_at
                    """,
                    user_id,
                    project_id,
                    name,
                    description,
                )
            except asyncpg.UniqueViolationError as e:
                raise ValueError("project name already exists") from e
        return dict(row) if row else None

    async def set_default(self, user_id: str, project_id: str) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "UPDATE projects SET is_default = FALSE WHERE user_id = $1::uuid",
                user_id,
            )
            await conn.execute(
                """
                UPDATE projects SET is_default = TRUE, updated_at = NOW()
                WHERE user_id = $1::uuid AND id = $2::uuid
                """,
                user_id,
                project_id,
            )

    async def delete(self, user_id: str, project_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM projects
                WHERE user_id = $1::uuid AND id = $2::uuid AND is_default = FALSE
                """,
                user_id,
                project_id,
            )
        # "DELETE N" or "DELETE 0"
        return result.endswith(" 1")
