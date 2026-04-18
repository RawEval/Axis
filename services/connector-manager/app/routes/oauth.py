"""OAuth routes — start a flow, handle callbacks. BYO credentials aware.

The callback returns an HTTP 302 redirect back to the web app so the user
lands on /connections with a success/error query param. Never return raw
JSON to the browser — the user's tab shouldn't dead-end on our API.
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx
from axis_common import get_logger
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import settings
from app.db import db
from app.oauth import github as github_oauth
from app.oauth import google as google_oauth
from app.oauth import notion as notion_oauth
from app.oauth import slack as slack_oauth
from app.repositories.connectors import ConnectorsRepository
from app.repositories.oauth_apps import OAuthAppsRepository
from app.security import encrypt_token

router = APIRouter()
logger = get_logger(__name__)


def _web_url() -> str:
    """Where to send the user after an OAuth dance — web app, not our API."""
    # Allow override via env; fall back to the local dev web app.
    return getattr(settings, "web_app_url", None) or "http://localhost:3001"


def _redirect_to_connections(
    *,
    tool: str,
    status: str,
    message: str | None = None,
) -> RedirectResponse:
    params = {"status": status, "tool": tool}
    if message:
        params["message"] = message
    target = f"{_web_url()}/connections?{urlencode(params)}"
    return RedirectResponse(target, status_code=302)


class OAuthStartRequest(BaseModel):
    user_id: str
    project_id: str
    org_id: str | None = None


class OAuthStartResponse(BaseModel):
    tool: str
    state: str
    consent_url: str
    using_byo_app: bool
    credential_source: str  # 'project' | 'org' | 'user' | 'default'


# ---------- Notion — fully implemented --------------------------------------

@router.post("/oauth/notion/start", response_model=OAuthStartResponse)
async def notion_start(body: OAuthStartRequest) -> OAuthStartResponse:
    apps_repo = OAuthAppsRepository(db.raw)
    client_id, _, redirect_uri, source = await notion_oauth.resolve_client_credentials(
        body.user_id,
        apps_repo,
        org_id=body.org_id,
        project_id=body.project_id,
    )
    repo = ConnectorsRepository(db.raw)
    state = await repo.create_oauth_state(
        user_id=body.user_id,
        tool="notion",
        project_id=body.project_id,
    )
    return OAuthStartResponse(
        tool="notion",
        state=state,
        using_byo_app=source != "default",
        credential_source=source,
        consent_url=notion_oauth.build_authorize_url(
            state=state, client_id=client_id, redirect_uri=redirect_uri
        ),
    )


@router.get("/oauth/notion/callback")
async def notion_callback(code: str, state: str) -> RedirectResponse:
    repo = ConnectorsRepository(db.raw)
    apps_repo = OAuthAppsRepository(db.raw)

    st = await repo.pop_oauth_state(state)
    if st is None:
        return _redirect_to_connections(
            tool="notion", status="error", message="invalid or expired state"
        )
    if st["tool"] != "notion":
        return _redirect_to_connections(
            tool="notion", status="error", message="state tool mismatch"
        )

    # Resolve with the same scope walk that was used on start — the state row
    # carries user_id + project_id so we can rehydrate org_id next session once
    # connectors track it. For now: project → user → default.
    client_id, client_secret, redirect_uri, _source = await notion_oauth.resolve_client_credentials(
        str(st["user_id"]),
        apps_repo,
        org_id=None,
        project_id=str(st["project_id"]),
    )

    try:
        token = await notion_oauth.exchange_code(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPStatusError as e:
        logger.warning("notion_token_exchange_failed", status=e.response.status_code)
        return _redirect_to_connections(
            tool="notion", status="error", message="token exchange failed"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("notion_token_exchange_error", error=str(e))
        return _redirect_to_connections(
            tool="notion", status="error", message="unexpected error"
        )

    await repo.upsert_connector(
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        tool="notion",
        access_token_enc=encrypt_token(token["access_token"]),
        refresh_token_enc=(
            encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None
        ),
        expires_at=token.get("expires_at"),
        scopes=token.get("scopes"),
        workspace_id=token.get("workspace_id"),
        workspace_name=token.get("workspace_name"),
    )
    logger.info(
        "notion_connected",
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        workspace=token.get("workspace_name"),
    )
    return _redirect_to_connections(tool="notion", status="connected")


# ---------- Slack — fully implemented ---------------------------------------


@router.post("/oauth/slack/start", response_model=OAuthStartResponse)
async def slack_start(body: OAuthStartRequest) -> OAuthStartResponse:
    apps_repo = OAuthAppsRepository(db.raw)
    client_id, _, redirect_uri, scope, source = await slack_oauth.resolve_client_credentials(
        body.user_id,
        apps_repo,
        org_id=body.org_id,
        project_id=body.project_id,
    )
    if not client_id:
        raise HTTPException(
            400,
            "slack oauth not configured — set SLACK_CLIENT_ID or register a BYO app",
        )
    repo = ConnectorsRepository(db.raw)
    state = await repo.create_oauth_state(
        user_id=body.user_id,
        tool="slack",
        project_id=body.project_id,
    )
    return OAuthStartResponse(
        tool="slack",
        state=state,
        using_byo_app=source != "default",
        credential_source=source,
        consent_url=slack_oauth.build_authorize_url(
            state=state,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
        ),
    )


@router.get("/oauth/slack/callback")
async def slack_callback(code: str, state: str) -> RedirectResponse:
    repo = ConnectorsRepository(db.raw)
    apps_repo = OAuthAppsRepository(db.raw)

    st = await repo.pop_oauth_state(state)
    if st is None:
        return _redirect_to_connections(
            tool="slack", status="error", message="invalid or expired state"
        )
    if st["tool"] != "slack":
        return _redirect_to_connections(
            tool="slack", status="error", message="state tool mismatch"
        )

    client_id, client_secret, redirect_uri, _scope, _source = (
        await slack_oauth.resolve_client_credentials(
            str(st["user_id"]),
            apps_repo,
            org_id=None,
            project_id=str(st["project_id"]),
        )
    )

    try:
        token = await slack_oauth.exchange_code(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPStatusError as e:
        logger.warning("slack_token_exchange_failed", status=e.response.status_code)
        return _redirect_to_connections(
            tool="slack", status="error", message="token exchange failed"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("slack_token_exchange_error", error=str(e))
        return _redirect_to_connections(
            tool="slack", status="error", message="unexpected error"
        )

    await repo.upsert_connector(
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        tool="slack",
        access_token_enc=encrypt_token(token["access_token"]),
        refresh_token_enc=None,
        expires_at=token.get("expires_at"),
        scopes=token.get("scopes"),
        workspace_id=token.get("workspace_id"),
        workspace_name=token.get("workspace_name"),
    )
    logger.info(
        "slack_connected",
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        workspace=token.get("workspace_name"),
    )
    return _redirect_to_connections(tool="slack", status="connected")


# ---------- Google (gmail + gdrive) -----------------------------------------


async def _google_start(tool: str, body: OAuthStartRequest) -> OAuthStartResponse:
    apps_repo = OAuthAppsRepository(db.raw)
    client_id, _, redirect_uri, scope, source = await google_oauth.resolve_client_credentials(
        body.user_id,
        apps_repo,
        tool=tool,
        org_id=body.org_id,
        project_id=body.project_id,
    )
    if not client_id:
        raise HTTPException(
            400,
            f"{tool} oauth not configured — set GOOGLE_CLIENT_ID or register a BYO app",
        )
    repo = ConnectorsRepository(db.raw)
    state = await repo.create_oauth_state(
        user_id=body.user_id,
        tool=tool,
        project_id=body.project_id,
    )
    return OAuthStartResponse(
        tool=tool,
        state=state,
        using_byo_app=source != "default",
        credential_source=source,
        consent_url=google_oauth.build_authorize_url(
            state=state,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
        ),
    )


async def _google_callback(tool: str, code: str, state: str) -> RedirectResponse:
    repo = ConnectorsRepository(db.raw)
    apps_repo = OAuthAppsRepository(db.raw)

    st = await repo.pop_oauth_state(state)
    if st is None:
        return _redirect_to_connections(
            tool=tool, status="error", message="invalid or expired state"
        )
    if st["tool"] != tool:
        return _redirect_to_connections(
            tool=tool, status="error", message="state tool mismatch"
        )

    client_id, client_secret, redirect_uri, _scope, _source = (
        await google_oauth.resolve_client_credentials(
            str(st["user_id"]),
            apps_repo,
            tool=tool,
            org_id=None,
            project_id=str(st["project_id"]),
        )
    )

    try:
        token = await google_oauth.exchange_code(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPStatusError as e:
        logger.warning(f"{tool}_token_exchange_failed", status=e.response.status_code)
        return _redirect_to_connections(
            tool=tool, status="error", message="token exchange failed"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"{tool}_token_exchange_error", error=str(e))
        return _redirect_to_connections(
            tool=tool, status="error", message="unexpected error"
        )

    await repo.upsert_connector(
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        tool=tool,
        access_token_enc=encrypt_token(token["access_token"]),
        refresh_token_enc=(
            encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None
        ),
        expires_at=token.get("expires_at"),
        scopes=token.get("scopes"),
        workspace_id=token.get("workspace_id"),
        workspace_name=token.get("workspace_name"),
    )
    logger.info(
        f"{tool}_connected",
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
    )
    return _redirect_to_connections(tool=tool, status="connected")


@router.post("/oauth/gmail/start", response_model=OAuthStartResponse)
async def gmail_start(body: OAuthStartRequest) -> OAuthStartResponse:
    return await _google_start("gmail", body)


@router.get("/oauth/gmail/callback")
async def gmail_callback(code: str, state: str) -> RedirectResponse:
    return await _google_callback("gmail", code, state)


@router.post("/oauth/gdrive/start", response_model=OAuthStartResponse)
async def gdrive_start(body: OAuthStartRequest) -> OAuthStartResponse:
    return await _google_start("gdrive", body)


@router.get("/oauth/gdrive/callback")
async def gdrive_callback(code: str, state: str) -> RedirectResponse:
    return await _google_callback("gdrive", code, state)


# ---------- GitHub — fully implemented --------------------------------------


@router.post("/oauth/github/start", response_model=OAuthStartResponse)
async def github_start(body: OAuthStartRequest) -> OAuthStartResponse:
    apps_repo = OAuthAppsRepository(db.raw)
    client_id, _, redirect_uri, source = await github_oauth.resolve_client_credentials(
        body.user_id,
        apps_repo,
        org_id=body.org_id,
        project_id=body.project_id,
    )
    if not client_id:
        raise HTTPException(
            400,
            "github oauth not configured — set GITHUB_CLIENT_ID or register a BYO app",
        )
    repo = ConnectorsRepository(db.raw)
    state = await repo.create_oauth_state(
        user_id=body.user_id,
        tool="github",
        project_id=body.project_id,
    )
    return OAuthStartResponse(
        tool="github",
        state=state,
        using_byo_app=source != "default",
        credential_source=source,
        consent_url=github_oauth.build_authorize_url(
            state=state, client_id=client_id, redirect_uri=redirect_uri
        ),
    )


@router.get("/oauth/github/callback")
async def github_callback(code: str, state: str) -> RedirectResponse:
    repo = ConnectorsRepository(db.raw)
    apps_repo = OAuthAppsRepository(db.raw)

    st = await repo.pop_oauth_state(state)
    if st is None:
        return _redirect_to_connections(
            tool="github", status="error", message="invalid or expired state"
        )
    if st["tool"] != "github":
        return _redirect_to_connections(
            tool="github", status="error", message="state tool mismatch"
        )

    client_id, client_secret, redirect_uri, _source = await github_oauth.resolve_client_credentials(
        str(st["user_id"]),
        apps_repo,
        org_id=None,
        project_id=str(st["project_id"]),
    )

    try:
        token = await github_oauth.exchange_code(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPStatusError as e:
        logger.warning("github_token_exchange_failed", status=e.response.status_code)
        return _redirect_to_connections(
            tool="github", status="error", message="token exchange failed"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("github_token_exchange_error", error=str(e))
        return _redirect_to_connections(
            tool="github", status="error", message="unexpected error"
        )

    await repo.upsert_connector(
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
        tool="github",
        access_token_enc=encrypt_token(token["access_token"]),
        refresh_token_enc=(
            encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None
        ),
        expires_at=token.get("expires_at"),
        scopes=token.get("scopes"),
        workspace_id=token.get("workspace_id"),
        workspace_name=token.get("workspace_name"),
    )
    logger.info(
        "github_connected",
        user_id=str(st["user_id"]),
        project_id=str(st["project_id"]),
    )
    return _redirect_to_connections(tool="github", status="connected")
