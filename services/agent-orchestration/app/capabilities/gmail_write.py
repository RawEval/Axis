"""connector.gmail.send + connector.gmail.draft — Gmail write capabilities
with recipient disambiguation.

Both capabilities take a free-text ``recipient_query`` (e.g. "Mrinal"),
not a pre-resolved email address. We push the resolution into the
capability so the planner doesn't have to learn provider-specific
search syntax. The resolver returns 0/1/N candidates:

  - 0  → CapabilityResult.error — the planner can ask the user to be
         more specific or pick a different action.
  - 1  → auto-select that recipient and continue down the normal
         write-with-gating lifecycle (send) or just execute (draft).
  - N  → stage the write_action with target_options, publish a
         ``write.target_pick_required`` event, and return
         ``pending_target_pick`` so the supervisor halts until the
         user picks via ``POST /writes/{id}/choose-target``.

Send is ALWAYS gated (spec §6.2). Draft is reversible so the agent
executes it directly when the recipient is unambiguous; with multiple
candidates we still pause for a picker because committing the wrong
recipient is annoying even on a draft.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient
from app.db import db
from app.events import publish as publish_event
from app.repositories.writes import WritesRepository
from app.writeback.resolver import GmailRecipientResolver, ResolutionError


class _RemoteGmailSearchAdapter:
    """Adapter that lets ``GmailRecipientResolver`` call the connector-manager
    HTTP API instead of holding a direct ``GmailClient``. The resolver only
    needs ``async def search(query, *, limit) -> list[dict]`` returning raw
    Gmail message hits with ``payload.headers`` preserved."""

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

    async def search(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        resp = await self._cm.gmail_search_raw(
            user_id=self._user_id,
            project_id=self._project_id,
            query=query,
            limit=limit,
        )
        if "error" in resp:
            return []
        return resp.get("results", []) or []


def _build_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "recipient_query": {
                "type": "string",
                "description": (
                    "Free-text reference to the recipient — a name, email, "
                    "or partial match (e.g. 'Mrinal'). The capability "
                    "resolves it against the user's Gmail history."
                ),
            },
            "subject": {"type": "string", "description": "Email subject."},
            "body": {"type": "string", "description": "Email body (plain text)."},
        },
        "required": ["recipient_query", "subject", "body"],
    }


_NULL_ACTION_ID = "00000000-0000-0000-0000-000000000000"


@dataclass
class _GmailSend:
    name: str = "connector.gmail.send"
    description: str = (
        "Send an email via Gmail. Always gated — the user sees a diff "
        "preview and must confirm before the message is sent. If the "
        "recipient query is ambiguous the user will be asked to pick "
        "one of the matched contacts first."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = _build_input_schema()

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
                error="gmail send requires an active project",
            )

        recipient_query = (inputs.get("recipient_query") or "").strip()
        subject = inputs.get("subject") or ""
        body = inputs.get("body") or ""
        if not recipient_query or not subject or not body:
            return CapabilityResult(
                summary="missing recipient_query, subject, or body",
                content=[],
                error="recipient_query, subject, and body are all required",
            )

        cm = ConnectorManagerClient()
        resolver = GmailRecipientResolver(
            _RemoteGmailSearchAdapter(cm, user_id=user_id, project_id=project_id)
        )

        try:
            candidates = await resolver.resolve(
                recipient_query, user_id=user_id, project_id=project_id
            )
        except ResolutionError as e:
            return CapabilityResult(
                summary="recipient resolution failed",
                content=[],
                error=str(e),
            )

        if not candidates:
            return CapabilityResult(
                summary=f"no recipient matches '{recipient_query}'",
                content=[],
                error=(
                    f"Couldn't find anyone matching '{recipient_query}' in "
                    "Gmail. Try a different name or full email address."
                ),
            )

        action_id = inputs.get("_action_id") or _NULL_ACTION_ID
        repo = WritesRepository(db.raw)

        if len(candidates) == 1:
            chosen = candidates[0]
            diff = {
                "before": None,
                "after": {"to": chosen.id, "subject": subject, "body": body},
                "summary": f"Send email to {chosen.label} ({chosen.id}) — {subject}",
            }
            pending = await repo.create_pending(
                action_id=action_id,
                user_id=user_id,
                project_id=project_id,
                tool="gmail",
                target_id=chosen.id,
                target_type="email_address",
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
                    "tool": "gmail",
                    "target_id": chosen.id,
                    "target": chosen.as_dict(),
                    "diff": diff,
                },
            )
            return CapabilityResult(
                summary=(
                    f"send pending — to {chosen.label} ({chosen.id}), "
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
                        source_type="gmail_recipient",
                        provider="gmail",
                        ref_id=chosen.id,
                        title=chosen.label,
                        excerpt=chosen.context,
                    )
                ],
            )

        # N>1 — stage the picker.
        diff = {
            "before": None,
            "after": {"to": None, "subject": subject, "body": body},
            "summary": f"Send email — subject: {subject} (recipient pending pick)",
        }
        pending = await repo.create_pending(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            tool="gmail",
            target_id="",
            target_type="email_address",
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
                "tool": "gmail",
                "options": [c.as_dict() for c in candidates],
                "diff": diff,
            },
        )
        return CapabilityResult.pending_target_pick(
            write_id=pending["write_action_id"]
        )


@dataclass
class _GmailDraft:
    name: str = "connector.gmail.draft"
    description: str = (
        "Create a Gmail draft — never sends. If the recipient query is "
        "ambiguous the user will be asked to pick one of the matched "
        "contacts before the draft is created."
    )
    scope: str = "write"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = _build_input_schema()

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
                error="gmail draft requires an active project",
            )

        recipient_query = (inputs.get("recipient_query") or "").strip()
        subject = inputs.get("subject") or ""
        body = inputs.get("body") or ""
        if not recipient_query or not subject or not body:
            return CapabilityResult(
                summary="missing recipient_query, subject, or body",
                content=[],
                error="recipient_query, subject, and body are all required",
            )

        cm = ConnectorManagerClient()
        resolver = GmailRecipientResolver(
            _RemoteGmailSearchAdapter(cm, user_id=user_id, project_id=project_id)
        )

        try:
            candidates = await resolver.resolve(
                recipient_query, user_id=user_id, project_id=project_id
            )
        except ResolutionError as e:
            return CapabilityResult(
                summary="recipient resolution failed",
                content=[],
                error=str(e),
            )

        if not candidates:
            return CapabilityResult(
                summary=f"no recipient matches '{recipient_query}'",
                content=[],
                error=(
                    f"Couldn't find anyone matching '{recipient_query}' in "
                    "Gmail. Try a different name or full email address."
                ),
            )

        if len(candidates) == 1:
            chosen = candidates[0]
            try:
                result = await cm.gmail_draft(
                    user_id=user_id,
                    project_id=project_id,
                    to=chosen.id,
                    subject=subject,
                    body=body,
                )
            except Exception as e:  # noqa: BLE001
                return CapabilityResult(
                    summary="gmail draft failed",
                    content=[],
                    error=f"connector.gmail.draft: {e}",
                )
            if "error" in result:
                return CapabilityResult(
                    summary="gmail draft error",
                    content=[],
                    error=str(result["error"]),
                )

            return CapabilityResult(
                summary=(
                    f"draft created for {chosen.label} ({chosen.id}) — "
                    f"subject: {subject}"
                ),
                content={
                    "status": "draft_created",
                    "draft_id": result.get("id"),
                    "to": chosen.id,
                    "subject": subject,
                    "target": chosen.as_dict(),
                },
                citations=[
                    Citation(
                        source_type="gmail_draft",
                        provider="gmail",
                        ref_id=str(result.get("id") or ""),
                        title=f"Draft to {chosen.label}",
                        excerpt=body[:200],
                    )
                ],
            )

        # N>1 — stage the picker. Drafts are cheap but committing the wrong
        # recipient is still annoying, so we pause for a pick. We use a
        # draft-specific event type so the UI can render a picker without
        # implying a confirmation gate.
        action_id = inputs.get("_action_id") or _NULL_ACTION_ID
        repo = WritesRepository(db.raw)
        diff = {
            "before": None,
            "after": {"to": None, "subject": subject, "body": body},
            "summary": f"Draft email — subject: {subject} (recipient pending pick)",
        }
        pending = await repo.create_pending(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            tool="gmail",
            target_id="",
            target_type="email_address",
            diff=diff,
            before_state={},
            target_options=[c.as_dict() for c in candidates],
            target_chosen=None,
        )
        await publish_event(
            user_id=user_id,
            project_id=project_id,
            event_type="write.draft_target_pick",
            payload={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "tool": "gmail",
                "intent": "draft",
                "options": [c.as_dict() for c in candidates],
                "diff": diff,
            },
        )
        return CapabilityResult.pending_target_pick(
            write_id=pending["write_action_id"]
        )


CAPABILITIES: list[Capability] = [_GmailSend(), _GmailDraft()]
