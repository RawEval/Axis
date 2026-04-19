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
