"""Repository for user-supplied OAuth client credentials (BYO, ADR 003)."""
from __future__ import annotations

from typing import Any

import asyncpg

from app.security import decrypt_token, encrypt_token


class UserOAuthAppsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tool_name, client_id, redirect_uri, extra, created_at, updated_at
                FROM user_oauth_apps
                WHERE user_id = $1::uuid
                ORDER BY tool_name
                """,
                user_id,
            )
        # Secrets never returned; callers get an `is_custom: true` marker.
        return [
            {
                "tool": r["tool_name"],
                "client_id": r["client_id"],
                "client_secret": "[redacted]",
                "redirect_uri": r["redirect_uri"],
                "extra": r["extra"],
                "is_custom": True,
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]

    async def get(self, user_id: str, tool: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tool_name, client_id, client_secret_encrypted, redirect_uri,
                       extra, created_at, updated_at
                FROM user_oauth_apps
                WHERE user_id = $1::uuid AND tool_name = $2
                """,
                user_id,
                tool,
            )
        return dict(row) if row else None

    async def get_decrypted(self, user_id: str, tool: str) -> dict[str, Any] | None:
        """Fetch + decrypt for use in the OAuth flow. Never exposed via API."""
        row = await self.get(user_id, tool)
        if row is None:
            return None
        return {
            "client_id": row["client_id"],
            "client_secret": decrypt_token(row["client_secret_encrypted"]),
            "redirect_uri": row["redirect_uri"],
            "extra": row["extra"],
        }

    async def upsert(
        self,
        *,
        user_id: str,
        tool: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
    ) -> dict[str, Any]:
        enc = encrypt_token(client_secret)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_oauth_apps (
                    user_id, tool_name, client_id, client_secret_encrypted, redirect_uri
                )
                VALUES ($1::uuid, $2, $3, $4, $5)
                ON CONFLICT (user_id, tool_name) DO UPDATE SET
                    client_id = EXCLUDED.client_id,
                    client_secret_encrypted = EXCLUDED.client_secret_encrypted,
                    redirect_uri = EXCLUDED.redirect_uri,
                    updated_at = NOW()
                RETURNING tool_name, client_id, redirect_uri, created_at, updated_at
                """,
                user_id,
                tool,
                client_id,
                enc,
                redirect_uri,
            )
        return {
            "tool": row["tool_name"],
            "client_id": row["client_id"],
            "client_secret": "[redacted]",
            "redirect_uri": row["redirect_uri"],
            "is_custom": True,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def delete(self, user_id: str, tool: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_oauth_apps WHERE user_id = $1::uuid AND tool_name = $2",
                user_id,
                tool,
            )
        return result.endswith(" 1")
