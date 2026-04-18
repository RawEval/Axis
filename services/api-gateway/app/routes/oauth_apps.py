"""BYO OAuth client routes.

Lets a user save their own OAuth client_id/client_secret per tool (ADR 003).
The api-gateway forwards these to connector-manager, which handles storage
and encryption. The gateway never touches the plaintext secret except on
the wire from the user to the downstream call.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.clients.base import forward, propagate_headers
from app.config import settings
from app.deps import CurrentUser, get_http_client

router = APIRouter()

ALLOWED_TOOLS = ("slack", "notion", "gmail", "gdrive", "github", "linear", "jira")


class OAuthAppBody(BaseModel):
    client_id: str = Field(min_length=1, max_length=400)
    client_secret: str = Field(min_length=1, max_length=400)
    redirect_uri: str | None = Field(default=None, max_length=500)


@router.get("")
async def list_apps(req: Request, user_id: CurrentUser) -> list[dict[str, Any]]:
    result = await forward(
        get_http_client(req),
        "GET",
        f"{settings.connector_manager_url}/oauth-apps",
        headers={**propagate_headers(req), "X-Axis-User": user_id},
    )
    return result if isinstance(result, list) else []


@router.get("/{tool}")
async def get_app(tool: str, req: Request, user_id: CurrentUser) -> dict[str, Any]:
    return await forward(
        get_http_client(req),
        "GET",
        f"{settings.connector_manager_url}/oauth-apps/{tool}",
        headers={**propagate_headers(req), "X-Axis-User": user_id},
    )


@router.put("/{tool}")
async def put_app(
    tool: str, body: OAuthAppBody, req: Request, user_id: CurrentUser
) -> dict[str, Any]:
    return await forward(
        get_http_client(req),
        "PUT",
        f"{settings.connector_manager_url}/oauth-apps/{tool}",
        json={
            "client_id": body.client_id,
            "client_secret": body.client_secret,
            "redirect_uri": body.redirect_uri,
        },
        headers={**propagate_headers(req), "X-Axis-User": user_id},
    )


@router.delete("/{tool}")
async def delete_app(tool: str, req: Request, user_id: CurrentUser) -> dict[str, Any]:
    return await forward(
        get_http_client(req),
        "DELETE",
        f"{settings.connector_manager_url}/oauth-apps/{tool}",
        headers={**propagate_headers(req), "X-Axis-User": user_id},
    )
