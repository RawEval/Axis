"""Cold-start relevance engine (ADR 007 §"Relevance scoring").

Until we have per-user accept/dismiss history (Session 5 correction loop),
we score candidate surfaces deterministically from three signals:

    score = recency_weight × recency + source_weight × source + keyword_weight × keyword

- **recency**: 1.0 for events in the last hour, linearly decaying to 0
  over 72 hours. Events older than that get 0.
- **source**: fixed per-provider priors — Slack mentions dominate because
  that's where real-time asks live; Notion edits score lower because they
  tend to be bulk-ingested.
- **keyword**: 1.0 if the event's text contains one of the user's
  configured priority keywords (``settings.priority_keywords``), else 0.
  Empty keyword list collapses this term to 0 without disabling the
  whole score.

The weights below are the Phase 1 cold-start defaults. When correction
signals land we swap in per-user weights read from
``correction_signals``. For now everything maps to the same constants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Must sum to 1.0 so the composite stays in [0, 1].
DEFAULT_WEIGHTS = {
    "recency": 0.45,
    "source": 0.35,
    "keyword": 0.20,
}

SOURCE_PRIORS: dict[str, float] = {
    "slack": 0.95,
    "gmail": 0.85,
    "github": 0.70,
    "linear": 0.65,
    "notion": 0.50,
    "gdrive": 0.45,
    "axis": 0.30,
}


@dataclass
class RelevanceContext:
    """Caller-supplied context that lets scoring be stateless."""

    now: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    priority_keywords: list[str] = field(default_factory=list)


def score_event(event: dict[str, Any], ctx: RelevanceContext) -> float:
    recency = _recency_score(event, ctx)
    source = SOURCE_PRIORS.get(event.get("source", ""), 0.4)
    keyword = _keyword_score(event, ctx)
    return round(
        DEFAULT_WEIGHTS["recency"] * recency
        + DEFAULT_WEIGHTS["source"] * source
        + DEFAULT_WEIGHTS["keyword"] * keyword,
        3,
    )


def _recency_score(event: dict[str, Any], ctx: RelevanceContext) -> float:
    occurred = event.get("occurred_at")
    if occurred is None:
        return 0.0
    if isinstance(occurred, str):
        try:
            occurred = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    delta_hours = (ctx.now - occurred).total_seconds() / 3600
    if delta_hours < 0:
        return 1.0   # clock skew — treat as brand new
    if delta_hours < 1:
        return 1.0
    if delta_hours >= 72:
        return 0.0
    # Linear decay from 1.0 at 1h to 0 at 72h.
    return max(0.0, 1.0 - (delta_hours - 1) / 71)


def _keyword_score(event: dict[str, Any], ctx: RelevanceContext) -> float:
    if not ctx.priority_keywords:
        return 0.0
    haystack = " ".join(
        [
            str(event.get("title") or ""),
            str(event.get("snippet") or ""),
        ]
    ).lower()
    if not haystack.strip():
        return 0.0
    for kw in ctx.priority_keywords:
        if kw and kw.lower() in haystack:
            return 1.0
    return 0.0
