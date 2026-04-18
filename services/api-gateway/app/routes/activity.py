"""Activity firehose read API — /activity (ADR 007)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.db import db
from app.deps import CurrentProject, CurrentUser

router = APIRouter()


@router.get("")
async def list_activity(
    user_id: CurrentUser,
    project: CurrentProject,
    source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Recent activity events, scoped to the active project(s).

    The ``source`` filter accepts any provider string (``slack`` /
    ``notion`` / ``gmail`` / ``gdrive`` / ``github``) or None to return
    everything. The frontend uses this for the Activity page table.
    """
    if not project.ids:
        return []
    async with db.acquire() as conn:
        if source:
            rows = await conn.fetch(
                """
                SELECT id, source, event_type, actor, actor_id, title, snippet,
                       raw_ref, occurred_at, indexed_at, project_id
                FROM activity_events
                WHERE user_id = $1::uuid
                  AND project_id = ANY($2::uuid[])
                  AND source = $3
                ORDER BY occurred_at DESC
                LIMIT $4
                """,
                user_id,
                project.ids,
                source,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, source, event_type, actor, actor_id, title, snippet,
                       raw_ref, occurred_at, indexed_at, project_id
                FROM activity_events
                WHERE user_id = $1::uuid
                  AND project_id = ANY($2::uuid[])
                ORDER BY occurred_at DESC
                LIMIT $3
                """,
                user_id,
                project.ids,
                limit,
            )
    return [
        {
            "id": str(r["id"]),
            "source": r["source"],
            "event_type": r["event_type"],
            "actor": r["actor"],
            "actor_id": r["actor_id"],
            "title": r["title"],
            "snippet": r["snippet"],
            "raw_ref": r["raw_ref"],
            "occurred_at": r["occurred_at"].isoformat() if r["occurred_at"] else None,
            "indexed_at": r["indexed_at"].isoformat() if r["indexed_at"] else None,
            "project_id": str(r["project_id"]) if r["project_id"] else None,
        }
        for r in rows
    ]
