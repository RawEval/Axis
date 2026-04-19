"""Slack HTTP client — comprehensive wrapper around the Web API.

Takes a decrypted xoxb bot token at construction time; never stores it.
Covers all methods the Axis Slack agent needs across read + write paths.

Docs: https://docs.slack.dev/reference/methods
Local ref: docs/references/slack/api-reference.md
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

SLACK_API_BASE = "https://slack.com/api"


class SlackError(Exception):
    """Slack returns 200 with {ok: false, error: '...'}."""


class SlackClient:
    def __init__(self, *, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _call(self, method: str, **params: Any) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{SLACK_API_BASE}/{method}",
                headers=self._headers,
                json={k: v for k, v in params.items() if v is not None},
            )
            resp.raise_for_status()
            body = resp.json()
        if not body.get("ok"):
            raise SlackError(body.get("error") or f"slack {method} failed")
        return body

    # ── Read: channels ──────────────────────────────────────────────────

    async def list_channels(
        self, *, limit: int = 200, types: str = "public_channel,private_channel"
    ) -> list[dict[str, Any]]:
        """conversations.list — all joined channels the bot can see."""
        all_channels: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body = await self._call(
                "conversations.list",
                types=types,
                limit=min(limit, 200),
                exclude_archived=True,
                cursor=cursor,
            )
            all_channels.extend(body.get("channels", []))
            cursor = (body.get("response_metadata") or {}).get("next_cursor")
            if not cursor or len(all_channels) >= limit:
                break
        return all_channels[:limit]

    async def channel_info(self, channel_id: str) -> dict[str, Any]:
        body = await self._call(
            "conversations.info", channel=channel_id, include_num_members=True
        )
        return body.get("channel", {})

    # ── Read: messages ──────────────────────────────────────────────────

    async def channel_history(
        self,
        channel_id: str,
        *,
        limit: int = 50,
        oldest: str | None = None,
        latest: str | None = None,
    ) -> list[dict[str, Any]]:
        """conversations.history — recent messages in a channel."""
        body = await self._call(
            "conversations.history",
            channel=channel_id,
            limit=limit,
            oldest=oldest,
            latest=latest,
        )
        return body.get("messages", [])

    async def thread_replies(
        self, channel_id: str, thread_ts: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        """conversations.replies — all messages in a thread."""
        body = await self._call(
            "conversations.replies",
            channel=channel_id,
            ts=thread_ts,
            limit=limit,
        )
        return body.get("messages", [])

    async def search_messages(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """search.messages — requires a user token (xoxp).

        Bot tokens can't hit this endpoint. Callers should fall back to
        channel_history scanning when this raises SlackError('not_allowed').
        """
        body = await self._call("search.messages", query=query, count=limit)
        return body.get("messages", {}).get("matches", [])

    # ── Read: users ─────────────────────────────────────────────────────

    async def user_info(self, user_id: str) -> dict[str, Any]:
        """users.info — full profile for one user."""
        body = await self._call("users.info", user=user_id)
        return body.get("user", {})

    async def list_users(self, *, limit: int = 200) -> list[dict[str, Any]]:
        all_users: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body = await self._call("users.list", limit=min(limit, 200), cursor=cursor)
            all_users.extend(body.get("members", []))
            cursor = (body.get("response_metadata") or {}).get("next_cursor")
            if not cursor or len(all_users) >= limit:
                break
        return all_users[:limit]

    # ── Read: reactions + pins ──────────────────────────────────────────

    async def reactions_get(self, channel: str, timestamp: str) -> list[dict[str, Any]]:
        body = await self._call("reactions.get", channel=channel, timestamp=timestamp)
        msg = body.get("message", {})
        return msg.get("reactions", [])

    async def pins_list(self, channel_id: str) -> list[dict[str, Any]]:
        body = await self._call("pins.list", channel=channel_id)
        return body.get("items", [])

    # ── Write: messages (GATED upstream) ────────────────────────────────

    async def post_message(
        self,
        *,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        reply_broadcast: bool = False,
    ) -> dict[str, Any]:
        """chat.postMessage — gated per ADR 006."""
        return await self._call(
            "chat.postMessage",
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            reply_broadcast=reply_broadcast or None,
        )

    async def update_message(
        self, *, channel: str, ts: str, text: str
    ) -> dict[str, Any]:
        return await self._call("chat.update", channel=channel, ts=ts, text=text)

    # ── Write: reactions (GATED upstream) ───────────────────────────────

    async def add_reaction(
        self, *, channel: str, timestamp: str, name: str
    ) -> dict[str, Any]:
        return await self._call(
            "reactions.add", channel=channel, timestamp=timestamp, name=name
        )

    # ── Read: recent (aggregate) ────────────────────────────────────────

    async def list_recent(
        self,
        *,
        since: datetime | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Aggregate messages across all joined channels, optionally filtered
        by `since`. Each message dict is annotated with `channel_id` and
        `channel_name` so callers can build event keys without a second lookup.
        """
        oldest = str(since.timestamp()) if since else None
        channels = await self.list_channels(limit=200)
        messages: list[dict[str, Any]] = []
        for ch in channels:
            if len(messages) >= limit:
                break
            try:
                history = await self.channel_history(
                    ch["id"], limit=min(100, limit - len(messages)), oldest=oldest,
                )
            except (SlackError, httpx.HTTPStatusError):
                continue  # skip the channel; surface aggregate failures elsewhere
            for m in history:
                m["channel_id"] = ch["id"]
                m["channel_name"] = ch.get("name")
                messages.append(m)
        return messages[:limit]

    # ── Identity ────────────────────────────────────────────────────────

    async def auth_test(self) -> dict[str, Any]:
        return await self._call("auth.test")
