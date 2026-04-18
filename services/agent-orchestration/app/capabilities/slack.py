"""Slack capabilities — search, summarize, thread context, user lookup, post, react.

All calls go through connector-manager for token decryption. Read
capabilities are auto or ask; write capabilities are always ask (gated).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient


def _project_guard(project_id: str | None) -> CapabilityResult | None:
    if not project_id:
        return CapabilityResult(summary="no active project", content=[], error="slack requires an active project")
    return None


def _error_guard(resp: dict[str, Any], name: str) -> CapabilityResult | None:
    if "error" in resp:
        return CapabilityResult(summary=f"{name} error", content=[], error=str(resp["error"]))
    return None


# ── connector.slack.search ──────────────────────────────────────────────


@dataclass
class _SlackSearch:
    name: str = "connector.slack.search"
    description: str = (
        "Search the user's Slack workspace for messages matching a keyword. "
        "Returns messages across all joined channels. Use for 'find what Alice "
        "said about pricing' or 'search for deployment updates'."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords to search for."},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
            "required": ["query"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_search(user_id=user_id, project_id=project_id, query=inputs.get("query", ""), limit=int(inputs.get("limit", 20)))
        except Exception as e:
            return CapabilityResult(summary="slack search failed", content=[], error=str(e))
        if err := _error_guard(resp, "slack search"): return err
        hits = resp.get("results", [])
        citations = [Citation(source_type="slack_message", provider="slack", ref_id=h.get("id"), url=h.get("url"), title=h.get("title"), actor=h.get("author"), excerpt=h.get("excerpt"), occurred_at=h.get("ts")) for h in hits]
        fallback = " (via channel history fallback)" if resp.get("fallback_used") else ""
        return CapabilityResult(summary=f"found {len(hits)} Slack messages{fallback}", content=hits, citations=citations)


# ── connector.slack.channel_summary ─────────────────────────────────────


@dataclass
class _SlackChannelSummary:
    name: str = "connector.slack.channel_summary"
    description: str = (
        "Fetch recent messages from a Slack channel for summarization. "
        "Returns the last N messages with user IDs, text, reactions, and "
        "thread reply counts. Use when the user asks 'summarize #product "
        "this week' or 'what's been happening in #engineering'."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Slack channel ID (e.g. C0123ABC)."},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200, "description": "How many recent messages to fetch."},
            },
            "required": ["channel_id"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_history(user_id=user_id, project_id=project_id, channel_id=inputs["channel_id"], limit=int(inputs.get("limit", 50)))
        except Exception as e:
            return CapabilityResult(summary="channel summary failed", content=[], error=str(e))
        if err := _error_guard(resp, "channel summary"): return err
        messages = resp.get("messages", [])
        return CapabilityResult(
            summary=f"fetched {len(messages)} messages from channel",
            content=messages,
            citations=[Citation(source_type="slack_channel", provider="slack", ref_id=inputs["channel_id"], title=f"#{inputs['channel_id']}", excerpt=f"{len(messages)} messages")],
        )


# ── connector.slack.thread_context ──────────────────────────────────────


@dataclass
class _SlackThreadContext:
    name: str = "connector.slack.thread_context"
    description: str = (
        "Fetch the full thread replies for a specific Slack message. Use "
        "when you need to understand the full conversation context around "
        "a message — 'get the thread where Alice asked about the deploy'."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Channel where the thread lives."},
                "thread_ts": {"type": "string", "description": "Timestamp of the parent message."},
                "limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 500},
            },
            "required": ["channel_id", "thread_ts"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_thread(user_id=user_id, project_id=project_id, channel_id=inputs["channel_id"], thread_ts=inputs["thread_ts"], limit=int(inputs.get("limit", 100)))
        except Exception as e:
            return CapabilityResult(summary="thread fetch failed", content=[], error=str(e))
        if err := _error_guard(resp, "thread context"): return err
        messages = resp.get("messages", [])
        return CapabilityResult(
            summary=f"fetched {len(messages)} thread replies",
            content=messages,
            citations=[Citation(source_type="slack_thread", provider="slack", ref_id=f"{inputs['channel_id']}:{inputs['thread_ts']}", title="Slack thread", excerpt=f"{len(messages)} replies")],
        )


# ── connector.slack.user_profile ────────────────────────────────────────


@dataclass
class _SlackUserProfile:
    name: str = "connector.slack.user_profile"
    description: str = (
        "Look up a Slack user's profile — real name, display name, email, "
        "title, timezone. Use when the agent needs to resolve a user ID "
        "to a human-readable name or contact info."
    )
    scope: str = "read"
    default_permission: str = "auto"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "slack_user_id": {"type": "string", "description": "Slack user ID (e.g. U0123ABC)."},
            },
            "required": ["slack_user_id"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_user(user_id=user_id, project_id=project_id, slack_user_id=inputs["slack_user_id"])
        except Exception as e:
            return CapabilityResult(summary="user lookup failed", content=[], error=str(e))
        if err := _error_guard(resp, "user profile"): return err
        return CapabilityResult(
            summary=f"found user {resp.get('real_name') or resp.get('name')}",
            content=[resp],
            citations=[Citation(source_type="slack_user", provider="slack", ref_id=inputs["slack_user_id"], title=resp.get("real_name") or resp.get("name"), actor=resp.get("email"))],
        )


# ── connector.slack.post (WRITE — gated) ───────────────────────────────


@dataclass
class _SlackPost:
    name: str = "connector.slack.post"
    description: str = (
        "Post a message to a Slack channel or reply in a thread. This is "
        "a WRITE action that requires user confirmation before executing. "
        "Use when the user asks 'send a message to #general about the deploy' "
        "or 'reply to Alice's question in the thread'."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel ID to post in."},
                "text": {"type": "string", "description": "Message text to post."},
                "thread_ts": {"type": "string", "description": "If replying in a thread, the parent message timestamp."},
            },
            "required": ["channel", "text"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_post(user_id=user_id, project_id=project_id, channel=inputs["channel"], text=inputs["text"], thread_ts=inputs.get("thread_ts"))
        except Exception as e:
            return CapabilityResult(summary="slack post failed", content=[], error=str(e))
        if err := _error_guard(resp, "slack post"): return err
        return CapabilityResult(
            summary=f"posted to {resp.get('channel', inputs['channel'])}",
            content=[resp],
            citations=[Citation(source_type="slack_message", provider="slack", ref_id=resp.get("ts"), title="Posted message", excerpt=inputs["text"][:200])],
        )


# ── connector.slack.react (WRITE — gated) ──────────────────────────────


@dataclass
class _SlackReact:
    name: str = "connector.slack.react"
    description: str = (
        "Add a reaction emoji to a Slack message. This is a WRITE action "
        "that requires user confirmation. Use when the user says 'react "
        "with thumbs up to Alice's message'."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel ID containing the message."},
                "timestamp": {"type": "string", "description": "Timestamp of the message to react to."},
                "emoji": {"type": "string", "description": "Emoji name without colons (e.g. 'thumbsup', 'rocket')."},
            },
            "required": ["channel", "timestamp", "emoji"],
        }

    async def __call__(self, *, user_id: str, project_id: str | None, org_id: str | None, inputs: dict[str, Any]) -> CapabilityResult:
        if err := _project_guard(project_id): return err
        client = ConnectorManagerClient()
        try:
            resp = await client.slack_react(user_id=user_id, project_id=project_id, channel=inputs["channel"], timestamp=inputs["timestamp"], emoji=inputs["emoji"])
        except Exception as e:
            return CapabilityResult(summary="slack react failed", content=[], error=str(e))
        if err := _error_guard(resp, "slack react"): return err
        return CapabilityResult(
            summary=f"reacted with :{inputs['emoji']}: in {inputs['channel']}",
            content=[resp],
        )


# ── Registry ────────────────────────────────────────────────────────────
# The auto-discovery in registry.py looks for a module-level CAPABILITY.
# Since we have 6 capabilities, we use CAPABILITIES (plural) and the
# registry's _autoload() needs to handle that. For backward compat we
# also export CAPABILITY as the first one (search).

CAPABILITIES = [
    _SlackSearch(),
    _SlackChannelSummary(),
    _SlackThreadContext(),
    _SlackUserProfile(),
    _SlackPost(),
    _SlackReact(),
]
CAPABILITY = CAPABILITIES[0]
