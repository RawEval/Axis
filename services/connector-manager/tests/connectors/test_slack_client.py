"""Tests for SlackClient.list_recent — uses the same sys.path shim as
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

from slack.src.client import SlackClient  # noqa: E402


@respx.mock
async def test_list_recent_aggregates_messages_across_channels():
    respx.post("https://slack.com/api/conversations.list").mock(
        return_value=Response(200, json={
            "ok": True,
            "channels": [
                {"id": "C1", "name": "general"},
                {"id": "C2", "name": "engineering"},
            ],
            "response_metadata": {},
        })
    )
    respx.post("https://slack.com/api/conversations.history").mock(
        return_value=Response(200, json={
            "ok": True,
            "messages": [{"ts": "1700000001.0", "text": "hello", "user": "U1"}],
        })
    )

    client = SlackClient(access_token="xoxb-test")
    msgs = await client.list_recent(limit=10)
    assert len(msgs) == 2  # 1 message per channel × 2 channels
    assert all("channel_id" in m for m in msgs)


@respx.mock
async def test_list_recent_respects_since_via_oldest_param():
    captured = {"oldest": None}

    def _channel_recorder(request):
        body = request.read().decode()
        if '"oldest"' in body:
            import re
            m = re.search(r'"oldest":\s*"([^"]+)"', body)
            if m:
                captured["oldest"] = m.group(1)
        return Response(200, json={"ok": True, "messages": []})

    respx.post("https://slack.com/api/conversations.list").mock(
        return_value=Response(200, json={
            "ok": True, "channels": [{"id": "C1", "name": "x"}],
            "response_metadata": {},
        })
    )
    respx.post("https://slack.com/api/conversations.history").mock(side_effect=_channel_recorder)

    client = SlackClient(access_token="xoxb-test")
    since = datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)
    await client.list_recent(limit=10, since=since)

    assert captured["oldest"] is not None
    assert captured["oldest"] == str(since.timestamp())


@respx.mock
async def test_list_recent_skips_failing_channels():
    """A 200/ok=false on one channel doesn't kill the whole aggregation."""
    respx.post("https://slack.com/api/conversations.list").mock(
        return_value=Response(200, json={
            "ok": True,
            "channels": [{"id": "BAD", "name": "x"}, {"id": "OK", "name": "y"}],
            "response_metadata": {},
        })
    )
    call_count = {"n": 0}
    def _history(request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return Response(200, json={"ok": False, "error": "channel_not_found"})
        return Response(200, json={"ok": True, "messages": [
            {"ts": "1700000001.0", "text": "hi", "user": "U1"}
        ]})
    respx.post("https://slack.com/api/conversations.history").mock(side_effect=_history)

    client = SlackClient(access_token="xoxb-test")
    msgs = await client.list_recent(limit=10)
    assert len(msgs) == 1  # only the OK channel's message
