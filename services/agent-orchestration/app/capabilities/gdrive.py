"""Google Drive capabilities — search, read content, create doc.

All calls go through connector-manager for token decryption.
Read capabilities are auto; write capabilities are ask (gated).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient
from app.db import db
from app.events import publish as publish_event
from app.repositories.writes import WritesRepository
from app.writeback.resolver import GDriveDocResolver, ResolutionError


_NULL_ACTION_ID = "00000000-0000-0000-0000-000000000000"


class _GDriveSearchAdapter:
    """Adapter that lets ``GDriveDocResolver`` call the connector-manager
    HTTP API. The resolver expects ``async search(query, *, limit) ->
    list[dict]`` returning raw Drive file hits with ``mimeType``,
    ``modifiedTime``, ``webViewLink``, and ``owners`` preserved."""

    def __init__(
        self,
        cm: ConnectorManagerClient,
        *,
        user_id: str,
        project_id: str,
    ) -> None:
        self._cm = cm
        self._user_id = user_id
        self._project_id = project_id

    async def __call__(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        resp = await self._cm.gdrive_search_raw(
            user_id=self._user_id,
            project_id=self._project_id,
            query=query,
            limit=limit,
        )
        if "error" in resp:
            return []
        return resp.get("results", []) or []


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


# ── connector.gdrive.append ────────────────────────────────────────────


@dataclass
class _GDriveAppend:
    name: str = "connector.gdrive.append"
    description: str = (
        "Append plain text to the end of an existing Google Doc. WRITE "
        "action — the user sees a diff preview and must confirm before "
        "the text lands on the doc. Pass ``doc_query`` (free-text doc "
        "name like 'Q3 roadmap'); if multiple docs match, the user is "
        "asked to pick one before confirming."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "doc_query": {
                    "type": "string",
                    "description": "Free-text doc name like 'Q3 roadmap'.",
                },
                "text": {
                    "type": "string",
                    "description": "Plain text to append. Newlines preserved.",
                },
            },
            "required": ["doc_query", "text"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        if err := _project_guard(project_id):
            return err

        text = inputs.get("text") or ""
        if not text:
            return CapabilityResult(
                summary="missing text",
                content=[],
                error="text is required",
            )

        # Backward compat: if the caller already has a resolved Drive doc id,
        # skip the resolver and go straight to a single candidate path.
        direct_doc_id = (inputs.get("doc_id") or "").strip()
        doc_query = (inputs.get("doc_query") or "").strip()

        if not direct_doc_id and not doc_query:
            return CapabilityResult(
                summary="missing doc_query",
                content=[],
                error="doc_query (or doc_id) is required",
            )

        cm = ConnectorManagerClient()
        candidates: list[Any]

        if direct_doc_id:
            from app.writeback.resolver import TargetCandidate
            candidates = [
                TargetCandidate(
                    kind="gdrive_doc",
                    id=direct_doc_id,
                    label=f"Google Doc {direct_doc_id}",
                    sub_label=None,
                    context=None,
                    metadata=None,
                )
            ]
        else:
            resolver = GDriveDocResolver(
                _GDriveSearchAdapter(cm, user_id=user_id, project_id=project_id)
            )
            try:
                candidates = await resolver.resolve(
                    doc_query, user_id=user_id, project_id=project_id
                )
            except ResolutionError as e:
                return CapabilityResult(
                    summary="doc resolution failed",
                    content=[],
                    error=str(e),
                )

        if not candidates:
            return CapabilityResult(
                summary=f"no doc matches '{doc_query}'",
                content=[],
                error=(
                    f"Couldn't find any Google Doc matching '{doc_query}' "
                    "in Drive."
                ),
            )

        action_id = inputs.get("_action_id") or _NULL_ACTION_ID
        repo = WritesRepository(db.raw)

        if len(candidates) == 1:
            chosen = candidates[0]
            diff = {
                "before": None,
                "after": {"doc_id": chosen.id, "text": text},
                "summary": f"Append {len(text)} chars to Google Doc: {chosen.label}",
            }
            pending = await repo.create_pending(
                action_id=action_id,
                user_id=user_id,
                project_id=project_id,
                tool="gdrive",
                target_id=chosen.id,
                target_type="gdrive_doc",
                diff=diff,
                before_state={},
                target_options=None,
                target_chosen=chosen.as_dict(),
            )
            await publish_event(
                user_id=user_id,
                project_id=project_id,
                event_type="write.preview",
                payload={
                    "write_action_id": pending["write_action_id"],
                    "snapshot_id": pending["snapshot_id"],
                    "tool": "gdrive",
                    "target_id": chosen.id,
                    "target": chosen.as_dict(),
                    "diff": diff,
                },
            )
            return CapabilityResult(
                summary=(
                    f"gdrive append pending — to {chosen.label}, "
                    f"awaiting user confirmation"
                ),
                content={
                    "write_action_id": pending["write_action_id"],
                    "snapshot_id": pending["snapshot_id"],
                    "status": "pending_confirmation",
                    "target": chosen.as_dict(),
                },
                citations=[
                    Citation(
                        source_type="gdrive_file",
                        provider="gdrive",
                        ref_id=chosen.id,
                        url=chosen.sub_label,
                        title=chosen.label,
                        excerpt=text[:200],
                    )
                ],
            )

        # N>1 — stage the picker.
        diff = {
            "before": None,
            "after": {"doc_id": None, "text": text},
            "summary": f"Append {len(text)} chars to a Google Doc (doc pending pick)",
        }
        pending = await repo.create_pending(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            tool="gdrive",
            target_id="",
            target_type="gdrive_doc",
            diff=diff,
            before_state={},
            target_options=[c.as_dict() for c in candidates],
            target_chosen=None,
        )
        await publish_event(
            user_id=user_id,
            project_id=project_id,
            event_type="write.target_pick_required",
            payload={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "tool": "gdrive",
                "options": [c.as_dict() for c in candidates],
                "diff": diff,
            },
        )
        return CapabilityResult.pending_target_pick(
            write_id=pending["write_action_id"]
        )


# ── Registry ────────────────────────────────────────────────────────────

CAPABILITIES = [
    _GDriveSearch(),
    _GDriveReadContent(),
    _GDriveCreateDoc(),
    _GDriveAppend(),
]
CAPABILITY = CAPABILITIES[0]
