"""Tests for connector.github.recent_activity capability.

Seeds a fresh sync_state row and an activity_events row, stubs the freshen
mixin to skip the HTTP call, and verifies the capability returns the seeded
event with a freshness footer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4


async def _seed_user(db_pool, user_id, tz="UTC"):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, timezone)
               VALUES ($1, $2, 'placeholder', $3)""",
            user_id, f"{user_id}@test.local", tz,
        )


async def _cleanup(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)


async def test_returns_seeded_github_event_with_freshness(db_pool, monkeypatch):
    user_id = uuid4()
    await _seed_user(db_pool, user_id)
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO connector_sync_state
                   (user_id, source, last_synced_at, last_status, cursor)
                   VALUES ($1, 'github', NOW(), 'ok', '{}'::jsonb)""",
                user_id,
            )
            await conn.execute(
                """INSERT INTO activity_events
                   (user_id, source, event_type, external_id, title, snippet, occurred_at, raw_ref)
                   VALUES ($1, 'github', 'PushEvent', 'event-abc-123',
                           'alice pushed to alice/myrepo', NULL,
                           NOW() - INTERVAL '2 minutes', '{}'::jsonb)""",
                user_id,
            )

        # Stub the mixin so it sees fresh state and skips the freshen HTTP call
        fake_client = AsyncMock()
        fake_client.sync_state_one.return_value = {
            "source": "github",
            "last_synced_at": datetime.now(timezone.utc),
            "last_status": "ok",
            "last_error": None,
            "last_event_at": None,
        }
        monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

        # Patch app.db.db (used by the capability) to use the test pool
        from app import db as db_module
        monkeypatch.setattr(db_module.db, "_pool", db_pool)

        from app.capabilities.github_recent_activity import CAPABILITY
        result = await CAPABILITY(
            user_id=str(user_id),
            project_id=None,
            org_id=None,
            inputs={"since": "today"},
        )

        assert "1 github" in result.summary.lower() or "found 1" in result.summary.lower()
        assert isinstance(result.content, dict)
        assert "events" in result.content
        assert len(result.content["events"]) == 1
        assert result.content["events"][0]["title"] == "alice pushed to alice/myrepo"
        assert "freshness" in result.content
        assert result.content["freshness"]["sync_status"] == "ok"
        assert result.content["freshness"]["source"] == "github"
    finally:
        await _cleanup(db_pool, user_id)


async def test_empty_when_no_events_in_window(db_pool, monkeypatch):
    user_id = uuid4()
    await _seed_user(db_pool, user_id)
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO connector_sync_state
                   (user_id, source, last_synced_at, last_status, cursor)
                   VALUES ($1, 'github', NOW(), 'ok', '{}'::jsonb)""",
                user_id,
            )

        fake_client = AsyncMock()
        fake_client.sync_state_one.return_value = {
            "source": "github",
            "last_synced_at": datetime.now(timezone.utc),
            "last_status": "ok",
            "last_error": None,
            "last_event_at": None,
        }
        monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

        from app import db as db_module
        monkeypatch.setattr(db_module.db, "_pool", db_pool)

        from app.capabilities.github_recent_activity import CAPABILITY
        result = await CAPABILITY(
            user_id=str(user_id),
            project_id=None,
            org_id=None,
            inputs={"since": "today"},
        )

        assert result.content["events"] == []
        # Empty events but ok freshness — agent can say "I checked GitHub just now, no activity"
        assert result.content["freshness"]["sync_status"] == "ok"
    finally:
        await _cleanup(db_pool, user_id)
