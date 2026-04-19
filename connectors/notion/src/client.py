"""Notion HTTP client — thin wrapper around the Notion REST API.

Uses the decrypted OAuth token (injected at call time). Never stores it.

Docs: https://developers.notion.com/reference
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"


class NotionClient:
    def __init__(self, *, access_token: str, notion_version: str = "2022-06-28") -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        }

    async def search(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{NOTION_API_BASE}/search",
                headers=self._headers,
                json={"query": query, "page_size": limit},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    async def list_recent(
        self,
        *,
        since: "datetime | None" = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return Notion pages sorted by last_edited_time desc, paginated.
        Pages older than `since` (if provided) cause the iteration to stop —
        Notion sorts by edit time descending so once we see one older than
        the cutoff, every subsequent page is also older.
        """
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            while len(pages) < limit:
                body: dict[str, Any] = {
                    "query": "",
                    "page_size": min(100, limit - len(pages)),
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                }
                if cursor:
                    body["start_cursor"] = cursor
                resp = await client.post(
                    f"{NOTION_API_BASE}/search",
                    headers=self._headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                for hit in data.get("results", []):
                    if hit.get("object") != "page":
                        continue
                    if since is not None:
                        edited_str = hit.get("last_edited_time")
                        if edited_str:
                            try:
                                edited = datetime.fromisoformat(
                                    edited_str.replace("Z", "+00:00")
                                )
                                if edited < since:
                                    return pages
                            except (ValueError, TypeError):
                                pass
                    pages.append(hit)
                    if len(pages) >= limit:
                        break
                cursor = data.get("next_cursor")
                if not data.get("has_more") or not cursor:
                    break
        return pages

    async def get_page(self, page_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{NOTION_API_BASE}/pages/{page_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_page_blocks(self, page_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{NOTION_API_BASE}/blocks/{page_id}/children",
                headers=self._headers,
                params={"page_size": 100},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    async def append_blocks(self, page_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
        """Append blocks to a page. This is the core write-back op for §6.5."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{NOTION_API_BASE}/blocks/{page_id}/children",
                headers=self._headers,
                json={"children": children},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_page(
        self,
        *,
        parent_page_id: str | None = None,
        parent_database_id: str | None = None,
        properties: dict[str, Any] | None = None,
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        parent: dict[str, Any]
        if parent_database_id:
            parent = {"database_id": parent_database_id}
        elif parent_page_id:
            parent = {"page_id": parent_page_id}
        else:
            raise ValueError("must specify parent_page_id or parent_database_id")

        payload: dict[str, Any] = {"parent": parent}
        if properties is not None:
            payload["properties"] = properties
        if children is not None:
            payload["children"] = children

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{NOTION_API_BASE}/pages",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


def paragraph_block(text: str) -> dict[str, Any]:
    """Helper: build a Notion paragraph block from plain text."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    }


def heading_block(text: str, level: int = 2) -> dict[str, Any]:
    level = max(1, min(3, level))
    block_type = f"heading_{level}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    }
