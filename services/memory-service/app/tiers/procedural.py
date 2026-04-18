"""Procedural tier — how the user likes things done.

Backed by the ``users.settings`` JSONB column. The procedural tier is
small, low-traffic, and doesn't need vector search — a few keys like
``trust_level``, ``brief_time``, ``output_format`` are read on every
query and retuned when the user toggles them in /settings.

Exposing procedural memory as retrievable rows lets the agent build
one uniform retrieval path and keeps the supervisor from having to
special-case user preferences in the system prompt.
"""
from __future__ import annotations

from typing import Any

from app.db import db


async def retrieve(*, user_id: str, query: str, limit: int) -> list[dict[str, Any]]:
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT settings FROM users WHERE id = $1::uuid",
            user_id,
        )
    if row is None:
        return []
    raw = row["settings"] or {}
    if isinstance(raw, str):
        import json as _json
        try:
            raw = _json.loads(raw)
        except (ValueError, TypeError):
            raw = {}

    q = (query or "").strip().lower()
    rows: list[dict[str, Any]] = []
    for key, val in raw.items():
        if q and q not in key.lower() and q not in str(val).lower():
            continue
        rows.append(
            {
                "id": f"procedural:{key}",
                "tier": "procedural",
                "type": "preference",
                "content": f"{key} = {val}",
                "score": 1.0,
                "metadata": {"key": key, "value": val},
            }
        )
        if len(rows) >= limit:
            break
    return rows
