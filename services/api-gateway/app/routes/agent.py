"""Agent routes — forwards /run to agent-orchestration with project scope."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.clients.agent import AgentOrchestrationClient
from app.clients.base import propagate_headers
from app.config import settings
from app.db import db
from app.deps import CurrentProject, CurrentUser, get_http_client, get_long_http_client
from app.ratelimit import limiter
from app.repositories.actions import ActionsRepository

router = APIRouter()


class RunRequest(BaseModel):
    prompt: str
    dry_run: bool = False
    # Async execution controls — set from the UI time-limit popup
    mode: str = Field(default="sync", pattern="^(sync|background)$")
    time_limit_sec: int | None = None   # 300 | 600 | 900 | None
    notify_on_complete: bool = True


@router.post("/run")
@limiter.limit(settings.rate_limit_agent_run)
async def run(
    body: RunRequest,
    request: Request,
    user_id: CurrentUser,
    project: CurrentProject,
) -> dict[str, Any]:
    client = AgentOrchestrationClient(
        get_long_http_client(request),
        headers=propagate_headers(request),
    )
    return await client.run(
        user_id=user_id,
        prompt=body.prompt,
        project_ids=project.ids,
        project_scope=project.mode,
        mode=body.mode,
        time_limit_sec=body.time_limit_sec,
        notify_on_complete=body.notify_on_complete,
    )


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str, request: Request, user_id: CurrentUser
) -> dict[str, Any]:
    """Check background task status — the UI polls this."""
    client: httpx.AsyncClient = get_http_client(request)
    resp = await client.get(
        f"{settings.agent_orchestration_url}/tasks/{task_id}"
    )
    if resp.status_code >= 400:
        return {"error": f"task lookup failed: {resp.status_code}"}
    return resp.json()


@router.get("/tasks")
async def list_tasks(
    request: Request, user_id: CurrentUser, limit: int = 20
) -> list[dict[str, Any]]:
    """List recent tasks for the background-task panel."""
    client: httpx.AsyncClient = get_http_client(request)
    resp = await client.get(
        f"{settings.agent_orchestration_url}/tasks",
        params={"user_id": user_id, "limit": limit},
    )
    if resp.status_code >= 400:
        return []
    return resp.json()


@router.get("/history")
async def history(
    user_id: CurrentUser,
    project: CurrentProject,
    limit: int = 50,
) -> list[dict[str, Any]]:
    repo = ActionsRepository(db.raw)
    clamped = min(max(limit, 1), 200)
    if project.mode == "all":
        rows = await repo.history_for_projects(user_id, project.ids, limit=clamped)
    elif project.primary:
        rows = await repo.history_for_project(user_id, project.primary, limit=clamped)
    else:
        rows = []
    out: list[dict[str, Any]] = []
    for r in rows:
        item: dict[str, Any] = {k: v for k, v in r.items() if k != "timestamp"}
        item["id"] = str(r["id"])
        if r.get("project_id") is not None:
            item["project_id"] = str(r["project_id"])
        item["timestamp"] = r["timestamp"].isoformat()
        out.append(item)
    return out
