"""connector.gmail.search — natural-language search over the user's Gmail inbox.

Calls connector-manager /tools/gmail/search which owns token decryption.
The agent never sees plaintext Google OAuth tokens. Sends (``gmail.send``)
are ALWAYS gated and live in a different write-action flow (spec §6.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


@dataclass
class _GmailSearch:
    name: str = "connector.gmail.search"
    description: str = (
        "Search the user's connected Gmail inbox using Gmail search syntax "
        "(from:, subject:, after:, etc.) or a plain keyword. Returns recent "
        "messages matching the query with subject, sender, and a snippet. "
        "Use for prompts like 'find the email from Acme about the contract' "
        "or 'what did Priya send last week'."
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
                    "description": (
                        "Gmail search query. Supports Gmail operators like "
                        "from:, subject:, after:, before:, has:attachment."
                    ),
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
                error="gmail search requires an active project",
            )

        client = ConnectorManagerClient()
        try:
            resp = await client.gmail_search(
                user_id=user_id,
                project_id=project_id,
                query=inputs.get("query", ""),
                limit=int(inputs.get("limit", 10)),
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="gmail search failed",
                content=[],
                error=f"connector.gmail.search: {e}",
            )

        if "error" in resp:
            return CapabilityResult(
                summary="gmail search error",
                content=[],
                error=str(resp["error"]),
            )

        hits: list[dict[str, Any]] = resp.get("results", [])
        citations = [
            Citation(
                source_type="gmail_thread",
                provider="gmail",
                ref_id=hit.get("id"),
                url=hit.get("url"),
                title=hit.get("title"),
                actor=hit.get("author"),
                excerpt=hit.get("excerpt"),
                occurred_at=hit.get("received_at"),
            )
            for hit in hits
        ]
        return CapabilityResult(
            summary=f"found {len(hits)} Gmail messages",
            content=hits,
            citations=citations,
        )


CAPABILITY = _GmailSearch()
