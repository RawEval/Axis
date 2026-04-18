"""memory.retrieve — pull relevant memory nodes for the current prompt.

Spec §6.4. Calls memory-service /retrieve. Since memory-service is still
a stub returning [], this capability will return an empty content list
today — but the call path is wired so Session 6 only has to populate the
upstream service.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.memory import MemoryClient


@dataclass
class _MemoryRetrieve:
    name: str = "memory.retrieve"
    description: str = (
        "Retrieve relevant memory nodes for the current user (episodic, "
        "semantic, or procedural). Use this when the user's question refers to "
        "something they said before or a preference they've expressed."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None  # set after init

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "what to look up in memory",
                },
                "tier": {
                    "type": "string",
                    "enum": ["episodic", "semantic", "procedural", "any"],
                    "description": "which memory tier to search; 'any' to search all",
                    "default": "any",
                },
                "limit": {
                    "type": "integer",
                    "description": "max rows to return",
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
        client = MemoryClient()
        try:
            rows = await client.retrieve(
                user_id=user_id,
                query=inputs["query"],
                project_id=project_id,
                tier=inputs.get("tier"),
                limit=int(inputs.get("limit", 10)),
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="memory-service unreachable",
                content=[],
                error=f"memory.retrieve failed: {e}",
            )

        citations = [
            Citation(
                source_type="memory_node",
                provider="memory",
                ref_id=row.get("id"),
                title=row.get("type") or "memory",
                excerpt=(row.get("content") or "")[:240],
            )
            for row in rows
        ]
        return CapabilityResult(
            summary=f"retrieved {len(rows)} memory rows",
            content=rows,
            citations=citations,
        )


CAPABILITY = _MemoryRetrieve()
