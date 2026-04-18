"""GitHub OAuth 2.0 flow.

Axis uses an OAuth App (not a GitHub App) in Phase 1 — simpler consent,
standard authorization-code grant, no app-installation step. Upgrade to a
GitHub App is Phase 2 when we need per-repo install + webhook receipts.

Docs: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"

# Keep the scopes narrow: read user, read public repo, read org membership.
# Write access (issue comment, PR comment) lives behind a separate
# confirmation flow and uses the already-issued token — GitHub's OAuth
# doesn't support incremental consent, so the scope we ask for is the one
# we keep.
DEFAULT_SCOPE = "read:user repo read:org"


def build_authorize_url(
    *,
    state: str,
    client_id: str,
    redirect_uri: str,
    scope: str = DEFAULT_SCOPE,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "allow_signup": "false",
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
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()

    if "error" in body:
        raise RuntimeError(
            f"github token exchange failed: {body.get('error_description') or body.get('error')}"
        )

    return {
        "access_token": body["access_token"],
        "refresh_token": body.get("refresh_token"),
        "expires_at": None,     # classic tokens don't expire; GitHub App tokens do
        "scopes": body.get("scope"),
        "workspace_id": None,   # fetched later via /user
        "workspace_name": None,
    }


async def resolve_client_credentials(
    user_id: str,
    repo,  # OAuthAppsRepository
    *,
    org_id: str | None = None,
    project_id: str | None = None,
) -> tuple[str, str, str, str]:
    """Walk project → org → user → Axis default.

    Returns (client_id, client_secret, redirect_uri, source).
    """
    byo = await repo.resolve(
        tool="github",
        user_id=user_id,
        org_id=org_id,
        project_id=project_id,
    )
    if byo is not None:
        redirect = byo["redirect_uri"] or settings.github_oauth_redirect_uri
        return byo["client_id"], byo["client_secret"], redirect, byo["scope"]
    return (
        settings.github_client_id,
        settings.github_client_secret,
        settings.github_oauth_redirect_uri,
        "default",
    )
