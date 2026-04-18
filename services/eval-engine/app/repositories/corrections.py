"""correction_signals + user_prompt_deltas repositories.

The two tables cooperate:

  correction_signals — raw user feedback. One row per "this was wrong"
      click, per "rewrite like this" edit, per "memory update" correction.
      Never deleted; it's training data.

  user_prompt_deltas — the short-loop's derived cache. One row per user.
      Refreshed on every new correction (fire-and-forget) so the next
      agent run sees the updated behavior without a DB aggregation on
      the critical path.
"""
from __future__ import annotations

from typing import Any

import asyncpg


CORRECTION_TYPES = {
    "wrong",          # "this answer was wrong"
    "rewrite",        # user supplied a better answer
    "memory_update",  # "remember that X is really Y"
    "scope",          # "too broad" / "too narrow"
}


class CorrectionsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        *,
        user_id: str,
        action_id: str,
        project_id: str | None,
        correction_type: str,
        note: str | None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO correction_signals
                    (user_id, action_id, project_id, correction_type, note)
                VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5)
                RETURNING id, created_at
                """,
                user_id,
                action_id,
                project_id,
                correction_type,
                note,
            )
        return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}

    async def recent_for_user(
        self, user_id: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT cs.id, cs.action_id, cs.correction_type, cs.note,
                       cs.created_at,
                       aa.prompt AS prompt,
                       aa.result AS result
                FROM correction_signals cs
                JOIN agent_actions aa ON aa.id = cs.action_id
                WHERE cs.user_id = $1::uuid
                ORDER BY cs.created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [dict(r) for r in rows]


class PromptDeltasRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, user_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, delta, source_corrections, model, token_count, updated_at
                FROM user_prompt_deltas
                WHERE user_id = $1::uuid
                """,
                user_id,
            )
        return dict(row) if row else None

    async def upsert(
        self,
        *,
        user_id: str,
        delta: str,
        source_corrections: list[str],
        model: str,
        token_count: int | None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_prompt_deltas
                    (user_id, delta, source_corrections, model, token_count, updated_at)
                VALUES ($1::uuid, $2, $3::uuid[], $4, $5, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    delta = EXCLUDED.delta,
                    source_corrections = EXCLUDED.source_corrections,
                    model = EXCLUDED.model,
                    token_count = EXCLUDED.token_count,
                    updated_at = NOW()
                RETURNING user_id, delta, source_corrections, model, token_count, updated_at
                """,
                user_id,
                delta,
                source_corrections,
                model,
                token_count,
            )
        return dict(row)
