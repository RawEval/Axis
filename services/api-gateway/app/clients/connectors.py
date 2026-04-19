from __future__ import annotations

from typing import Any

import httpx

from app.clients.base import forward
from app.config import settings


class ConnectorManagerClient:
    def __init__(self, http: httpx.AsyncClient, *, headers: dict[str, str] | None = None) -> None:
        self._http = http
        self._base = settings.connector_manager_url
        self._headers = headers or {}

    async def oauth_start(
        self, tool: str, *, user_id: str, project_id: str
    ) -> dict[str, Any]:
        return await forward(
            self._http,
            "POST",
            f"{self._base}/oauth/{tool}/start",
            json={"user_id": user_id, "project_id": project_id},
            headers=self._headers,
        )

    async def oauth_callback(self, tool: str, code: str, state: str) -> dict[str, Any]:
        return await forward(
            self._http,
            "GET",
            f"{self._base}/oauth/{tool}/callback",
            params={"code": code, "state": state},
            headers=self._headers,
        )

    async def sync_state(self, *, user_id: str) -> dict[str, Any]:
        return await forward(
            self._http,
            "GET",
            f"{self._base}/connectors/sync-state",
            params={"user_id": user_id},
            headers=self._headers,
        )

    async def freshen(self, *, source: str, user_id: str, force: bool = True) -> dict[str, Any]:
        return await forward(
            self._http,
            "POST",
            f"{self._base}/tools/{source}/freshen",
            json={"user_id": user_id, "force": force},
            headers=self._headers,
        )
