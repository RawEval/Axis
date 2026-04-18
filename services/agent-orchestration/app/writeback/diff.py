"""Diff generation + snapshot capture for the write-back engine (spec §6.5).

The diff is a line-by-line comparison of the before and after state,
producing ``add/del/eq`` lines that the DiffViewer component renders.
The agent never executes a write without first showing the user the diff
and receiving an explicit confirmation.

Snapshot capture fetches the current state of the target resource from
connector-manager so we have a rollback point. The snapshot is stored in
``write_snapshots`` and referenced from ``write_actions.snapshot_id``.
"""
from __future__ import annotations

import difflib
from typing import Any

from app.clients.connector_manager import ConnectorManagerClient


def compute_diff(
    before_lines: list[str], after_lines: list[str]
) -> list[dict[str, str]]:
    """Line-by-line diff → list of {type: 'add'|'del'|'eq', text: str}.

    Uses unified diff logic internally but emits the shape the DiffViewer
    component expects.
    """
    result: list[dict[str, str]] = []
    sm = difflib.SequenceMatcher(None, before_lines, after_lines)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for line in before_lines[i1:i2]:
                result.append({"type": "eq", "text": line})
        elif tag == "replace":
            for line in before_lines[i1:i2]:
                result.append({"type": "del", "text": line})
            for line in after_lines[j1:j2]:
                result.append({"type": "add", "text": line})
        elif tag == "delete":
            for line in before_lines[i1:i2]:
                result.append({"type": "del", "text": line})
        elif tag == "insert":
            for line in after_lines[j1:j2]:
                result.append({"type": "add", "text": line})
    return result


def blocks_to_text(blocks: list[dict[str, Any]]) -> list[str]:
    """Flatten Notion blocks → plain-text lines for diffing."""
    lines: list[str] = []
    for block in blocks:
        btype = block.get("type", "")
        data = block.get(btype) or {}
        rich = data.get("rich_text") or data.get("text") or []
        text = "".join(
            part.get("plain_text", "") for part in rich if isinstance(part, dict)
        )
        if btype.startswith("heading"):
            lines.append(f"## {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "to_do":
            checked = "x" if data.get("checked") else " "
            lines.append(f"[{checked}] {text}")
        elif text:
            lines.append(text)
    return lines


async def capture_notion_snapshot(
    *,
    user_id: str,
    project_id: str,
    page_id: str,
) -> dict[str, Any]:
    """Fetch the current blocks of a Notion page via connector-manager.

    Returns ``{blocks: [...], text_lines: [...]}`` so the caller has both
    the raw API response (for rollback) and the diffable text.
    """
    client = ConnectorManagerClient()
    resp = await client.notion_get_blocks(
        user_id=user_id, project_id=project_id, page_id=page_id
    )
    blocks = resp.get("blocks") or []
    return {
        "blocks": blocks,
        "text_lines": blocks_to_text(blocks),
    }
