"""``summarisation`` rubric — used when the agent is compressing source material."""
from __future__ import annotations

from typing import Any

from app.rubrics.base import Dimension, Rubric

SYSTEM = """You are a strict evaluator for an AI assistant named Axis.

Axis has summarized a piece of source material (Notion page, Slack
thread, email, PR, etc.). You are being shown the source and the summary.

Score the summary on three dimensions:

1. **faithfulness** — every claim in the summary can be traced to the
   source. Hallucinated facts score 1.
2. **coverage** — the summary captures the key points; omitting the
   single most important line drops the score.
3. **conciseness** — the summary is short enough to be useful; padding
   drops the score.

Return the scores by calling the ``submit_scores`` tool. Every dimension
gets an integer 1–5 and a one-sentence reason. Do not write anything
outside the tool call.
""".strip()


def _build_user_prompt(ctx: dict[str, Any]) -> str:
    source = (ctx.get("source") or ctx.get("prompt") or "").strip()
    summary = (ctx.get("output") or "").strip()
    return (
        f"<source>\n{source}\n</source>\n\n"
        f"<summary>\n{summary}\n</summary>"
    )


RUBRIC = Rubric(
    key="summarisation",
    label="Summarisation rubric",
    dimensions=(
        Dimension("faithfulness", "Every claim is traceable to the source.", 0.5),
        Dimension("coverage", "Captures the key points of the source.", 0.3),
        Dimension("conciseness", "Short enough to be useful; no padding.", 0.2),
    ),
    system_prompt=SYSTEM,
    build_user_prompt=_build_user_prompt,
)
