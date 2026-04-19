"""GmailSyncWorker — pulls recent Gmail messages and writes them to
activity_events. Mirrors SlackSyncWorker exactly, swapping vendor specifics.
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

from gmail.src.client import GmailClient  # noqa: E402

logger = get_logger(__name__)


class GmailSyncWorker:
    source = "gmail"

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

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="gmail")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "gmail", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = GmailClient(access_token=token)
            try:
                messages = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "gmail", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for m in messages:
                mapped = _map_gmail_message(m)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
                    source="gmail",
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
            user_id, "gmail",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _header(headers: list[dict[str, Any]], name: str) -> str | None:
    if not isinstance(headers, list):
        return None
    for h in headers:
        if isinstance(h, dict) and h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _map_gmail_message(message: dict[str, Any]) -> dict[str, Any] | None:
    msg_id = message.get("id")
    if not msg_id:
        return None

    headers = message.get("payload", {}).get("headers", [])
    subject = _header(headers, "Subject") or "(no subject)"
    from_header = _header(headers, "From")

    snippet = message.get("snippet")
    external_id = msg_id

    internal_date = message.get("internalDate")
    try:
        occurred_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        occurred_at = datetime.now(tz=timezone.utc)

    return {
        "event_type": "email_received",
        "key": external_id,
        "title": subject,
        "snippet": snippet,
        "actor": None,
        "actor_id": from_header,
        "occurred_at": occurred_at,
        "raw_ref": {
            "message_id": msg_id,
            "thread_id": message.get("threadId"),
            "from": from_header,
        },
    }


sync_registry.register(GmailSyncWorker())


async def gmail_poll_loop_v2(interval_sec: int = 60) -> None:
    """Temporary cron loop — Phase 3 (adaptive scheduler) replaces this.

    For each connected Gmail user, run GmailSyncWorker.freshen(). Errors are
    caught per-user so one bad token doesn't kill the loop.
    """
    import asyncio

    logger.info("gmail_poll_loop_v2_started", interval_sec=interval_sec)
    worker = GmailSyncWorker()
    while True:
        try:
            conn_repo = ConnectorsRepository(db.raw)
            user_ids = {str(r["user_id"]) for r in await conn_repo.list_connected(tool="gmail")}
            for uid in user_ids:
                try:
                    await worker.freshen(UUID(uid))
                except Exception as e:  # noqa: BLE001
                    logger.error("gmail_freshen_crashed", user_id=uid, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("gmail_poll_v2_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
