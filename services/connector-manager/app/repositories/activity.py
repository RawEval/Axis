"""Activity events repository — the shared writer for the §6.3 firehose.

Every ingestion path (Slack Events webhook, Notion poll, Gmail push, GitHub
webhook, Drive push) feeds rows into ``activity_events`` via this class.
The proactive-monitor and the agent's ``activity.query`` capability both
read from the same table.

Dedup: we key on ``(user_id, source, raw_ref->>'key')`` so a re-delivery of
the same webhook message is a no-op. The ``key`` must be stable across
retries — Slack uses ``channel:ts``, Notion uses the page id, Gmail uses
the message id, GitHub uses the event delivery GUID.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg


class ActivityEventsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(
        self,
        *,
        user_id: str,
        project_id: str | None,
        source: str,
        event_type: str,
        key: str,
        title: str,
        snippet: str | None = None,
        actor: str | None = None,
        actor_id: str | None = None,
        occurred_at: datetime | None = None,
        raw_ref: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert or no-op if a row with the same (user, source, key) exists.

        Returns ``{id, inserted: bool}``. ``inserted`` is False on dedup.
        """
        merged_ref = dict(raw_ref or {})
        merged_ref["key"] = key
        when = occurred_at or datetime.utcnow()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO activity_events
                    (user_id, project_id, source, event_type, actor, actor_id,
                     title, snippet, raw_ref, occurred_at)
                SELECT $1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9::jsonb, $10
                WHERE NOT EXISTS (
                    SELECT 1 FROM activity_events
                    WHERE user_id = $1::uuid
                      AND source = $3
                      AND raw_ref->>'key' = $11
                )
                RETURNING id
                """,
                user_id,
                project_id,
                source,
                event_type,
                actor,
                actor_id,
                title,
                snippet,
                json.dumps(merged_ref),
                when,
                key,
            )
        if row is None:
            return {"id": None, "inserted": False}
        return {"id": str(row["id"]), "inserted": True}

    async def recent_for_user(
        self,
        user_id: str,
        *,
        source: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read back the latest N rows — used by the relevance engine + /activity."""
        async with self._pool.acquire() as conn:
            if source:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, project_id, source, event_type, actor,
                           title, snippet, raw_ref, occurred_at
                    FROM activity_events
                    WHERE user_id = $1::uuid AND source = $2
                    ORDER BY occurred_at DESC
                    LIMIT $3
                    """,
                    user_id,
                    source,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, project_id, source, event_type, actor,
                           title, snippet, raw_ref, occurred_at
                    FROM activity_events
                    WHERE user_id = $1::uuid
                    ORDER BY occurred_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                )
        return [dict(r) for r in rows]
