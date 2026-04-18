"""Projects routes — CRUD + set-default."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.db import db
from app.deps import CurrentUser
from app.repositories.projects import ProjectsRepository

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row.get("description"),
        "is_default": row["is_default"],
        "settings": row.get("settings") or {},
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.get("")
async def list_projects(user_id: CurrentUser) -> list[dict[str, Any]]:
    repo = ProjectsRepository(db.raw)
    rows = await repo.list_for_user(user_id)
    return [_serialize(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, user_id: CurrentUser) -> dict[str, Any]:
    repo = ProjectsRepository(db.raw)
    try:
        row = await repo.create(user_id=user_id, name=body.name, description=body.description)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return _serialize(row)


@router.get("/{project_id}")
async def get_project(project_id: str, user_id: CurrentUser) -> dict[str, Any]:
    repo = ProjectsRepository(db.raw)
    row = await repo.get(user_id, project_id)
    if row is None:
        raise HTTPException(404, "project not found")
    return _serialize(row)


@router.patch("/{project_id}")
async def update_project(
    project_id: str, body: ProjectUpdate, user_id: CurrentUser
) -> dict[str, Any]:
    repo = ProjectsRepository(db.raw)
    try:
        row = await repo.rename(
            user_id=user_id,
            project_id=project_id,
            name=body.name,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    if row is None:
        raise HTTPException(404, "project not found")
    return _serialize(row)


@router.post("/{project_id}/set-default")
async def set_default_project(project_id: str, user_id: CurrentUser) -> dict[str, Any]:
    repo = ProjectsRepository(db.raw)
    existing = await repo.get(user_id, project_id)
    if existing is None:
        raise HTTPException(404, "project not found")
    await repo.set_default(user_id, project_id)
    row = await repo.get(user_id, project_id)
    return _serialize(row)  # type: ignore[arg-type]


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user_id: CurrentUser) -> None:
    repo = ProjectsRepository(db.raw)
    existing = await repo.get(user_id, project_id)
    if existing is None:
        raise HTTPException(404, "project not found")
    if existing["is_default"]:
        raise HTTPException(400, "cannot delete the default project")
    ok = await repo.delete(user_id, project_id)
    if not ok:
        raise HTTPException(404, "project not found")
