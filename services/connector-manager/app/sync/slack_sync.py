"""Slack background sync — indexes channel messages into connector_index.

For each connected Slack workspace:
1. Lists all joined channels
2. Pulls recent history from each channel (last 7 days)
3. Upserts messages into connector_index with full text

This makes "where was X discussed" searches instant — Postgres FTS
across all indexed messages instead of paginating through each channel.

The Events API webhook (already live) handles real-time NEW messages.
This sync fills in the backlog so the index is complete.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from axis_common import get_logger

from app.db import db
from app.repositories.connectors import ConnectorsRepository
from app.repositories.index import ConnectorIndexRepository
from app.security import decrypt_token

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from slack.src.client import SlackClient  # noqa: E402

logger = get_logger(__name__)


async def sync_all_slack_workspaces() -> dict[str, int]:
    conn_repo = ConnectorsRepository(db.raw)
    index_repo = ConnectorIndexRepository(db.raw)
    connectors = await conn_repo.list_connected(tool="slack")

    total_indexed = 0
    total_failed = 0

    for row in connectors:
        try:
            access_token = decrypt_token(row["auth_token_encrypted"])
        except Exception as e:  # noqa: BLE001
            logger.warning("slack_sync_decrypt_failed", error=str(e))
            total_failed += 1
            continue

        client = SlackClient(access_token=access_token)
        user_id = str(row["user_id"])
        project_id = str(row["project_id"]) if row.get("project_id") else None

        try:
            indexed = await _sync_one_workspace(client, index_repo, user_id, project_id)
            total_indexed += indexed
        except Exception as e:  # noqa: BLE001
            logger.warning("slack_sync_workspace_failed", user_id=user_id, error=str(e))
            total_failed += 1

        await conn_repo.touch_last_sync(str(row["id"]))

    logger.info("slack_sync_tick", connectors=len(connectors), indexed=total_indexed, failed=total_failed)
    return {"connectors": len(connectors), "indexed": total_indexed, "failed": total_failed}


async def _sync_one_workspace(
    client: SlackClient,
    index_repo: ConnectorIndexRepository,
    user_id: str,
    project_id: str | None,
) -> int:
    indexed = 0
    # Only sync last 7 days to keep initial sync fast
    oldest = str((datetime.now(tz=timezone.utc) - timedelta(days=7)).timestamp())

    try:
        channels = await client.list_channels(limit=50)
    except Exception as e:  # noqa: BLE001
        logger.warning("slack_sync_channels_failed", error=str(e))
        return 0

    for ch in channels:
        ch_id = ch.get("id")
        ch_name = ch.get("name") or ch_id
        if not ch_id:
            continue

        try:
            messages = await client.channel_history(ch_id, limit=100, oldest=oldest)
        except Exception:  # noqa: BLE001
            continue

        for msg in messages:
            text = msg.get("text") or ""
            if not text.strip():
                continue
            ts = msg.get("ts") or ""
            resource_id = f"{ch_id}:{ts}"

            occurred_at: datetime | None = None
            try:
                occurred_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            except (ValueError, TypeError):
                pass

            await index_repo.upsert(
                user_id=user_id,
                project_id=project_id,
                tool="slack",
                resource_type="message",
                resource_id=resource_id,
                title=f"#{ch_name}",
                body=text[:5000],
                url=None,
                author=msg.get("user"),
                occurred_at=occurred_at,
                metadata={"channel_id": ch_id, "thread_ts": msg.get("thread_ts")},
            )
            indexed += 1

    return indexed


async def slack_sync_loop(interval_sec: int) -> None:
    logger.info("slack_sync_loop_started", interval_sec=interval_sec)
    await asyncio.sleep(30)
    while True:
        try:
            await sync_all_slack_workspaces()
        except Exception as e:  # noqa: BLE001
            logger.error("slack_sync_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
