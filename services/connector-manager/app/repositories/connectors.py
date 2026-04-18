"""Repository for the connectors table + oauth_states side-table.

Every read/write is scoped by (user_id, project_id, tool_name) since the
projects model (ADR 002). One user can connect the same tool to multiple
projects with different workspaces.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

import asyncpg


class ConnectorsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ---------- OAuth state -----------------------------------------------

    async def create_oauth_state(
        self,
        *,
        user_id: str,
        tool: str,
        project_id: str,
        pkce_verifier: str | None = None,
        redirect_after: str | None = None,
    ) -> str:
        state = secrets.token_urlsafe(32)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO oauth_states
                    (state, user_id, tool, project_id, pkce_verifier, redirect_after)
                VALUES ($1, $2::uuid, $3, $4::uuid, $5, $6)
                """,
                state,
                user_id,
                tool,
                project_id,
                pkce_verifier,
                redirect_after,
            )
        return state

    async def pop_oauth_state(self, state: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM oauth_states
                WHERE state = $1 AND expires_at > NOW()
                RETURNING user_id, project_id, tool, pkce_verifier, redirect_after
                """,
                state,
            )
        return dict(row) if row else None

    # ---------- Connector upsert / read / update --------------------------

    async def upsert_connector(
        self,
        *,
        user_id: str,
        project_id: str,
        tool: str,
        access_token_enc: bytes,
        refresh_token_enc: bytes | None,
        expires_at: datetime | None,
        scopes: str | None,
        workspace_id: str | None,
        workspace_name: str | None,
    ) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO connectors (
                    user_id, project_id, tool_name, status, auth_token_encrypted,
                    refresh_token_encrypted, token_expires_at, scopes,
                    workspace_id, workspace_name, permissions, last_sync, health_status
                )
                VALUES (
                    $1::uuid, $2::uuid, $3, 'connected', $4, $5, $6, $7, $8, $9,
                    '{"read": true, "write": true}'::jsonb, NOW(), 'green'
                )
                ON CONFLICT (user_id, project_id, tool_name) DO UPDATE SET
                    status = 'connected',
                    auth_token_encrypted = EXCLUDED.auth_token_encrypted,
                    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    token_expires_at = EXCLUDED.token_expires_at,
                    scopes = EXCLUDED.scopes,
                    workspace_id = EXCLUDED.workspace_id,
                    workspace_name = EXCLUDED.workspace_name,
                    last_sync = NOW(),
                    health_status = 'green',
                    error_log = NULL
                RETURNING id, tool_name, status, health_status, last_sync
                """,
                user_id,
                project_id,
                tool,
                access_token_enc,
                refresh_token_enc,
                expires_at,
                scopes,
                workspace_id,
                workspace_name,
            )
        return dict(row)

    async def get_token(
        self, user_id: str, project_id: str, tool: str
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT auth_token_encrypted, refresh_token_encrypted,
                       token_expires_at, workspace_id
                FROM connectors
                WHERE user_id = $1::uuid
                  AND project_id = $2::uuid
                  AND tool_name = $3
                  AND status = 'connected'
                """,
                user_id,
                project_id,
                tool,
            )
        return dict(row) if row else None

    async def find_by_workspace(
        self, *, tool: str, workspace_id: str
    ) -> list[dict[str, Any]]:
        """Return every connector row for a given tool + workspace.

        Webhooks arrive keyed on provider workspace ids (Slack team_id,
        GitHub installation id, etc.) — not on Axis user_ids. This lets the
        webhook handler find the right (user_id, project_id) pair(s) to
        attribute the event to. More than one row is possible when multiple
        Axis users in the same org each connected the same workspace.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, project_id, tool_name, workspace_id,
                       workspace_name, status
                FROM connectors
                WHERE tool_name = $1
                  AND workspace_id = $2
                  AND status = 'connected'
                """,
                tool,
                workspace_id,
            )
        return [dict(r) for r in rows]

    async def list_connected(self, *, tool: str) -> list[dict[str, Any]]:
        """Every live connector row for a tool — used by the Notion poll task."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, project_id, tool_name,
                       auth_token_encrypted, last_sync
                FROM connectors
                WHERE tool_name = $1 AND status = 'connected'
                """,
                tool,
            )
        return [dict(r) for r in rows]

    async def touch_last_sync(self, connector_id: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE connectors SET last_sync = NOW() WHERE id = $1::uuid",
                connector_id,
            )

    async def delete_connector(
        self, user_id: str, project_id: str, tool: str
    ) -> dict[str, Any] | None:
        """Hard delete: wipes the encrypted token and all state for this connector."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM connectors
                WHERE user_id = $1::uuid AND project_id = $2::uuid AND tool_name = $3
                RETURNING auth_token_encrypted
                """,
                user_id,
                project_id,
                tool,
            )
        return dict(row) if row else None

    async def mark_error(
        self, user_id: str, project_id: str, tool: str, error: str
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE connectors
                SET health_status = 'red',
                    error_log = jsonb_build_object(
                      'error', $4,
                      'at', to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
                    )
                WHERE user_id = $1::uuid
                  AND project_id = $2::uuid
                  AND tool_name = $3
                """,
                user_id,
                project_id,
                tool,
                error,
            )

    @staticmethod
    def is_expired(token_row: dict[str, Any]) -> bool:
        exp: datetime | None = token_row.get("token_expires_at")
        if exp is None:
            return False
        return exp <= datetime.now(tz=exp.tzinfo or timezone.utc)
