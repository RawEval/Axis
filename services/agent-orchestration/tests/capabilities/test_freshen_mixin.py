from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.capabilities._freshen_mixin import FreshenBeforeRead


class _ConcreteCap(FreshenBeforeRead):
    source = "notion"


async def test_recent_sync_skips_freshen_call(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    fresh_state = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=5),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = fresh_state
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    freshness = await cap.ensure_fresh(user_id)

    assert freshness.sync_status == "ok"
    fake_client.freshen.assert_not_called()
    fake_client.sync_state_one.assert_called_once()


async def test_stale_sync_triggers_freshen_call(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    stale = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=120),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    refreshed = {**stale, "last_synced_at": datetime.now(timezone.utc)}

    fake_client = AsyncMock()
    fake_client.sync_state_one.side_effect = [stale, refreshed]
    fake_client.freshen.return_value = {"status": "ok"}
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    await cap.ensure_fresh(user_id)

    fake_client.freshen.assert_called_once_with(source="notion", user_id=str(user_id), force=False)


async def test_freshen_failure_does_not_raise(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    stale = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=120),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = stale
    fake_client.freshen.return_value = {"status": "network_error", "error": "timeout"}
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    freshness = await cap.ensure_fresh(user_id)

    # Should not raise — returns whatever state we have
    assert freshness.source == "notion"
