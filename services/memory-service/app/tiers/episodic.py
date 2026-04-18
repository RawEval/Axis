"""Episodic tier — hybrid vector search + recency decay.

Score formula:
    score = 0.7 * cosine_similarity + 0.3 * recency_decay

Cosine comes straight from Qdrant (0..1 for normalized vectors; Qdrant
hands back a distance-to-similarity conversion already). Recency is a
linear ramp from 1.0 at t=now down to 0 at ``memory_episodic_decay_days``
days old. Everything older than the decay window scores 0 on recency but
can still return on pure vector match if the similarity is high enough.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.vector.client import search_episodic


async def retrieve(
    *, user_id: str, query: str, project_id: str | None, limit: int
) -> list[dict[str, Any]]:
    hits = await search_episodic(
        user_id=user_id,
        query=query,
        project_id=project_id,
        limit=limit * 2,  # over-pull so recency reranking has headroom
    )
    now = datetime.now(tz=timezone.utc)
    rescored: list[dict[str, Any]] = []
    for hit in hits:
        occurred_raw = hit.get("occurred_at")
        recency = _recency_score(occurred_raw, now)
        vector_sim = float(hit.get("score") or 0.0)
        final = round(0.7 * vector_sim + 0.3 * recency, 4)
        rescored.append(
            {
                "id": hit["id"],
                "tier": "episodic",
                "type": hit.get("role") or "turn",
                "content": hit.get("content") or "",
                "score": final,
                "metadata": {
                    "occurred_at": occurred_raw,
                    "action_id": hit.get("action_id"),
                    "project_id": hit.get("project_id"),
                    "tags": hit.get("tags") or [],
                    "vector_score": vector_sim,
                    "recency_score": recency,
                },
            }
        )
    rescored.sort(key=lambda r: r["score"], reverse=True)
    return rescored[:limit]


def _recency_score(occurred_at: Any, now: datetime) -> float:
    if not occurred_at:
        return 0.0
    if isinstance(occurred_at, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    delta_days = (now - occurred_at).total_seconds() / 86400
    if delta_days < 0:
        return 1.0
    window = max(1, settings.memory_episodic_decay_days)
    return max(0.0, 1.0 - (delta_days / window))
