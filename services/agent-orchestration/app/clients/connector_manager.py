"""httpx client for connector-manager tool endpoints.

All tool calls go through here so the agent-orchestration service never
touches encrypted OAuth tokens directly — connector-manager owns decryption.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class ConnectorManagerClient:
    def __init__(self) -> None:
        self._base = settings.connector_manager_url

    async def _tool_search(
        self,
        *,
        tool: str,
        user_id: str,
        project_id: str,
        query: str,
        limit: int,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            resp = await client.post(
                f"{self._base}/tools/{tool}/search",
                json={
                    "user_id": user_id,
                    "project_id": project_id,
                    "query": query,
                    "limit": limit,
                },
            )
            if resp.status_code == 404:
                return {"error": f"{tool} not connected for this project"}
            if resp.status_code >= 400:
                return {"error": f"connector-manager returned {resp.status_code}"}
            return resp.json()

    async def notion_search(
        self, *, user_id: str, project_id: str, query: str, limit: int = 10
    ) -> dict[str, Any]:
        return await self._tool_search(
            tool="notion",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def slack_search(
        self, *, user_id: str, project_id: str, query: str, limit: int = 20
    ) -> dict[str, Any]:
        return await self._tool_search(
            tool="slack",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def gmail_search(
        self, *, user_id: str, project_id: str, query: str, limit: int = 10
    ) -> dict[str, Any]:
        return await self._tool_search(
            tool="gmail",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def gdrive_search(
        self, *, user_id: str, project_id: str, query: str, limit: int = 10
    ) -> dict[str, Any]:
        return await self._tool_search(
            tool="gdrive",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def github_search(
        self, *, user_id: str, project_id: str, query: str, limit: int = 10
    ) -> dict[str, Any]:
        return await self._tool_search(
            tool="github",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    # ---------- Slack extended ------------------------------------------

    async def slack_channels(
        self, *, user_id: str, project_id: str, limit: int = 100
    ) -> dict[str, Any]:
        return await self._tool_call("slack/channels", user_id=user_id, project_id=project_id, limit=limit)

    async def slack_history(
        self, *, user_id: str, project_id: str, channel_id: str, limit: int = 50,
        oldest: str | None = None, latest: str | None = None,
    ) -> dict[str, Any]:
        return await self._tool_call(
            "slack/history", user_id=user_id, project_id=project_id,
            channel_id=channel_id, limit=limit, oldest=oldest, latest=latest,
        )

    async def slack_thread(
        self, *, user_id: str, project_id: str, channel_id: str, thread_ts: str, limit: int = 100,
    ) -> dict[str, Any]:
        return await self._tool_call(
            "slack/thread", user_id=user_id, project_id=project_id,
            channel_id=channel_id, thread_ts=thread_ts, limit=limit,
        )

    async def slack_user(
        self, *, user_id: str, project_id: str, slack_user_id: str
    ) -> dict[str, Any]:
        return await self._tool_call(
            "slack/user", user_id=user_id, project_id=project_id, slack_user_id=slack_user_id,
        )

    async def slack_post(
        self, *, user_id: str, project_id: str, channel: str, text: str, thread_ts: str | None = None,
    ) -> dict[str, Any]:
        return await self._tool_call(
            "slack/post", user_id=user_id, project_id=project_id,
            channel=channel, text=text, thread_ts=thread_ts,
        )

    async def slack_react(
        self, *, user_id: str, project_id: str, channel: str, timestamp: str, emoji: str,
    ) -> dict[str, Any]:
        return await self._tool_call(
            "slack/react", user_id=user_id, project_id=project_id,
            channel=channel, timestamp=timestamp, emoji=emoji,
        )

    async def index_search(
        self, *, user_id: str, project_id: str | None, query: str,
        tool: str | None = None, limit: int = 20,
    ) -> dict[str, Any]:
        return await self._tool_call(
            "index/search", user_id=user_id, project_id=project_id,
            query=query, tool=tool, limit=limit,
        )

    async def _tool_call(self, path: str, **kwargs: Any) -> dict[str, Any]:
        payload = {k: v for k, v in kwargs.items() if v is not None}
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            resp = await client.post(f"{self._base}/tools/{path}", json=payload)
            if resp.status_code == 404:
                return {"error": f"{path.split('/')[0]} not connected for this project"}
            if resp.status_code >= 400:
                return {"error": f"connector-manager returned {resp.status_code}"}
            return resp.json()

    # ---------- Notion write-path -----------------------------------------

    async def notion_get_blocks(
        self, *, user_id: str, project_id: str, page_id: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            resp = await client.post(
                f"{self._base}/tools/notion/blocks",
                json={
                    "user_id": user_id,
                    "project_id": project_id,
                    "page_id": page_id,
                },
            )
            if resp.status_code == 404:
                return {"error": "notion not connected for this project"}
            if resp.status_code >= 400:
                return {"error": f"connector-manager returned {resp.status_code}"}
            return resp.json()

    # ---------- Gmail write-path -----------------------------------------

    async def gmail_search_raw(
        self, *, user_id: str, project_id: str, query: str, limit: int = 25
    ) -> dict[str, Any]:
        """Raw Gmail search hits with ``payload.headers`` preserved — used
        by the recipient resolver. The normalized ``gmail_search`` flattens
        headers away."""
        return await self._tool_call(
            "gmail/search-raw",
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=limit,
        )

    async def gmail_send(
        self, *, user_id: str, project_id: str, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        return await self._tool_call(
            "gmail/send",
            user_id=user_id,
            project_id=project_id,
            to=to,
            subject=subject,
            body=body,
        )

    async def gmail_draft(
        self, *, user_id: str, project_id: str, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        return await self._tool_call(
            "gmail/draft",
            user_id=user_id,
            project_id=project_id,
            to=to,
            subject=subject,
            body=body,
        )

    async def notion_append(
        self,
        *,
        user_id: str,
        project_id: str,
        page_id: str,
        children: list[dict[str, Any]],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            resp = await client.post(
                f"{self._base}/tools/notion/append",
                json={
                    "user_id": user_id,
                    "project_id": project_id,
                    "page_id": page_id,
                    "children": children,
                },
            )
            if resp.status_code == 404:
                return {"error": "notion not connected for this project"}
            if resp.status_code >= 400:
                return {"error": f"connector-manager returned {resp.status_code}"}
            return resp.json()
