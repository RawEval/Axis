"""Repository for agent_actions, proactive_surfaces, connectors (read)."""
from __future__ import annotations

from typing import Any

import asyncpg


class ActionsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def history_for_project(
        self, user_id: str, project_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, prompt, plan, result, eval_score, timestamp
                FROM agent_actions
                WHERE user_id = $1::uuid AND project_id = $2::uuid
                ORDER BY timestamp DESC
                LIMIT $3
                """,
                user_id,
                project_id,
                limit,
            )
        return [dict(r) for r in rows]

    async def history_for_projects(
        self, user_id: str, project_ids: list[str], *, limit: int = 50
    ) -> list[dict[str, Any]]:
        if not project_ids:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, project_id, prompt, plan, result, eval_score, timestamp
                FROM agent_actions
                WHERE user_id = $1::uuid AND project_id = ANY($2::uuid[])
                ORDER BY timestamp DESC
                LIMIT $3
                """,
                user_id,
                project_ids,
                limit,
            )
        return [dict(r) for r in rows]

    async def surfaces_for_project(
        self, user_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, signal_type, title, context_snippet, confidence_score,
                       proposed_action, status, created_at
                FROM proactive_surfaces
                WHERE user_id = $1::uuid AND project_id = $2::uuid
                  AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 50
                """,
                user_id,
                project_id,
            )
        return [dict(r) for r in rows]

    async def connectors_for_project(
        self, user_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tool_name, status, permissions, last_sync, health_status,
                       workspace_id, workspace_name
                FROM connectors
                WHERE user_id = $1::uuid AND project_id = $2::uuid
                ORDER BY tool_name
                """,
                user_id,
                project_id,
            )
        return [dict(r) for r in rows]
