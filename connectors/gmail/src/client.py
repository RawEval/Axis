"""Gmail HTTP client — thin wrapper around the Gmail REST API.

Takes a decrypted OAuth access token at call time; never stores it.

Only the methods the agent needs in Session 3: list messages by Gmail
search query, fetch one message (for snippet + metadata), and draft/send.
Send is always gated upstream (spec §6.2 — Gmail is one of the ALWAYS-gated
write actions).

Docs: https://developers.google.com/gmail/api/reference/rest/v1/users.messages
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient:
    def __init__(self, *, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
        }

    async def list_messages(
        self, query: str = "", *, limit: int = 10
    ) -> list[dict[str, Any]]:
        """messages.list — Gmail search syntax (``from:`` / ``subject:`` / etc)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages",
                headers=self._headers,
                params={"q": query, "maxResults": limit},
            )
            resp.raise_for_status()
            body = resp.json()
        return body.get("messages", [])

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """messages.get with ``format=metadata`` — headers + snippet, no body."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{message_id}",
                headers=self._headers,
                params={
                    "format": "metadata",
                    "metadataHeaders": ["From", "To", "Subject", "Date"],
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def search(self, query: str = "", *, limit: int = 10) -> list[dict[str, Any]]:
        """Return hydrated messages (metadata + snippet) for a Gmail query."""
        ids = await self.list_messages(query, limit=limit)
        results: list[dict[str, Any]] = []
        for m in ids:
            try:
                full = await self.get_message(m["id"])
                results.append(full)
            except Exception:  # noqa: BLE001
                continue
        return results

    async def list_recent(
        self,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return hydrated Gmail messages received in the time window.

        Uses Gmail search syntax (`after:UNIX_TIMESTAMP`). For default
        ('today / past day') we pass `newer_than:1d` which Gmail accepts.
        Each message dict has the standard Gmail v1 shape — `id`,
        `internalDate`, `snippet`, `payload.headers`.

        Phase 2 will replace this with `users.history.list` for true delta
        sync via webhook. For Phase 1 this is good enough.
        """
        if since is not None:
            query = f"after:{int(since.timestamp())}"
        else:
            query = "newer_than:1d"
        return await self.search(query, limit=limit)

    async def send_message(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        """messages.send — ALWAYS gated upstream. Here we just do the send.

        The caller is responsible for surfacing the preview + confirmation
        per ADR 006 before invoking this method.
        """
        raw = self._build_raw_mime(to=to, subject=subject, body=body)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GMAIL_API_BASE}/messages/send",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"raw": raw},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_draft(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        """drafts.create — stages a Gmail draft without sending.

        Drafts are cheap and reversible (the user can delete or edit before
        sending), so the agent can create them without the strict ALWAYS-gate
        treatment that send carries. Returns ``{id, message: {...}}``.
        """
        raw = self._build_raw_mime(to=to, subject=subject, body=body)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GMAIL_API_BASE}/drafts",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"message": {"raw": raw}},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _build_raw_mime(*, to: str, subject: str, body: str) -> str:
        mime = (
            f"From: me\r\nTo: {to}\r\nSubject: {subject}\r\n"
            f"MIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
        )
        return base64.urlsafe_b64encode(mime.encode("utf-8")).decode("ascii").rstrip("=")
