"""Tests for GmailClient.list_recent — uses the same sys.path shim as
notion_poll.py to import the connectors package."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import respx
from httpx import Response

_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from gmail.src.client import GmailClient  # noqa: E402

GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"


@respx.mock
async def test_list_recent_passes_after_query_when_since_given():
    captured = {"q": None}

    def _record(request):
        captured["q"] = dict(request.url.params).get("q")
        return Response(200, json={"messages": []})

    respx.get(f"{GMAIL}/messages").mock(side_effect=_record)

    client = GmailClient(access_token="t")
    since = datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)
    await client.list_recent(since=since, limit=10)

    assert captured["q"] is not None
    assert captured["q"].startswith("after:")
    assert str(int(since.timestamp())) in captured["q"]


@respx.mock
async def test_list_recent_defaults_to_newer_than_1d_when_no_since():
    captured = {"q": None}

    def _record(request):
        captured["q"] = dict(request.url.params).get("q")
        return Response(200, json={"messages": []})

    respx.get(f"{GMAIL}/messages").mock(side_effect=_record)

    client = GmailClient(access_token="t")
    await client.list_recent(limit=10)

    assert captured["q"] == "newer_than:1d"


@respx.mock
async def test_list_recent_hydrates_each_message():
    """list returns id stubs; list_recent must hydrate via messages.get."""
    respx.get(f"{GMAIL}/messages").mock(
        return_value=Response(200, json={
            "messages": [{"id": "msg1", "threadId": "th1"}],
        })
    )
    respx.get(f"{GMAIL}/messages/msg1").mock(
        return_value=Response(200, json={
            "id": "msg1",
            "threadId": "th1",
            "internalDate": "1745000000000",
            "snippet": "hello world",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "From", "value": "alice@example.com"},
                ],
            },
        })
    )

    client = GmailClient(access_token="t")
    msgs = await client.list_recent(limit=10)
    assert len(msgs) == 1
    assert msgs[0]["id"] == "msg1"
    assert msgs[0]["snippet"] == "hello world"
