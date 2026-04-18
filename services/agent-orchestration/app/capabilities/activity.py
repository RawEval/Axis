"""activity.query — query the user's cross-tool activity firehose.

Spec §6.3 / ADR 007. Today activity_events is empty because no ingestion
worker populates it — the capability still works (returns []) and is ready
for Session 4 when ingestion ships.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.db import db


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
        interval = _parse_since(inputs.get("since", "today"))

        async with db.acquire() as conn:
            # asyncpg encodes intervals as timedelta, not str, so we inline
            # the whitelisted interval literal instead of binding it.
            base_sql = f"""
                SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
                FROM activity_events
                WHERE user_id = $1::uuid
                  AND occurred_at >= NOW() - INTERVAL '{interval}'
            """
            args: list[Any] = [user_id]
            if project_id:
                base_sql += f" AND project_id = ${len(args) + 1}::uuid"
                args.append(project_id)
            if source and source != "all":
                base_sql += f" AND source = ${len(args) + 1}"
                args.append(source)
            if keyword:
                base_sql += (
                    f" AND to_tsvector('english', title || ' ' || COALESCE(snippet, '')) "
                    f"@@ plainto_tsquery('english', ${len(args) + 1})"
                )
                args.append(keyword)
            base_sql += f" ORDER BY occurred_at DESC LIMIT ${len(args) + 1}"
            args.append(limit)

            rows = await conn.fetch(base_sql, *args)

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


_INTERVAL_MAP = {
    "last hour": "1 hour",
    "1h": "1 hour",
    "1 hour": "1 hour",
    "today": "1 day",
    "24h": "1 day",
    "1d": "1 day",
    "1 day": "1 day",
    "this week": "7 days",
    "7d": "7 days",
    "1 week": "7 days",
    "this month": "30 days",
    "30d": "30 days",
    "1 month": "30 days",
}


def _parse_since(s: str) -> str:
    """Map a natural phrase to a whitelisted Postgres INTERVAL literal.

    Only values in ``_INTERVAL_MAP`` are ever returned — this is inlined into
    the SQL below so it must stay untrusted-input-free.
    """
    return _INTERVAL_MAP.get((s or "").strip().lower(), "1 day")


CAPABILITY = _ActivityQuery()
