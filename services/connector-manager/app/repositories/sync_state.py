# services/connector-manager/app/repositories/sync_state.py
"""Repository for connector_sync_state — the single source of truth for
'is this connector's data fresh?' per (user, source) pair.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg


class ConnectorSyncStateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, user_id: UUID, source: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, source, last_synced_at, last_status, last_error,
                       last_event_at, consecutive_fails, cursor, updated_at
                FROM connector_sync_state
                WHERE user_id = $1 AND source = $2
                """,
                user_id,
                source,
            )
            if row is None:
                return None
            d = dict(row)
            d["cursor"] = json.loads(d["cursor"]) if isinstance(d["cursor"], str) else (d["cursor"] or {})
            return d

    async def list_for_user(self, user_id: UUID) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source, last_synced_at, last_status, last_error,
                       last_event_at, consecutive_fails
                FROM connector_sync_state
                WHERE user_id = $1
                ORDER BY source
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def record_success(
        self,
        user_id: UUID,
        source: str,
        *,
        last_event_at: datetime | None,
        cursor: dict[str, Any],
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO connector_sync_state
                  (user_id, source, last_synced_at, last_status, last_error,
                   last_event_at, consecutive_fails, cursor, updated_at)
                VALUES ($1, $2, NOW(), 'ok', NULL, $3, 0, $4::jsonb, NOW())
                ON CONFLICT (user_id, source) DO UPDATE SET
                  last_synced_at = NOW(),
                  last_status = 'ok',
                  last_error = NULL,
                  last_event_at = COALESCE(EXCLUDED.last_event_at, connector_sync_state.last_event_at),
                  consecutive_fails = 0,
                  cursor = EXCLUDED.cursor,
                  updated_at = NOW()
                """,
                user_id,
                source,
                last_event_at,
                json.dumps(cursor),
            )

    async def record_failure(
        self,
        user_id: UUID,
        source: str,
        *,
        status: str,
        error: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO connector_sync_state
                  (user_id, source, last_status, last_error, consecutive_fails, updated_at)
                VALUES ($1, $2, $3, $4, 1, NOW())
                ON CONFLICT (user_id, source) DO UPDATE SET
                  last_status = EXCLUDED.last_status,
                  last_error = EXCLUDED.last_error,
                  consecutive_fails = connector_sync_state.consecutive_fails + 1,
                  updated_at = NOW()
                """,
                user_id,
                source,
                status,
                error[:500],
            )
