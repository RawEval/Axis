"""Shared types for SyncWorker implementations.

Each connector's SyncWorker is a class that implements `freshen(user_id, ...)` —
the cron loop and the on-query freshen path call the same method.
"""
from __future__ import annotations

import httpx
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

SyncStatus = Literal["ok", "auth_failed", "vendor_error", "network_error"]


class SyncResult(BaseModel):
    rows_added: int = 0
    last_event_at: datetime | None = None
    status: SyncStatus = "ok"
    error_message: str | None = None


class SyncWorker(Protocol):
    source: str

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
    ) -> SyncResult: ...


def categorize_error(exc: Exception) -> tuple[SyncStatus, str]:
    """Map a raw exception to (sync_status, short_message).

    Used uniformly by every connector worker so the freshness chip and
    capability responses surface consistent error categories.
    """
    msg = str(exc) or exc.__class__.__name__

    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return "auth_failed", f"{code} {exc.response.reason_phrase}"
        if 500 <= code < 600 or code == 429:
            return "vendor_error", f"{code} {exc.response.reason_phrase}"
        return "vendor_error", f"{code} {exc.response.reason_phrase}"

    if isinstance(exc, httpx.TimeoutException):
        return "network_error", f"timeout: {msg}"
    if isinstance(exc, (httpx.NetworkError, httpx.ConnectError)):
        return "network_error", msg

    return "vendor_error", msg
