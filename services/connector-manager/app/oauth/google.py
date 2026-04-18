"""Shared Google OAuth 2.0 flow — used by both Gmail and Google Drive.

Google treats scopes as the discriminator: one client app can request
``gmail.readonly`` and ``drive.readonly`` from the same consent flow and the
same refresh token unlocks both. We expose per-tool wrappers so each tool
can request only the scopes it needs — this keeps the consent screen honest
and lets compliance-sensitive orgs install Gmail without Drive.

Google's token endpoint returns a short-lived access token + a refresh
token. We encrypt both at rest; the refresh happens lazily when a tool
endpoint fails with 401 (the sync loop isn't wired yet — Session 4).

Docs: https://developers.google.com/identity/protocols/oauth2/web-server
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Per-tool scope subsets. Keep them narrow — the consent screen shows the
# user exactly what they're granting, and broader scopes than we need is a
# compliance red flag.
GMAIL_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "openid",
        "email",
    ]
)
GDRIVE_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "openid",
        "email",
    ]
)


def build_authorize_url(
    *,
    state: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",   # return a refresh token
        "prompt": "consent",        # re-prompt so we always get a fresh refresh_token
        "state": state,
        "include_granted_scopes": "true",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
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
        "scopes": body.get("scope"),
        # Google's token endpoint doesn't return workspace metadata; fetching
        # the user's email requires a second call to /oauth2/v3/userinfo.
        "workspace_id": None,
        "workspace_name": None,
    }


async def refresh_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        body = resp.json()

    expires_at: datetime | None = None
    if "expires_in" in body:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=int(body["expires_in"]))
    return {
        "access_token": body["access_token"],
        "expires_at": expires_at,
        "scopes": body.get("scope"),
    }


async def revoke_token(*, token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(REVOKE_URL, data={"token": token})
        return resp.status_code < 400
    except Exception:  # noqa: BLE001
        return False


async def resolve_client_credentials(
    user_id: str,
    repo,  # OAuthAppsRepository
    *,
    tool: str,                        # 'gmail' | 'gdrive'
    org_id: str | None = None,
    project_id: str | None = None,
) -> tuple[str, str, str, str, str]:
    """Walk project → org → user → Axis default for the given Google tool.

    BYO credentials are keyed by tool name ('gmail' or 'gdrive'), not
    'google' — even though one OAuth client could serve both, Axis users may
    want to install Gmail without Drive on one project. Tracking per tool
    matches the existing connectors table.

    Returns (client_id, client_secret, redirect_uri, scope, source).
    """
    scope = GMAIL_SCOPES if tool == "gmail" else GDRIVE_SCOPES
    default_redirect = (
        settings.gmail_oauth_redirect_uri
        if tool == "gmail"
        else settings.gdrive_oauth_redirect_uri
    )
    byo = await repo.resolve(
        tool=tool,
        user_id=user_id,
        org_id=org_id,
        project_id=project_id,
    )
    if byo is not None:
        redirect = byo["redirect_uri"] or default_redirect
        return byo["client_id"], byo["client_secret"], redirect, scope, byo["scope"]
    return (
        settings.google_client_id,
        settings.google_client_secret,
        default_redirect,
        scope,
        "default",
    )
