"""connector.github.search — search issues and PRs on GitHub.

Calls connector-manager /tools/github/search which owns token decryption.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


@dataclass
class _GitHubSearch:
    name: str = "connector.github.search"
    description: str = (
        "Search issues and pull requests on the user's connected GitHub "
        "account. Accepts GitHub search syntax — 'is:pr is:open author:alice' "
        "or a plain keyword. Good for 'any PRs waiting on review' or 'find "
        "the issue about the onboarding bug'."
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
                        "GitHub search query. Supports operators like "
                        "is:pr, is:open, author:, label:, repo:, org:."
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
                error="github search requires an active project",
            )

        client = ConnectorManagerClient()
        try:
            resp = await client.github_search(
                user_id=user_id,
                project_id=project_id,
                query=inputs.get("query", ""),
                limit=int(inputs.get("limit", 10)),
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="github search failed",
                content=[],
                error=f"connector.github.search: {e}",
            )

        if "error" in resp:
            return CapabilityResult(
                summary="github search error",
                content=[],
                error=str(resp["error"]),
            )

        hits: list[dict[str, Any]] = resp.get("results", [])
        citations = [
            Citation(
                source_type=f"github_{hit.get('kind') or 'issue'}",
                provider="github",
                ref_id=hit.get("id"),
                url=hit.get("url"),
                title=hit.get("title"),
                actor=hit.get("author"),
                excerpt=hit.get("excerpt"),
                occurred_at=hit.get("updated_at"),
            )
            for hit in hits
        ]
        return CapabilityResult(
            summary=f"found {len(hits)} GitHub items",
            content=hits,
            citations=citations,
        )


CAPABILITY = _GitHubSearch()
