"""Google Drive connector. Docs write-back in P1; Sheets in P2."""
from __future__ import annotations

from typing import Any


class GDriveConnector:
    tool_name = "gdrive"
    supports_write = True

    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        return []

    async def listen(self, user_id: str) -> None:
        pass

    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        return []

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}
