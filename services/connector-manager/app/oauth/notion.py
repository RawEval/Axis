"""Notion OAuth 2.0 flow.

Notion uses the standard OAuth 2.0 Authorization Code grant. The access token
is a workspace token — it grants access to the specific pages/databases the
user chose to share with the integration.

Docs: https://developers.notion.com/docs/authorization

The ``build_authorize_url`` and ``exchange_code`` functions accept client
credentials at call time so the resolver pattern (ADR 003 — BYO credentials)
can inject either the Axis-default app or the user's own OAuth client.

In addition to the REST API, Notion runs a hosted MCP server at
https://mcp.notion.com/mcp that speaks OAuth 2.1 + PKCE. For Axis we use the
REST OAuth flow here (simpler, the API is stable), and then use Notion's
official SDK via HTTP for reads/writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
TOKEN_URL = "https://api.notion.com/v1/oauth/token"
REVOKE_URL = "https://api.notion.com/v1/oauth/revoke"


def build_authorize_url(
    *,
    state: str,
    client_id: str,
    redirect_uri: str,
) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens.

    Uses basic auth with the supplied client credentials — can be the Axis
    default app from settings, or a user's BYO app from user_oauth_apps.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            headers={"Notion-Version": settings.notion_version},
        )
        resp.raise_for_status()
        body = resp.json()

    expires_at: datetime | None = None
    if "expires_in" in body:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=int(body["expires_in"]))

    return {
        "access_token": body["access_token"],
        "refresh_token": body.get("refresh_token"),
        "expires_at": expires_at,
        "workspace_id": body.get("workspace_id"),
        "workspace_name": body.get("workspace_name"),
        "scopes": None,
    }


async def revoke_token(
    *,
    access_token: str,
    client_id: str,
    client_secret: str,
) -> bool:
    """Best-effort token revocation at the provider.

    Notion exposes /v1/oauth/revoke. Returns True on success; logs + returns
    False otherwise (we still delete locally regardless).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                REVOKE_URL,
                json={"token": access_token},
                auth=(client_id, client_secret),
                headers={"Notion-Version": settings.notion_version},
            )
        return resp.status_code < 400
    except Exception:  # noqa: BLE001
        return False


async def resolve_client_credentials(
    user_id: str,
    repo,  # OAuthAppsRepository
    *,
    org_id: str | None = None,
    project_id: str | None = None,
) -> tuple[str, str, str, str]:
    """Walk project → org → user → Axis default.

    Returns (client_id, client_secret, redirect_uri, source) where source is
    one of 'project' | 'org' | 'user' | 'default'.
    """
    byo = await repo.resolve(
        tool="notion",
        user_id=user_id,
        org_id=org_id,
        project_id=project_id,
    )
    if byo is not None:
        redirect = byo["redirect_uri"] or settings.notion_oauth_redirect_uri
        return byo["client_id"], byo["client_secret"], redirect, byo["scope"]
    return (
        settings.notion_client_id,
        settings.notion_client_secret,
        settings.notion_oauth_redirect_uri,
        "default",
    )
