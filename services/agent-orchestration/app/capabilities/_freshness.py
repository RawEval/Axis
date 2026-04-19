"""Freshness model used by every connector recent_activity capability.

Returned in CapabilityResult.content under the 'freshness' key so the
agent's prompt can surface honest statements like 'I checked Slack 3 seconds
ago — no activity. Last successful sync was 14:32.'
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SyncStatus = Literal["ok", "stale", "auth_failed", "vendor_error", "network_error", "never"]


class Freshness(BaseModel):
    source: str
    last_synced_at: datetime | None = None
    sync_status: SyncStatus = "never"
    error_message: str | None = None

    @classmethod
    def from_state(cls, source: str, state: dict | None) -> "Freshness":
        if state is None:
            return cls(source=source, sync_status="never")
        return cls(
            source=source,
            last_synced_at=state.get("last_synced_at"),
            sync_status=state.get("last_status", "never"),
            error_message=state.get("last_error"),
        )
