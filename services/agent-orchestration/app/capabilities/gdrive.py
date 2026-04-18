"""Google Drive capabilities — search, read content, create doc.

All calls go through connector-manager for token decryption.
Read capabilities are auto; write capabilities are ask (gated).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


def _project_guard(project_id: str | None) -> CapabilityResult | None:
    if not project_id:
        return CapabilityResult(summary="no active project", content=[], error="gdrive requires an active project")
    return None


def _error_guard(resp: dict[str, Any], name: str) -> CapabilityResult | None:
    if "error" in resp:
        return CapabilityResult(summary=f"{name} error", content=[], error=str(resp["error"]))
    return None


# ── connector.gdrive.search ────────────────────────────────────────────


@dataclass
class _GDriveSearch:
    name: str = "connector.gdrive.search"
    description: str = (
        "Search the user's Google Drive. Accepts plain keywords or Drive "
        "query syntax. Returns files sorted by most recently modified."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords or a Drive query."},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.gdrive_search(user_id=user_id, project_id=project_id, query=inputs.get("query", ""), limit=int(inputs.get("limit", 10)))
        except Exception as e:
            return CapabilityResult(summary="gdrive search failed", content=[], error=str(e))
        if err := _error_guard(resp, "gdrive search"): return err
        hits = resp.get("results", [])
        citations = [Citation(source_type="gdrive_file", provider="gdrive", ref_id=h.get("id"), url=h.get("url"), title=h.get("title"), actor=h.get("author"), excerpt=h.get("excerpt"), occurred_at=h.get("modified_time")) for h in hits]
        return CapabilityResult(summary=f"found {len(hits)} Drive files", content=hits, citations=citations)


# ── connector.gdrive.read_content ──────────────────────────────────────


@dataclass
class _GDriveReadContent:
    name: str = "connector.gdrive.read_content"
    description: str = (
        "Read the full text content of a Google Doc, Sheet, or Slide. "
        "Use this when you need to look INSIDE a file, not just find it. "
        "For example: 'what does the pricing doc say about enterprise tiers' "
        "or 'read the Q3 planning doc and summarize it'."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID."},
            },
            "required": ["file_id"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client._tool_call("gdrive/read", user_id=user_id, project_id=project_id, file_id=inputs["file_id"])
        except Exception as e:
            return CapabilityResult(summary="gdrive read failed", content=[], error=str(e))
        if err := _error_guard(resp, "gdrive read"): return err
        content = resp.get("content", "")
        title = resp.get("title") or "Untitled"
        return CapabilityResult(
            summary=f"read {len(content)} chars from '{title}'",
            content=[{"title": title, "content": content[:10000], "url": resp.get("url"), "mime_type": resp.get("mime_type")}],
            citations=[Citation(source_type="gdrive_file", provider="gdrive", ref_id=inputs["file_id"], url=resp.get("url"), title=title, excerpt=content[:200])],
        )


# ── connector.gdrive.create_doc (WRITE — gated) ───────────────────────


@dataclass
class _GDriveCreateDoc:
    name: str = "connector.gdrive.create_doc"
    description: str = (
        "Create a new Google Doc with a title and initial content. This is "
        "a WRITE action that requires user confirmation. Use when the user "
        "asks 'create a doc with the meeting notes' or 'save this analysis "
        "as a Google Doc'. The doc will be owned by the user's Google account."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title."},
                "content": {"type": "string", "description": "Initial text content for the doc."},
                "folder_id": {"type": "string", "description": "Optional Drive folder ID to put the doc in."},
            },
            "required": ["title", "content"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client._tool_call(
                "gdrive/create-doc",
                user_id=user_id, project_id=project_id,
                title=inputs["title"], content=inputs.get("content", ""),
                folder_id=inputs.get("folder_id"),
            )
        except Exception as e:
            return CapabilityResult(summary="gdrive create doc failed", content=[], error=str(e))
        if err := _error_guard(resp, "gdrive create doc"): return err
        return CapabilityResult(
            summary=f"created Google Doc: {resp.get('title')}",
            content=[resp],
            citations=[Citation(source_type="gdrive_file", provider="gdrive", ref_id=resp.get("id"), url=resp.get("url"), title=resp.get("title"), excerpt="New document created")],
        )


# ── Registry ────────────────────────────────────────────────────────────

CAPABILITIES = [
    _GDriveSearch(),
    _GDriveReadContent(),
    _GDriveCreateDoc(),
]
CAPABILITY = CAPABILITIES[0]
