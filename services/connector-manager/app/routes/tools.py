"""Tool execution endpoints — the agent calls these to actually use a connector.

Separation of concerns: agent-orchestration owns the reasoning loop, this
service owns encrypted-token storage and provider-side API calls. The agent
never touches plaintext tokens.

Each tool returns a normalized response with `results: list[dict]` where
each hit has at least: `id`, `url`, `title`, `excerpt`. The agent turns
those into Citation objects in its capability layer.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from axis_common import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import db
from app.repositories.connectors import ConnectorsRepository
from app.security import decrypt_token

# The connectors package lives at /<repo>/connectors/notion/src/client.py.
# Add it to sys.path so we can import it cleanly from this service.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from gdrive.src.client import GDriveClient  # noqa: E402
from github.src.client import GitHubClient  # noqa: E402
from gmail.src.client import GmailClient  # noqa: E402
from notion.src.client import NotionClient  # noqa: E402
from slack.src.client import SlackClient, SlackError  # noqa: E402

from app.repositories.index import ConnectorIndexRepository

router = APIRouter()
logger = get_logger(__name__)


# ---------------- Cross-tool local index search ----------------


class IndexSearchRequest(BaseModel):
    user_id: str
    project_id: str | None = None
    query: str
    tool: str | None = None          # filter to one tool, or None for all
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/tools/index/search")
async def index_search(body: IndexSearchRequest) -> dict[str, Any]:
    """Search the pre-indexed local data. Instant — no provider API call.

    The background sync workers populate connector_index with searchable
    data from all connected tools. This endpoint searches it via Postgres
    full-text search. When the index has data, this is 10-100x faster
    than hitting the live provider APIs.
    """
    repo = ConnectorIndexRepository(db.raw)
    results = await repo.search(
        user_id=body.user_id,
        tool=body.tool,
        query=body.query,
        project_id=body.project_id,
        limit=body.limit,
    )
    return {"results": results, "source": "local_index", "count": len(results)}


@router.get("/tools/index/stats")
async def index_stats(user_id: str) -> dict[str, Any]:
    repo = ConnectorIndexRepository(db.raw)
    counts = await repo.count_for_user(user_id)
    return {"user_id": user_id, "counts": counts, "total": sum(counts.values())}


# ---------------- Notion ----------------


class NotionSearchRequest(BaseModel):
    user_id: str
    project_id: str
    query: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class NotionSearchResult(BaseModel):
    id: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    author: str | None = None
    last_edited_time: str | None = None


class NotionSearchResponse(BaseModel):
    results: list[NotionSearchResult]


@router.post("/tools/notion/search", response_model=NotionSearchResponse)
async def notion_search(body: NotionSearchRequest) -> NotionSearchResponse:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "notion")
    if token_row is None:
        raise HTTPException(
            status_code=404,
            detail="notion is not connected for this project — connect it first",
        )

    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        logger.error("notion_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt notion token") from e

    client = NotionClient(access_token=access_token)
    try:
        hits = await client.search(query=body.query, limit=body.limit)
    except Exception as e:  # noqa: BLE001
        logger.warning("notion_search_api_failed", error=str(e))
        raise HTTPException(502, f"notion api error: {e}") from e

    results = [_normalize_notion_hit(hit) for hit in hits]
    return NotionSearchResponse(results=results)


# --- Notion blocks (read) + append (write) ---


class NotionBlocksRequest(BaseModel):
    user_id: str
    project_id: str
    page_id: str


@router.post("/tools/notion/blocks")
async def notion_get_blocks(body: NotionBlocksRequest) -> dict[str, Any]:
    """Return the block children of a Notion page — used by the snapshot
    capture before a write action.
    """
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "notion")
    if token_row is None:
        raise HTTPException(404, "notion is not connected for this project")
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, "failed to decrypt notion token") from e
    client = NotionClient(access_token=access_token)
    try:
        blocks = await client.get_page_blocks(body.page_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"notion api error: {e}") from e
    return {"blocks": blocks}


class NotionAppendRequest(BaseModel):
    user_id: str
    project_id: str
    page_id: str
    children: list[dict[str, Any]]


@router.post("/tools/notion/append")
async def notion_append(body: NotionAppendRequest) -> dict[str, Any]:
    """Append blocks to a Notion page — the core write-back op for §6.5.

    This endpoint is only called AFTER the user has confirmed the diff
    preview. The agent-orchestration /writes/{id}/confirm endpoint gates
    the call.
    """
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "notion")
    if token_row is None:
        raise HTTPException(404, "notion is not connected for this project")
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, "failed to decrypt notion token") from e
    client = NotionClient(access_token=access_token)
    try:
        result = await client.append_blocks(body.page_id, body.children)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"notion append error: {e}") from e
    return {"ok": True, "result": result}


# ---------------- GitHub ----------------


class GitHubSearchRequest(BaseModel):
    user_id: str
    project_id: str
    query: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class GitHubSearchResult(BaseModel):
    id: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    author: str | None = None
    state: str | None = None
    kind: str | None = None   # 'issue' | 'pr'
    updated_at: str | None = None


class GitHubSearchResponse(BaseModel):
    results: list[GitHubSearchResult]


@router.post("/tools/github/search", response_model=GitHubSearchResponse)
async def github_search(body: GitHubSearchRequest) -> GitHubSearchResponse:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "github")
    if token_row is None:
        raise HTTPException(
            status_code=404,
            detail="github is not connected for this project — connect it first",
        )
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        logger.error("github_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt github token") from e

    client = GitHubClient(access_token=access_token)
    try:
        hits = await client.search_issues(body.query, limit=body.limit)
    except Exception as e:  # noqa: BLE001
        logger.warning("github_search_api_failed", error=str(e))
        raise HTTPException(502, f"github api error: {e}") from e

    return GitHubSearchResponse(results=[_normalize_github_hit(h) for h in hits])


def _normalize_github_hit(hit: dict[str, Any]) -> GitHubSearchResult:
    kind = "pr" if hit.get("pull_request") else "issue"
    user = hit.get("user") or {}
    return GitHubSearchResult(
        id=str(hit.get("id", "")),
        url=hit.get("html_url"),
        title=hit.get("title"),
        excerpt=(hit.get("body") or "")[:240] or None,
        author=user.get("login") if isinstance(user, dict) else None,
        state=hit.get("state"),
        kind=kind,
        updated_at=hit.get("updated_at"),
    )


# ---------------- Google Drive ----------------


class GDriveSearchRequest(BaseModel):
    user_id: str
    project_id: str
    query: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class GDriveSearchResult(BaseModel):
    id: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    author: str | None = None
    mime_type: str | None = None
    modified_time: str | None = None


class GDriveSearchResponse(BaseModel):
    results: list[GDriveSearchResult]


@router.post("/tools/gdrive/search", response_model=GDriveSearchResponse)
async def gdrive_search(body: GDriveSearchRequest) -> GDriveSearchResponse:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "gdrive")
    if token_row is None:
        raise HTTPException(
            status_code=404,
            detail="gdrive is not connected for this project — connect it first",
        )
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        logger.error("gdrive_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt gdrive token") from e

    client = GDriveClient(access_token=access_token)
    try:
        files = await client.list_files(body.query, limit=body.limit)
    except Exception as e:  # noqa: BLE001
        logger.warning("gdrive_search_api_failed", error=str(e))
        raise HTTPException(502, f"gdrive api error: {e}") from e

    return GDriveSearchResponse(results=[_normalize_gdrive_hit(f) for f in files])


def _normalize_gdrive_hit(f: dict[str, Any]) -> GDriveSearchResult:
    owners = f.get("owners") or []
    author = None
    if owners and isinstance(owners[0], dict):
        author = owners[0].get("displayName") or owners[0].get("emailAddress")
    return GDriveSearchResult(
        id=f.get("id", ""),
        url=f.get("webViewLink"),
        title=f.get("name") or "(untitled)",
        excerpt=f.get("description"),
        author=author,
        mime_type=f.get("mimeType"),
        modified_time=f.get("modifiedTime"),
    )


# ---- Google Drive extended: read content + create doc ----


async def _get_gdrive_client(user_id: str, project_id: str) -> GDriveClient:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(user_id, project_id, "gdrive")
    if token_row is None:
        raise HTTPException(404, "gdrive is not connected for this project")
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, "failed to decrypt gdrive token") from e
    return GDriveClient(access_token=access_token)


class GDriveReadContentRequest(BaseModel):
    user_id: str
    project_id: str
    file_id: str


@router.post("/tools/gdrive/read")
async def gdrive_read_content(body: GDriveReadContentRequest) -> dict[str, Any]:
    """Read the full text content of a Google Doc/Sheet/Slide."""
    client = await _get_gdrive_client(body.user_id, body.project_id)
    meta = await client.get_file(body.file_id)
    mime = meta.get("mimeType", "")
    if "document" in mime:
        text = await client.read_doc_content(body.file_id)
    elif "spreadsheet" in mime:
        text = await client.read_sheet_content(body.file_id)
    elif "presentation" in mime:
        text = await client.export_as_text(body.file_id, "text/plain")
    else:
        text = f"[Cannot read content of {mime} files — only Google Docs/Sheets/Slides]"
    return {
        "file_id": body.file_id,
        "title": meta.get("name"),
        "mime_type": mime,
        "content": text[:50000],  # cap at 50KB
        "url": meta.get("webViewLink"),
    }


class GDriveCreateDocRequest(BaseModel):
    user_id: str
    project_id: str
    title: str
    content: str = ""
    folder_id: str | None = None


@router.post("/tools/gdrive/create-doc")
async def gdrive_create_doc(body: GDriveCreateDocRequest) -> dict[str, Any]:
    """Create a new Google Doc — only called AFTER user confirmation (write gate)."""
    client = await _get_gdrive_client(body.user_id, body.project_id)
    result = await client.create_doc(
        title=body.title,
        content=body.content,
        folder_id=body.folder_id,
    )
    return {"ok": True, **result}


class GDriveAppendRequest(BaseModel):
    user_id: str
    project_id: str
    doc_id: str
    text: str


@router.post("/tools/gdrive/append")
async def gdrive_append(body: GDriveAppendRequest) -> dict[str, Any]:
    """Append text to a Google Doc — only called AFTER user confirmation."""
    client = await _get_gdrive_client(body.user_id, body.project_id)
    result = await client.append_to_doc(doc_id=body.doc_id, text=body.text)
    return {"ok": True}


# ---------------- Gmail ----------------


class GmailSearchRequest(BaseModel):
    user_id: str
    project_id: str
    query: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class GmailSearchResult(BaseModel):
    id: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    author: str | None = None
    received_at: str | None = None


class GmailSearchResponse(BaseModel):
    results: list[GmailSearchResult]


@router.post("/tools/gmail/search", response_model=GmailSearchResponse)
async def gmail_search(body: GmailSearchRequest) -> GmailSearchResponse:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "gmail")
    if token_row is None:
        raise HTTPException(
            status_code=404,
            detail="gmail is not connected for this project — connect it first",
        )
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        logger.error("gmail_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt gmail token") from e

    client = GmailClient(access_token=access_token)
    try:
        hits = await client.search(body.query, limit=body.limit)
    except Exception as e:  # noqa: BLE001
        logger.warning("gmail_search_api_failed", error=str(e))
        raise HTTPException(502, f"gmail api error: {e}") from e

    return GmailSearchResponse(results=[_normalize_gmail_hit(h) for h in hits])


def _normalize_gmail_hit(hit: dict[str, Any]) -> GmailSearchResult:
    headers = {h["name"]: h["value"] for h in hit.get("payload", {}).get("headers", [])}
    return GmailSearchResult(
        id=hit.get("id", ""),
        url=f"https://mail.google.com/mail/u/0/#inbox/{hit.get('id', '')}",
        title=headers.get("Subject") or "(no subject)",
        excerpt=hit.get("snippet"),
        author=headers.get("From"),
        received_at=headers.get("Date"),
    )


# ---------------- Slack ----------------


class SlackSearchRequest(BaseModel):
    user_id: str
    project_id: str
    query: str = ""
    limit: int = Field(default=20, ge=1, le=100)


class SlackSearchResult(BaseModel):
    id: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    author: str | None = None
    channel: str | None = None
    ts: str | None = None


class SlackSearchResponse(BaseModel):
    results: list[SlackSearchResult]
    fallback_used: bool = False


@router.post("/tools/slack/search", response_model=SlackSearchResponse)
async def slack_search(body: SlackSearchRequest) -> SlackSearchResponse:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(body.user_id, body.project_id, "slack")
    if token_row is None:
        raise HTTPException(
            status_code=404,
            detail="slack is not connected for this project — connect it first",
        )

    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        logger.error("slack_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt slack token") from e

    client = SlackClient(access_token=access_token)

    # Try search.messages first. On workspaces without a user token the bot
    # can't hit search, so we fall back to walking joined channels and
    # scanning recent history for the keyword — slower but works with a
    # bot-only token.
    fallback_used = False
    try:
        hits = await client.search_messages(body.query or "", limit=body.limit)
    except SlackError as e:
        if "not_allowed" in str(e) or "not_authed" in str(e):
            fallback_used = True
            hits = await _slack_fallback_search(client, body.query or "", body.limit)
        else:
            logger.warning("slack_search_failed", error=str(e))
            raise HTTPException(502, f"slack api error: {e}") from e
    except Exception as e:  # noqa: BLE001
        logger.warning("slack_search_api_failed", error=str(e))
        raise HTTPException(502, f"slack api error: {e}") from e

    results = [_normalize_slack_hit(h) for h in hits]
    return SlackSearchResponse(results=results, fallback_used=fallback_used)


async def _slack_fallback_search(
    client: SlackClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """search.messages needs a user token. Walk channels.history instead."""
    channels = await client.list_channels(limit=30)
    q = query.lower().strip()
    matches: list[dict[str, Any]] = []
    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue
        try:
            messages = await client.channel_history(ch_id, limit=20)
        except Exception:  # noqa: BLE001
            continue
        for msg in messages:
            text = (msg.get("text") or "").lower()
            if not q or q in text:
                msg["_channel_id"] = ch_id
                msg["_channel_name"] = ch.get("name")
                matches.append(msg)
                if len(matches) >= limit:
                    return matches
    return matches


def _normalize_slack_hit(hit: dict[str, Any]) -> SlackSearchResult:
    """Shape: search.messages returns richer objects than channels.history."""
    text = hit.get("text") or ""
    excerpt = text[:240] if text else None
    ts = hit.get("ts")
    channel = hit.get("channel")
    channel_name: str | None = None
    channel_id: str | None = None
    if isinstance(channel, dict):
        channel_id = channel.get("id")
        channel_name = channel.get("name")
    elif isinstance(channel, str):
        channel_id = channel
    channel_name = channel_name or hit.get("_channel_name")
    channel_id = channel_id or hit.get("_channel_id")
    author = None
    username = hit.get("username") or hit.get("user")
    if isinstance(username, str):
        author = username

    permalink = hit.get("permalink")
    ref = f"{channel_id or 'unknown'}:{ts or ''}"
    title = f"#{channel_name}" if channel_name else "Slack message"

    return SlackSearchResult(
        id=ref,
        url=permalink,
        title=title,
        excerpt=excerpt,
        author=author,
        channel=channel_name,
        ts=ts,
    )


# ---- Slack extended endpoints ----

async def _get_slack_client(user_id: str, project_id: str) -> SlackClient:
    """Shared helper — decrypt the Slack token and return a live client."""
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(user_id, project_id, "slack")
    if token_row is None:
        raise HTTPException(404, "slack is not connected for this project")
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, "failed to decrypt slack token") from e
    return SlackClient(access_token=access_token)


class SlackChannelsRequest(BaseModel):
    user_id: str
    project_id: str
    limit: int = Field(default=100, ge=1, le=500)


@router.post("/tools/slack/channels")
async def slack_channels(body: SlackChannelsRequest) -> dict[str, Any]:
    client = await _get_slack_client(body.user_id, body.project_id)
    channels = await client.list_channels(limit=body.limit)
    return {
        "channels": [
            {
                "id": ch.get("id"),
                "name": ch.get("name"),
                "is_private": ch.get("is_private", False),
                "num_members": ch.get("num_members"),
                "topic": (ch.get("topic") or {}).get("value"),
                "purpose": (ch.get("purpose") or {}).get("value"),
            }
            for ch in channels
        ]
    }


class SlackHistoryRequest(BaseModel):
    user_id: str
    project_id: str
    channel_id: str
    limit: int = Field(default=50, ge=1, le=200)
    oldest: str | None = None
    latest: str | None = None


@router.post("/tools/slack/history")
async def slack_history(body: SlackHistoryRequest) -> dict[str, Any]:
    client = await _get_slack_client(body.user_id, body.project_id)
    messages = await client.channel_history(
        body.channel_id, limit=body.limit, oldest=body.oldest, latest=body.latest
    )
    return {"messages": [_enrich_slack_message(m) for m in messages]}


class SlackThreadRequest(BaseModel):
    user_id: str
    project_id: str
    channel_id: str
    thread_ts: str
    limit: int = Field(default=100, ge=1, le=500)


@router.post("/tools/slack/thread")
async def slack_thread(body: SlackThreadRequest) -> dict[str, Any]:
    client = await _get_slack_client(body.user_id, body.project_id)
    replies = await client.thread_replies(
        body.channel_id, body.thread_ts, limit=body.limit
    )
    return {"messages": [_enrich_slack_message(m) for m in replies]}


class SlackUserRequest(BaseModel):
    user_id: str
    project_id: str
    slack_user_id: str


@router.post("/tools/slack/user")
async def slack_user(body: SlackUserRequest) -> dict[str, Any]:
    client = await _get_slack_client(body.user_id, body.project_id)
    user = await client.user_info(body.slack_user_id)
    profile = user.get("profile") or {}
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "real_name": user.get("real_name") or profile.get("real_name"),
        "display_name": profile.get("display_name"),
        "email": profile.get("email"),
        "title": profile.get("title"),
        "image": profile.get("image_72"),
        "is_bot": user.get("is_bot", False),
        "tz": user.get("tz"),
    }


class SlackPostRequest(BaseModel):
    user_id: str
    project_id: str
    channel: str
    text: str
    thread_ts: str | None = None


@router.post("/tools/slack/post")
async def slack_post(body: SlackPostRequest) -> dict[str, Any]:
    """Post a message — only called AFTER user confirmation (write gate)."""
    client = await _get_slack_client(body.user_id, body.project_id)
    result = await client.post_message(
        channel=body.channel, text=body.text, thread_ts=body.thread_ts
    )
    return {
        "ok": True,
        "channel": result.get("channel"),
        "ts": result.get("ts"),
        "message": result.get("message", {}).get("text"),
    }


class SlackReactRequest(BaseModel):
    user_id: str
    project_id: str
    channel: str
    timestamp: str
    emoji: str


@router.post("/tools/slack/react")
async def slack_react(body: SlackReactRequest) -> dict[str, Any]:
    """Add a reaction — only called AFTER user confirmation (write gate)."""
    client = await _get_slack_client(body.user_id, body.project_id)
    await client.add_reaction(
        channel=body.channel, timestamp=body.timestamp, name=body.emoji
    )
    return {"ok": True, "channel": body.channel, "emoji": body.emoji}


def _enrich_slack_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw Slack message for the agent."""
    return {
        "ts": msg.get("ts"),
        "user": msg.get("user"),
        "text": msg.get("text"),
        "thread_ts": msg.get("thread_ts"),
        "reply_count": msg.get("reply_count", 0),
        "reactions": [
            {"name": r.get("name"), "count": r.get("count", 0)}
            for r in (msg.get("reactions") or [])
        ],
        "files": [
            {"name": f.get("name"), "url": f.get("url_private")}
            for f in (msg.get("files") or [])
        ],
    }


