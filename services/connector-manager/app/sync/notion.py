"""NotionSyncWorker — pulls recently-edited Notion pages and writes them
to activity_events. Replaces the old notion_poll.py shape with the
SyncWorker Protocol so the cron and the on-query freshen path share code.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.security import decrypt_token
from app.sync import registry as sync_registry
from app.sync.base import SyncResult, categorize_error

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from notion.src.client import NotionClient  # noqa: E402

logger = get_logger(__name__)


class NotionSyncWorker:
    source = "notion"

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
        _pool: object = None,
    ) -> SyncResult:
        pool = _pool or db.raw
        conn_repo = ConnectorsRepository(pool)
        activity_repo = ActivityEventsRepository(pool)
        state_repo = ConnectorSyncStateRepository(pool)

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="notion")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "notion", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = NotionClient(access_token=token)
            try:
                pages = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "notion", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for page in pages:
                mapped = _map_notion_page(page)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
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
                    rows_added += 1
                if newest_event is None or (mapped["occurred_at"] and mapped["occurred_at"] > newest_event):
                    newest_event = mapped["occurred_at"]

        await state_repo.record_success(
            user_id, "notion",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _map_notion_page(page: dict[str, Any]) -> dict[str, Any] | None:
    if page.get("object") != "page":
        return None
    page_id = page.get("id")
    if not page_id:
        return None

    title: str | None = None
    for v in (page.get("properties") or {}).values():
        if isinstance(v, dict) and v.get("type") == "title":
            parts = v.get("title", [])
            if parts:
                title = "".join(p.get("plain_text", "") for p in parts if isinstance(p, dict))
            break

    last_edited_raw = page.get("last_edited_time")
    occurred_at: datetime | None = None
    if last_edited_raw:
        try:
            occurred_at = datetime.fromisoformat(last_edited_raw.replace("Z", "+00:00"))
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
        "actor": None,
        "actor_id": actor_id,
        "occurred_at": occurred_at,
        "raw_ref": {
            "page_id": page_id,
            "url": page.get("url"),
            "last_edited_time": last_edited_raw,
        },
    }


sync_registry.register(NotionSyncWorker())


async def notion_poll_loop_v2(interval_sec: int = 60) -> None:
    """Temporary cron loop — Phase 3 (adaptive scheduler) replaces this.

    For each connected Notion user, run NotionSyncWorker.freshen(). Errors
    are caught per-user so one bad token doesn't kill the loop. The worker
    itself records auth_failed / vendor_error / network_error into
    connector_sync_state — there's nothing we need to log differently here.
    """
    import asyncio

    logger.info("notion_poll_loop_v2_started", interval_sec=interval_sec)
    worker = NotionSyncWorker()
    while True:
        try:
            conn_repo = ConnectorsRepository(db.raw)
            user_ids = {str(r["user_id"]) for r in await conn_repo.list_connected(tool="notion")}
            for uid in user_ids:
                try:
                    await worker.freshen(UUID(uid))
                except Exception as e:  # noqa: BLE001
                    logger.error("notion_freshen_crashed", user_id=uid, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("notion_poll_v2_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
