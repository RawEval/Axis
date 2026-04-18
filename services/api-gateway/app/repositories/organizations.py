"""Organizations + membership + invites (ADR 010).

Rule zero: role is a permission tier, never a job title. The only
allowed values are owner | admin | manager | member | viewer.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

ROLES = ("owner", "admin", "manager", "member", "viewer")
ROLE_RANK = {role: i for i, role in enumerate(ROLES)}  # owner=0, viewer=4


def role_can_invite(inviter: str, invitee: str) -> bool:
    """Monotonic invite rule — never invite above your own tier."""
    if inviter == "viewer":
        return False
    if inviter not in ROLE_RANK or invitee not in ROLE_RANK:
        return False
    return ROLE_RANK[inviter] <= ROLE_RANK[invitee]


def role_can_manage_members(role: str) -> bool:
    return role in ("owner", "admin")


class OrganizationsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ---------- Orgs -------------------------------------------------------

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT o.id, o.name, o.slug, o.plan, o.is_personal,
                       o.created_at, om.role
                FROM organizations o
                JOIN organization_members om ON om.org_id = o.id
                WHERE om.user_id = $1::uuid
                  AND om.removed_at IS NULL
                  AND o.deleted_at IS NULL
                ORDER BY o.is_personal DESC, o.created_at ASC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def get(self, user_id: str, org_id: str) -> dict[str, Any] | None:
        """Returns the org row + the caller's role in it, or None."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT o.id, o.name, o.slug, o.plan, o.is_personal,
                       o.created_at, o.updated_at, om.role
                FROM organizations o
                JOIN organization_members om ON om.org_id = o.id
                WHERE o.id = $1::uuid
                  AND om.user_id = $2::uuid
                  AND om.removed_at IS NULL
                  AND o.deleted_at IS NULL
                """,
                org_id,
                user_id,
            )
        return dict(row) if row else None

    async def create(
        self,
        *,
        user_id: str,
        name: str,
    ) -> dict[str, Any]:
        """Create a new org and add the creator as owner in one transaction."""
        async with self._pool.acquire() as conn, conn.transaction():
            org = await conn.fetchrow(
                """
                INSERT INTO organizations (name, is_personal)
                VALUES ($1, FALSE)
                RETURNING id, name, slug, plan, is_personal, created_at, updated_at
                """,
                name,
            )
            await conn.execute(
                """
                INSERT INTO organization_members (org_id, user_id, role)
                VALUES ($1, $2::uuid, 'owner')
                """,
                org["id"],
                user_id,
            )
        return {**dict(org), "role": "owner"}

    async def rename(
        self, *, user_id: str, org_id: str, name: str
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            # Only admins+ can rename
            role = await self._role_for(conn, user_id, org_id)
            if role not in ("owner", "admin"):
                return None
            row = await conn.fetchrow(
                """
                UPDATE organizations
                SET name = $1, updated_at = NOW()
                WHERE id = $2::uuid AND deleted_at IS NULL
                RETURNING id, name, slug, plan, is_personal, created_at, updated_at
                """,
                name,
                org_id,
            )
        return {**dict(row), "role": role} if row else None

    # ---------- Members ----------------------------------------------------

    async def list_members(self, user_id: str, org_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            # Caller must be a member
            caller_role = await self._role_for(conn, user_id, org_id)
            if caller_role is None:
                return []
            rows = await conn.fetch(
                """
                SELECT om.id, om.user_id, om.role, om.joined_at, om.invited_by,
                       u.email, u.name
                FROM organization_members om
                JOIN users u ON u.id = om.user_id
                WHERE om.org_id = $1::uuid
                  AND om.removed_at IS NULL
                ORDER BY
                    CASE om.role
                        WHEN 'owner' THEN 0
                        WHEN 'admin' THEN 1
                        WHEN 'manager' THEN 2
                        WHEN 'member' THEN 3
                        WHEN 'viewer' THEN 4
                        ELSE 5
                    END,
                    om.joined_at ASC
                """,
                org_id,
            )
        return [dict(r) for r in rows]

    async def change_role(
        self, *, caller_id: str, org_id: str, target_user_id: str, new_role: str
    ) -> bool:
        if new_role not in ROLES:
            return False
        async with self._pool.acquire() as conn, conn.transaction():
            caller_role = await self._role_for(conn, caller_id, org_id)
            if not role_can_manage_members(caller_role or ""):
                return False
            target_role = await self._role_for(conn, target_user_id, org_id)
            if target_role is None:
                return False
            # Admins cannot touch owners
            if caller_role == "admin" and target_role == "owner":
                return False
            # Cannot demote the last owner
            if target_role == "owner" and new_role != "owner":
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM organization_members
                    WHERE org_id = $1::uuid AND role = 'owner' AND removed_at IS NULL
                    """,
                    org_id,
                )
                if count <= 1:
                    return False
            await conn.execute(
                """
                UPDATE organization_members
                SET role = $3
                WHERE org_id = $1::uuid AND user_id = $2::uuid
                """,
                org_id,
                target_user_id,
                new_role,
            )
        return True

    async def remove_member(
        self, *, caller_id: str, org_id: str, target_user_id: str
    ) -> bool:
        async with self._pool.acquire() as conn, conn.transaction():
            caller_role = await self._role_for(conn, caller_id, org_id)
            if not role_can_manage_members(caller_role or ""):
                return False
            target_role = await self._role_for(conn, target_user_id, org_id)
            if target_role is None:
                return False
            if caller_role == "admin" and target_role == "owner":
                return False
            if target_role == "owner":
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM organization_members
                    WHERE org_id = $1::uuid AND role = 'owner' AND removed_at IS NULL
                    """,
                    org_id,
                )
                if count <= 1:
                    return False
            await conn.execute(
                """
                UPDATE organization_members
                SET removed_at = NOW()
                WHERE org_id = $1::uuid AND user_id = $2::uuid
                """,
                org_id,
                target_user_id,
            )
        return True

    # ---------- Invites ----------------------------------------------------

    async def create_invite(
        self,
        *,
        caller_id: str,
        org_id: str,
        email: str,
        role: str,
        project_id: str | None,
        note: str | None,
        expires_in_days: int = 7,
    ) -> dict[str, Any] | None:
        if role not in ROLES:
            return None
        async with self._pool.acquire() as conn:
            caller_role = await self._role_for(conn, caller_id, org_id)
            if caller_role is None:
                return None
            # Monotonic rule
            if not role_can_invite(caller_role, role):
                return None
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            row = await conn.fetchrow(
                """
                INSERT INTO organization_invites
                    (org_id, email, role, project_id, token, invited_by, note, expires_at)
                VALUES ($1::uuid, $2, $3, $4::uuid, $5, $6::uuid, $7, $8)
                RETURNING id, org_id, email, role, project_id, token,
                          created_at, expires_at
                """,
                org_id,
                email.lower(),
                role,
                project_id,
                token,
                caller_id,
                note,
                expires_at,
            )
        return dict(row)

    async def list_pending_invites(
        self, caller_id: str, org_id: str
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            role = await self._role_for(conn, caller_id, org_id)
            if not role_can_manage_members(role or ""):
                return []
            rows = await conn.fetch(
                """
                SELECT id, email, role, project_id, created_at, expires_at
                FROM organization_invites
                WHERE org_id = $1::uuid
                  AND consumed_at IS NULL
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                ORDER BY created_at DESC
                """,
                org_id,
            )
        return [dict(r) for r in rows]

    async def revoke_invite(
        self, caller_id: str, org_id: str, invite_id: str
    ) -> bool:
        async with self._pool.acquire() as conn:
            role = await self._role_for(conn, caller_id, org_id)
            if not role_can_manage_members(role or ""):
                return False
            result = await conn.execute(
                """
                UPDATE organization_invites
                SET revoked_at = NOW()
                WHERE id = $1::uuid AND org_id = $2::uuid
                  AND consumed_at IS NULL AND revoked_at IS NULL
                """,
                invite_id,
                org_id,
            )
        return result.endswith(" 1")

    async def get_invite_by_token(self, token: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT i.id, i.org_id, i.email, i.role, i.project_id,
                       i.expires_at, o.name AS org_name
                FROM organization_invites i
                JOIN organizations o ON o.id = i.org_id
                WHERE i.token = $1
                  AND i.consumed_at IS NULL
                  AND i.revoked_at IS NULL
                  AND i.expires_at > NOW()
                """,
                token,
            )
        return dict(row) if row else None

    async def consume_invite(
        self, *, token: str, accepting_user_id: str
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn, conn.transaction():
            invite = await conn.fetchrow(
                """
                SELECT id, org_id, email, role, project_id, expires_at
                FROM organization_invites
                WHERE token = $1
                  AND consumed_at IS NULL
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                FOR UPDATE
                """,
                token,
            )
            if invite is None:
                return None

            # Verify the accepting user's email matches the invite
            user_email = await conn.fetchval(
                "SELECT email FROM users WHERE id = $1::uuid",
                accepting_user_id,
            )
            if not user_email or user_email.lower() != invite["email"].lower():
                return None

            # Upsert org membership
            await conn.execute(
                """
                INSERT INTO organization_members (org_id, user_id, role, invited_by)
                VALUES ($1, $2::uuid, $3,
                    (SELECT invited_by FROM organization_invites WHERE id = $4::uuid))
                ON CONFLICT (org_id, user_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    removed_at = NULL
                """,
                invite["org_id"],
                accepting_user_id,
                invite["role"],
                invite["id"],
            )

            # Optional project-scoped membership
            if invite["project_id"] is not None:
                await conn.execute(
                    """
                    INSERT INTO project_members (project_id, user_id, role)
                    VALUES ($1, $2::uuid, $3)
                    ON CONFLICT (project_id, user_id) DO UPDATE SET
                        role = EXCLUDED.role,
                        removed_at = NULL
                    """,
                    invite["project_id"],
                    accepting_user_id,
                    invite["role"],
                )

            # Mark consumed
            await conn.execute(
                "UPDATE organization_invites SET consumed_at = NOW() WHERE id = $1::uuid",
                invite["id"],
            )
        return dict(invite)

    # ---------- helpers ----------------------------------------------------

    @staticmethod
    async def _role_for(
        conn: asyncpg.Connection, user_id: str, org_id: str
    ) -> str | None:
        return await conn.fetchval(
            """
            SELECT role FROM organization_members
            WHERE user_id = $1::uuid AND org_id = $2::uuid AND removed_at IS NULL
            """,
            user_id,
            org_id,
        )
