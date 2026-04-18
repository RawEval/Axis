"""Slack connector. Real-time via Events API (spec §07)."""
from __future__ import annotations

from typing import Any


class SlackConnector:
    tool_name = "slack"
    supports_write = True

    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        # TODO: conversations.list + conversations.history for each channel
        return []

    async def listen(self, user_id: str) -> None:
        # TODO: subscribe to Slack Events API
        pass

    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        return []

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # TODO: chat.postMessage / chat.postEphemeral / reactions.add
        return {"ok": True, "action": action}
