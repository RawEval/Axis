"""Base connector protocol. All connectors implement this interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Connector(ABC):
    tool_name: str
    supports_write: bool = False

    @abstractmethod
    async def index(self, user_id: str, since: str | None = None) -> list[dict[str, Any]]:
        """Pull all (or incremental) content into the vector store."""

    @abstractmethod
    async def listen(self, user_id: str) -> None:
        """Subscribe to real-time updates (webhook/Pub/Sub/polling)."""

    @abstractmethod
    async def query(self, user_id: str, query: str) -> list[dict[str, Any]]:
        """Answer a specific structured question."""

    async def write(self, user_id: str, action: dict[str, Any]) -> dict[str, Any]:
        """Push an action back. Override if supports_write = True."""
        raise NotImplementedError(f"{self.tool_name} does not support writes")
