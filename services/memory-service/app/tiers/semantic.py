"""Semantic tier — entity graph lookups.

Strategy is deliberately dumb for Phase 1:
  1. Name-substring match on every Entity node scoped to the user.
  2. For each hit, pull 1-hop neighbors to give the agent a tiny sub-graph.

A production semantic search would tokenize the query, run NER to pull
entity candidates, then traverse — that lands in Session 6.5+ when the
correction loop produces enough labelled data to train a small extractor.
"""
from __future__ import annotations

from typing import Any

from app.graph.client import search_entities, traverse_neighbors


async def retrieve(
    *, user_id: str, query: str, limit: int
) -> list[dict[str, Any]]:
    seeds = await search_entities(user_id=user_id, query=query, limit=limit)
    results: list[dict[str, Any]] = []
    for idx, seed in enumerate(seeds):
        try:
            neighbors = await traverse_neighbors(
                user_id=user_id,
                name=seed["name"],
                kind=seed["kind"],
                depth=2,
                limit=10,
            )
        except Exception:  # noqa: BLE001
            neighbors = []
        content = _format_content(seed, neighbors)
        results.append(
            {
                "id": f"entity:{seed['kind']}:{seed['name']}",
                "tier": "semantic",
                "type": seed["kind"],
                "content": content,
                # Seeds are ranked by neo4j's "name contains" ORDER BY
                # updated_at DESC — index position is the signal.
                "score": round(1.0 - (idx / max(1, limit)), 4),
                "metadata": {
                    "name": seed["name"],
                    "kind": seed["kind"],
                    "attrs": seed.get("attrs") or {},
                    "neighbors": neighbors,
                },
            }
        )
    return results


def _format_content(seed: dict[str, Any], neighbors: list[dict[str, Any]]) -> str:
    head = f"{seed['kind']}: {seed['name']}"
    if not neighbors:
        return head
    neigh = ", ".join(f"{n['name']} ({n['kind']})" for n in neighbors[:5])
    return f"{head} — related: {neigh}"
