"""``proactive_surface`` rubric — scores a surface the proactive layer wants to show the user.

Used by the proactive-monitor pipeline in Session 4+. Unlike ``action``
and ``summarisation``, this rubric has no "user prompt" — the input is
the surface metadata, the output is the proposed title + snippet.
"""
from __future__ import annotations

from typing import Any

from app.rubrics.base import Dimension, Rubric

SYSTEM = """You are a strict evaluator for an AI assistant named Axis.

Axis has decided to proactively surface something to the user — an
unanswered Slack mention, a stale doc, a pending decision. You are shown
the surface payload and the reason it triggered.

Score the surface on three dimensions:

1. **relevance** — does this actually matter to this user right now?
2. **timing** — is this the right moment to show it, or will the user
   feel interrupted?
3. **actionability** — can the user do something about this within 30s?

Return the scores by calling the ``submit_scores`` tool. Every dimension
gets an integer 1–5 and a one-sentence reason. Do not write anything
outside the tool call.
""".strip()


def _build_user_prompt(ctx: dict[str, Any]) -> str:
    title = (ctx.get("title") or ctx.get("output") or "").strip()
    snippet = (ctx.get("snippet") or ctx.get("context") or "").strip()
    signal = (ctx.get("signal_type") or "").strip()
    return (
        f"<signal>{signal}</signal>\n"
        f"<title>{title}</title>\n"
        f"<snippet>\n{snippet}\n</snippet>"
    )


RUBRIC = Rubric(
    key="proactive_surface",
    label="Proactive surface rubric",
    dimensions=(
        Dimension("relevance", "Actually matters to this user right now.", 0.4),
        Dimension("timing", "Right moment to show it; not an interruption.", 0.3),
        Dimension("actionability", "User can act on it inside 30 seconds.", 0.3),
    ),
    system_prompt=SYSTEM,
    build_user_prompt=_build_user_prompt,
)
