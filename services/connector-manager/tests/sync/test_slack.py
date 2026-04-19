"""End-to-end tests for SlackSyncWorker — mocks Slack API via respx,
hits the real Postgres via the session-scoped db_pool fixture."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
import respx
from httpx import Response


@pytest.fixture
def fake_slack_message():
    return {
        "ts": "1745020800.000100",
        "text": "Hello from the test suite",
        "user": "U123ABC",
        "channel_id": "C1",
        "channel_name": "general",
    }


async def _seed_slack_connector(db_pool, user_id):
    """Insert a user + connector row so the worker has something to sync."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, email_verified)
            VALUES ($1, $2, false)
            ON CONFLICT (id) DO NOTHING
            """,
            user_id, f"test-{user_id}@example.com",
        )
        await conn.execute(
            """
            INSERT INTO connectors (id, user_id, project_id, tool_name,
                                    auth_token_encrypted, status)
            VALUES (gen_random_uuid(), $1, NULL, 'slack', $2, 'connected')
            """,
            user_id, b"\x00" * 64,
        )


async def _cleanup(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connectors WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)


@respx.mock
async def test_freshen_writes_activity_event_and_records_success(db_pool, fake_slack_message):
    from app.sync.slack import SlackSyncWorker

    user_id = uuid4()
    await _seed_slack_connector(db_pool, user_id)
    try:
        respx.post("https://slack.com/api/conversations.list").mock(
            return_value=Response(200, json={
                "ok": True,
                "channels": [{"id": "C1", "name": "general"}],
                "response_metadata": {},
            })
        )
        respx.post("https://slack.com/api/conversations.history").mock(
            return_value=Response(200, json={
                "ok": True,
                "messages": [fake_slack_message],
            })
        )

        with patch("app.sync.slack.decrypt_token", return_value="xoxb-dummy"):
            result = await SlackSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "ok"
        assert result.rows_added == 1

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id, title, source FROM activity_events "
                "WHERE user_id = $1 AND source = 'slack'", user_id,
            )
            assert len(events) == 1
            assert events[0]["external_id"] == "C1:1745020800.000100"
            assert events[0]["title"] == "Hello from the test suite"

            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'slack'", user_id,
            )
            assert state["last_status"] == "ok"
            assert state["consecutive_fails"] == 0
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_records_auth_failed_on_401(db_pool):
    from app.sync.slack import SlackSyncWorker

    user_id = uuid4()
    await _seed_slack_connector(db_pool, user_id)
    try:
        respx.post("https://slack.com/api/conversations.list").mock(
            return_value=Response(401, json={"error": "invalid_auth"})
        )
        with patch("app.sync.slack.decrypt_token", return_value="xoxb-bad"):
            result = await SlackSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "auth_failed"
        assert result.rows_added == 0

        async with db_pool.acquire() as conn:
            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'slack'", user_id,
            )
            assert state["last_status"] == "auth_failed"
            assert state["consecutive_fails"] == 1
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_is_idempotent_on_repeated_call(db_pool, fake_slack_message):
    from app.sync.slack import SlackSyncWorker

    user_id = uuid4()
    await _seed_slack_connector(db_pool, user_id)
    try:
        respx.post("https://slack.com/api/conversations.list").mock(
            return_value=Response(200, json={
                "ok": True,
                "channels": [{"id": "C1", "name": "general"}],
                "response_metadata": {},
            })
        )
        respx.post("https://slack.com/api/conversations.history").mock(
            return_value=Response(200, json={
                "ok": True,
                "messages": [fake_slack_message],
            })
        )

        with patch("app.sync.slack.decrypt_token", return_value="xoxb-t"):
            await SlackSyncWorker().freshen(user_id, _pool=db_pool)
            await SlackSyncWorker().freshen(user_id, _pool=db_pool)

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id FROM activity_events "
                "WHERE user_id = $1 AND source = 'slack'", user_id,
            )
            assert len(events) == 1  # idempotent
    finally:
        await _cleanup(db_pool, user_id)


async def test_freshen_no_op_when_no_connector(db_pool):
    """User with no Slack connector → freshen returns ok with 0 rows."""
    from app.sync.slack import SlackSyncWorker

    user_id = uuid4()  # no connector inserted
    result = await SlackSyncWorker().freshen(user_id, _pool=db_pool)
    assert result.status == "ok"
    assert result.rows_added == 0
