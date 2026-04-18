"""GitHub connector. MD file write-back is the core use case."""
from __future__ import annotations

from typing import Any


class GitHubConnector:
    tool_name = "github"
    supports_write = True

    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        return []

    async def listen(self, user_id: str) -> None:
        # TODO: register webhook on target repos
        pass

    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        return []

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        # TODO: commit file via contents API; comment on PR/issue
        return {"ok": True}
