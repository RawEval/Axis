"""Eval routes — correction capture + read-side queries for the dashboard.

Everything here is a thin proxy to eval-engine except the dashboard list,
which reads ``eval_results`` directly off the gateway's Postgres pool so
the frontend gets a small scoped response without an extra hop.
"""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.db import db
from app.deps import CurrentProject, CurrentUser, get_http_client
from app.ratelimit import limiter

router = APIRouter()


class CorrectionRequest(BaseModel):
    action_id: str
    correction_type: str = Field(..., pattern="^(wrong|rewrite|memory_update|scope)$")
    note: str | None = None


@router.post("/corrections")
@limiter.limit(settings.rate_limit_corrections)
async def submit_correction(
    body: CorrectionRequest,
    request: Request,
    user_id: CurrentUser,
    project: CurrentProject,
) -> dict[str, Any]:
    """Record a user correction on an agent_actions row.

    Forwarded to eval-engine which persists it and fires a short-loop
    refresh in the background.
    """
    client: httpx.AsyncClient = get_http_client(request)
    try:
        resp = await client.post(
            f"{settings.eval_engine_url}/corrections",
            json={
                "user_id": user_id,
                "action_id": body.action_id,
                "project_id": project.primary,
                "correction_type": body.correction_type,
                "note": body.note,
            },
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"eval-engine unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@router.get("/scores")
async def list_scores(
    user_id: CurrentUser,
    project: CurrentProject,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Recent eval_results rows for the active project(s).

    Joined against agent_actions so the dashboard can show the original
    prompt alongside the composite score. Powers the Output-Quality
    panel on /settings.
    """
    if not project.ids:
        return []
    clamped = max(1, min(limit, 500))
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT er.id, er.action_id, er.rubric_type, er.scores,
                   er.composite_score, er.flagged, er.created_at,
                   aa.prompt
            FROM eval_results er
            JOIN agent_actions aa ON aa.id = er.action_id
            WHERE aa.user_id = $1::uuid
              AND aa.project_id = ANY($2::uuid[])
            ORDER BY er.created_at DESC
            LIMIT $3
            """,
            user_id,
            project.ids,
            clamped,
        )
    return [
        {
            "id": str(r["id"]),
            "action_id": str(r["action_id"]),
            "rubric_type": r["rubric_type"],
            "scores": r["scores"],
            "composite_score": float(r["composite_score"])
            if r["composite_score"] is not None
            else None,
            "flagged": r["flagged"],
            "created_at": r["created_at"].isoformat(),
            "prompt": r["prompt"],
        }
        for r in rows
    ]
