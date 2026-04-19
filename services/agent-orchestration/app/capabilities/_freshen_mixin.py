"""Mixin for capabilities that read from activity_events.

Before reading, check connector_sync_state. If the source's data is older
than `stale_after`, fire a synchronous /tools/<src>/freshen call (bounded
8s) so the read sees fresh data. If the freshen times out, return what we
have with stale freshness rather than blocking the user.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.capabilities._freshness import Freshness
from app.clients.connector_manager import ConnectorManagerClient

_client = ConnectorManagerClient()


class FreshenBeforeRead:
    source: str
    stale_after: timedelta = timedelta(seconds=60)

    async def ensure_fresh(self, user_id: UUID) -> Freshness:
        state = await _client.sync_state_one(user_id=str(user_id), source=self.source)
        if (
            state
            and state.get("last_status") == "ok"
            and state.get("last_synced_at")
            and (datetime.now(timezone.utc) - state["last_synced_at"]) < self.stale_after
        ):
            return Freshness.from_state(self.source, state)

        # Stale — fire a non-forced freshen (the route also checks staleness
        # server-side, so concurrent requests don't hammer the vendor).
        await _client.freshen(source=self.source, user_id=str(user_id), force=False)
        state = await _client.sync_state_one(user_id=str(user_id), source=self.source)
        return Freshness.from_state(self.source, state)
