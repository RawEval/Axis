"""Tests for connectors/notion/src/client.py — uses the same sys.path shim
as services/connector-manager/app/sync/notion_poll.py so we can import
the connector module without making it a proper package."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import respx
from httpx import Response

# sys.path shim — connectors/ is sibling to services/, not a package on PYTHONPATH
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from notion.src.client import NotionClient  # noqa: E402


@respx.mock
async def test_list_recent_sorts_by_last_edited_time_desc():
    captured = {}

    def _record(request):
        captured["body"] = request.read().decode()
        return Response(200, json={"results": [], "has_more": False, "next_cursor": None})

    respx.post("https://api.notion.com/v1/search").mock(side_effect=_record)

    client = NotionClient(access_token="test")
    await client.list_recent(limit=20)

    assert '"sort"' in captured["body"]
    assert '"last_edited_time"' in captured["body"]
    assert '"descending"' in captured["body"]


@respx.mock
async def test_list_recent_paginates_beyond_one_page():
    page_1 = {
        "results": [
            {"object": "page", "id": f"p{i}", "last_edited_time": "2026-04-19T10:00:00.000Z"}
            for i in range(100)
        ],
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    page_2 = {
        "results": [
            {"object": "page", "id": f"q{i}", "last_edited_time": "2026-04-18T10:00:00.000Z"}
            for i in range(50)
        ],
        "has_more": False,
        "next_cursor": None,
    }
    calls = iter([page_1, page_2])

    def _next(request):
        return Response(200, json=next(calls))

    respx.post("https://api.notion.com/v1/search").mock(side_effect=_next)

    client = NotionClient(access_token="test")
    pages = await client.list_recent(limit=150)
    assert len(pages) == 150


@respx.mock
async def test_list_recent_stops_paginating_once_past_since():
    """When `since` is given and we hit a page older than `since`, return
    immediately — don't paginate further."""
    page_1 = {
        "results": [
            {"object": "page", "id": "p_new", "last_edited_time": "2026-04-19T10:00:00.000Z"},
            {"object": "page", "id": "p_old", "last_edited_time": "2026-04-10T10:00:00.000Z"},
        ],
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    respx.post("https://api.notion.com/v1/search").mock(return_value=Response(200, json=page_1))

    client = NotionClient(access_token="test")
    since = datetime(2026, 4, 18, tzinfo=timezone.utc)
    pages = await client.list_recent(limit=100, since=since)
    assert len(pages) == 1
    assert pages[0]["id"] == "p_new"


@respx.mock
async def test_list_recent_skips_non_page_objects():
    """Notion search returns 'page' and 'database' objects mixed; we only
    care about pages for the activity feed."""
    payload = {
        "results": [
            {"object": "database", "id": "db1", "last_edited_time": "2026-04-19T10:00:00.000Z"},
            {"object": "page", "id": "pg1", "last_edited_time": "2026-04-19T10:00:00.000Z"},
        ],
        "has_more": False,
        "next_cursor": None,
    }
    respx.post("https://api.notion.com/v1/search").mock(return_value=Response(200, json=payload))

    client = NotionClient(access_token="test")
    pages = await client.list_recent(limit=10)
    assert len(pages) == 1
    assert pages[0]["object"] == "page"
