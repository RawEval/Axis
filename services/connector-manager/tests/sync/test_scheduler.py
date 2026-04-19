"""Unit tests for the adaptive cadence scheduler.

The scheduler decides per-(user, source) whether enough time has elapsed
to dispatch another freshen. These tests verify the cadence math in
isolation — they do NOT exercise the full scheduler_tick loop (that needs
the real DB + a mocked worker, covered by an integration test below).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from app.sync.scheduler import compute_cadence_state, CadenceState


@freeze_time("2026-04-19T18:30:00+00:00")
def test_active_when_recent_event_within_24h():
    state = compute_cadence_state(
        last_user_query_at=None,
        last_event_at=datetime.now(timezone.utc) - timedelta(hours=2),
        consecutive_fails=0,
    )
    assert state == CadenceState(interval_sec=60, label="active")


@freeze_time("2026-04-19T18:30:00+00:00")
def test_active_when_recent_user_query_within_1h():
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        last_event_at=None,
        consecutive_fails=0,
    )
    assert state.interval_sec == 60
    assert state.label == "active"


@freeze_time("2026-04-19T18:30:00+00:00")
def test_idle_when_neither_recent_query_nor_recent_event():
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(hours=5),
        last_event_at=datetime.now(timezone.utc) - timedelta(days=3),
        consecutive_fails=0,
    )
    assert state == CadenceState(interval_sec=300, label="idle")


@freeze_time("2026-04-19T18:30:00+00:00")
def test_idle_when_both_signals_are_None():
    state = compute_cadence_state(
        last_user_query_at=None, last_event_at=None, consecutive_fails=0,
    )
    assert state.interval_sec == 300
    assert state.label == "idle"


@freeze_time("2026-04-19T18:30:00+00:00")
@pytest.mark.parametrize("fails,expected_sec", [
    (3, 120),
    (4, 240),
    (5, 480),
    (6, 960),
    (7, 1800),
    (10, 1800),  # capped at 30 min
])
def test_backoff_with_exponential_progression_capped_at_30min(fails, expected_sec):
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        last_event_at=None,
        consecutive_fails=fails,
    )
    assert state.interval_sec == expected_sec
    assert state.label == "erroring"


@freeze_time("2026-04-19T18:30:00+00:00")
def test_below_3_fails_uses_normal_active_idle():
    """consecutive_fails of 0/1/2 should NOT trigger backoff — only 3+."""
    for fails in (0, 1, 2):
        state = compute_cadence_state(
            last_user_query_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            last_event_at=None,
            consecutive_fails=fails,
        )
        assert state.label != "erroring", f"fails={fails} should not be erroring"
        assert state.interval_sec == 60  # active path


# ---------------------------------------------------------------------------
# Integration tests for scheduler_tick
# ---------------------------------------------------------------------------

"""Integration test for scheduler_tick — uses a fake SyncWorker so we
don't hit any vendor API. Verifies the dispatch decision against real
connector_sync_state rows."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.sync.base import SyncResult


class _FakeWorker:
    source = "notion"  # reuse notion source so we don't pollute real registry slots
    def __init__(self):
        self.freshen_calls = []

    async def freshen(self, user_id, *, since=None, force=False):
        self.freshen_calls.append(user_id)
        return SyncResult(rows_added=0, status="ok")


async def _seed_user_with_connector(db_pool, user_id, tool="notion"):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES ($1, $2, 'placeholder')",
            user_id, f"{user_id}@test.local",
        )
        await conn.execute(
            """INSERT INTO connectors (id, user_id, project_id, tool_name,
                                       auth_token_encrypted, status)
               VALUES (gen_random_uuid(), $1, NULL, $2, $3, 'connected')""",
            user_id, tool, b"\x00" * 64,
        )


async def _cleanup(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connectors WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)


async def test_scheduler_tick_dispatches_when_never_synced(db_pool):
    """No connector_sync_state row → elapsed = infinity → ALWAYS dispatch."""
    from app.sync import registry as sync_registry
    from app.sync.scheduler import scheduler_tick

    user_id = uuid4()
    await _seed_user_with_connector(db_pool, user_id, tool="notion")
    try:
        fake = _FakeWorker()
        # Replace the registered notion worker temporarily
        original = sync_registry._workers.get("notion")
        sync_registry._workers["notion"] = fake
        try:
            counts = await scheduler_tick(_pool=db_pool)
        finally:
            if original is not None:
                sync_registry._workers["notion"] = original
            else:
                sync_registry._workers.pop("notion", None)

        assert counts["dispatched"] >= 1
        assert user_id in fake.freshen_calls
    finally:
        await _cleanup(db_pool, user_id)


async def test_scheduler_tick_skips_when_recently_synced(db_pool):
    """last_synced_at within the cadence window → skip dispatch."""
    from app.sync import registry as sync_registry
    from app.sync.scheduler import scheduler_tick

    user_id = uuid4()
    await _seed_user_with_connector(db_pool, user_id, tool="notion")
    async with db_pool.acquire() as conn:
        # Synced 10 seconds ago — well within the 60s active cadence
        await conn.execute(
            """INSERT INTO connector_sync_state
               (user_id, source, last_synced_at, last_status, last_event_at, cursor)
               VALUES ($1, 'notion', NOW() - INTERVAL '10 seconds', 'ok',
                       NOW() - INTERVAL '1 hour', '{}'::jsonb)""",
            user_id,
        )
    try:
        fake = _FakeWorker()
        original = sync_registry._workers.get("notion")
        sync_registry._workers["notion"] = fake
        try:
            counts = await scheduler_tick(_pool=db_pool)
        finally:
            if original is not None:
                sync_registry._workers["notion"] = original
            else:
                sync_registry._workers.pop("notion", None)

        assert user_id not in fake.freshen_calls  # this user should have been skipped
    finally:
        await _cleanup(db_pool, user_id)
