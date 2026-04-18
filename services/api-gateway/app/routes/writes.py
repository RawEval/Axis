"""Write-actions proxy — confirm + rollback forwarded to agent-orchestration."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.deps import CurrentUser, get_http_client

router = APIRouter()


@router.post("/{write_action_id}/confirm")
async def confirm_write(
    write_action_id: str, req: Request, user_id: CurrentUser
) -> dict[str, Any]:
    client: httpx.AsyncClient = get_http_client(req)
    try:
        resp = await client.post(
            f"{settings.agent_orchestration_url}/writes/{write_action_id}/confirm",
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"agent-orchestration unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@router.post("/{write_action_id}/rollback")
async def rollback_write(
    write_action_id: str, req: Request, user_id: CurrentUser
) -> dict[str, Any]:
    client: httpx.AsyncClient = get_http_client(req)
    try:
        resp = await client.post(
            f"{settings.agent_orchestration_url}/writes/{write_action_id}/rollback",
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"agent-orchestration unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()
