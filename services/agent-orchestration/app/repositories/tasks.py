"""Persists agent_tasks + agent_task_steps for supervisor runs (ADR 005).

One row in ``agent_tasks`` per /run. Each entry in the supervisor's ``plan``
list becomes one row in ``agent_task_steps``:

  - ``kind=='tool_use'`` → one step per Claude tool_use block
  - ``kind=='synthesise'`` → one step for the final end_turn call

This gives the UI a real task tree it can render, and gives eval-engine
fine-grained targets to score later.
"""
from __future__ import annotations

import json
from typing import Any

import asyncpg


class TasksRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        *,
        user_id: str,
        project_id: str | None,
        prompt: str,
        scope: str,
        plan: list[dict[str, Any]],
        output: str,
        tokens_used: int,
        latency_ms: int,
        status: str = "done",
        model: str | None = None,
    ) -> dict[str, Any]:
        result_blob = {
            "output": output,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": model,
        }
        async with self._pool.acquire() as conn, conn.transaction():
            task_row = await conn.fetchrow(
                """
                INSERT INTO agent_tasks
                    (user_id, project_id, prompt, scope, status,
                     plan, result, tokens_used, latency_ms, completed_at)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5,
                        $6::jsonb, $7::jsonb, $8, $9, NOW())
                RETURNING id, created_at
                """,
                user_id,
                project_id,
                prompt,
                scope,
                status,
                json.dumps(plan),
                json.dumps(result_blob),
                tokens_used,
                latency_ms,
            )

            step_ids: list[str] = []
            for entry in plan:
                kind = entry.get("kind", "unknown")
                role = _kind_to_role(kind)
                capability = entry.get("name")
                input_blob: dict[str, Any] = {
                    "step": entry.get("step"),
                    "iteration": entry.get("iteration"),
                }
                output_blob: dict[str, Any] = {"summary": entry.get("summary")}
                step = await conn.fetchrow(
                    """
                    INSERT INTO agent_task_steps
                        (task_id, agent_role, capability, input, output,
                         status, started_at, completed_at)
                    VALUES ($1::uuid, $2, $3, $4::jsonb, $5::jsonb,
                            $6, NOW(), NOW())
                    RETURNING id
                    """,
                    task_row["id"],
                    role,
                    capability,
                    json.dumps(input_blob),
                    json.dumps(output_blob),
                    entry.get("status", "done"),
                )
                step_ids.append(str(step["id"]))

        return {
            "id": str(task_row["id"]),
            "created_at": task_row["created_at"].isoformat(),
            "step_ids": step_ids,
        }


def _kind_to_role(kind: str) -> str:
    """Map supervisor plan kinds onto the ``agent_role`` enum in schema 006."""
    if kind == "tool_use":
        return "reader"
    if kind == "synthesise":
        return "synthesise"
    if kind == "stub_fallback":
        return "synthesise"
    return "reader"
