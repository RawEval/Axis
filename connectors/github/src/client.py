"""GitHub HTTP client — thin wrapper around the REST API.

Uses the decrypted OAuth user token at call time; never stores it. REST
(not GraphQL) because the search endpoint is simpler and the agent only
needs a handful of read operations.

Docs: https://docs.github.com/en/rest
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, *, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def search_issues(
        self, query: str, *, limit: int = 10
    ) -> list[dict[str, Any]]:
        """/search/issues — covers both issues and pull requests.

        The caller can prefix with ``is:pr`` / ``is:issue`` to narrow; if
        they pass a bare keyword we search across both types in the user's
        repos by default.
        """
        q = query.strip() or "is:open"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/search/issues",
                headers=self._headers,
                params={"q": q, "per_page": limit},
            )
            resp.raise_for_status()
            body = resp.json()
        return body.get("items", [])

    async def get_pull_request(
        self, owner: str, repo: str, number: int
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{number}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Gated upstream — this is a write action per ADR 006."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self._headers,
                json={"body": body},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_issue(
        self,
        *,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """POST /repos/{owner}/{repo}/issues — gated upstream."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def authenticated_user(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_recent(
        self,
        *,
        since: "datetime | None" = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return public events for the authenticated user, optionally
        filtered by `since`. Stops scanning once it hits an event older than
        `since` (events are sorted newest-first by GitHub).

        Phase 2 will replace this with webhooks (per-repo or per-org). For
        Phase 1 the user's events feed is sufficient.
        """
        # Step 1: get the authenticated user's login (for the events URL).
        me = await self.authenticated_user()
        login = me.get("login")
        if not login:
            return []

        # Step 2: fetch one page of events (most recent first).
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/users/{login}/events",
                headers=self._headers,
                params={"per_page": min(100, limit)},
            )
            resp.raise_for_status()
            events: list[dict[str, Any]] = resp.json()

        if since is None:
            return events[:limit]

        # Filter client-side; stop early on the first event older than `since`.
        kept: list[dict[str, Any]] = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
            except (ValueError, TypeError, KeyError):
                continue
            if ts < since:
                break
            kept.append(e)
            if len(kept) >= limit:
                break
        return kept
