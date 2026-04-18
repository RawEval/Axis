"""Organizations routes — ADR 010.

Role names in the API are always owner/admin/manager/member/viewer.
Clients must never send job titles.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.db import db
from app.deps import CurrentUser
from app.repositories.organizations import ROLES, OrganizationsRepository

router = APIRouter()


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OrgUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RoleChange(BaseModel):
    role: str = Field(pattern="^(owner|admin|manager|member|viewer)$")


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(owner|admin|manager|member|viewer)$")
    project_id: str | None = None
    note: str | None = Field(default=None, max_length=500)


def _serialize_org(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "slug": row.get("slug"),
        "plan": row.get("plan", "free"),
        "is_personal": row.get("is_personal", False),
        "role": row.get("role"),
        "created_at": row["created_at"].isoformat(),
    }


def _serialize_member(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": str(row["user_id"]),
        "email": row["email"],
        "name": row.get("name"),
        "role": row["role"],
        "joined_at": row["joined_at"].isoformat(),
        "invited_by": str(row["invited_by"]) if row.get("invited_by") else None,
    }


def _serialize_invite(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "email": row.get("email"),
        "role": row["role"],
        "project_id": str(row["project_id"]) if row.get("project_id") else None,
        "token": row.get("token"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "expires_at": row["expires_at"].isoformat(),
    }


@router.get("")
async def list_orgs(user_id: CurrentUser) -> list[dict[str, Any]]:
    repo = OrganizationsRepository(db.raw)
    rows = await repo.list_for_user(user_id)
    return [_serialize_org(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org(body: OrgCreate, user_id: CurrentUser) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    org = await repo.create(user_id=user_id, name=body.name)
    return _serialize_org(org)


@router.get("/{org_id}")
async def get_org(org_id: str, user_id: CurrentUser) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    row = await repo.get(user_id, org_id)
    if row is None:
        raise HTTPException(404, "organization not found")
    return _serialize_org(row)


@router.patch("/{org_id}")
async def rename_org(
    org_id: str, body: OrgUpdate, user_id: CurrentUser
) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    row = await repo.rename(user_id=user_id, org_id=org_id, name=body.name)
    if row is None:
        raise HTTPException(403, "not permitted")
    return _serialize_org(row)


# ---------- Members ---------------------------------------------------------

@router.get("/{org_id}/members")
async def list_members(org_id: str, user_id: CurrentUser) -> list[dict[str, Any]]:
    repo = OrganizationsRepository(db.raw)
    rows = await repo.list_members(user_id, org_id)
    return [_serialize_member(r) for r in rows]


@router.patch("/{org_id}/members/{target_user_id}")
async def change_role(
    org_id: str,
    target_user_id: str,
    body: RoleChange,
    user_id: CurrentUser,
) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    ok = await repo.change_role(
        caller_id=user_id,
        org_id=org_id,
        target_user_id=target_user_id,
        new_role=body.role,
    )
    if not ok:
        raise HTTPException(403, "cannot change role")
    return {"user_id": target_user_id, "role": body.role}


@router.delete("/{org_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str, target_user_id: str, user_id: CurrentUser
) -> None:
    repo = OrganizationsRepository(db.raw)
    ok = await repo.remove_member(
        caller_id=user_id,
        org_id=org_id,
        target_user_id=target_user_id,
    )
    if not ok:
        raise HTTPException(403, "cannot remove member")


# ---------- Invites ---------------------------------------------------------

@router.get("/{org_id}/invites")
async def list_invites(org_id: str, user_id: CurrentUser) -> list[dict[str, Any]]:
    repo = OrganizationsRepository(db.raw)
    rows = await repo.list_pending_invites(user_id, org_id)
    return [_serialize_invite(r) for r in rows]


@router.post("/{org_id}/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: str, body: InviteCreate, user_id: CurrentUser
) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    row = await repo.create_invite(
        caller_id=user_id,
        org_id=org_id,
        email=str(body.email),
        role=body.role,
        project_id=body.project_id,
        note=body.note,
    )
    if row is None:
        raise HTTPException(403, "cannot invite at that role")
    invite = _serialize_invite(row)
    invite["accept_url"] = f"/accept-invite/{row['token']}"
    return invite


@router.delete(
    "/{org_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_invite(org_id: str, invite_id: str, user_id: CurrentUser) -> None:
    repo = OrganizationsRepository(db.raw)
    ok = await repo.revoke_invite(user_id, org_id, invite_id)
    if not ok:
        raise HTTPException(404, "invite not found or already consumed")
