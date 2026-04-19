"""End-to-end tests for GDriveSyncWorker — mocks Drive API via respx,
hits the real Postgres via the session-scoped db_pool fixture."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
import respx
from httpx import Response

DRIVE = "https://www.googleapis.com/drive/v3/files"


@pytest.fixture
def fake_gdrive_file():
    return {
        "id": "file-abc",
        "name": "Q3 Plan.docx",
        "mimeType": "application/vnd.google-apps.document",
        "modifiedTime": "2026-04-19T18:25:00.000Z",
        "webViewLink": "https://docs.google.com/document/d/file-abc",
        "lastModifyingUser": {
            "displayName": "Alice Smith",
            "emailAddress": "alice@example.com",
        },
    }


async def _seed_gdrive_connector(db_pool, user_id):
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
            VALUES (gen_random_uuid(), $1, NULL, 'gdrive', $2, 'connected')
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
async def test_freshen_writes_activity_event_and_records_success(db_pool, fake_gdrive_file):
    from app.sync.gdrive import GDriveSyncWorker

    user_id = uuid4()
    await _seed_gdrive_connector(db_pool, user_id)
    try:
        respx.get(DRIVE).mock(
            return_value=Response(200, json={"files": [fake_gdrive_file]})
        )

        with patch("app.sync.gdrive.decrypt_token", return_value="ya29-dummy"):
            result = await GDriveSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "ok"
        assert result.rows_added == 1

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id, title, source FROM activity_events "
                "WHERE user_id = $1 AND source = 'gdrive'", user_id,
            )
            assert len(events) == 1
            assert events[0]["external_id"] == "file-abc"
            assert events[0]["title"] == "Q3 Plan.docx"

            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'gdrive'", user_id,
            )
            assert state["last_status"] == "ok"
            assert state["consecutive_fails"] == 0
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_records_auth_failed_on_401(db_pool):
    from app.sync.gdrive import GDriveSyncWorker

    user_id = uuid4()
    await _seed_gdrive_connector(db_pool, user_id)
    try:
        respx.get(DRIVE).mock(
            return_value=Response(401, json={"error": "invalid_credentials"})
        )
        with patch("app.sync.gdrive.decrypt_token", return_value="ya29-bad"):
            result = await GDriveSyncWorker().freshen(user_id, _pool=db_pool)

        assert result.status == "auth_failed"
        assert result.rows_added == 0

        async with db_pool.acquire() as conn:
            state = await conn.fetchrow(
                "SELECT last_status, consecutive_fails FROM connector_sync_state "
                "WHERE user_id = $1 AND source = 'gdrive'", user_id,
            )
            assert state["last_status"] == "auth_failed"
            assert state["consecutive_fails"] == 1
    finally:
        await _cleanup(db_pool, user_id)


@respx.mock
async def test_freshen_is_idempotent_on_repeated_call(db_pool, fake_gdrive_file):
    from app.sync.gdrive import GDriveSyncWorker

    user_id = uuid4()
    await _seed_gdrive_connector(db_pool, user_id)
    try:
        respx.get(DRIVE).mock(
            return_value=Response(200, json={"files": [fake_gdrive_file]})
        )

        with patch("app.sync.gdrive.decrypt_token", return_value="ya29-t"):
            await GDriveSyncWorker().freshen(user_id, _pool=db_pool)
            await GDriveSyncWorker().freshen(user_id, _pool=db_pool)

        async with db_pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT external_id FROM activity_events "
                "WHERE user_id = $1 AND source = 'gdrive'", user_id,
            )
            assert len(events) == 1  # idempotent
    finally:
        await _cleanup(db_pool, user_id)


async def test_freshen_no_op_when_no_connector(db_pool):
    """User with no GDrive connector → freshen returns ok with 0 rows."""
    from app.sync.gdrive import GDriveSyncWorker

    user_id = uuid4()  # no connector inserted
    result = await GDriveSyncWorker().freshen(user_id, _pool=db_pool)
    assert result.status == "ok"
    assert result.rows_added == 0
