"""Tiny httpx client for eval-engine — score (fire-and-forget) + prompt deltas."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


async def fetch_prompt_delta(
    user_id: str, *, timeout_sec: float = 2.0
) -> str:
    """Return the user's current short-loop system-prompt delta.

    Fast, low-timeout, swallows errors. The supervisor calls this on the
    critical path of every /run, so we cannot afford a slow response — if
    eval-engine is down we return an empty delta and continue.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                f"{settings.eval_engine_url}/prompt-deltas/{user_id}",
            )
            if resp.status_code >= 400:
                return ""
            body = resp.json()
            return str(body.get("delta") or "")
    except Exception:  # noqa: BLE001
        return ""


async def score_action(
    *,
    action_id: str,
    user_id: str,
    project_id: str | None,
    rubric_type: str,
    prompt: str,
    output: str,
    citations: list[dict[str, Any]] | None = None,
    plan: list[dict[str, Any]] | None = None,
    timeout_sec: float = 15.0,
) -> dict[str, Any] | None:
    """Best-effort call to eval-engine /score. Swallows errors — scoring is
    not on the critical path and we don't block the user if it fails.

    ``citations`` and ``plan`` are forwarded as rubric context so the judge
    can ground its correctness/safety scores in what the agent actually
    retrieved. Without them, the judge will penalize every response as
    "unverifiable" even when real sources exist.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(
                f"{settings.eval_engine_url}/score",
                json={
                    "action_id": action_id,
                    "user_id": user_id,
                    "project_id": project_id,
                    "rubric_type": rubric_type,
                    "prompt": prompt,
                    "output": output,
                    "context": {
                        "citations": citations or [],
                        "plan": plan or [],
                    },
                },
            )
            if resp.status_code >= 400:
                return None
            return resp.json()
    except Exception:  # noqa: BLE001
        return None
