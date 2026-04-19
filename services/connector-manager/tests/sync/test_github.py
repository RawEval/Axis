"""End-to-end tests for GitHubSyncWorker — mocks GitHub API via respx,
hits the real Postgres via the session-scoped db_pool fixture."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
import respx
from httpx import Response

GH_USER = "https://api.github.com/user"
GH_EVENTS = "https://api.github.com/users/alice/events"


@pytest.fixture
def fake_github_event():
    return {
        "id": "event-abc-123",
        "type": "PushEvent",
        "created_at": "2026-04-19T18:25:00Z",
        "actor": {"login": "alice"},
        "repo": {"name": "alice/myrepo"},
        "payload": {"commits": []},
    }


async def _seed_github_connector(db_pool, user_id):
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
            VALUES (gen_random_uuid(), $1, NULL, 'github', $2, 'connected')
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
async def test_freshen_writes_activity_event_and_records_success(db_pool, fake_github_event):
    from app.sync.github import GitHubSyncWorker

    user_id = uuid4()
    await _seed_github_connector(db_pool, user_id)
    try:
        respx.get(GH_USER).mock(return_value=Response(200, json={"login": "alice"}))
        respx.get(GH_EVENTS).mock(
            return_value=Response(200, json=[fake_github_event])
        )

        with patch("app.sync.github.decrypt_token", return_value="ghp-dummy"):
            result = await GitHubSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "ok"
        assert result.rows_added == 1

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id, title, source FROM activity_events "
                "WHERE user_id = $1 AND source = 'github'", user_id,
            )
            assert len(events) == 1
            assert events[0]["external_id"] == "event-abc-123"
            assert "alice" in events[0]["title"]

            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'github'", user_id,
            )
            assert state["last_status"] == "ok"
            assert state["consecutive_fails"] == 0
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_records_auth_failed_on_401(db_pool):
    from app.sync.github import GitHubSyncWorker

    user_id = uuid4()
    await _seed_github_connector(db_pool, user_id)
    try:
        respx.get(GH_USER).mock(
            return_value=Response(401, json={"message": "Bad credentials"})
        )
        with patch("app.sync.github.decrypt_token", return_value="ghp-bad"):
            result = await GitHubSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "auth_failed"
        assert result.rows_added == 0

        async with db_pool.acquire() as conn:
            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'github'", user_id,
            )
            assert state["last_status"] == "auth_failed"
            assert state["consecutive_fails"] == 1
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_is_idempotent_on_repeated_call(db_pool, fake_github_event):
    from app.sync.github import GitHubSyncWorker

    user_id = uuid4()
    await _seed_github_connector(db_pool, user_id)
    try:
        respx.get(GH_USER).mock(return_value=Response(200, json={"login": "alice"}))
        respx.get(GH_EVENTS).mock(
            return_value=Response(200, json=[fake_github_event])
        )

        with patch("app.sync.github.decrypt_token", return_value="ghp-t"):
            await GitHubSyncWorker().freshen(user_id, _pool=db_pool)
            await GitHubSyncWorker().freshen(user_id, _pool=db_pool)

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id FROM activity_events "
                "WHERE user_id = $1 AND source = 'github'", user_id,
            )
            assert len(events) == 1  # idempotent
    finally:
        await _cleanup(db_pool, user_id)


async def test_freshen_no_op_when_no_connector(db_pool):
    """User with no GitHub connector → freshen returns ok with 0 rows."""
    from app.sync.github import GitHubSyncWorker

    user_id = uuid4()  # no connector inserted
    result = await GitHubSyncWorker().freshen(user_id, _pool=db_pool)
    assert result.status == "ok"
    assert result.rows_added == 0
