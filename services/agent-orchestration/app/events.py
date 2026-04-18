"""EventBus — Redis pub/sub for streaming supervisor progress.

Every /run publishes lifecycle events to a per-user channel that the
api-gateway WebSocket handler subscribes to and fans out to the browser.

Channel layout:
    axis:events:{user_id}             per-user firehose (read by /ws)
    axis:events:{user_id}:{action_id} per-run stream (optional replay)

Event schema:
    {
      "type": "task.started" | "step.started" | "step.completed"
            | "permission.request" | "task.completed" | "task.failed",
      "user_id": str,
      "project_id": str | None,
      "action_id": str,
      "task_id": str | None,
      "step_id": str | None,
      "payload": {…},                  # type-specific
      "ts": ISO8601,
    }

The supervisor publishes; nothing subscribes inside agent-orchestration.
Subscription lives in api-gateway's ws.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from axis_common import get_logger

from app.config import settings

logger = get_logger(__name__)

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:  # noqa: BLE001
            pass
        _client = None


def user_channel(user_id: str) -> str:
    return f"axis:events:{user_id}"


async def publish(
    *,
    user_id: str,
    event_type: str,
    project_id: str | None = None,
    action_id: str | None = None,
    task_id: str | None = None,
    step_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    """Fire-and-forget publish. Never raises — the supervisor cannot block
    on stream delivery. Returns the number of subscribers that received it.
    """
    event = {
        "type": event_type,
        "user_id": user_id,
        "project_id": project_id,
        "action_id": action_id,
        "task_id": task_id,
        "step_id": step_id,
        "payload": payload or {},
        "ts": datetime.now(tz=timezone.utc).isoformat(),
    }
    try:
        client = get_client()
        n = await client.publish(user_channel(user_id), json.dumps(event))
        return int(n)
    except Exception as e:  # noqa: BLE001
        logger.warning("event_publish_failed", event_type=event_type, error=str(e))
        return 0
