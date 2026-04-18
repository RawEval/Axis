"""Persists agent_actions rows as the orchestrator completes runs."""
from __future__ import annotations

import json
from typing import Any

import asyncpg


class AgentActionsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        *,
        user_id: str,
        project_id: str | None,
        prompt: str,
        plan: list[dict[str, Any]],
        output: str,
        sources: list[dict[str, Any]],
        tokens_used: int,
        latency_ms: int,
    ) -> dict[str, Any]:
        result_blob = {
            "output": output,
            "sources": sources,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        }
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent_actions (user_id, project_id, prompt, plan, result)
                VALUES ($1::uuid, $2::uuid, $3, $4::jsonb, $5::jsonb)
                RETURNING id, timestamp
                """,
                user_id,
                project_id,
                prompt,
                json.dumps(plan),
                json.dumps(result_blob),
            )
        return {"id": str(row["id"]), "timestamp": row["timestamp"].isoformat()}
