"""SlackSyncWorker — pulls recent Slack messages and writes them to
activity_events. Mirrors NotionSyncWorker exactly, swapping vendor specifics.
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

from slack.src.client import SlackClient  # noqa: E402

logger = get_logger(__name__)


class SlackSyncWorker:
    source = "slack"

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

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="slack")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "slack", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = SlackClient(access_token=token)
            try:
                messages = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "slack", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for m in messages:
                mapped = _map_slack_message(m)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
                    source="slack",
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
            user_id, "slack",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _map_slack_message(m: dict[str, Any]) -> dict[str, Any] | None:
    ts = m.get("ts")
    channel_id = m.get("channel_id")
    if not ts or not channel_id:
        return None

    text = m.get("text") or ""
    title = text[:120] if text else "(empty Slack message)"
    snippet = text if len(text) > 120 else None
    external_id = f"{channel_id}:{ts}"

    occurred_at: datetime
    try:
        occurred_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, OSError):
        occurred_at = datetime.now(tz=timezone.utc)

    return {
        "event_type": "message_posted",
        "key": external_id,
        "title": title,
        "snippet": snippet,
        "actor": None,
        "actor_id": m.get("user"),
        "occurred_at": occurred_at,
        "raw_ref": {
            "channel_id": channel_id,
            "channel_name": m.get("channel_name"),
            "ts": ts,
        },
    }


sync_registry.register(SlackSyncWorker())


async def slack_poll_loop_v2(interval_sec: int = 60) -> None:
    """Temporary cron loop — Phase 3 (adaptive scheduler) replaces this.

    For each connected Slack user, run SlackSyncWorker.freshen(). Errors are
    caught per-user so one bad token doesn't kill the loop.
    """
    import asyncio

    logger.info("slack_poll_loop_v2_started", interval_sec=interval_sec)
    worker = SlackSyncWorker()
    while True:
        try:
            conn_repo = ConnectorsRepository(db.raw)
            user_ids = {str(r["user_id"]) for r in await conn_repo.list_connected(tool="slack")}
            for uid in user_ids:
                try:
                    await worker.freshen(UUID(uid))
                except Exception as e:  # noqa: BLE001
                    logger.error("slack_freshen_crashed", user_id=uid, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("slack_poll_v2_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
