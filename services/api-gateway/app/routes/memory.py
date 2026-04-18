"""Memory routes — thin proxy to memory-service for the web inspector."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import CurrentProject, CurrentUser, get_http_client

router = APIRouter()


class MemorySearchRequest(BaseModel):
    query: str = ""
    tier: str | None = None  # 'episodic' | 'semantic' | 'procedural' | None
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/search")
async def search_memory(
    body: MemorySearchRequest,
    req: Request,
    user_id: CurrentUser,
    project: CurrentProject,
) -> list[dict[str, Any]]:
    client: httpx.AsyncClient = get_http_client(req)
    try:
        resp = await client.post(
            f"{settings.memory_service_url}/retrieve",
            json={
                "user_id": user_id,
                "query": body.query,
                "project_id": project.primary,
                "tier": body.tier if body.tier and body.tier != "any" else None,
                "limit": body.limit,
            },
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"memory-service unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@router.get("/stats")
async def memory_stats(
    req: Request, user_id: CurrentUser
) -> dict[str, Any]:
    client: httpx.AsyncClient = get_http_client(req)
    try:
        resp = await client.get(
            f"{settings.memory_service_url}/stats/{user_id}"
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"memory-service unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@router.delete("/episodic/{point_id}")
async def delete_episodic_point(
    point_id: str,
    req: Request,
    user_id: CurrentUser,
) -> dict[str, Any]:
    client: httpx.AsyncClient = get_http_client(req)
    resp = await client.delete(
        f"{settings.memory_service_url}/episodic/{point_id}",
        params={"user_id": user_id},
    )
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@router.delete("/semantic/entity")
async def delete_semantic_entity(
    req: Request,
    user_id: CurrentUser,
    name: str = Query(...),
    kind: str = Query(...),
) -> dict[str, Any]:
    client: httpx.AsyncClient = get_http_client(req)
    resp = await client.delete(
        f"{settings.memory_service_url}/semantic/entity",
        params={"user_id": user_id, "name": name, "kind": kind},
    )
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()