def _normalize_notion_hit(hit: dict[str, Any]) -> NotionSearchResult:
    """Notion's search response has a polymorphic shape — flatten it."""
    object_type = hit.get("object", "page")
    hit_id = hit.get("id", "")
    url = hit.get("url")
    last_edited = hit.get("last_edited_time")

    # Title: pulled from the properties (for DBs) or from the title property (for pages)
    title: str | None = None
    if object_type == "page":
        props = hit.get("properties", {}) or {}
        for v in props.values():
            if isinstance(v, dict) and v.get("type") == "title":
                title_parts = v.get("title", [])
                if title_parts:
                    title = "".join(
                        p.get("plain_text", "") for p in title_parts if isinstance(p, dict)
                    )
                    break
    elif object_type == "database":
        title_arr = hit.get("title", [])
        if isinstance(title_arr, list):
            title = "".join(
                p.get("plain_text", "") for p in title_arr if isinstance(p, dict)
            )

    # Author: created_by.id when present
    author: str | None = None
    created_by = hit.get("created_by") or {}
    if isinstance(created_by, dict):
        author = created_by.get("id")

    return NotionSearchResult(
        id=hit_id,
        url=url,
        title=title or "(untitled)",
        excerpt=None,  # Notion search doesn't return excerpts; we'd fetch blocks for that
        author=author,
        last_edited_time=last_edited,
    )
