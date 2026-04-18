"""Write-actions + snapshots repository.

Lifecycle of a write:
  1. ``create_pending`` — inserts write_actions (confirmed_by_user=false)
     + write_snapshots (before_state captured from the live resource).
     Returns the write_action_id + snapshot_id. A write.preview event is
     published; the UI renders the diff.
  2. ``confirm`` — sets confirmed_by_user=true, confirmed_at=NOW(). The
     caller then executes the write through the connector and calls
     ``set_after_state`` to store the post-write state.
  3. ``rollback`` — sets rolled_back=true. The caller replays the
     before_state through the connector.

All three are idempotent — confirming a confirmed write or rolling back
a rolled-back write is a no-op.
"""
from __future__ import annotations

import json
from typing import Any

import asyncpg


class WritesRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_pending(
        self,
        *,
        action_id: str,
        user_id: str,
        project_id: str | None,
        tool: str,
        target_id: str,
        target_type: str | None,
        diff: dict[str, Any],
        before_state: dict[str, Any] | list[Any],
        target_options: list[dict[str, Any]] | None = None,
        target_chosen: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn, conn.transaction():
            wa = await conn.fetchrow(
                """
                INSERT INTO write_actions
                    (action_id, project_id, tool, target_id, target_type, diff,
                     confirmed_by_user, rolled_back, target_options, target_chosen)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, false, false,
                        $7::jsonb, $8::jsonb)
                RETURNING id
                """,
                action_id,
                project_id,
                tool,
                target_id,
                target_type,
                json.dumps(diff),
                json.dumps(target_options) if target_options is not None else None,
                json.dumps(target_chosen) if target_chosen is not None else None,
            )
            ss = await conn.fetchrow(
                """
                INSERT INTO write_snapshots
                    (write_action_id, user_id, project_id, tool, target_id,
                     target_type, before_state)
                VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6, $7::jsonb)
                RETURNING id
                """,
                wa["id"],
                user_id,
                project_id,
                tool,
                target_id,
                target_type,
                json.dumps(before_state),
            )
            # Link snapshot back to write_actions
            await conn.execute(
                "UPDATE write_actions SET snapshot_id = $1 WHERE id = $2::uuid",
                str(ss["id"]),
                wa["id"],
            )
        return {
            "write_action_id": str(wa["id"]),
            "snapshot_id": str(ss["id"]),
        }

    async def confirm(self, write_action_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE write_actions
                SET confirmed_by_user = true, confirmed_at = NOW()
                WHERE id = $1::uuid AND confirmed_by_user = false
                """,
                write_action_id,
            )
        return result.endswith(" 1")

    async def choose_target(
        self, write_action_id: str, chosen: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Pick one of the staged target_options. Returns the updated row
        joined with the action's user_id (for downstream event publishing)
        and snapshot before/after state. Returns None if the row is missing
        or already executed (confirmed_by_user=true)."""
        async with self._pool.acquire() as conn, conn.transaction():
            updated = await conn.fetchrow(
                """
                UPDATE write_actions
                SET target_chosen = $2::jsonb,
                    target_id = COALESCE(target_id, $3)
                WHERE id = $1::uuid AND confirmed_by_user = false
                RETURNING id
                """,
                write_action_id,
                json.dumps(chosen),
                str(chosen.get("id") or ""),
            )
            if updated is None:
                return None
            row = await conn.fetchrow(
                """
                SELECT wa.id, wa.action_id, wa.tool, wa.target_id, wa.target_type,
                       wa.diff, wa.target_options, wa.target_chosen,
                       wa.confirmed_by_user, wa.rolled_back, wa.project_id,
                       aa.user_id,
                       ws.before_state, ws.after_state
                FROM write_actions wa
                LEFT JOIN agent_actions aa ON aa.id = wa.action_id
                LEFT JOIN write_snapshots ws ON ws.write_action_id = wa.id
                WHERE wa.id = $1::uuid
                """,
                write_action_id,
            )
        return dict(row) if row else None

    async def set_after_state(
        self, write_action_id: str, after_state: dict[str, Any] | list[Any]
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE write_snapshots
                SET after_state = $2::jsonb
                WHERE write_action_id = $1::uuid
                """,
                write_action_id,
                json.dumps(after_state),
            )

    async def rollback(self, write_action_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE write_actions
                SET rolled_back = true
                WHERE id = $1::uuid AND rolled_back = false
                """,
                write_action_id,
            )
        return result.endswith(" 1")

    async def get(self, write_action_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT wa.id, wa.action_id, wa.tool, wa.target_id, wa.target_type,
                       wa.diff, wa.confirmed_by_user, wa.confirmed_at,
                       wa.rolled_back, wa.snapshot_id, wa.project_id,
                       ws.before_state, ws.after_state
                FROM write_actions wa
                LEFT JOIN write_snapshots ws ON ws.write_action_id = wa.id
                WHERE wa.id = $1::uuid
                """,
                write_action_id,
            )
        return dict(row) if row else None

    async def list_for_project(
        self, user_id: str, project_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT wa.id, wa.tool, wa.target_id, wa.target_type, wa.diff,
                       wa.confirmed_by_user, wa.confirmed_at, wa.rolled_back,
                       wa.created_at, ws.before_state IS NOT NULL AS has_snapshot
                FROM write_actions wa
                LEFT JOIN write_snapshots ws ON ws.write_action_id = wa.id
                WHERE wa.project_id = $1::uuid
                ORDER BY wa.created_at DESC
                LIMIT $2
                """,
                project_id,
                limit,
            )
        return [dict(r) for r in rows]
