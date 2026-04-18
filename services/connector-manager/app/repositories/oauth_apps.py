"""Multi-scope BYO OAuth credentials (ADR 003 extended, migration 008).

Three scopes:
    - user      personal credentials (only that user can use them)
    - org       shared across the organization (admin+ can save)
    - project   scoped to one project (manager+ of the project can save)

Resolution order at call time:
    project → org → user → Axis default (from settings)

The first hit wins. This matches the Pipedream BYO pattern — the narrower
scope always overrides the broader one.
"""
from __future__ import annotations

from typing import Any

import asyncpg

from app.security import decrypt_token, encrypt_token

Scope = str  # 'user' | 'org' | 'project'


class OAuthAppsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ---------- Resolver ---------------------------------------------------

    async def resolve(
        self,
        *,
        tool: str,
        user_id: str | None,
        org_id: str | None,
        project_id: str | None,
    ) -> dict[str, Any] | None:
        """Walk project → org → user and return the first hit, decrypted.

        Returns None if no BYO app matches; the caller should fall back to
        the Axis default credentials from settings.
        """
        async with self._pool.acquire() as conn:
            if project_id:
                row = await conn.fetchrow(
                    """
                    SELECT scope, client_id, client_secret_encrypted, redirect_uri
                    FROM oauth_apps
                    WHERE scope = 'project' AND project_id = $1::uuid
                      AND tool_name = $2
                    """,
                    project_id,
                    tool,
                )
                if row:
                    return self._decrypt(row)

            if org_id:
                row = await conn.fetchrow(
                    """
                    SELECT scope, client_id, client_secret_encrypted, redirect_uri
                    FROM oauth_apps
                    WHERE scope = 'org' AND org_id = $1::uuid
                      AND tool_name = $2
                    """,
                    org_id,
                    tool,
                )
                if row:
                    return self._decrypt(row)

            if user_id:
                row = await conn.fetchrow(
                    """
                    SELECT scope, client_id, client_secret_encrypted, redirect_uri
                    FROM oauth_apps
                    WHERE scope = 'user' AND user_id = $1::uuid
                      AND tool_name = $2
                    """,
                    user_id,
                    tool,
                )
                if row:
                    return self._decrypt(row)
        return None

    # ---------- CRUD -------------------------------------------------------

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """All personal apps for this user (scope='user'), secrets redacted."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tool_name, client_id, redirect_uri, created_at, updated_at
                FROM oauth_apps
                WHERE scope = 'user' AND user_id = $1::uuid
                ORDER BY tool_name
                """,
                user_id,
            )
        return [
            {
                "id": str(r["id"]),
                "scope": "user",
                "tool": r["tool_name"],
                "client_id": r["client_id"],
                "client_secret": "[redacted]",
                "redirect_uri": r["redirect_uri"],
                "is_custom": True,
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]

    async def list_for_org(self, org_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tool_name, client_id, redirect_uri, created_at, updated_at
                FROM oauth_apps
                WHERE scope = 'org' AND org_id = $1::uuid
                ORDER BY tool_name
                """,
                org_id,
            )
        return [
            {
                "id": str(r["id"]),
                "scope": "org",
                "tool": r["tool_name"],
                "client_id": r["client_id"],
                "client_secret": "[redacted]",
                "redirect_uri": r["redirect_uri"],
                "is_custom": True,
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]

    async def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tool_name, client_id, redirect_uri, created_at, updated_at
                FROM oauth_apps
                WHERE scope = 'project' AND project_id = $1::uuid
                ORDER BY tool_name
                """,
                project_id,
            )
        return [
            {
                "id": str(r["id"]),
                "scope": "project",
                "tool": r["tool_name"],
                "client_id": r["client_id"],
                "client_secret": "[redacted]",
                "redirect_uri": r["redirect_uri"],
                "is_custom": True,
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]

    async def upsert_user(
        self,
        *,
        user_id: str,
        tool: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        return await self._upsert(
            scope="user",
            user_id=user_id,
            org_id=None,
            project_id=None,
            created_by=user_id,
            tool=tool,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

    async def upsert_org(
        self,
        *,
        created_by: str,
        org_id: str,
        tool: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        return await self._upsert(
            scope="org",
            user_id=None,
            org_id=org_id,
            project_id=None,
            created_by=created_by,
            tool=tool,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

    async def upsert_project(
        self,
        *,
        created_by: str,
        project_id: str,
        tool: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        return await self._upsert(
            scope="project",
            user_id=None,
            org_id=None,
            project_id=project_id,
            created_by=created_by,
            tool=tool,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

    async def delete_user(self, user_id: str, tool: str) -> bool:
        return await self._delete("user", user_id, tool)

    async def delete_org(self, org_id: str, tool: str) -> bool:
        return await self._delete("org", org_id, tool)

    async def delete_project(self, project_id: str, tool: str) -> bool:
        return await self._delete("project", project_id, tool)

    # ---------- Internals --------------------------------------------------

    async def _upsert(
        self,
        *,
        scope: Scope,
        user_id: str | None,
        org_id: str | None,
        project_id: str | None,
        created_by: str,
        tool: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        enc = encrypt_token(client_secret)
        async with self._pool.acquire() as conn:
            # Delete any existing row at the same (scope, identity, tool) before
            # inserting a new one. Cheaper than building a custom ON CONFLICT
            # target that respects the partial indexes.
            if scope == "user":
                await conn.execute(
                    "DELETE FROM oauth_apps WHERE scope = 'user' AND user_id = $1::uuid AND tool_name = $2",
                    user_id,
                    tool,
                )
            elif scope == "org":
                await conn.execute(
                    "DELETE FROM oauth_apps WHERE scope = 'org' AND org_id = $1::uuid AND tool_name = $2",
                    org_id,
                    tool,
                )
            elif scope == "project":
                await conn.execute(
                    "DELETE FROM oauth_apps WHERE scope = 'project' AND project_id = $1::uuid AND tool_name = $2",
                    project_id,
                    tool,
                )
            row = await conn.fetchrow(
                """
                INSERT INTO oauth_apps (
                    scope, user_id, org_id, project_id,
                    tool_name, client_id, client_secret_encrypted, redirect_uri,
                    created_by
                )
                VALUES ($1, $2::uuid, $3::uuid, $4::uuid, $5, $6, $7, $8, $9::uuid)
                RETURNING id, tool_name, client_id, redirect_uri, created_at, updated_at
                """,
                scope,
                user_id,
                org_id,
                project_id,
                tool,
                client_id,
                enc,
                redirect_uri,
                created_by,
            )
        return {
            "id": str(row["id"]),
            "scope": scope,
            "tool": row["tool_name"],
            "client_id": row["client_id"],
            "client_secret": "[redacted]",
            "redirect_uri": row["redirect_uri"],
            "is_custom": True,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def _delete(self, scope: Scope, identity: str, tool: str) -> bool:
        col = {"user": "user_id", "org": "org_id", "project": "project_id"}[scope]
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM oauth_apps
                WHERE scope = $1 AND {col} = $2::uuid AND tool_name = $3
                """,
                scope,
                identity,
                tool,
            )
        return result.endswith(" 1")

    @staticmethod
    def _decrypt(row: asyncpg.Record) -> dict[str, Any]:
        return {
            "scope": row["scope"],
            "client_id": row["client_id"],
            "client_secret": decrypt_token(row["client_secret_encrypted"]),
            "redirect_uri": row["redirect_uri"],
        }
