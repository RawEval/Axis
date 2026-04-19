"""connector.gmail.recent_activity — time-windowed feed of Gmail messages.

Reads from the local activity_events cache (kept fresh by GmailSyncWorker
in connector-manager). The FreshenBeforeRead mixin runs a synchronous
/tools/gmail/freshen call if cache is older than 60s — invisible to the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.capabilities._freshen_mixin import FreshenBeforeRead
from app.capabilities.base import CapabilityResult, Citation
from app.db import db
from app.repositories.users import UsersRepository
from app.util.since import resolve_since


@dataclass
class _GmailRecentActivity(FreshenBeforeRead):
    name: str = "connector.gmail.recent_activity"
    description: str = (
        "List Gmail messages received in a time window. Use for prompts like "
        "'what emails came in today' or 'who emailed me this week'. "
        "Reads a fresh local cache (auto-refreshed if older than 60s)."
    )
    scope: str = "read"
    default_permission: str = "auto"
    source: str = "gmail"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "ISO timestamp or 'today'/'1h'/'24h'/'7d'",
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
                "keyword": {
                    "type": "string",
                    "description": "optional substring filter on title/snippet",
                },
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
        uid = UUID(user_id)
        freshness = await self.ensure_fresh(uid)

        users_repo = UsersRepository(db.raw)
        tz_name = await users_repo.get_timezone(uid)
        start_ts = resolve_since(inputs.get("since", "today"), ZoneInfo(tz_name))

        limit = int(inputs.get("limit", 50))
        keyword = inputs.get("keyword")

        async with db.raw.acquire() as conn:
            sql = """
                SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
                FROM activity_events
                WHERE user_id = $1::uuid AND source = 'gmail' AND occurred_at >= $2
            """
            args: list[Any] = [user_id, start_ts]
            if keyword:
                sql += f" AND (title ILIKE ${len(args) + 1} OR COALESCE(snippet, '') ILIKE ${len(args) + 1})"
                args.append(f"%{keyword}%")
            sql += f" ORDER BY occurred_at DESC LIMIT ${len(args) + 1}"
            args.append(limit)
            rows = await conn.fetch(sql, *args)

        events = [dict(r) for r in rows]
        citations = [
            Citation(
                source_type=f"gmail_{r['event_type']}",
                provider="gmail",
                ref_id=str(r["id"]),
                title=r["title"],
                actor=r.get("actor"),
                excerpt=r.get("snippet"),
                occurred_at=r["occurred_at"].isoformat() if r.get("occurred_at") else None,
            )
            for r in events
        ]
        return CapabilityResult(
            summary=f"found {len(events)} gmail events since {inputs['since']}",
            content={"events": events, "freshness": freshness.model_dump()},
            citations=citations,
        )


CAPABILITY = _GmailRecentActivity()
