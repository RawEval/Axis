"""Haiku-as-judge — real Anthropic call with deterministic stub fallback.

Every /score call flows through ``judge()``. If ``ANTHROPIC_API_KEY`` is a
placeholder, we return the deterministic stub so local dev (and CI)
exercises the full pipeline without spending tokens. When the key is
real, we call Haiku with the rubric's system prompt (cache-enabled) and
force a structured ``submit_scores`` tool call so the response always
parses.

Prompt caching cuts tokens on repeat requests with the same rubric — the
system prompt is identical for every run under a given rubric type, so
each new turn only pays for the per-request user prompt.
"""
from __future__ import annotations

import hashlib
from typing import Any

from anthropic import AsyncAnthropic
from axis_common import get_logger

from app.config import settings
from app.rubrics import Rubric

logger = get_logger(__name__)

_client: AsyncAnthropic | None = None


def _is_real_key(key: str | None) -> bool:
    return bool(key) and not key.lower().startswith(("replace", "change", "stub"))


def get_client() -> AsyncAnthropic | None:
    global _client
    if _client is not None:
        return _client
    if not _is_real_key(settings.anthropic_api_key):
        return None
    _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def judge(
    rubric: Rubric,
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], float, str, bool]:
    """Return (per_dimension_rows, composite_score, model, is_stub).

    ``per_dimension_rows`` is the list the /score endpoint persists into
    ``eval_results.scores``. Each row is
    ``{"dimension": "...", "score": int, "reason": "..."}``.
    """
    client = get_client()
    if client is None:
        scores, composite = _deterministic_stub(rubric, context)
        return scores, composite, "stub-deterministic", True

    try:
        scores, composite = await _call_haiku(client, rubric, context)
        return scores, composite, settings.anthropic_model_haiku, False
    except Exception as e:  # noqa: BLE001
        logger.warning("haiku_judge_failed_falling_back", error=str(e))
        scores, composite = _deterministic_stub(rubric, context)
        return scores, composite, "stub-deterministic-fallback", True


async def _call_haiku(
    client: AsyncAnthropic,
    rubric: Rubric,
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], float]:
    tool_def = {
        "name": "submit_scores",
        "description": (
            "Submit the per-dimension scores for this assistant turn. You must "
            "call this tool exactly once with an integer 1–5 for every "
            "dimension plus a one-sentence reason each."
        ),
        "input_schema": rubric.tool_schema(),
    }

    user_prompt = rubric.build_user_prompt(context)
    resp = await client.messages.create(
        model=settings.anthropic_model_haiku,
        max_tokens=settings.anthropic_max_tokens,
        temperature=0.0,
        system=[
            {
                "type": "text",
                "text": rubric.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[tool_def],
        tool_choice={"type": "tool", "name": "submit_scores"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_block = None
    for block in resp.content:
        if getattr(block, "type", "") == "tool_use" and block.name == "submit_scores":
            tool_block = block
            break
    if tool_block is None:
        raise RuntimeError("haiku judge returned no tool_use block")

    raw = dict(tool_block.input)
    rows: list[dict[str, Any]] = []
    composite_inputs: dict[str, float] = {}
    for dim in rubric.dimensions:
        try:
            score = int(raw.get(f"{dim.name}_score"))
        except (TypeError, ValueError):
            score = 0
        score = max(1, min(5, score))
        composite_inputs[dim.name] = float(score)
        rows.append(
            {
                "dimension": dim.name,
                "score": score,
                "reason": str(raw.get(f"{dim.name}_reason") or ""),
            }
        )
    composite = rubric.composite(composite_inputs)
    return rows, composite


def _deterministic_stub(
    rubric: Rubric, context: dict[str, Any]
) -> tuple[list[dict[str, Any]], float]:
    """Stable pseudo-scores so the pipeline runs without a real key.

    The score is hashed from the output text so re-scoring the same row
    returns the same number — useful for tests and for the correction loop
    which diffs score changes.
    """
    output = str(context.get("output") or context.get("prompt") or "")
    digest = hashlib.sha256(output.encode()).digest()
    rows: list[dict[str, Any]] = []
    composite_inputs: dict[str, float] = {}
    for i, dim in enumerate(rubric.dimensions):
        byte = digest[i % len(digest)]
        # Map [0,255] → [3, 5] so the stub rarely flags. Real bad runs can
        # still be created by sending a known "bad" output in tests.
        score = 3 + (byte * 2 // 256)
        composite_inputs[dim.name] = float(score)
        rows.append(
            {"dimension": dim.name, "score": int(score), "reason": "stub"}
        )
    return rows, rubric.composite(composite_inputs)
