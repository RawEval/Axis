"""Slack OAuth v2 flow.

Slack uses a standard OAuth 2.0 authorization-code grant with a few wrinkles:

- The consent URL is ``slack.com/oauth/v2/authorize`` and takes ``scope`` for
  bot-level scopes and ``user_scope`` for user-level scopes. We only ask for
  bot scopes in P1 — the write path is chat.postMessage which works with a
  bot token.
- The token exchange lives at ``slack.com/api/oauth.v2.access`` and returns
  ``access_token`` (the xoxb bot token) plus ``team`` and ``authed_user``.
- There's no refresh token unless the workspace opts into token rotation; we
  don't today, so ``expires_at`` stays NULL and the token is long-lived until
  revoked.

Docs: https://api.slack.com/authentication/oauth-v2
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
REVOKE_URL = "https://slack.com/api/auth.revoke"


def build_authorize_url(
    *,
    state: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
) -> str:
    params = {
        "client_id": client_id,
        "scope": scope,
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
    """Exchange the authorization code for a bot token.

    Slack's oauth.v2.access uses form-encoded credentials in the body
    alongside the code and redirect_uri.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        body = resp.json()

    if not body.get("ok"):
        raise RuntimeError(f"slack token exchange failed: {body.get('error')}")

    team = body.get("team") or {}
    return {
        "access_token": body["access_token"],
        "refresh_token": None,  # only present when token rotation is enabled
        "expires_at": None,
        "workspace_id": team.get("id"),
        "workspace_name": team.get("name"),
        "scopes": body.get("scope"),
        "bot_user_id": body.get("bot_user_id"),
    }


async def revoke_token(*, access_token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                REVOKE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return resp.status_code < 400 and resp.json().get("ok", False)
    except Exception:  # noqa: BLE001
        return False


async def resolve_client_credentials(
    user_id: str,
    repo,  # OAuthAppsRepository
    *,
    org_id: str | None = None,
    project_id: str | None = None,
) -> tuple[str, str, str, str, str]:
    """project → org → user → Axis default.

    Returns (client_id, client_secret, redirect_uri, scope, source).
    """
    byo = await repo.resolve(
        tool="slack",
        user_id=user_id,
        org_id=org_id,
        project_id=project_id,
    )
    if byo is not None:
        redirect = byo["redirect_uri"] or settings.slack_oauth_redirect_uri
        return (
            byo["client_id"],
            byo["client_secret"],
            redirect,
            settings.slack_bot_scopes,
            byo["scope"],
        )
    return (
        settings.slack_client_id,
        settings.slack_client_secret,
        settings.slack_oauth_redirect_uri,
        settings.slack_bot_scopes,
        "default",
    )
