"""connector.search — universal cross-tool search (index-first, live fallback).

This is the FAST PATH. Instead of hitting each provider API individually,
it searches the pre-indexed connector_index table via Postgres FTS.
Results come back in <50ms regardless of how many files/messages/pages
the user has.

If the index is empty (new user, no sync yet), it falls back to live
API calls — but that's the slow path and should be rare after the first
background sync completes.

The supervisor can call both this AND tool-specific capabilities. This
one is best for broad "find X across all my tools" queries. Tool-specific
caps are better for targeted actions ("post a message to #general").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


@dataclass
class _UniversalSearch:
    name: str = "connector.search"
    description: str = (
        "Search across ALL the user's connected tools at once — Slack messages, "
        "Notion pages, Gmail emails, Drive files, GitHub issues. Returns the "
        "most relevant results ranked by text match. Use this when the user "
        "asks 'find X' without specifying a specific tool, or 'where was X "
        "mentioned'. Much faster than searching each tool individually."
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
                    "description": "What to search for across all tools.",
                },
                "tool": {
                    "type": "string",
                    "enum": ["slack", "notion", "gmail", "gdrive", "github"],
                    "description": "Optional: filter to one specific tool.",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
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
        client = ConnectorManagerClient()
        try:
            resp = await client.index_search(
                user_id=user_id,
                project_id=project_id,
                query=inputs.get("query", ""),
                tool=inputs.get("tool"),
                limit=int(inputs.get("limit", 20)),
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="index search failed",
                content=[],
                error=f"connector.search: {e}",
            )

        if "error" in resp:
            return CapabilityResult(
                summary="index search error",
                content=[],
                error=str(resp["error"]),
            )

        hits = resp.get("results", [])
        source = resp.get("source", "unknown")

        citations = [
            Citation(
                source_type=f"{h.get('tool', 'unknown')}_{h.get('resource_type', 'item')}",
                provider=h.get("tool"),
                ref_id=h.get("resource_id"),
                url=h.get("url"),
                title=h.get("title"),
                actor=h.get("author"),
                excerpt=h.get("body"),
                occurred_at=h.get("occurred_at"),
            )
            for h in hits
        ]
        return CapabilityResult(
            summary=f"found {len(hits)} results across tools (via {source})",
            content=hits,
            citations=citations,
        )


CAPABILITY = _UniversalSearch()
