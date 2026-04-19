"""Regression test for the original 2026-04-19 Notion staleness bug.

User reported: edited a Notion page, asked 'what happened in my Notion today?'
10 minutes later, got 'no activity found.' Audit found the activity feed was
read-from-stale-cache + swallowed errors + only Notion had any sync at all.

This test simulates the exact scenario end-to-end at the capability layer:
1. User exists with timezone='Asia/Kolkata' (the user's actual TZ)
2. NotionSyncWorker has already ingested an edit from 10 minutes ago into
   activity_events (this is what the worker does in production)
3. Connector_sync_state shows the source is 'ok' and was synced just now
   (so FreshenBeforeRead doesn't trigger another HTTP call)
4. User asks 'what happened in my Notion today?' via the recent_activity
   capability → assert the edit is in the answer.

If this test fails, the bug has regressed — somebody broke the freshness
chain or the timezone math or the activity_events read path.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4


async def _seed_user_with_kolkata_tz(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, timezone)
               VALUES ($1, $2, 'placeholder', 'Asia/Kolkata')""",
            user_id, f"{user_id}@test.local",
        )


async def _cleanup(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)


async def test_notion_edit_10min_ago_is_visible_in_recent_activity(db_pool, monkeypatch):
    """The bug: ask 'what happened in Notion today' after a recent edit, get
    'no activity found.' The fix: NotionSyncWorker writes the edit to
    activity_events, and recent_activity reads it back honestly."""
    user_id = uuid4()
    await _seed_user_with_kolkata_tz(db_pool, user_id)
    try:
        # Simulate what NotionSyncWorker does in production: writes the page
        # edit + records sync success
        edit_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO activity_events
                   (user_id, source, event_type, external_id, title, occurred_at, raw_ref)
                   VALUES ($1, 'notion', 'page_edited', 'edited-page',
                           'My recent edit', $2, '{}'::jsonb)""",
                user_id, edit_time,
            )
            await conn.execute(
                """INSERT INTO connector_sync_state
                   (user_id, source, last_synced_at, last_status, cursor)
                   VALUES ($1, 'notion', NOW(), 'ok', '{}'::jsonb)""",
                user_id,
            )

        # Stub the freshen mixin so it sees fresh state and skips the HTTP call.
        # In production this would also have been fresh because NotionSyncWorker
        # just ran via the 60s lifespan loop.
        fake_client = AsyncMock()
        fake_client.sync_state_one.return_value = {
            "source": "notion",
            "last_synced_at": datetime.now(timezone.utc),
            "last_status": "ok",
            "last_error": None,
            "last_event_at": edit_time,
        }
        monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

        # Patch app.db.db._pool to use the test pool
        from app import db as db_module
        monkeypatch.setattr(db_module.db, "_pool", db_pool)

        # The exact prompt the user asked, routed to the right capability
        from app.capabilities.notion_recent_activity import CAPABILITY
        result = await CAPABILITY(
            user_id=str(user_id), project_id=None, org_id=None,
            inputs={"since": "today"},
        )

        # The fix: the edit IS visible
        events = result.content["events"]
        titles = [e["title"] for e in events]
        assert "My recent edit" in titles, (
            "Regression — the original Apr 19 bug is back: a Notion page "
            "edited 10 minutes ago must be visible when the user asks "
            "'what happened in Notion today?'. Got events with titles: "
            f"{titles!r}. The freshness chain or TZ math or read path is broken."
        )

        # And the answer comes with honest freshness metadata
        freshness = result.content["freshness"]
        assert freshness["sync_status"] == "ok", (
            f"Expected sync_status='ok', got {freshness}. The agent should "
            "be able to say 'I checked Notion just now — here's what changed' "
            "instead of saying 'no activity found' when sync actually worked."
        )
    finally:
        await _cleanup(db_pool, user_id)
