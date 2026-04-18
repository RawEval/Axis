"""Gmail connector — Pub/Sub push notifications."""
from __future__ import annotations

from typing import Any


class GmailConnector:
    tool_name = "gmail"
    supports_write = True

    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        return []

    async def listen(self, user_id: str) -> None:
        # TODO: users.watch for Gmail push via Pub/Sub
        pass

    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        return []

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # Per spec: send requires explicit confirmation ALWAYS
        return {"ok": True, "requires_confirmation": True}
