"""Fixtures for route-level tests.

Route tests use TestClient as a context manager so the app lifespan
creates and closes the asyncpg pool in the correct event loop (the one
TestClient manages internally). This avoids the cross-loop asyncpg error
that occurs when the session-scoped db_pool fixture from the parent
conftest is used with a synchronous TestClient.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
