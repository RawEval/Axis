"""connector.notion.append — append blocks to a Notion page (write action).

This is a WRITE capability: ``default_permission='ask'`` means the
permission gate will always fire unless the user has a prior grant.
Even then, the write confirmation flow (diff preview → confirm button)
provides a second gate before the blocks actually land on the page.

The capability itself does NOT execute the write. Instead it:
  1. Captures a snapshot of the target page (before-state).
  2. Computes the diff between the before-state and the proposed append.
  3. Creates a ``write_actions`` + ``write_snapshots`` row in pending state.
  4. Publishes a ``write.preview`` event so the UI renders the DiffViewer.
  5. Returns a tool_result telling Claude that the write is "pending user
     confirmation" so it can move on to other tool calls or synthesise.

Execution happens later via ``POST /writes/{id}/confirm``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient
from app.db import db
from app.events import publish as publish_event
from app.repositories.writes import WritesRepository
from app.writeback.diff import blocks_to_text, compute_diff


def _paragraph_block(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    }


@dataclass
class _NotionAppend:
    name: str = "connector.notion.append"
    description: str = (
        "Append a paragraph or heading to a Notion page. The user will see "
        "a diff preview and must confirm before the blocks are written. Use "
        "this when the user asks to add content to a specific Notion page."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The Notion page id to append to.",
                },
                "text": {
                    "type": "string",
                    "description": "The text to append as a new paragraph.",
                },
            },
            "required": ["page_id", "text"],
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
                error="notion append requires an active project",
            )

        page_id = inputs.get("page_id", "")
        text = inputs.get("text", "")
        if not page_id or not text:
            return CapabilityResult(
                summary="missing page_id or text",
                content=[],
                error="page_id and text are required",
            )

        cm = ConnectorManagerClient()

        # 1. Capture before-state
        try:
            snap = await cm.notion_get_blocks(
                user_id=user_id, project_id=project_id, page_id=page_id
            )
        except Exception as e:  # noqa: BLE001
            return CapabilityResult(
                summary="snapshot capture failed",
                content=[],
                error=f"could not read page blocks: {e}",
            )

        if "error" in snap:
            return CapabilityResult(
                summary="snapshot capture error",
                content=[],
                error=str(snap["error"]),
            )

        before_blocks = snap.get("blocks") or []
        before_lines = blocks_to_text(before_blocks)
        new_block = _paragraph_block(text)
        after_lines = before_lines + [text]

        diff_lines = compute_diff(before_lines, after_lines)

        # 2. Persist pending write + snapshot
        writes_repo = WritesRepository(db.raw)
        pending = await writes_repo.create_pending(
            action_id=inputs.get("_action_id") or "00000000-0000-0000-0000-000000000000",
            user_id=user_id,
            project_id=project_id,
            tool="notion",
            target_id=page_id,
            target_type="notion_page",
            diff={"lines": diff_lines, "text": text},
            before_state=before_blocks,
        )

        # 3. Publish a write.preview event for the UI
        await publish_event(
            user_id=user_id,
            project_id=project_id,
            event_type="write.preview",
            payload={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "tool": "notion",
                "target_id": page_id,
                "diff_lines": diff_lines,
                "text": text,
            },
        )

        return CapabilityResult(
            summary=f"write pending — appending to page {page_id[:8]}…, awaiting user confirmation",
            content={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "status": "pending_confirmation",
                "diff_line_count": len(diff_lines),
            },
            citations=[
                Citation(
                    source_type="notion_page",
                    provider="notion",
                    ref_id=page_id,
                    title="Write preview",
                    excerpt=text[:200],
                )
            ],
        )


CAPABILITY = _NotionAppend()
