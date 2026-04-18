"""Provider webhooks — Slack Events API (P1), GitHub (P1), Linear (P2).

Every webhook:
  1. Verifies the provider's signature (raw body + secret).
  2. Maps the provider workspace id to one or more Axis (user_id, project_id)
     rows via ConnectorsRepository.find_by_workspace.
  3. Normalizes the event onto ``activity_events`` via the shared repository.

Slack-specific:
  - POST /webhooks/slack receives both ``url_verification`` (used once
    during app configuration) and real events.
  - Signature uses v0 HMAC-SHA256 over ``v0:{timestamp}:{body}`` per spec
    https://api.slack.com/authentication/verifying-requests-from-slack
  - Timestamps older than 5 minutes are rejected to prevent replay.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any

from axis_common import get_logger
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.db import db
from app.proactive.unanswered import detect_unanswered_messages
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.sync.notion_poll import poll_all_notion_workspaces

router = APIRouter()
logger = get_logger(__name__)

_SLACK_MAX_SKEW_SEC = 60 * 5


def _verify_slack_signature(
    *, body: bytes, timestamp: str, signature: str, signing_secret: str
) -> bool:
    if not signing_secret:
        # Dev-mode escape hatch — when the signing secret isn't configured
        # we still accept the webhook but log it loudly so the operator
        # knows they're wide open.
        logger.warning("slack_signing_secret_missing_skipping_verification")
        return True
    try:
        ts_int = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts_int) > _SLACK_MAX_SKEW_SEC:
        return False
    base = f"v0:{timestamp}:".encode() + body
    digest = hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature or "")


@router.post("/webhooks/slack")
async def slack_webhook(
    request: Request,
    x_slack_signature: str | None = Header(None),
    x_slack_request_timestamp: str | None = Header(None),
) -> dict[str, Any]:
    body = await request.body()
    if not _verify_slack_signature(
        body=body,
        timestamp=x_slack_request_timestamp or "",
        signature=x_slack_signature or "",
        signing_secret=settings.slack_signing_secret,
    ):
        raise HTTPException(401, "invalid slack signature")

    payload = await request.json()

    # One-time URL verification handshake — Slack expects the challenge
    # string echoed back as plain JSON.
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    if payload.get("type") != "event_callback":
        # Rate-limit / event-delivery envelope types we don't handle yet.
        return {"ok": True, "ignored": True}

    team_id = payload.get("team_id")
    event = payload.get("event") or {}
    event_type = event.get("type")
    if not team_id or not event_type:
        return {"ok": True, "ignored": True}

    conn_repo = ConnectorsRepository(db.raw)
    matches = await conn_repo.find_by_workspace(tool="slack", workspace_id=team_id)
    if not matches:
        logger.info("slack_webhook_no_connector", team_id=team_id)
        return {"ok": True, "ignored": True, "reason": "no connected workspace"}

    activity_repo = ActivityEventsRepository(db.raw)
    inserted = 0

    for row in matches:
        mapped = _map_slack_event(event)
        if mapped is None:
            continue
        result = await activity_repo.upsert(
            user_id=str(row["user_id"]),
            project_id=str(row["project_id"]) if row.get("project_id") else None,
            source="slack",
            event_type=mapped["event_type"],
            key=mapped["key"],
            title=mapped["title"],
            snippet=mapped.get("snippet"),
            actor=mapped.get("actor"),
            actor_id=mapped.get("actor_id"),
            occurred_at=mapped.get("occurred_at"),
            raw_ref=mapped.get("raw_ref"),
        )
        if result["inserted"]:
            inserted += 1

    logger.info(
        "slack_webhook_ingested",
        team_id=team_id,
        event_type=event_type,
        fanout=len(matches),
        inserted=inserted,
    )
    return {"ok": True, "inserted": inserted, "fanout": len(matches)}


# Manual trigger — useful during local dev so we don't wait 15 minutes
# between poll ticks. Idempotent, safe to hit repeatedly.


@router.post("/sync/notion/run")
async def trigger_notion_poll() -> dict[str, Any]:
    result = await poll_all_notion_workspaces()
    return {"ok": True, **result}


@router.post("/proactive/detect/unanswered")
async def trigger_unanswered_detector() -> dict[str, Any]:
    result = await detect_unanswered_messages(db.raw)
    return {"ok": True, **result}


def _map_slack_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize the event_types we care about onto our activity row shape.

    We capture ``message`` and ``app_mention`` today — enough to populate
    the activity feed and drive the unanswered-message detector.
    """
    etype = event.get("type")
    if etype not in {"message", "app_mention"}:
        return None

    if event.get("subtype") in {"message_changed", "message_deleted", "bot_message"}:
        return None

    channel = event.get("channel") or ""
    ts = event.get("ts") or ""
    if not channel or not ts:
        return None

    text = (event.get("text") or "").strip()
    snippet = text[:300] if text else None
    title = (
        f"Slack mention in #{channel}"
        if etype == "app_mention"
        else f"Slack message in #{channel}"
    )

    occurred_at: datetime | None = None
    try:
        occurred_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except ValueError:
        occurred_at = None

    return {
        "event_type": "mention" if etype == "app_mention" else "message",
        "key": f"{channel}:{ts}",
        "title": title,
        "snippet": snippet,
        "actor": event.get("user"),      # provider user id; display name needs users.info
        "actor_id": event.get("user"),
        "occurred_at": occurred_at,
        "raw_ref": {"channel": channel, "ts": ts},
    }
