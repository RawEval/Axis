"""Notion polling loop — Session 4.3.

Runs as a background asyncio task inside the connector-manager process.
Every ``NOTION_POLL_INTERVAL_SEC`` (default 15 minutes) we iterate every
connected Notion workspace and ingest any page that was edited since the
connector's last_sync timestamp. Each new/edited page becomes one
``activity_events`` row; re-poll is idempotent via the repository's
(source, raw_ref->>'key') dedup.

This is deliberately *not* Celery. The poll is idempotent, cheap, and not
worth dragging in a broker just for one task. If the service restarts
mid-poll the next tick picks up wherever ``last_sync`` was. When we need
fan-out across many users or a real beat scheduler we'll move to
proactive-monitor's existing Celery worker.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axis_common import get_logger

from app.db import db
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.security import decrypt_token

# The NotionClient lives in the connectors/ package — same sys.path trick
# the /tools routes use.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from notion.src.client import NotionClient  # noqa: E402

logger = get_logger(__name__)


async def poll_all_notion_workspaces() -> dict[str, int]:
    """Single tick: pull each connected Notion workspace once.

    Returns a counter for observability — inserted / seen / failed.
    """
    conn_repo = ConnectorsRepository(db.raw)
    activity_repo = ActivityEventsRepository(db.raw)

    connectors = await conn_repo.list_connected(tool="notion")
    inserted = 0
    seen = 0
    failed = 0

    for row in connectors:
        try:
            access_token = decrypt_token(row["auth_token_encrypted"])
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "notion_poll_decrypt_failed",
                connector_id=str(row["id"]),
                error=str(e),
            )
            failed += 1
            continue

        client = NotionClient(access_token=access_token)
        try:
            hits = await client.search(query="", limit=20)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "notion_poll_api_failed",
                connector_id=str(row["id"]),
                error=str(e),
            )
            failed += 1
            continue

        last_sync: datetime | None = row.get("last_sync")
        for page in hits:
            seen += 1
            mapped = _map_notion_page(page)
            if mapped is None:
                continue
            # If last_sync is set, skip pages older than it — saves churning
            # dedup checks for the same pages every tick.
            if last_sync and mapped["occurred_at"] and mapped["occurred_at"] <= last_sync:
                continue
            result = await activity_repo.upsert(
                user_id=str(row["user_id"]),
                project_id=str(row["project_id"]) if row.get("project_id") else None,
                source="notion",
                event_type=mapped["event_type"],
                key=mapped["key"],
                external_id=mapped["key"],
                title=mapped["title"],
                snippet=mapped.get("snippet"),
                actor=mapped.get("actor"),
                actor_id=mapped.get("actor_id"),
                occurred_at=mapped["occurred_at"],
                raw_ref=mapped.get("raw_ref"),
            )
            if result["inserted"]:
                inserted += 1

        await conn_repo.touch_last_sync(str(row["id"]))

    logger.info(
        "notion_poll_tick",
        connectors=len(connectors),
        seen=seen,
        inserted=inserted,
        failed=failed,
    )
    return {
        "connectors": len(connectors),
        "seen": seen,
        "inserted": inserted,
        "failed": failed,
    }


def _map_notion_page(page: dict[str, Any]) -> dict[str, Any] | None:
    """Flatten a Notion search hit onto the activity row shape.

    Notion's search response is polymorphic — page vs database. We only
    ingest pages in Phase 1; databases are metadata, not activity.
    """
    if page.get("object") != "page":
        return None

    page_id = page.get("id")
    if not page_id:
        return None

    title: str | None = None
    props = page.get("properties", {}) or {}
    for v in props.values():
        if isinstance(v, dict) and v.get("type") == "title":
            parts = v.get("title", [])
            if parts:
                title = "".join(
                    p.get("plain_text", "") for p in parts if isinstance(p, dict)
                )
            break

    last_edited_raw = page.get("last_edited_time")
    occurred_at: datetime | None = None
    if last_edited_raw:
        try:
            occurred_at = datetime.fromisoformat(
                last_edited_raw.replace("Z", "+00:00")
            )
        except ValueError:
            occurred_at = None
    if occurred_at is None:
        occurred_at = datetime.now(tz=timezone.utc)

    actor_id: str | None = None
    edited_by = page.get("last_edited_by") or {}
    if isinstance(edited_by, dict):
        actor_id = edited_by.get("id")

    return {
        "event_type": "page_edited",
        "key": page_id,
        "title": title or "(untitled Notion page)",
        "snippet": None,
        "actor": None,   # Notion's search doesn't return actor display name
        "actor_id": actor_id,
        "occurred_at": occurred_at,
        "raw_ref": {
            "page_id": page_id,
            "url": page.get("url"),
            "last_edited_time": last_edited_raw,
        },
    }


async def notion_poll_loop(interval_sec: int) -> None:
    """Background loop — runs forever until the service shuts down."""
    logger.info("notion_poll_loop_started", interval_sec=interval_sec)
    while True:
        try:
            await poll_all_notion_workspaces()
        except Exception as e:  # noqa: BLE001
            logger.error("notion_poll_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
