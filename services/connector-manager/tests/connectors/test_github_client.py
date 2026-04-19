"""Tests for GitHubClient.list_recent — uses sys.path shim."""
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

from github.src.client import GitHubClient  # noqa: E402

GH = "https://api.github.com"


@respx.mock
async def test_list_recent_calls_user_then_events_endpoint():
    respx.get(f"{GH}/user").mock(return_value=Response(200, json={"login": "alice"}))
    captured = {"called": False}

    def _events(request):
        captured["called"] = True
        return Response(200, json=[])

    respx.get(f"{GH}/users/alice/events").mock(side_effect=_events)

    client = GitHubClient(access_token="t")
    out = await client.list_recent(limit=10)
    assert out == []
    assert captured["called"] is True


@respx.mock
async def test_list_recent_filters_events_older_than_since():
    respx.get(f"{GH}/user").mock(return_value=Response(200, json={"login": "alice"}))
    respx.get(f"{GH}/users/alice/events").mock(return_value=Response(200, json=[
        {"id": "1", "type": "PushEvent", "created_at": "2026-04-19T12:00:00Z",
         "actor": {"login": "alice"}, "repo": {"name": "alice/repo"}, "payload": {}},
        {"id": "2", "type": "PushEvent", "created_at": "2026-04-19T08:00:00Z",
         "actor": {"login": "alice"}, "repo": {"name": "alice/repo"}, "payload": {}},
        {"id": "3", "type": "PushEvent", "created_at": "2026-04-18T08:00:00Z",
         "actor": {"login": "alice"}, "repo": {"name": "alice/repo"}, "payload": {}},
    ]))

    client = GitHubClient(access_token="t")
    since = datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)
    events = await client.list_recent(since=since, limit=10)

    # Only the two events on Apr 19 pass the cutoff
    assert len(events) == 2
    assert {e["id"] for e in events} == {"1", "2"}


@respx.mock
async def test_list_recent_returns_empty_when_user_has_no_login():
    respx.get(f"{GH}/user").mock(return_value=Response(200, json={}))  # no login
    # NOTE: events endpoint should NOT be called

    client = GitHubClient(access_token="t")
    out = await client.list_recent(limit=10)
    assert out == []
