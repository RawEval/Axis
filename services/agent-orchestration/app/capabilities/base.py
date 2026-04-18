"""Capability protocol — the contract every tool implements.

ADR 005 §"Capability" — a capability is a typed function the agent can call.
Each one ships:
  - name           a dotted identifier like 'connector.notion.search'
  - description    what it does, in a sentence Claude will see
  - input_schema   a JSON schema Claude uses to produce arguments
  - scopes         'read' / 'write' / 'execute'
  - default_permission 'auto' / 'ask' / 'always_gate'
  - __call__       async function that executes the work

The return shape is a CapabilityResult — a structured blob the supervisor
forwards back to Claude via a `tool_result` content block, plus zero or more
Citation objects the supervisor collects and attaches to the assistant
message so the UI can render them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Scope = Literal["read", "write", "execute"]
PermissionDefault = Literal["auto", "ask", "always_gate"]


@dataclass
class Citation:
    """One cited source — the UI renders this in the sources panel."""

    source_type: str                        # notion_page | slack_message | gmail_thread | ...
    provider: str | None = None             # notion | slack | gmail | ...
    ref_id: str | None = None               # provider-native id
    url: str | None = None
    title: str | None = None
    actor: str | None = None
    excerpt: str | None = None
    occurred_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "provider": self.provider,
            "ref_id": self.ref_id,
            "url": self.url,
            "title": self.title,
            "actor": self.actor,
            "excerpt": self.excerpt,
            "occurred_at": self.occurred_at,
            "metadata": self.metadata,
        }


@dataclass
class CapabilityResult:
    """The structured return from a capability call.

    - summary: short human-readable one-liner the supervisor logs
    - content: the payload Claude sees inside the tool_result content block
    - citations: sources to attach to the assistant message for rendering
    - error: populated if the capability couldn't do its job; Claude still
      receives the error text and can recover / retry / ask the user
    """

    summary: str
    content: Any
    citations: list[Citation] = field(default_factory=list)
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None

    def to_tool_result(self) -> str:
        """Serialize for Claude's tool_result block."""
        import json

        if self.is_error:
            return json.dumps({"error": self.error})
        try:
            return json.dumps({"summary": self.summary, "content": self.content})
        except (TypeError, ValueError):
            return json.dumps({"summary": self.summary, "content": str(self.content)})


@runtime_checkable
class Capability(Protocol):
    """Every capability implements this protocol."""

    name: str
    description: str
    scope: Scope
    default_permission: PermissionDefault
    input_schema: dict[str, Any]

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult: ...


def anthropic_tool(cap: Capability) -> dict[str, Any]:
    """Build the dict that goes into Claude's ``tools=`` array."""
    return {
        "name": cap.name.replace(".", "_"),   # Claude tool names are dotted-unsafe
        "description": cap.description,
        "input_schema": cap.input_schema,
    }
