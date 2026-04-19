"""activity.query — query the user's cross-tool activity firehose.

Spec §6.3 / ADR 007. Reads from activity_events, filtering by a user-local
'today' window resolved via app.util.since.resolve_since.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.capabilities.base import CapabilityResult, Citation
from app.db import db
from app.repositories.users import UsersRepository
from app.util.since import resolve_since


@dataclass
class _ActivityQuery:
    name: str = "activity.query"
    description: str = (
        "Query the user's activity stream — events from every connected tool "
        "(Slack messages, Gmail arrivals, Notion edits, GitHub commits, "
        "Linear changes). Use time-range + source + keyword filters. Good for "
        "'what happened today' and 'did anyone say X this week' prompts."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": (
                        "ISO timestamp or natural phrase like 'last hour' / 'today' / 'this week'"
                    ),
                },
                "source": {
                    "type": "string",
                    "enum": [
                        "slack",
                        "notion",
                        "gmail",
                        "gdrive",
                        "github",
                        "linear",
                        "axis",
                        "all",
                    ],
                    "default": "all",
                },
                "keyword": {
                    "type": "string",
                    "description": "optional full-text match",
                },
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
            },
            "required": ["since"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        limit = int(inputs.get("limit", 50))
        source = inputs.get("source", "all")
        keyword = inputs.get("keyword")

        users_repo = UsersRepository(db.raw)
        tz_name = await users_repo.get_timezone(UUID(user_id))
        start_ts = resolve_since(inputs.get("since", "today"), ZoneInfo(tz_name))

        async with db.raw.acquire() as conn:
            sql = """
                SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
                FROM activity_events
                WHERE user_id = $1::uuid AND occurred_at >= $2
            """
            args: list[Any] = [user_id, start_ts]
            if project_id:
                sql += f" AND project_id = ${len(args) + 1}::uuid"
                args.append(project_id)
            if source and source != "all":
                sql += f" AND source = ${len(args) + 1}"
                args.append(source)
            if keyword:
                sql += (
                    f" AND to_tsvector('english', title || ' ' || COALESCE(snippet, '')) "
                    f"@@ plainto_tsquery('english', ${len(args) + 1})"
                )
                args.append(keyword)
            sql += f" ORDER BY occurred_at DESC LIMIT ${len(args) + 1}"
            args.append(limit)
            rows = await conn.fetch(sql, *args)

        events = [dict(r) for r in rows]
        citations = [
            Citation(
                source_type=f"{r['source']}_{r['event_type']}",
                provider=r["source"],
                ref_id=str(r["id"]),
                title=r["title"],
                actor=r.get("actor"),
                excerpt=r.get("snippet"),
                occurred_at=r["occurred_at"].isoformat() if r.get("occurred_at") else None,
            )
            for r in events
        ]
        return CapabilityResult(
            summary=f"found {len(events)} activity events",
            content=events,
            citations=citations,
        )


CAPABILITY = _ActivityQuery()
