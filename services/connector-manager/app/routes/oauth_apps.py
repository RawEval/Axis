"""BYO OAuth client routes on connector-manager — multi-scope edition.

Three scopes: user / org / project. Routes:

    GET    /oauth-apps?scope=user|org|project&id=<identity>
    PUT    /oauth-apps/{tool}?scope=user|org|project&id=<identity>
    DELETE /oauth-apps/{tool}?scope=user|org|project&id=<identity>

The api-gateway is responsible for checking the caller's role in the target
org/project before forwarding; this service assumes the call is authorized
by the time it arrives.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db import db
from app.repositories.oauth_apps import OAuthAppsRepository

router = APIRouter()

ALLOWED_TOOLS = ("slack", "notion", "gmail", "gdrive", "github", "linear", "jira")

Scope = Literal["user", "org", "project"]


class OAuthAppBody(BaseModel):
    client_id: str = Field(min_length=1, max_length=400)
    client_secret: str = Field(min_length=1, max_length=400)
    redirect_uri: str | None = Field(default=None, max_length=500)


def _require_user(x_axis_user: str | None) -> str:
    if not x_axis_user:
        raise HTTPException(400, "missing X-Axis-User header")
    return x_axis_user


def _validate_tool(tool: str) -> None:
    if tool not in ALLOWED_TOOLS:
        raise HTTPException(400, f"unknown tool: {tool}")


@router.get("/oauth-apps")
async def list_apps(
    scope: Scope = Query("user"),
    id: str | None = Query(None, description="identity — user_id / org_id / project_id"),
    x_axis_user: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    user_id = _require_user(x_axis_user)
    repo = OAuthAppsRepository(db.raw)
    if scope == "user":
        target = id or user_id
        return await repo.list_for_user(target)
    if scope == "org":
        if not id:
            raise HTTPException(400, "id (org_id) required for scope=org")
        return await repo.list_for_org(id)
    if scope == "project":
        if not id:
            raise HTTPException(400, "id (project_id) required for scope=project")
        return await repo.list_for_project(id)
    raise HTTPException(400, "invalid scope")


@router.put("/oauth-apps/{tool}")
async def put_app(
    tool: str,
    body: OAuthAppBody,
    scope: Scope = Query("user"),
    id: str | None = Query(None),
    x_axis_user: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _require_user(x_axis_user)
    _validate_tool(tool)
    repo = OAuthAppsRepository(db.raw)

    if scope == "user":
        return await repo.upsert_user(
            user_id=id or user_id,
            tool=tool,
            client_id=body.client_id,
            client_secret=body.client_secret,
            redirect_uri=body.redirect_uri,
        )
    if scope == "org":
        if not id:
            raise HTTPException(400, "id (org_id) required for scope=org")
        return await repo.upsert_org(
            created_by=user_id,
            org_id=id,
            tool=tool,
            client_id=body.client_id,
            client_secret=body.client_secret,
            redirect_uri=body.redirect_uri,
        )
    if scope == "project":
        if not id:
            raise HTTPException(400, "id (project_id) required for scope=project")
        return await repo.upsert_project(
            created_by=user_id,
            project_id=id,
            tool=tool,
            client_id=body.client_id,
            client_secret=body.client_secret,
            redirect_uri=body.redirect_uri,
        )
    raise HTTPException(400, "invalid scope")


@router.delete("/oauth-apps/{tool}", status_code=status.HTTP_200_OK)
async def delete_app(
    tool: str,
    scope: Scope = Query("user"),
    id: str | None = Query(None),
    x_axis_user: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _require_user(x_axis_user)
    _validate_tool(tool)
    repo = OAuthAppsRepository(db.raw)

    if scope == "user":
        ok = await repo.delete_user(id or user_id, tool)
    elif scope == "org":
        if not id:
            raise HTTPException(400, "id (org_id) required for scope=org")
        ok = await repo.delete_org(id, tool)
    elif scope == "project":
        if not id:
            raise HTTPException(400, "id (project_id) required for scope=project")
        ok = await repo.delete_project(id, tool)
    else:
        raise HTTPException(400, "invalid scope")

    return {"tool": tool, "scope": scope, "deleted": ok}
