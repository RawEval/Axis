"""Connector index repository — local search cache for instant queries.

Instead of hitting live provider APIs on every user question, the
background sync workers populate this table with searchable data.
The agent's capabilities search HERE first (Postgres FTS), falling
back to live API only for real-time data not yet indexed.

Dedup: UPSERT on (user_id, tool, resource_id).
"""
from __future__ import annotations

import json
from typing import Any

import asyncpg


class ConnectorIndexRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(
        self,
        *,
        user_id: str,
        project_id: str | None,
        tool: str,
        resource_type: str,
        resource_id: str,
        title: str | None = None,
        body: str | None = None,
        url: str | None = None,
        author: str | None = None,
        author_id: str | None = None,
        occurred_at: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO connector_index
                    (user_id, project_id, tool, resource_type, resource_id,
                     title, body, url, author, author_id, occurred_at, metadata,
                     indexed_at, stale)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb,
                        NOW(), FALSE)
                ON CONFLICT (user_id, tool, resource_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    url = EXCLUDED.url,
                    author = EXCLUDED.author,
                    occurred_at = COALESCE(EXCLUDED.occurred_at, connector_index.occurred_at),
                    metadata = EXCLUDED.metadata,
                    indexed_at = NOW(),
                    stale = FALSE
                RETURNING id
                """,
                user_id, project_id, tool, resource_type, resource_id,
                title, body, url, author, author_id, occurred_at,
                json.dumps(metadata or {}),
            )
        return {"id": str(row["id"]), "upserted": True}

    async def search(
        self,
        *,
        user_id: str,
        tool: str | None = None,
        query: str,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Full-text search across the local index. Instant — no API call."""
        async with self._pool.acquire() as conn:
            if tool:
                rows = await conn.fetch(
                    """
                    SELECT id, tool, resource_type, resource_id, title, body, url,
                           author, occurred_at, metadata,
                           ts_rank(to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(body,'')),
                                   plainto_tsquery('english', $3)) AS rank
                    FROM connector_index
                    WHERE user_id = $1::uuid
                      AND tool = $2
                      AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(body,''))
                          @@ plainto_tsquery('english', $3)
                      AND stale = FALSE
                    ORDER BY rank DESC, occurred_at DESC NULLS LAST
                    LIMIT $4
                    """,
                    user_id, tool, query, limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, tool, resource_type, resource_id, title, body, url,
                           author, occurred_at, metadata,
                           ts_rank(to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(body,'')),
                                   plainto_tsquery('english', $2)) AS rank
                    FROM connector_index
                    WHERE user_id = $1::uuid
                      AND to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(body,''))
                          @@ plainto_tsquery('english', $2)
                      AND stale = FALSE
                    ORDER BY rank DESC, occurred_at DESC NULLS LAST
                    LIMIT $3
                    """,
                    user_id, query, limit,
                )
        return [
            {
                "id": str(r["id"]),
                "tool": r["tool"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "title": r["title"],
                "body": (r["body"] or "")[:300],
                "url": r["url"],
                "author": r["author"],
                "occurred_at": r["occurred_at"].isoformat() if r["occurred_at"] else None,
                "rank": float(r["rank"]),
            }
            for r in rows
        ]

    async def count_for_user(self, user_id: str) -> dict[str, int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tool, COUNT(*) AS n
                FROM connector_index
                WHERE user_id = $1::uuid AND stale = FALSE
                GROUP BY tool
                """,
                user_id,
            )
        return {r["tool"]: int(r["n"]) for r in rows}

    async def mark_stale(self, user_id: str, tool: str) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE connector_index SET stale = TRUE
                WHERE user_id = $1::uuid AND tool = $2 AND stale = FALSE
                """,
                user_id, tool,
            )
        return int(result.split()[-1]) if result else 0
