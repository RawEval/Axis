from __future__ import annotations

from uuid import uuid4

import pytest

from app.repositories.sync_state import ConnectorSyncStateRepository


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(db_pool):
    repo = ConnectorSyncStateRepository(db_pool)
    user_id = uuid4()

    # First call → INSERT
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={"foo": "bar"})
    state = await repo.get(user_id, "notion")
    assert state is not None
    assert state["last_status"] == "ok"
    assert state["consecutive_fails"] == 0
    assert state["cursor"] == {"foo": "bar"}

    # Failure → UPDATE, increments consecutive_fails
    await repo.record_failure(user_id, "notion", status="vendor_error", error="500 Server")
    state = await repo.get(user_id, "notion")
    assert state["last_status"] == "vendor_error"
    assert state["consecutive_fails"] == 1
    assert state["last_error"] == "500 Server"

    # Success resets counter
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={"foo": "baz"})
    state = await repo.get(user_id, "notion")
    assert state["consecutive_fails"] == 0
    assert state["cursor"] == {"foo": "baz"}

    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)


@pytest.mark.asyncio
async def test_list_for_user(db_pool):
    repo = ConnectorSyncStateRepository(db_pool)
    user_id = uuid4()
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={})
    await repo.record_success(user_id, "slack", last_event_at=None, cursor={})

    rows = await repo.list_for_user(user_id)
    sources = {r["source"] for r in rows}
    assert sources == {"notion", "slack"}

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)


@pytest.mark.asyncio
async def test_get_returns_none_for_unknown_pair(db_pool):
    repo = ConnectorSyncStateRepository(db_pool)
    state = await repo.get(uuid4(), "notion")
    assert state is None
