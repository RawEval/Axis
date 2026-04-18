"""connector.notion.search — natural-language search over the user's Notion workspace.

Calls connector-manager /tools/notion/search which owns the encrypted
access-token decryption. This capability never sees plaintext tokens —
separation of concerns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


@dataclass
class _NotionSearch:
    name: str = "connector.notion.search"
    description: str = (
        "Search the user's connected Notion workspace by keyword. Returns "
        "pages and database rows that match. Use for prompts like "
        "'find the doc about Q3 planning' or 'what did we write about pricing'."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search Notion for. Empty string returns recent pages.",
                },
                "limit": {
                    "type": "integer",
                    "description": "max results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["query"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        if not project_id:
            return CapabilityResult(
                summary="no active project",
                content=[],
                error="notion search requires an active project",
            )

        client = ConnectorManagerClient()
        try:
            resp = await client.notion_search(
                user_id=user_id,
                project_id=project_id,
                query=inputs.get("query", ""),
                limit=int(inputs.get("limit", 10)),
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="notion search failed",
                content=[],
                error=f"connector.notion.search: {e}",
            )

        if "error" in resp:
            return CapabilityResult(
                summary="notion search error",
                content=[],
                error=str(resp["error"]),
            )

        hits: list[dict[str, Any]] = resp.get("results", [])
        citations = [
            Citation(
                source_type="notion_page",
                provider="notion",
                ref_id=hit.get("id"),
                url=hit.get("url"),
                title=hit.get("title"),
                actor=hit.get("author"),
                excerpt=hit.get("excerpt"),
                occurred_at=hit.get("last_edited_time"),
            )
            for hit in hits
        ]
        return CapabilityResult(
            summary=f"found {len(hits)} Notion pages",
            content=hits,
            citations=citations,
        )


CAPABILITY = _NotionSearch()
