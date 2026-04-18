"""Thin httpx client for memory-service — retrieve + episodic write."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class MemoryClient:
    def __init__(self) -> None:
        self._base = settings.memory_service_url

    async def retrieve(
        self,
        *,
        user_id: str,
        query: str,
        project_id: str | None = None,
        tier: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{self._base}/retrieve",
                json={
                    "user_id": user_id,
                    "query": query,
                    "project_id": project_id,
                    "tier": tier if tier and tier != "any" else None,
                    "limit": limit,
                },
            )
            if resp.status_code >= 400:
                return []
            data = resp.json()
        return data if isinstance(data, list) else []

    async def write_episodic(
        self,
        *,
        user_id: str,
        project_id: str | None,
        role: str,
        content: str,
        action_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        """Best-effort — memory writes must never block the user."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base}/episodic",
                    json={
                        "user_id": user_id,
                        "project_id": project_id,
                        "role": role,
                        "content": content,
                        "action_id": action_id,
                        "tags": tags or [],
                    },
                )
                if resp.status_code >= 400:
                    return None
                return resp.json().get("id")
        except Exception:  # noqa: BLE001
            return None
