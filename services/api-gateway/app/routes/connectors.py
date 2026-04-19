"""Connector routes — read from DB scoped to the active project.

Each connector tile is (user, project, tool). A user can connect the same
tool to multiple projects with different workspaces.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.clients.base import propagate_headers
from app.clients.connectors import ConnectorManagerClient
from app.db import db
from app.deps import CurrentProject, CurrentUser, get_http_client
from app.repositories.actions import ActionsRepository

router = APIRouter()

PHASE_1_TOOLS = ("slack", "notion", "gmail", "gdrive", "github")


@router.get("")
async def list_connectors(
    user_id: CurrentUser, project: CurrentProject
) -> list[dict[str, Any]]:
    repo = ActionsRepository(db.raw)
    project_id = project.primary
    if project_id is None:
        return []
    connected = {
        r["tool_name"]: r for r in await repo.connectors_for_project(user_id, project_id)
    }
    tiles: list[dict[str, Any]] = []
    for tool in PHASE_1_TOOLS:
        row = connected.get(tool)
        tiles.append(
            {
                "tool": tool,
                "project_id": project_id,
                "status": row["status"] if row else "disconnected",
                "health": row["health_status"] if row else None,
                "last_sync": row["last_sync"].isoformat() if row and row["last_sync"] else None,
                "permissions": row["permissions"] if row else {"read": False, "write": False},
                "workspace_name": row.get("workspace_name") if row else None,
            }
        )
    return tiles


@router.post("/{tool}/connect")
async def connect(
    tool: str, req: Request, user_id: CurrentUser, project: CurrentProject
) -> dict[str, Any]:
    if tool not in PHASE_1_TOOLS:
        return {"tool": tool, "status": "unsupported"}
    project_id = project.primary
    if project_id is None:
        return {"tool": tool, "status": "no_project"}
    client = ConnectorManagerClient(
        get_http_client(req),
        headers=propagate_headers(req),
    )
    return await client.oauth_start(tool, user_id=user_id, project_id=project_id)


@router.delete("/{tool}")
async def disconnect(
    tool: str, user_id: CurrentUser, project: CurrentProject
) -> dict[str, Any]:
    """Hard-delete the connector row for this (user, project, tool)."""
    project_id = project.primary
    if project_id is None:
        return {"tool": tool, "status": "no_project"}
    async with db.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM connectors
            WHERE user_id = $1::uuid
              AND project_id = $2::uuid
              AND tool_name = $3
            """,
            user_id,
            project_id,
            tool,
        )
    return {"tool": tool, "status": "revoked"}


@router.get("/sync-state")
async def get_sync_state(
    user_id: CurrentUser,
    req: Request,
) -> dict[str, Any]:
    client = ConnectorManagerClient(
        get_http_client(req),
        headers=propagate_headers(req),
    )
    return await client.sync_state(user_id=user_id)


@router.post("/{source}/freshen")
async def freshen_connector(
    source: str,
    user_id: CurrentUser,
    req: Request,
) -> dict[str, Any]:
    if source not in PHASE_1_TOOLS:
        raise HTTPException(404, f"unknown source '{source}'")
    client = ConnectorManagerClient(
        get_http_client(req),
        headers=propagate_headers(req),
    )
    return await client.freshen(source=source, user_id=user_id, force=True)
