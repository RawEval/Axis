"""unanswered_message signal detector (ADR 007 §"Signal detectors").

Scans recent Slack mentions that the user hasn't replied to and emits a
proactive_surfaces row per stale thread. Phase 1 heuristic:

    candidate = Slack mention OR DM addressed to user
    stale     = occurred_at older than STALE_THRESHOLD_HOURS
    unanswered = no subsequent slack message from the same user in the
                 same channel after the mention (proxy for "no reply")

The proxy is imperfect — a Slack reply in a thread won't count unless the
user's response message is itself indexed in ``activity_events``. That's
fine for Phase 1 because the firehose ingests the user's own messages
too. Session 5 refines this with real thread-reply tracking.

Dedupes against existing pending surfaces keyed on
``proposed_action->>'event_id'`` so re-running the detector is safe.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
from axis_common import get_logger

from app.proactive.relevance import RelevanceContext, score_event

logger = get_logger(__name__)

STALE_THRESHOLD_HOURS = 24
MAX_CANDIDATES_PER_TICK = 20


async def detect_unanswered_messages(
    pool: asyncpg.Pool,
    *,
    priority_keywords: list[str] | None = None,
) -> dict[str, int]:
    """Run the detector over every user. Returns counters for observability."""
    ctx = RelevanceContext(priority_keywords=priority_keywords or [])
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=STALE_THRESHOLD_HOURS)

    created = 0
    skipped = 0
    seen = 0

    async with pool.acquire() as conn:
        # Pull recent Slack mentions — cheap index hit on (user_id, source, occurred_at).
        rows = await conn.fetch(
            """
            SELECT id, user_id, project_id, source, event_type, actor, actor_id,
                   title, snippet, raw_ref, occurred_at
            FROM activity_events
            WHERE source = 'slack'
              AND event_type = 'mention'
              AND occurred_at < $1
              AND occurred_at > NOW() - INTERVAL '7 days'
            ORDER BY occurred_at DESC
            LIMIT $2
            """,
            cutoff,
            MAX_CANDIDATES_PER_TICK,
        )

        for row in rows:
            seen += 1
            event = dict(row)
            user_id = str(event["user_id"])

            # asyncpg returns jsonb as a raw JSON string, not a dict.
            raw_ref = event["raw_ref"]
            if isinstance(raw_ref, str):
                try:
                    raw_ref = json.loads(raw_ref)
                except (ValueError, TypeError):
                    raw_ref = {}
            raw_ref = raw_ref or {}

            # Replied proxy: any Slack event with the same channel, from the
            # same user, after the mention. ``actor`` holds the original
            # mentioner; we check if the _Axis user_ posted anything in the
            # channel after. Phase 1 shortcut: any later slack row in the
            # same channel counts as a reply.
            channel = raw_ref.get("channel")
            if not channel:
                skipped += 1
                continue
            replied = await conn.fetchval(
                """
                SELECT 1 FROM activity_events
                WHERE user_id = $1::uuid
                  AND source = 'slack'
                  AND raw_ref->>'channel' = $2
                  AND occurred_at > $3
                LIMIT 1
                """,
                user_id,
                channel,
                event["occurred_at"],
            )
            if replied:
                skipped += 1
                continue

            # Dedup: existing pending surface for this event_id? skip.
            existing = await conn.fetchval(
                """
                SELECT 1 FROM proactive_surfaces
                WHERE user_id = $1::uuid
                  AND signal_type = 'unanswered_message'
                  AND proposed_action->>'event_id' = $2
                  AND status = 'pending'
                LIMIT 1
                """,
                user_id,
                str(event["id"]),
            )
            if existing:
                skipped += 1
                continue

            score = score_event(event, ctx)
            proposed_action = {
                "event_id": str(event["id"]),
                "channel": channel,
                "open_url": raw_ref.get("permalink"),
                "suggested": "Draft a reply or mark read",
            }
            title = f"Unanswered mention in #{channel}"
            snippet = event.get("snippet")

            await conn.execute(
                """
                INSERT INTO proactive_surfaces
                    (user_id, project_id, signal_type, title,
                     context_snippet, confidence_score, proposed_action, status)
                VALUES ($1::uuid, $2::uuid, 'unanswered_message', $3, $4, $5,
                        $6::jsonb, 'pending')
                """,
                user_id,
                event.get("project_id"),
                title,
                snippet,
                score,
                json.dumps(proposed_action),
            )
            created += 1

    logger.info(
        "unanswered_detector_tick",
        seen=seen,
        created=created,
        skipped=skipped,
    )
    return {"seen": seen, "created": created, "skipped": skipped}
