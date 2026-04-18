"""Notion connector — MCP-compatible."""
from __future__ import annotations

from typing import Any


class NotionConnector:
    tool_name = "notion"
    supports_write = True

    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        # TODO: search + pages.retrieve + blocks.children.list
        return []

    async def listen(self, user_id: str) -> None:
        # Polling every 15 minutes per spec §6.1
        pass

    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        return []

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}
