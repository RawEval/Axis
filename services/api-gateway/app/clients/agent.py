from __future__ import annotations

from typing import Any

import httpx

from app.clients.base import forward
from app.config import settings


class AgentOrchestrationClient:
    """Use the LONG http client (120s) — agent runs are slow."""

    def __init__(self, http: httpx.AsyncClient, *, headers: dict[str, str] | None = None) -> None:
        self._http = http
        self._base = settings.agent_orchestration_url
        self._headers = headers

    async def run(
        self,
        *,
        user_id: str,
        prompt: str,
        project_ids: list[str],
        project_scope: str,
        mode: str = "sync",
        time_limit_sec: int | None = None,
        notify_on_complete: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "prompt": prompt,
            "project_ids": project_ids,
            "project_scope": project_scope,
            "mode": mode,
        }
        if time_limit_sec is not None:
            payload["time_limit_sec"] = time_limit_sec
        if not notify_on_complete:
            payload["notify_on_complete"] = False
        return await forward(
            self._http,
            "POST",
            f"{self._base}/run",
            json=payload,
            headers=self._headers,
        )
