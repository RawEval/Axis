"""GDriveSyncWorker — pulls recently modified Drive files and writes them to
activity_events. Mirrors GmailSyncWorker exactly, swapping vendor specifics.
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

from gdrive.src.client import GDriveClient  # noqa: E402

logger = get_logger(__name__)


class GDriveSyncWorker:
    source = "gdrive"

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

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="gdrive")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "gdrive", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = GDriveClient(access_token=token)
            try:
                files = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "gdrive", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for f in files:
                mapped = _map_gdrive_file(f)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
                    source="gdrive",
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
            user_id, "gdrive",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _map_gdrive_file(file: dict[str, Any]) -> dict[str, Any] | None:
    file_id = file.get("id")
    if not file_id:
        return None

    external_id = file_id
    title = file.get("name") or "(untitled file)"
    snippet = file.get("mimeType")
    actor = file.get("lastModifyingUser", {}).get("displayName")
    actor_id = file.get("lastModifyingUser", {}).get("emailAddress")

    try:
        occurred_at = datetime.fromisoformat(file["modifiedTime"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        occurred_at = datetime.now(tz=timezone.utc)

    return {
        "event_type": "file_modified",
        "key": external_id,
        "title": title,
        "snippet": snippet,
        "actor": actor,
        "actor_id": actor_id,
        "occurred_at": occurred_at,
        "raw_ref": {
            "file_id": file_id,
            "url": file.get("webViewLink"),
            "mime_type": file.get("mimeType"),
        },
    }


sync_registry.register(GDriveSyncWorker())
