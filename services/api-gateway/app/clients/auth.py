from __future__ import annotations

from typing import Any

import httpx

from app.clients.base import forward
from app.config import settings


class AuthClient:
    def __init__(self, http: httpx.AsyncClient, *, headers: dict[str, str] | None = None) -> None:
        self._http = http
        self._base = settings.auth_service_url
        self._headers = headers or {}

    async def register(self, email: str, password: str, name: str | None) -> dict[str, Any]:
        return await forward(
            self._http,
            "POST",
            f"{self._base}/register",
            json={"email": email, "password": password, "name": name},
            headers=self._headers,
        )

    async def login(self, email: str, password: str) -> dict[str, Any]:
        return await forward(
            self._http,
            "POST",
            f"{self._base}/login",
            json={"email": email, "password": password},
            headers=self._headers,
        )

    async def me(self, token: str) -> dict[str, Any]:
        return await forward(
            self._http,
            "GET",
            f"{self._base}/me",
            headers={"Authorization": f"Bearer {token}", **self._headers},
        )
