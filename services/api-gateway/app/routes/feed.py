"""Feed routes — read proactive surfaces scoped to the active project."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db import db
from app.deps import CurrentProject, CurrentUser
from app.repositories.actions import ActionsRepository

router = APIRouter()


@router.get("")
async def get_feed(
    user_id: CurrentUser, project: CurrentProject
) -> list[dict[str, Any]]:
    repo = ActionsRepository(db.raw)
    project_id = project.primary
    if project_id is None:
        return []
    return await repo.surfaces_for_project(user_id, project_id)


@router.post("/{surface_id}/accept")
async def accept(
    surface_id: str, user_id: CurrentUser, project: CurrentProject
) -> dict[str, Any]:
    async with db.acquire() as conn:
        await conn.execute(
            """
            UPDATE proactive_surfaces
            SET status = 'accepted', user_response_at = NOW()
            WHERE id = $1::uuid AND user_id = $2::uuid
              AND project_id = ANY($3::uuid[])
            """,
            surface_id,
            user_id,
            project.ids,
        )
    return {"id": surface_id, "status": "accepted"}


@router.post("/{surface_id}/dismiss")
async def dismiss(
    surface_id: str, user_id: CurrentUser, project: CurrentProject
) -> dict[str, Any]:
    async with db.acquire() as conn:
        await conn.execute(
            """
            UPDATE proactive_surfaces
            SET status = 'dismissed', user_response_at = NOW()
            WHERE id = $1::uuid AND user_id = $2::uuid
              AND project_id = ANY($3::uuid[])
            """,
            surface_id,
            user_id,
            project.ids,
        )
    return {"id": surface_id, "status": "dismissed"}
