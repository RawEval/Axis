"""api-gateway proxy + auth-middleware tests using respx."""
from __future__ import annotations

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.config import settings
from app.main import app


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["service"] == "axis-api-gateway"


@pytest.mark.asyncio
async def test_connectors_unauth(client: AsyncClient) -> None:
    r = await client.get("/connectors")
    assert r.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_auth_register_proxies_to_auth_service(client: AsyncClient) -> None:
    respx.post(f"{settings.auth_service_url}/register").mock(
        return_value=Response(
            201,
            json={
                "access_token": "mocked",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "11111111-1111-1111-1111-111111111111",
            },
        )
    )
    r = await client.post(
        "/auth/register",
        json={"email": "x@raweval.com", "password": "PytestPassword123!"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"] == "mocked"


@pytest.mark.asyncio
@respx.mock
async def test_auth_login_error_preserves_status(client: AsyncClient) -> None:
    respx.post(f"{settings.auth_service_url}/login").mock(
        return_value=Response(401, json={"detail": "invalid email or password"}),
    )
    r = await client.post(
        "/auth/login",
        json={"email": "x@raweval.com", "password": "wrong"},
    )
    assert r.status_code == 401
    assert "invalid" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_request_id_header_emitted(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert "x-request-id" in r.headers
    assert len(r.headers["x-request-id"]) >= 16
