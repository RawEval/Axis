"""Tests for the freshness proxy routes added in Phase 1."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from jose import jwt

from app.config import settings
from app.main import app


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def _bearer_for(user_id: str) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sync_state_unauth(client: AsyncClient):
    r = await client.get("/connectors/sync-state")
    assert r.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_sync_state_proxies_to_connector_manager(client: AsyncClient):
    user_id = str(uuid4())
    upstream = respx.get(
        f"{settings.connector_manager_url}/connectors/sync-state"
    ).mock(return_value=Response(200, json={"items": [
        {"source": "notion", "last_synced_at": None, "last_status": "ok",
         "last_error": None, "last_event_at": None}
    ]}))
    r = await client.get("/connectors/sync-state", headers=_bearer_for(user_id))
    assert r.status_code == 200
    assert upstream.called
    assert r.json()["items"][0]["source"] == "notion"


@pytest.mark.asyncio
@respx.mock
async def test_freshen_proxies_to_connector_manager(client: AsyncClient):
    user_id = str(uuid4())
    upstream = respx.post(
        f"{settings.connector_manager_url}/tools/notion/freshen"
    ).mock(return_value=Response(200, json={
        "status": "ok", "last_synced_at": "2026-04-19T18:30:00+00:00",
        "rows_added": 3, "error": None,
    }))
    r = await client.post("/connectors/notion/freshen", headers=_bearer_for(user_id))
    assert r.status_code == 200
    assert upstream.called
    assert r.json()["rows_added"] == 3


@pytest.mark.asyncio
async def test_freshen_unknown_source_returns_404(client: AsyncClient):
    user_id = str(uuid4())
    r = await client.post("/connectors/notexists/freshen", headers=_bearer_for(user_id))
    assert r.status_code == 404
