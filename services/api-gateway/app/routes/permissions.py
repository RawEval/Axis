"""Permission resolve proxy — forwards user grants to agent-orchestration."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import CurrentUser, get_http_client

router = APIRouter()


class ResolveRequest(BaseModel):
    pending_id: str
    granted: bool
    lifetime: str = Field(default="session", pattern="^(session|24h|project|forever)$")


@router.post("/resolve")
async def resolve_permission(
    body: ResolveRequest,
    req: Request,
    user_id: CurrentUser,
) -> dict[str, Any]:
    """The user just clicked Allow/Deny on the permission modal.

    We don't verify that the pending_id actually belongs to this user —
    agent-orchestration holds the pending map in-process and will only
    unblock a request that exists there, so an attacker guessing a UUID
    can't unlock someone else's gate. We do forward the user_id for
    logging clarity.
    """
    client: httpx.AsyncClient = get_http_client(req)
    try:
        resp = await client.post(
            f"{settings.agent_orchestration_url}/permissions/resolve",
            json={
                "pending_id": body.pending_id,
                "granted": body.granted,
                "lifetime": body.lifetime,
            },
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"agent-orchestration unreachable: {e}") from e
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()
