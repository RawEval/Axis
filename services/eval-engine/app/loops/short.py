"""Short-loop prompt mutation — the hours-to-minutes feedback path.

Reads the last ``short_loop_window_size`` correction_signals for a user,
asks Haiku to synthesize a one-paragraph *behavior delta* — a set of
instructions the agent should follow on top of its base system prompt —
and caches the result in ``user_prompt_deltas``.

Agent-orchestration fetches the cached delta before every supervisor
call via ``GET /prompt-deltas/{user_id}`` and prepends it to its
SYSTEM_PROMPT. That closes the loop: correction → new delta → next run
behaves differently.

The generated delta is deliberately short — long additions to the system
prompt are expensive and dilute the base instructions. Haiku is told to
return no more than 6 bullet points.
"""
from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from axis_common import get_logger

from app.config import settings
from app.db import db
from app.judges.haiku import get_client
from app.repositories.corrections import (
    CorrectionsRepository,
    PromptDeltasRepository,
)

logger = get_logger(__name__)


SYSTEM = """You are a prompt-engineering assistant working inside an AI
product called Axis.

Axis is a cross-tool agent that answers questions using the user's
workspace (Notion, Slack, Gmail, Drive, GitHub). Sometimes the user
marks an answer as wrong, suggests a rewrite, or leaves a short note
explaining what was off.

Your job is to synthesize those corrections into a BEHAVIOR DELTA — a
short set of instructions the agent should follow on top of its base
system prompt. The delta will be prepended to the system prompt for
every future call from this user.

Rules:
- No more than 6 bullet points. Fewer is better.
- Each bullet is an imperative — "Always verify X", "Prefer Y over Z".
- Write instructions, not analysis. Do not explain why; just say what.
- If the corrections are contradictory, pick the most common direction.
- If the corrections contain personal facts ("I work on X", "call me Y")
  encode them as memory rules: "Remember that the user …".

Return the result by calling the ``submit_delta`` tool with a single
``delta`` string containing the bullet points, separated by newlines.
Do not write anything outside the tool call.
""".strip()


TOOL_DEF = {
    "name": "submit_delta",
    "description": "Submit the synthesized behavior delta for this user.",
    "input_schema": {
        "type": "object",
        "properties": {
            "delta": {
                "type": "string",
                "description": (
                    "Up to 6 imperative bullet points, newline-separated, "
                    "each starting with '- '."
                ),
            }
        },
        "required": ["delta"],
    },
}


async def refresh_prompt_delta(user_id: str) -> dict[str, Any]:
    """Regenerate the per-user delta from recent corrections.

    Safe to call on every correction — it's idempotent-ish: given the
    same window it produces similar output. Logged + persisted so the
    next ``/prompt-deltas/{user_id}`` call returns the updated string.
    """
    corrections_repo = CorrectionsRepository(db.raw)
    deltas_repo = PromptDeltasRepository(db.raw)

    rows = await corrections_repo.recent_for_user(
        user_id, limit=settings.short_loop_window_size
    )
    if not rows:
        # No corrections yet → clear any cached delta so the agent uses
        # the base prompt. An empty string is a meaningful state.
        await deltas_repo.upsert(
            user_id=user_id,
            delta="",
            source_corrections=[],
            model="none",
            token_count=0,
        )
        return {"delta": "", "n": 0}

    client = get_client()
    source_ids = [str(r["id"]) for r in rows]

    if client is None:
        delta = _stub_delta(rows)
        await deltas_repo.upsert(
            user_id=user_id,
            delta=delta,
            source_corrections=source_ids,
            model="stub-deterministic",
            token_count=None,
        )
        logger.info(
            "short_loop_refreshed_stub",
            user_id=user_id,
            corrections=len(rows),
            delta_len=len(delta),
        )
        return {"delta": delta, "n": len(rows)}

    payload = _build_user_prompt(rows)
    try:
        resp = await client.messages.create(
            model=settings.anthropic_model_haiku,
            max_tokens=settings.anthropic_max_tokens,
            temperature=0.0,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[TOOL_DEF],
            tool_choice={"type": "tool", "name": "submit_delta"},
            messages=[{"role": "user", "content": payload}],
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("short_loop_haiku_failed_stubbing", error=str(e))
        delta = _stub_delta(rows)
        await deltas_repo.upsert(
            user_id=user_id,
            delta=delta,
            source_corrections=source_ids,
            model="stub-fallback",
            token_count=None,
        )
        return {"delta": delta, "n": len(rows)}

    delta_str = ""
    tokens = None
    for block in resp.content:
        if getattr(block, "type", "") == "tool_use" and block.name == "submit_delta":
            delta_str = str(block.input.get("delta") or "").strip()
            break
    if hasattr(resp, "usage") and resp.usage is not None:
        tokens = (resp.usage.input_tokens or 0) + (resp.usage.output_tokens or 0)

    await deltas_repo.upsert(
        user_id=user_id,
        delta=delta_str,
        source_corrections=source_ids,
        model=settings.anthropic_model_haiku,
        token_count=tokens,
    )
    logger.info(
        "short_loop_refreshed",
        user_id=user_id,
        corrections=len(rows),
        delta_len=len(delta_str),
        tokens=tokens,
    )
    return {"delta": delta_str, "n": len(rows)}


def _build_user_prompt(rows: list[dict[str, Any]]) -> str:
    lines = ["Here are this user's recent corrections (newest first):", ""]
    for i, row in enumerate(rows, start=1):
        prompt = _extract_prompt(row)
        note = row.get("note") or ""
        kind = row.get("correction_type") or "wrong"
        lines.append(f"{i}. [{kind}] prompt: {prompt[:200]}")
        if note:
            lines.append(f"   note: {note[:200]}")
    lines.append("")
    lines.append(
        "Synthesize the corrections into a behavior delta. Call submit_delta."
    )
    return "\n".join(lines)


def _extract_prompt(row: dict[str, Any]) -> str:
    raw = row.get("prompt")
    if isinstance(raw, str):
        return raw
    return ""


def _stub_delta(rows: list[dict[str, Any]]) -> str:
    """No-API fallback: echo the notes back as literal bullets so the
    agent at least sees something, and the UI can confirm the loop fired.
    """
    bullets: list[str] = []
    for row in rows[:6]:
        note = (row.get("note") or "").strip()
        kind = row.get("correction_type") or "wrong"
        if note:
            bullets.append(f"- ({kind}) {note[:180]}")
        else:
            bullets.append(f"- ({kind}) Avoid the pattern from this correction.")
    return "\n".join(bullets)
