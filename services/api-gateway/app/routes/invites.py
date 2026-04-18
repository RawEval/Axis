"""Invite acceptance — unauthenticated lookup + authenticated accept.

Looking up a token without being logged in lets the signup flow pre-fill
the invitee's email. Accepting an invite requires a logged-in user whose
email matches the invite.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import db
from app.deps import CurrentUser
from app.repositories.organizations import OrganizationsRepository

router = APIRouter()


@router.get("/{token}")
async def preview_invite(token: str) -> dict[str, Any]:
    """Public — lets the signup page pre-fill the invited email."""
    repo = OrganizationsRepository(db.raw)
    row = await repo.get_invite_by_token(token)
    if row is None:
        raise HTTPException(404, "invite not found, expired, or revoked")
    return {
        "org_id": str(row["org_id"]),
        "org_name": row["org_name"],
        "email": row["email"],
        "role": row["role"],
        "expires_at": row["expires_at"].isoformat(),
    }


@router.post("/{token}/accept")
async def accept_invite(token: str, user_id: CurrentUser) -> dict[str, Any]:
    repo = OrganizationsRepository(db.raw)
    invite = await repo.consume_invite(token=token, accepting_user_id=user_id)
    if invite is None:
        raise HTTPException(
            403,
            "invite cannot be accepted — make sure your logged-in email matches the invite",
        )
    return {
        "org_id": str(invite["org_id"]),
        "role": invite["role"],
        "project_id": str(invite["project_id"]) if invite.get("project_id") else None,
    }
