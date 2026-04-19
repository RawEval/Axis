from __future__ import annotations

from uuid import uuid4

import pytest


def test_freshen_unknown_source_returns_404(client):
    resp = client.post("/tools/notexists/freshen", json={"user_id": str(uuid4())})
    assert resp.status_code == 404
    assert "no sync worker" in resp.json()["detail"].lower()


def test_sync_state_returns_empty_list_for_new_user(client):
    user_id = uuid4()
    resp = client.get(f"/connectors/sync-state?user_id={user_id}")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_freshen_notion_route_finds_worker(client):
    """After Task 1.3, NotionSyncWorker is self-registered. The route should
    NOT return 404 'no sync worker registered' for source='notion'.

    The route may still return some other status (e.g. 500 if the user has
    no connector — that's tested elsewhere). What we care about here is that
    the registry lookup found the worker."""
    from uuid import uuid4

    resp = client.post("/tools/notion/freshen", json={"user_id": str(uuid4())})
    assert resp.status_code != 404, (
        "NotionSyncWorker should be registered; got 404 with: " + resp.text
    )
