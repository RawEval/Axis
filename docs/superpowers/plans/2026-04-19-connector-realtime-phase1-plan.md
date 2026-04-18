# Connector Real-Time Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every connected tool answer "what happened today?" with ≤2-second freshness, bring all five connectors (Slack/Notion/Gmail/GDrive/GitHub) to feature parity, and never silently return "no activity found" when sync actually failed.

**Architecture:** Two-tier freshness — adaptive 60s/5min polling per source writes to `activity_events`, on-query `FreshenBeforeRead` mixin runs a synchronous freshen via connector-manager when the cache is older than 60s, manual `RefreshButton` in the UI is the user-facing escape hatch. New `connector_sync_state` table is the single source of truth for "is data fresh?" Webhook ingestion is explicitly Phase 2.

**Tech Stack:** Python 3.12 (FastAPI, Pydantic v2, asyncpg, httpx, pytest+respx), Postgres 16, Next.js 14 + TypeScript + React Query, Tailwind, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-19-connector-realtime-phase1-design.md`

---

## Phase Layout

| Phase | Deliverable | Independent? |
|---|---|---|
| **0 — Shared infrastructure** | Migrations, `SyncWorker` Protocol, `ConnectorSyncStateRepository`, `FreshenBeforeRead` mixin, `/api/connectors/sync-state` + `/api/tools/<src>/freshen`, `tests/` directory in both services | Blocks every other phase |
| **1 — Notion refactor + regression test** | Replace `notion_poll.py` with `NotionSyncWorker`. Add `connector.notion.recent_activity` capability. Fix `activity.query` timezone. The original bug's regression test passes. | Blocks Phase 2 (proves the pattern) |
| **2A — Slack worker + capability** | `SlackSyncWorker`, `connector.slack.recent_activity`, `/tools/slack/freshen` | Independent of 2B/2C/2D — parallelizable |
| **2B — Gmail worker + capability** | Same shape | Independent |
| **2C — GDrive worker + capability** | Same shape | Independent |
| **2D — GitHub worker + capability** | Same shape | Independent |
| **3 — Adaptive scheduler** | Replaces fixed-cadence sleeps with `compute_state(user, source) → 60s/5min/backoff` dispatch | Needs at least one worker (Phase 1). Independent of frontend. |
| **4 — Frontend** | `ConnectorFreshnessChip`, `RefreshButton`, three placements + status dot, render-layer auth_failed alert | Needs Phase 0 routes; needs at least Phase 1 backend to demo |
| **5 — Cleanup** | Delete the old `notion_poll.py`, drop `notion_poll_enabled` config flag | Last |

---

# Phase 0 — Shared infrastructure

This phase ships nothing user-visible. Every later phase depends on it. Land as one PR.

## Task 0.1 — Migration: `connector_sync_state` table

**Files:**
- Create: `infra/docker/init/postgres/015_connector_sync_state.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 015_connector_sync_state.sql
-- Single source of truth for "is data fresh?" per (user, source).
-- Read by the freshness chip, the FreshenBeforeRead mixin, and the cron scheduler.

CREATE TABLE IF NOT EXISTS connector_sync_state (
  user_id            UUID        NOT NULL,
  source             TEXT        NOT NULL CHECK (source IN ('slack','notion','gmail','gdrive','github')),
  last_synced_at     TIMESTAMPTZ,
  last_status        TEXT        NOT NULL DEFAULT 'never'
                     CHECK (last_status IN ('never','ok','auth_failed','vendor_error','network_error')),
  last_error         TEXT,
  last_event_at      TIMESTAMPTZ,
  consecutive_fails  INT         NOT NULL DEFAULT 0,
  cursor             JSONB       NOT NULL DEFAULT '{}'::jsonb,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, source)
);

CREATE INDEX IF NOT EXISTS connector_sync_state_status_not_ok_idx
  ON connector_sync_state (last_status)
  WHERE last_status != 'ok';

ALTER TABLE connector_sync_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY connector_sync_state_user_isolation ON connector_sync_state
  FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid);
```

- [ ] **Step 2: Apply locally and verify**

Run:
```bash
make infra-down && make infra-up
psql -h localhost -U axis -d axis -c "\d connector_sync_state"
```
Expected output: table exists, 7 columns, primary key on `(user_id, source)`, RLS enabled.

- [ ] **Step 3: Commit**

```bash
git add infra/docker/init/postgres/015_connector_sync_state.sql
git commit -m "feat(db): add connector_sync_state table for freshness tracking"
```

---

## Task 0.2 — Migration: `activity_events.external_id` column

**Files:**
- Create: `infra/docker/init/postgres/016_activity_events_external_id.sql`

- [ ] **Step 1: Inspect current `activity_events` schema first**

Run:
```bash
psql -h localhost -U axis -d axis -c "\d activity_events"
```
Confirm there is no existing `external_id` column. If there is one with the same purpose, skip this task.

- [ ] **Step 2: Write the migration**

```sql
-- 016_activity_events_external_id.sql
-- Adds the vendor's stable identifier (Notion page id, Slack message ts+channel,
-- Gmail message id, etc.) and uses it as the idempotency key for ingest.
-- Backfill existing rows from the existing `id` so the constraint holds during deploy.

ALTER TABLE activity_events
  ADD COLUMN IF NOT EXISTS external_id TEXT;

UPDATE activity_events SET external_id = id::text WHERE external_id IS NULL;

ALTER TABLE activity_events ALTER COLUMN external_id SET NOT NULL;

ALTER TABLE activity_events
  ADD CONSTRAINT activity_events_source_external_uniq
  UNIQUE (user_id, source, external_id);
```

- [ ] **Step 3: Apply locally and verify**

Run:
```bash
psql -h localhost -U axis -d axis -f infra/docker/init/postgres/016_activity_events_external_id.sql
psql -h localhost -U axis -d axis -c "\d activity_events"
```
Expected output: `external_id text NOT NULL` column present, unique constraint `activity_events_source_external_uniq` listed.

- [ ] **Step 4: Commit**

```bash
git add infra/docker/init/postgres/016_activity_events_external_id.sql
git commit -m "feat(db): add activity_events.external_id with idempotency constraint"
```

---

## Task 0.3 — Migration: `users.timezone` column

**Files:**
- Create: `infra/docker/init/postgres/017_users_timezone.sql`

- [ ] **Step 1: Inspect current `users` schema**

Run:
```bash
psql -h localhost -U axis -d axis -c "\d users"
```
Confirm no `timezone` column exists. If it does, skip this task.

- [ ] **Step 2: Write the migration**

```sql
-- 017_users_timezone.sql
-- IANA timezone name, used by activity.query to compute "today" in user's local time.
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';
```

- [ ] **Step 3: Apply locally and verify**

```bash
psql -h localhost -U axis -d axis -f infra/docker/init/postgres/017_users_timezone.sql
psql -h localhost -U axis -d axis -c "\d users" | grep timezone
```
Expected: `timezone | text | not null | 'UTC'::text`.

- [ ] **Step 4: Commit**

```bash
git add infra/docker/init/postgres/017_users_timezone.sql
git commit -m "feat(db): add users.timezone column"
```

---

## Task 0.4 — Test directory bootstrap (connector-manager)

**Files:**
- Create: `services/connector-manager/tests/__init__.py` (empty)
- Create: `services/connector-manager/tests/conftest.py`

- [ ] **Step 1: Write the conftest**

```python
# services/connector-manager/tests/conftest.py
"""Shared fixtures for connector-manager tests."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.config import settings
from app.db import db
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    await db.connect()
    yield db.raw
    await db.close()


@pytest.fixture
def client(db_pool) -> TestClient:
    return TestClient(app)
```

- [ ] **Step 2: Add test deps to pyproject**

Edit `services/connector-manager/pyproject.toml` — add to `[tool.uv]` dev dependencies (or under `[project.optional-dependencies]` test):

```toml
[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "respx>=0.21",  # httpx mocking — used by sync worker tests
]
```

- [ ] **Step 3: Install and verify**

Run:
```bash
cd services/connector-manager
uv sync --extra test
uv run pytest tests/ -q
```
Expected: `0 passed` (no tests yet — directory is bootstrapped).

- [ ] **Step 4: Commit**

```bash
git add services/connector-manager/tests/ services/connector-manager/pyproject.toml services/connector-manager/uv.lock
git commit -m "test(connector-manager): bootstrap tests/ directory + pytest-asyncio + respx"
```

---

## Task 0.5 — Test directory bootstrap (agent-orchestration)

**Files:**
- Create: `services/agent-orchestration/tests/__init__.py` (empty)
- Create: `services/agent-orchestration/tests/conftest.py`

- [ ] **Step 1: Write the conftest**

```python
# services/agent-orchestration/tests/conftest.py
"""Shared fixtures for agent-orchestration tests."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

from app.db import db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    await db.connect()
    yield db.raw
    await db.close()
```

- [ ] **Step 2: Add test deps to pyproject**

Edit `services/agent-orchestration/pyproject.toml` — same `[project.optional-dependencies]` block as Task 0.4.

- [ ] **Step 3: Install and verify**

```bash
cd services/agent-orchestration
uv sync --extra test
uv run pytest tests/ -q
```
Expected: `0 passed`.

- [ ] **Step 4: Commit**

```bash
git add services/agent-orchestration/tests/ services/agent-orchestration/pyproject.toml services/agent-orchestration/uv.lock
git commit -m "test(agent-orchestration): bootstrap tests/ directory"
```

---

## Task 0.6 — `ConnectorSyncStateRepository`

**Files:**
- Create: `services/connector-manager/app/repositories/sync_state.py`
- Test: `services/connector-manager/tests/repositories/test_sync_state.py`
- Create: `services/connector-manager/tests/repositories/__init__.py` (empty)

- [ ] **Step 1: Write the failing test**

```python
# services/connector-manager/tests/repositories/test_sync_state.py
from __future__ import annotations

from uuid import uuid4

import pytest

from app.repositories.sync_state import ConnectorSyncStateRepository


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(db_pool):
    repo = ConnectorSyncStateRepository(db_pool)
    user_id = uuid4()

    # First call → INSERT
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={"foo": "bar"})
    state = await repo.get(user_id, "notion")
    assert state is not None
    assert state["last_status"] == "ok"
    assert state["consecutive_fails"] == 0
    assert state["cursor"] == {"foo": "bar"}

    # Second call → UPDATE
    await repo.record_failure(user_id, "notion", status="vendor_error", error="500 Server")
    state = await repo.get(user_id, "notion")
    assert state["last_status"] == "vendor_error"
    assert state["consecutive_fails"] == 1
    assert state["last_error"] == "500 Server"

    # Success resets counter
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={"foo": "baz"})
    state = await repo.get(user_id, "notion")
    assert state["consecutive_fails"] == 0
    assert state["cursor"] == {"foo": "baz"}

    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)


@pytest.mark.asyncio
async def test_list_all_for_user(db_pool):
    repo = ConnectorSyncStateRepository(db_pool)
    user_id = uuid4()
    await repo.record_success(user_id, "notion", last_event_at=None, cursor={})
    await repo.record_success(user_id, "slack", last_event_at=None, cursor={})

    rows = await repo.list_for_user(user_id)
    sources = {r["source"] for r in rows}
    assert sources == {"notion", "slack"}

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd services/connector-manager
uv run pytest tests/repositories/test_sync_state.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.repositories.sync_state'`.

- [ ] **Step 3: Implement the repository**

```python
# services/connector-manager/app/repositories/sync_state.py
"""Repository for connector_sync_state — the single source of truth for
'is this connector's data fresh?' per (user, source) pair.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg


class ConnectorSyncStateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, user_id: UUID, source: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, source, last_synced_at, last_status, last_error,
                       last_event_at, consecutive_fails, cursor, updated_at
                FROM connector_sync_state
                WHERE user_id = $1 AND source = $2
                """,
                user_id,
                source,
            )
            if row is None:
                return None
            d = dict(row)
            d["cursor"] = json.loads(d["cursor"]) if isinstance(d["cursor"], str) else (d["cursor"] or {})
            return d

    async def list_for_user(self, user_id: UUID) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source, last_synced_at, last_status, last_error,
                       last_event_at, consecutive_fails
                FROM connector_sync_state
                WHERE user_id = $1
                ORDER BY source
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def record_success(
        self,
        user_id: UUID,
        source: str,
        *,
        last_event_at: datetime | None,
        cursor: dict[str, Any],
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO connector_sync_state
                  (user_id, source, last_synced_at, last_status, last_error,
                   last_event_at, consecutive_fails, cursor, updated_at)
                VALUES ($1, $2, NOW(), 'ok', NULL, $3, 0, $4::jsonb, NOW())
                ON CONFLICT (user_id, source) DO UPDATE SET
                  last_synced_at = NOW(),
                  last_status = 'ok',
                  last_error = NULL,
                  last_event_at = COALESCE(EXCLUDED.last_event_at, connector_sync_state.last_event_at),
                  consecutive_fails = 0,
                  cursor = EXCLUDED.cursor,
                  updated_at = NOW()
                """,
                user_id,
                source,
                last_event_at,
                json.dumps(cursor),
            )

    async def record_failure(
        self,
        user_id: UUID,
        source: str,
        *,
        status: str,
        error: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO connector_sync_state
                  (user_id, source, last_status, last_error, consecutive_fails, updated_at)
                VALUES ($1, $2, $3, $4, 1, NOW())
                ON CONFLICT (user_id, source) DO UPDATE SET
                  last_status = EXCLUDED.last_status,
                  last_error = EXCLUDED.last_error,
                  consecutive_fails = connector_sync_state.consecutive_fails + 1,
                  updated_at = NOW()
                """,
                user_id,
                source,
                status,
                error[:500],   # bound the column
            )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/repositories/test_sync_state.py -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add services/connector-manager/app/repositories/sync_state.py services/connector-manager/tests/repositories/
git commit -m "feat(connector-manager): add ConnectorSyncStateRepository"
```

---

## Task 0.7 — `SyncWorker` Protocol + `SyncResult` model

**Files:**
- Create: `services/connector-manager/app/sync/base.py`

- [ ] **Step 1: Write the file**

```python
# services/connector-manager/app/sync/base.py
"""Shared types for SyncWorker implementations.

Each connector's SyncWorker is a class that implements `freshen(user_id, ...)` —
the cron loop and the on-query freshen path call the same method.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

SyncStatus = Literal["ok", "auth_failed", "vendor_error", "network_error"]


class SyncResult(BaseModel):
    rows_added: int = 0
    last_event_at: datetime | None = None
    status: SyncStatus = "ok"
    error_message: str | None = None


class SyncWorker(Protocol):
    source: str

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
    ) -> SyncResult: ...


def categorize_error(exc: Exception) -> tuple[SyncStatus, str]:
    """Map a raw exception to (sync_status, short_message).

    Used uniformly by every connector worker so the freshness chip and
    capability responses surface consistent error categories.
    """
    import httpx

    msg = str(exc) or exc.__class__.__name__

    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return "auth_failed", f"{code} {exc.response.reason_phrase}"
        if 500 <= code < 600 or code == 429:
            return "vendor_error", f"{code} {exc.response.reason_phrase}"
        return "vendor_error", f"{code} {exc.response.reason_phrase}"

    if isinstance(exc, httpx.TimeoutException):
        return "network_error", f"timeout: {msg}"
    if isinstance(exc, (httpx.NetworkError, httpx.ConnectError)):
        return "network_error", msg

    return "vendor_error", msg
```

- [ ] **Step 2: No test for the Protocol itself** (it's a typing stub) — the categorizer gets covered in connector-specific worker tests where it's exercised end-to-end.

- [ ] **Step 3: Commit**

```bash
git add services/connector-manager/app/sync/base.py
git commit -m "feat(connector-manager): add SyncWorker Protocol + SyncResult + error categorizer"
```

---

## Task 0.8 — `/tools/<source>/freshen` route stub + sync-state route

The route dispatches to a registered worker. Workers register themselves in Phase 1+2.

**Files:**
- Create: `services/connector-manager/app/sync/registry.py`
- Modify: `services/connector-manager/app/routes/tools.py` (append new endpoints)
- Test: `services/connector-manager/tests/routes/test_freshen.py`
- Create: `services/connector-manager/tests/routes/__init__.py` (empty)

- [ ] **Step 1: Write the worker registry**

```python
# services/connector-manager/app/sync/registry.py
"""In-process registry of SyncWorker instances, keyed by source.

Workers self-register at import time (each worker module ends with
`registry.register(<Worker>())`). Routes look workers up here.
"""
from __future__ import annotations

from app.sync.base import SyncWorker

_workers: dict[str, SyncWorker] = {}


def register(worker: SyncWorker) -> None:
    _workers[worker.source] = worker


def get(source: str) -> SyncWorker | None:
    return _workers.get(source)


def all_sources() -> list[str]:
    return sorted(_workers.keys())
```

- [ ] **Step 2: Write the failing route test**

```python
# services/connector-manager/tests/routes/test_freshen.py
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_freshen_unknown_source_returns_404(client):
    resp = client.post("/tools/notexists/freshen", json={"user_id": str(uuid4())})
    assert resp.status_code == 404
    assert "no sync worker registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sync_state_returns_empty_list_for_new_user(client):
    user_id = uuid4()
    resp = client.get(f"/connectors/sync-state?user_id={user_id}")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run pytest tests/routes/test_freshen.py -v
```
Expected: 404 returns `{"detail": "Not Found"}` because the routes don't exist yet — both tests fail.

- [ ] **Step 4: Add the routes**

Append to `services/connector-manager/app/routes/tools.py`:

```python
# ... existing imports ...
from datetime import datetime
from uuid import UUID

from app.repositories.sync_state import ConnectorSyncStateRepository
from app.sync import registry as sync_registry
from app.sync.base import SyncResult


class FreshenRequest(BaseModel):
    user_id: UUID
    force: bool = False
    since: datetime | None = None


class FreshenResponse(BaseModel):
    status: str
    last_synced_at: datetime | None = None
    rows_added: int = 0
    error: str | None = None


@router.post("/tools/{source}/freshen", response_model=FreshenResponse)
async def freshen(source: str, body: FreshenRequest) -> FreshenResponse:
    worker = sync_registry.get(source)
    if worker is None:
        raise HTTPException(404, f"no sync worker registered for source '{source}'")

    repo = ConnectorSyncStateRepository(db.raw)
    if not body.force:
        state = await repo.get(body.user_id, source)
        if state and state.get("last_status") == "ok" and state.get("last_synced_at"):
            from datetime import datetime, timezone, timedelta
            age = datetime.now(timezone.utc) - state["last_synced_at"]
            if age < timedelta(seconds=60):
                return FreshenResponse(
                    status="ok",
                    last_synced_at=state["last_synced_at"],
                    rows_added=0,
                )

    result: SyncResult = await worker.freshen(body.user_id, since=body.since, force=body.force)
    state = await repo.get(body.user_id, source)
    return FreshenResponse(
        status=result.status,
        last_synced_at=state["last_synced_at"] if state else None,
        rows_added=result.rows_added,
        error=result.error_message,
    )


class SyncStateItem(BaseModel):
    source: str
    last_synced_at: datetime | None
    last_status: str
    last_error: str | None
    last_event_at: datetime | None


class SyncStateResponse(BaseModel):
    items: list[SyncStateItem]


@router.get("/connectors/sync-state", response_model=SyncStateResponse)
async def sync_state(user_id: UUID) -> SyncStateResponse:
    repo = ConnectorSyncStateRepository(db.raw)
    rows = await repo.list_for_user(user_id)
    return SyncStateResponse(items=[SyncStateItem(**r) for r in rows])
```

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/routes/test_freshen.py -v
```
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add services/connector-manager/app/sync/registry.py services/connector-manager/app/routes/tools.py services/connector-manager/tests/routes/
git commit -m "feat(connector-manager): /tools/<src>/freshen + /connectors/sync-state routes + worker registry"
```

---

## Task 0.9 — `Freshness` model + sync-state client in agent-orchestration

**Files:**
- Create: `services/agent-orchestration/app/capabilities/_freshness.py`

- [ ] **Step 1: Write the file**

```python
# services/agent-orchestration/app/capabilities/_freshness.py
"""Freshness model used by every connector recent_activity capability.

Returned in CapabilityResult.content under the 'freshness' key so the
agent's prompt can surface honest statements like 'I checked Slack 3 seconds
ago — no activity. Last successful sync was 14:32.'
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SyncStatus = Literal["ok", "stale", "auth_failed", "vendor_error", "network_error", "never"]


class Freshness(BaseModel):
    source: str
    last_synced_at: datetime | None = None
    sync_status: SyncStatus = "never"
    error_message: str | None = None

    @classmethod
    def from_state(cls, source: str, state: dict | None) -> "Freshness":
        if state is None:
            return cls(source=source, sync_status="never")
        return cls(
            source=source,
            last_synced_at=state.get("last_synced_at"),
            sync_status=state.get("last_status", "never"),
            error_message=state.get("last_error"),
        )
```

- [ ] **Step 2: No test** (pure data shape).

- [ ] **Step 3: Commit**

```bash
git add services/agent-orchestration/app/capabilities/_freshness.py
git commit -m "feat(agent-orchestration): add Freshness model"
```

---

## Task 0.10 — `FreshenBeforeRead` mixin

**Files:**
- Create: `services/agent-orchestration/app/capabilities/_freshen_mixin.py`
- Test: `services/agent-orchestration/tests/capabilities/test_freshen_mixin.py`
- Create: `services/agent-orchestration/tests/capabilities/__init__.py` (empty)

- [ ] **Step 1: Extend the connector_manager client first**

Edit `services/agent-orchestration/app/clients/connector_manager.py` — append two methods inside `ConnectorManagerClient`:

```python
    # ---------- Freshness ------------------------------------------------

    async def freshen(
        self, *, source: str, user_id: str, force: bool = False
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            try:
                resp = await client.post(
                    f"{self._base}/tools/{source}/freshen",
                    json={"user_id": user_id, "force": force},
                )
            except httpx.TimeoutException:
                return {"status": "network_error", "error": "freshen timeout"}
            if resp.status_code >= 400:
                return {"status": "vendor_error", "error": f"connector-manager {resp.status_code}"}
            return resp.json()

    async def sync_state(self, *, user_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            resp = await client.get(
                f"{self._base}/connectors/sync-state",
                params={"user_id": user_id},
            )
            if resp.status_code >= 400:
                return []
            return resp.json().get("items", [])

    async def sync_state_one(self, *, user_id: str, source: str) -> dict[str, Any] | None:
        items = await self.sync_state(user_id=user_id)
        for item in items:
            if item.get("source") == source:
                return item
        return None
```

- [ ] **Step 2: Write the failing mixin test**

```python
# services/agent-orchestration/tests/capabilities/test_freshen_mixin.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.capabilities._freshen_mixin import FreshenBeforeRead


class _ConcreteCap(FreshenBeforeRead):
    source = "notion"


@pytest.mark.asyncio
async def test_recent_sync_skips_freshen_call(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    fresh_state = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=5),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = fresh_state
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    freshness = await cap.ensure_fresh(user_id)

    assert freshness.sync_status == "ok"
    fake_client.freshen.assert_not_called()
    fake_client.sync_state_one.assert_called_once()


@pytest.mark.asyncio
async def test_stale_sync_triggers_freshen_call(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    stale = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=120),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    refreshed = {**stale, "last_synced_at": datetime.now(timezone.utc)}

    fake_client = AsyncMock()
    fake_client.sync_state_one.side_effect = [stale, refreshed]
    fake_client.freshen.return_value = {"status": "ok"}
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    await cap.ensure_fresh(user_id)

    fake_client.freshen.assert_called_once_with(source="notion", user_id=str(user_id), force=False)


@pytest.mark.asyncio
async def test_freshen_timeout_does_not_raise(monkeypatch):
    cap = _ConcreteCap()
    user_id = uuid4()

    stale = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc) - timedelta(seconds=120),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = stale
    fake_client.freshen.return_value = {"status": "network_error", "error": "timeout"}
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    freshness = await cap.ensure_fresh(user_id)

    assert freshness.sync_status in ("ok", "network_error")  # whatever state stays
```

- [ ] **Step 3: Run to verify failure**

```bash
cd services/agent-orchestration
uv run pytest tests/capabilities/test_freshen_mixin.py -v
```
Expected: ImportError on `_freshen_mixin`.

- [ ] **Step 4: Implement the mixin**

```python
# services/agent-orchestration/app/capabilities/_freshen_mixin.py
"""Mixin for capabilities that read from activity_events.

Before reading, check connector_sync_state. If the source's data is older
than `stale_after`, fire a synchronous /tools/<src>/freshen call (bounded
8s) so the read sees fresh data. If the freshen times out, return what we
have with stale freshness rather than blocking the user.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.capabilities._freshness import Freshness
from app.clients.connector_manager import ConnectorManagerClient

_client = ConnectorManagerClient()


class FreshenBeforeRead:
    source: str
    stale_after: timedelta = timedelta(seconds=60)

    async def ensure_fresh(self, user_id: UUID) -> Freshness:
        state = await _client.sync_state_one(user_id=str(user_id), source=self.source)
        if (
            state
            and state.get("last_status") == "ok"
            and state.get("last_synced_at")
            and (datetime.now(timezone.utc) - state["last_synced_at"]) < self.stale_after
        ):
            return Freshness.from_state(self.source, state)

        # Stale — fire a non-forced freshen (the route also checks staleness
        # server-side, so concurrent requests don't hammer the vendor).
        await _client.freshen(source=self.source, user_id=str(user_id), force=False)
        state = await _client.sync_state_one(user_id=str(user_id), source=self.source)
        return Freshness.from_state(self.source, state)
```

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/capabilities/test_freshen_mixin.py -v
```
Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add services/agent-orchestration/app/capabilities/_freshen_mixin.py services/agent-orchestration/app/clients/connector_manager.py services/agent-orchestration/tests/capabilities/
git commit -m "feat(agent-orchestration): add FreshenBeforeRead mixin + connector_manager freshen/sync_state methods"
```

---

## Task 0.11 — Timezone-aware `resolve_since` helper

**Files:**
- Create: `services/agent-orchestration/app/util/since.py`
- Create: `services/agent-orchestration/app/util/__init__.py` (empty if missing)
- Test: `services/agent-orchestration/tests/util/test_since.py`
- Create: `services/agent-orchestration/tests/util/__init__.py` (empty)

- [ ] **Step 1: Write the failing test**

```python
# services/agent-orchestration/tests/util/test_since.py
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from app.util.since import resolve_since


@freeze_time("2026-04-19T18:30:00+00:00")
def test_today_in_kolkata_is_midnight_local_in_utc():
    # 11pm IST on Apr 19 ↔ 17:30 UTC. "Today" started 00:00 IST = 18:30 UTC on Apr 18.
    result = resolve_since("today", ZoneInfo("Asia/Kolkata"))
    assert result == datetime(2026, 4, 18, 18, 30, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
def test_today_in_utc_is_midnight_utc():
    result = resolve_since("today", ZoneInfo("UTC"))
    assert result == datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
def test_yesterday_in_pt_starts_at_local_midnight_yesterday():
    # PT = UTC-7 on this date. "Yesterday" = 00:00 PT Apr 18 = 07:00 UTC Apr 18
    result = resolve_since("yesterday", ZoneInfo("America/Los_Angeles"))
    assert result == datetime(2026, 4, 18, 7, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
@pytest.mark.parametrize("phrase,hours_ago", [
    ("1h", 1), ("1 hour", 1), ("last hour", 1),
    ("24h", 24), ("1d", 24), ("1 day", 24),
    ("7d", 24 * 7), ("1 week", 24 * 7),
])
def test_relative_phrases_are_tz_independent(phrase, hours_ago):
    result_utc = resolve_since(phrase, ZoneInfo("UTC"))
    result_kol = resolve_since(phrase, ZoneInfo("Asia/Kolkata"))
    assert result_utc == result_kol


def test_iso_string_passthrough():
    result = resolve_since("2026-04-15T10:00:00+00:00", ZoneInfo("UTC"))
    assert result == datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
```

- [ ] **Step 2: Add `freezegun` to test deps**

Edit `services/agent-orchestration/pyproject.toml`:
```toml
[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "respx>=0.21",
  "freezegun>=1.5",
]
```
Run `uv sync --extra test`.

- [ ] **Step 3: Run to verify failure**

```bash
uv run pytest tests/util/test_since.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement**

```python
# services/agent-orchestration/app/util/since.py
"""Resolve a 'since' input ('today', '1h', ISO string, ...) to an absolute
UTC datetime in the user's local timezone.

Used by activity.query and every connector recent_activity capability so
'today' means 'today in the user's wall-clock', not 'today in DB UTC'.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_RELATIVE = {
    "1h": timedelta(hours=1),
    "1 hour": timedelta(hours=1),
    "last hour": timedelta(hours=1),
    "24h": timedelta(days=1),
    "1d": timedelta(days=1),
    "1 day": timedelta(days=1),
    "7d": timedelta(days=7),
    "1 week": timedelta(days=7),
    "this week": timedelta(days=7),
    "30d": timedelta(days=30),
    "1 month": timedelta(days=30),
    "this month": timedelta(days=30),
}


def resolve_since(value: str, user_tz: ZoneInfo) -> datetime:
    s = (value or "").strip().lower()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(user_tz)

    if s == "today":
        local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(timezone.utc)

    if s == "yesterday":
        local_midnight_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return (local_midnight_today - timedelta(days=1)).astimezone(timezone.utc)

    if s in _RELATIVE:
        return now_utc - _RELATIVE[s]

    # Try ISO 8601 (with or without timezone)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=user_tz)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    # Fallback: treat as 'today'
    local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc)
```

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/util/test_since.py -v
```
Expected: all parameterized + named tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/agent-orchestration/app/util/ services/agent-orchestration/tests/util/ services/agent-orchestration/pyproject.toml services/agent-orchestration/uv.lock
git commit -m "feat(agent-orchestration): timezone-aware resolve_since helper"
```

---

## Task 0.12 — `users.timezone` repository accessor

**Files:**
- Modify: `services/agent-orchestration/app/repositories/users.py` (or create if missing)
- Test: `services/agent-orchestration/tests/repositories/test_users_timezone.py`
- Create: `services/agent-orchestration/tests/repositories/__init__.py` (empty)

- [ ] **Step 1: Inspect existing users repo**

Run:
```bash
ls services/agent-orchestration/app/repositories/
```
If `users.py` exists, read it to match patterns. Otherwise create per the template below.

- [ ] **Step 2: Write the failing test**

```python
# services/agent-orchestration/tests/repositories/test_users_timezone.py
from __future__ import annotations

from uuid import uuid4

import pytest

from app.repositories.users import UsersRepository


@pytest.mark.asyncio
async def test_get_timezone_returns_default_when_user_missing(db_pool):
    repo = UsersRepository(db_pool)
    tz = await repo.get_timezone(uuid4())
    assert tz == "UTC"


@pytest.mark.asyncio
async def test_get_timezone_returns_stored_value(db_pool):
    repo = UsersRepository(db_pool)
    user_id = uuid4()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, timezone) VALUES ($1, $2, 'x', $3)",
            user_id, f"tz-{user_id}@test.local", "Asia/Kolkata",
        )
    try:
        tz = await repo.get_timezone(user_id)
        assert tz == "Asia/Kolkata"
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
```

- [ ] **Step 3: Add or extend the repo**

If `users.py` doesn't exist, create:

```python
# services/agent-orchestration/app/repositories/users.py
from __future__ import annotations

from uuid import UUID

import asyncpg


class UsersRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_timezone(self, user_id: UUID) -> str:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT timezone FROM users WHERE id = $1", user_id
            )
            return row["timezone"] if row else "UTC"
```

If it exists, append the `get_timezone` method.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/repositories/test_users_timezone.py -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add services/agent-orchestration/app/repositories/users.py services/agent-orchestration/tests/repositories/
git commit -m "feat(agent-orchestration): UsersRepository.get_timezone()"
```

---

## Task 0.13 — api-gateway proxy routes

**Files:**
- Create: `services/api-gateway/app/routes/connectors_sync.py`
- Modify: `services/api-gateway/app/main.py` (include new router)
- Test: `services/api-gateway/tests/routes/test_connectors_sync.py`

- [ ] **Step 1: Verify api-gateway has a tests directory**

If not, follow Task 0.4 to bootstrap one in `services/api-gateway/tests/`.

- [ ] **Step 2: Write the failing route test**

```python
# services/api-gateway/tests/routes/test_connectors_sync.py
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_sync_state_proxies_to_connector_manager(client, auth_header):
    user_id = str(uuid4())
    upstream = respx.get(
        "http://localhost:8002/connectors/sync-state"
    ).mock(return_value=Response(200, json={"items": [
        {"source": "notion", "last_synced_at": None, "last_status": "ok",
         "last_error": None, "last_event_at": None}
    ]}))
    resp = client.get("/api/connectors/sync-state", headers=auth_header)
    assert resp.status_code == 200
    assert upstream.called
    assert resp.json()["items"][0]["source"] == "notion"


@pytest.mark.asyncio
@respx.mock
async def test_freshen_proxies_to_connector_manager(client, auth_header):
    upstream = respx.post(
        "http://localhost:8002/tools/notion/freshen"
    ).mock(return_value=Response(200, json={
        "status": "ok", "last_synced_at": "2026-04-19T18:30:00+00:00",
        "rows_added": 3, "error": None,
    }))
    resp = client.post("/api/tools/notion/freshen", headers=auth_header)
    assert resp.status_code == 200
    assert upstream.called
    assert resp.json()["rows_added"] == 3
```

(`auth_header` is an existing fixture in api-gateway's conftest that mints a JWT for test user; if absent, add one mirroring the existing auth pattern.)

- [ ] **Step 3: Implement the route module**

```python
# services/api-gateway/app/routes/connectors_sync.py
"""Thin proxy routes for the freshness UI.

GET  /api/connectors/sync-state            → connector-manager
POST /api/tools/<source>/freshen           → connector-manager
"""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.deps import get_current_user_id

router = APIRouter()


@router.get("/api/connectors/sync-state")
async def get_sync_state(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.connector_manager_url}/connectors/sync-state",
            params={"user_id": user_id},
        )
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, "sync-state lookup failed")
        return resp.json()


@router.post("/api/tools/{source}/freshen")
async def freshen(source: str, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.connector_manager_url}/tools/{source}/freshen",
            json={"user_id": user_id, "force": True},
        )
        if resp.status_code == 404:
            raise HTTPException(404, f"no sync worker for source '{source}'")
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, f"freshen failed: {resp.text[:200]}")
        return resp.json()
```

- [ ] **Step 4: Wire the router**

Edit `services/api-gateway/app/main.py` — add to imports and include_router:
```python
from app.routes import connectors_sync

# ... below other include_router calls:
app.include_router(connectors_sync.router, tags=["connectors-sync"])
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd services/api-gateway
uv run pytest tests/routes/test_connectors_sync.py -v
```
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add services/api-gateway/app/routes/connectors_sync.py services/api-gateway/app/main.py services/api-gateway/tests/
git commit -m "feat(api-gateway): /api/connectors/sync-state + /api/tools/<src>/freshen proxy routes"
```

---

# Phase 1 — Notion refactor + regression test

This phase ships "Notion answers freshly within 2 seconds" — the original bug is fixed end-to-end and covered by an automated test.

## Task 1.1 — `NotionClient.list_recent`

**Files:**
- Modify: `connectors/notion/src/client.py`
- Test: `connectors/notion/tests/test_client_list_recent.py`
- Create: `connectors/notion/tests/__init__.py` (empty if missing)

- [ ] **Step 1: Read the existing client to match patterns**

Run:
```bash
cat connectors/notion/src/client.py
```
Note the existing `search()` method signature and `_headers` property.

- [ ] **Step 2: Write the failing test**

```python
# connectors/notion/tests/test_client_list_recent.py
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import respx
from httpx import Response

from notion.src.client import NotionClient


@pytest.mark.asyncio
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


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_paginates():
    page_1 = {
        "results": [{"object": "page", "id": "p1", "last_edited_time": "2026-04-19T10:00:00.000Z"}] * 100,
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    page_2 = {
        "results": [{"object": "page", "id": "p2", "last_edited_time": "2026-04-18T10:00:00.000Z"}] * 50,
        "has_more": False,
        "next_cursor": None,
    }
    calls = iter([page_1, page_2])
    respx.post("https://api.notion.com/v1/search").mock(side_effect=lambda req: Response(200, json=next(calls)))

    client = NotionClient(access_token="test")
    pages = await client.list_recent(limit=150)
    assert len(pages) == 150


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_stops_paginating_once_past_since():
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
```

- [ ] **Step 3: Run to verify failure**

```bash
cd connectors/notion
uv run pytest tests/test_client_list_recent.py -v
# Or whatever the connectors test runner is — check connectors/README.md
```
If the connectors package has no test runner, run from the repo root with the appropriate pytest discovery.

Expected: `AttributeError: 'NotionClient' has no attribute 'list_recent'`.

- [ ] **Step 4: Add the method**

Append to `connectors/notion/src/client.py`:

```python
from datetime import datetime
from dateutil.parser import parse as _parse_dt  # if not already imported


class NotionClient:
    # ... existing ...

    async def list_recent(
        self,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return Notion pages sorted by last_edited_time desc, optionally
        bounded by `since`. Paginates beyond a single page (Notion's search
        page_size cap is 100)."""
        pages: list[dict] = []
        cursor: str | None = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            while len(pages) < limit:
                body: dict = {
                    "query": "",
                    "page_size": min(100, limit - len(pages)),
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                }
                if cursor:
                    body["start_cursor"] = cursor
                resp = await client.post(
                    f"{NOTION_API_BASE}/search",
                    headers=self._headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                for hit in data.get("results", []):
                    if hit.get("object") != "page":
                        continue
                    if since:
                        edited_str = hit.get("last_edited_time")
                        if edited_str:
                            try:
                                edited = _parse_dt(edited_str)
                                if edited < since:
                                    return pages
                            except (ValueError, TypeError):
                                pass
                    pages.append(hit)
                    if len(pages) >= limit:
                        break
                cursor = data.get("next_cursor")
                if not data.get("has_more") or not cursor:
                    break
        return pages
```

If `dateutil` isn't already a dependency, use stdlib `datetime.fromisoformat(s.replace("Z", "+00:00"))` to avoid adding a new dep.

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/test_client_list_recent.py -v
```
Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add connectors/notion/src/client.py connectors/notion/tests/
git commit -m "feat(notion): NotionClient.list_recent — sort by last_edited_time desc + paginate"
```

---

## Task 1.2 — `NotionSyncWorker`

**Files:**
- Create: `services/connector-manager/app/sync/notion.py`
- Test: `services/connector-manager/tests/sync/test_notion.py`
- Create: `services/connector-manager/tests/sync/__init__.py` (empty)

- [ ] **Step 1: Write the failing worker test**

```python
# services/connector-manager/tests/sync/test_notion.py
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import respx
from httpx import Response


@pytest.fixture
def fake_notion_page():
    return {
        "object": "page",
        "id": "page-abc",
        "last_edited_time": "2026-04-19T18:25:00.000Z",
        "url": "https://www.notion.so/page-abc",
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Test Page"}]}
        },
        "last_edited_by": {"id": "user-x"},
    }


@pytest.mark.asyncio
@respx.mock
async def test_freshen_writes_activity_event_and_records_success(db_pool, fake_notion_page):
    """End-to-end: a Notion page hit becomes an activity_events row and
    connector_sync_state shows status=ok."""
    from app.sync.notion import NotionSyncWorker

    user_id = uuid4()
    # Pretend the user has a Notion connector row
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO connectors (id, user_id, project_id, tool, auth_token_encrypted, status)
            VALUES (gen_random_uuid(), $1, NULL, 'notion', $2, 'connected')
            """,
            user_id,
            b"\x00" * 64,  # placeholder; the worker will be patched to skip decryption
        )

    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(200, json={
            "results": [fake_notion_page], "has_more": False, "next_cursor": None,
        })
    )

    with patch("app.sync.notion.decrypt_token", return_value="dummy_token"):
        worker = NotionSyncWorker()
        result = await worker.freshen(user_id)

    assert result.status == "ok"
    assert result.rows_added == 1

    async with db_pool.acquire() as conn:
        events = await conn.fetch(
            "SELECT * FROM activity_events WHERE user_id = $1 AND source = 'notion'",
            user_id,
        )
        assert len(events) == 1
        assert events[0]["external_id"] == "page-abc"

        state = await conn.fetchrow(
            "SELECT * FROM connector_sync_state WHERE user_id = $1 AND source = 'notion'",
            user_id,
        )
        assert state["last_status"] == "ok"

        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connectors WHERE user_id = $1", user_id)


@pytest.mark.asyncio
@respx.mock
async def test_freshen_records_auth_failed_on_401(db_pool):
    from app.sync.notion import NotionSyncWorker

    user_id = uuid4()
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO connectors (id, user_id, project_id, tool, auth_token_encrypted, status)
               VALUES (gen_random_uuid(), $1, NULL, 'notion', $2, 'connected')""",
            user_id, b"\x00" * 64,
        )

    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(401, json={"message": "Unauthorized"})
    )

    with patch("app.sync.notion.decrypt_token", return_value="bad_token"):
        result = await NotionSyncWorker().freshen(user_id)

    assert result.status == "auth_failed"
    assert result.rows_added == 0

    async with db_pool.acquire() as conn:
        state = await conn.fetchrow(
            "SELECT * FROM connector_sync_state WHERE user_id = $1 AND source = 'notion'",
            user_id,
        )
        assert state["last_status"] == "auth_failed"
        assert state["consecutive_fails"] == 1

        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connectors WHERE user_id = $1", user_id)


@pytest.mark.asyncio
@respx.mock
async def test_freshen_is_idempotent_on_repeated_call(db_pool, fake_notion_page):
    from app.sync.notion import NotionSyncWorker

    user_id = uuid4()
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO connectors (id, user_id, project_id, tool, auth_token_encrypted, status)
               VALUES (gen_random_uuid(), $1, NULL, 'notion', $2, 'connected')""",
            user_id, b"\x00" * 64,
        )

    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(200, json={"results": [fake_notion_page], "has_more": False})
    )

    with patch("app.sync.notion.decrypt_token", return_value="t"):
        await NotionSyncWorker().freshen(user_id)
        await NotionSyncWorker().freshen(user_id)  # second call, same data

    async with db_pool.acquire() as conn:
        events = await conn.fetch(
            "SELECT * FROM activity_events WHERE user_id = $1 AND source = 'notion'",
            user_id,
        )
        assert len(events) == 1  # idempotent

        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connectors WHERE user_id = $1", user_id)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd services/connector-manager
uv run pytest tests/sync/test_notion.py -v
```
Expected: `ImportError: cannot import name 'NotionSyncWorker'`.

- [ ] **Step 3: Implement the worker**

```python
# services/connector-manager/app/sync/notion.py
"""NotionSyncWorker — pulls recently-edited Notion pages and writes them
to activity_events. Replaces the old notion_poll.py shape with the
SyncWorker Protocol so the cron and the on-query freshen path share code.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.security import decrypt_token
from app.sync import registry as sync_registry
from app.sync.base import SyncResult, categorize_error

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from notion.src.client import NotionClient  # noqa: E402

logger = get_logger(__name__)


class NotionSyncWorker:
    source = "notion"

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
    ) -> SyncResult:
        conn_repo = ConnectorsRepository(db.raw)
        activity_repo = ActivityEventsRepository(db.raw)
        state_repo = ConnectorSyncStateRepository(db.raw)

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="notion")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")  # nothing to sync

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "notion", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = NotionClient(access_token=token)
            try:
                pages = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "notion", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for page in pages:
                mapped = _map_notion_page(page)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
                    source="notion",
                    event_type=mapped["event_type"],
                    key=mapped["key"],
                    title=mapped["title"],
                    snippet=mapped.get("snippet"),
                    actor=mapped.get("actor"),
                    actor_id=mapped.get("actor_id"),
                    occurred_at=mapped["occurred_at"],
                    raw_ref=mapped.get("raw_ref"),
                    external_id=mapped["key"],
                )
                if result["inserted"]:
                    rows_added += 1
                if newest_event is None or (mapped["occurred_at"] and mapped["occurred_at"] > newest_event):
                    newest_event = mapped["occurred_at"]

        await state_repo.record_success(
            user_id, "notion",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _map_notion_page(page: dict[str, Any]) -> dict[str, Any] | None:
    if page.get("object") != "page":
        return None
    page_id = page.get("id")
    if not page_id:
        return None

    title: str | None = None
    for v in (page.get("properties") or {}).values():
        if isinstance(v, dict) and v.get("type") == "title":
            parts = v.get("title", [])
            if parts:
                title = "".join(p.get("plain_text", "") for p in parts if isinstance(p, dict))
            break

    last_edited_raw = page.get("last_edited_time")
    occurred_at: datetime | None = None
    if last_edited_raw:
        try:
            occurred_at = datetime.fromisoformat(last_edited_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = None
    if occurred_at is None:
        occurred_at = datetime.now(tz=timezone.utc)

    actor_id: str | None = None
    edited_by = page.get("last_edited_by") or {}
    if isinstance(edited_by, dict):
        actor_id = edited_by.get("id")

    return {
        "event_type": "page_edited",
        "key": page_id,
        "title": title or "(untitled Notion page)",
        "snippet": None,
        "actor": None,
        "actor_id": actor_id,
        "occurred_at": occurred_at,
        "raw_ref": {
            "page_id": page_id,
            "url": page.get("url"),
            "last_edited_time": last_edited_raw,
        },
    }


sync_registry.register(NotionSyncWorker())
```

- [ ] **Step 4: Add `ConnectorsRepository.list_by_user_and_tool` if missing**

If the existing `ConnectorsRepository.list_connected(tool=...)` doesn't filter by user, add a method:

```python
# Append to services/connector-manager/app/repositories/connectors.py
async def list_by_user_and_tool(self, *, user_id: str, tool: str) -> list[dict]:
    async with self._pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, project_id, tool, auth_token_encrypted, status, last_sync
            FROM connectors
            WHERE user_id = $1::uuid AND tool = $2 AND status = 'connected'
            """,
            user_id, tool,
        )
        return [dict(r) for r in rows]
```

- [ ] **Step 5: Add `ActivityEventsRepository.upsert(external_id=...)`**

The existing `upsert` may not accept `external_id`. Add the parameter and use the new uniqueness constraint:

Find current `upsert` in `app/repositories/activity.py`. Add `external_id: str` to the signature and update the SQL `INSERT ... ON CONFLICT (user_id, source, external_id) DO UPDATE`.

- [ ] **Step 6: Run tests to verify pass**

```bash
uv run pytest tests/sync/test_notion.py -v
```
Expected: `3 passed`.

- [ ] **Step 7: Commit**

```bash
git add services/connector-manager/app/sync/notion.py services/connector-manager/app/repositories/connectors.py services/connector-manager/app/repositories/activity.py services/connector-manager/tests/sync/
git commit -m "feat(connector-manager): NotionSyncWorker — replaces notion_poll with idempotent freshen"
```

---

## Task 1.3 — Wire `NotionSyncWorker` into the connector-manager lifespan

**Files:**
- Modify: `services/connector-manager/app/main.py`

- [ ] **Step 1: Replace the old notion poll loop import**

Edit `services/connector-manager/app/main.py`:
- Remove: `from app.sync.notion_poll import notion_poll_loop`
- Add: `from app.sync.notion import NotionSyncWorker  # registers itself`

The import side-effect registers the worker. The cron loop dispatch comes in Phase 3 (adaptive scheduler). For now, retain the old `notion_poll_loop` as the temporary cron driver — but point it at `NotionSyncWorker.freshen` instead of the deleted `poll_all_notion_workspaces`.

- [ ] **Step 2: Add a temporary multi-user cron loop**

Add to `services/connector-manager/app/sync/notion.py`:

```python
async def notion_poll_loop_v2(interval_sec: int) -> None:
    """Temporary cron loop — Phase 3 replaces this with the adaptive scheduler."""
    import asyncio
    from app.repositories.connectors import ConnectorsRepository

    logger.info("notion_poll_loop_v2_started", interval_sec=interval_sec)
    worker = NotionSyncWorker()
    while True:
        try:
            conn_repo = ConnectorsRepository(db.raw)
            user_ids = {str(row["user_id"]) for row in await conn_repo.list_connected(tool="notion")}
            for uid in user_ids:
                try:
                    await worker.freshen(UUID(uid))
                except Exception as e:  # noqa: BLE001
                    logger.error("notion_freshen_crashed", user_id=uid, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("notion_poll_v2_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
```

- [ ] **Step 3: Update `main.py` lifespan**

```python
# Replace:
#   if settings.notion_poll_enabled:
#       bg_tasks.append(asyncio.create_task(notion_poll_loop(settings.notion_poll_interval_sec)))
# With:
from app.sync.notion import notion_poll_loop_v2  # noqa: E402

if settings.notion_poll_enabled:
    bg_tasks.append(asyncio.create_task(notion_poll_loop_v2(60)))  # 60s default until Phase 3
```

- [ ] **Step 4: Smoke test**

Start the service:
```bash
cd services/connector-manager
uv run uvicorn app.main:app --reload --port 8002
```
Expected log lines: `notion_poll_loop_v2_started interval_sec=60`. No errors. Hit `curl http://localhost:8002/healthz` — returns `{"status": "ok", ...}`.

- [ ] **Step 5: Commit**

```bash
git add services/connector-manager/app/main.py services/connector-manager/app/sync/notion.py
git commit -m "feat(connector-manager): wire NotionSyncWorker into lifespan (60s interim cadence)"
```

---

## Task 1.4 — `connector.notion.recent_activity` capability

**Files:**
- Create: `services/agent-orchestration/app/plugins/notion/recent_activity.py`
- Modify: `services/agent-orchestration/app/plugins/notion/__init__.py` (export the capability)
- Test: `services/agent-orchestration/tests/capabilities/test_notion_recent_activity.py`

- [ ] **Step 1: Inspect existing notion plugin shape**

```bash
cat services/agent-orchestration/app/plugins/notion/__init__.py
ls services/agent-orchestration/app/plugins/notion/
```
Match the existing pattern for plugin discovery (the registry walks plugin packages and reads exported `CAPABILITY` symbols).

- [ ] **Step 2: Write the failing test**

```python
# services/agent-orchestration/tests/capabilities/test_notion_recent_activity.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.plugins.notion.recent_activity import CAPABILITY


@pytest.mark.asyncio
async def test_returns_events_with_freshness(db_pool, monkeypatch):
    user_id = uuid4()

    # Seed a fresh sync state + an activity_events row
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO connector_sync_state (user_id, source, last_synced_at, last_status, cursor)
               VALUES ($1, 'notion', NOW(), 'ok', '{}'::jsonb)""",
            user_id,
        )
        await conn.execute(
            """INSERT INTO activity_events
               (id, user_id, source, event_type, external_id, title, snippet, occurred_at, raw_ref)
               VALUES (gen_random_uuid(), $1, 'notion', 'page_edited', 'page-test',
                       'Test Page', NULL, NOW() - INTERVAL '2 minutes', '{}'::jsonb)""",
            user_id,
        )

    # Stub the freshen mixin to a no-op (state is already fresh)
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": None,
    }
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    result = await CAPABILITY(
        user_id=str(user_id),
        project_id=None,
        org_id=None,
        inputs={"since": "today"},
    )

    assert result.summary.startswith("found 1") or "1 notion event" in result.summary.lower()
    content = result.content
    assert isinstance(content, dict)
    assert "events" in content and len(content["events"]) == 1
    assert "freshness" in content
    assert content["freshness"]["sync_status"] == "ok"

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
```

- [ ] **Step 3: Run to verify failure**

```bash
cd services/agent-orchestration
uv run pytest tests/capabilities/test_notion_recent_activity.py -v
```
Expected: `ImportError`.

- [ ] **Step 4: Implement the capability**

```python
# services/agent-orchestration/app/plugins/notion/recent_activity.py
"""connector.notion.recent_activity — time-windowed feed of Notion edits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.capabilities._freshen_mixin import FreshenBeforeRead
from app.capabilities.base import Capability, CapabilityResult, Citation
from app.db import db
from app.repositories.users import UsersRepository
from app.util.since import resolve_since


@dataclass
class _NotionRecentActivity(FreshenBeforeRead):
    name: str = "connector.notion.recent_activity"
    description: str = (
        "List Notion pages edited in a time window. Use for 'what happened in "
        "Notion today/this week' prompts. Reads a fresh local cache (auto-refreshed "
        "if older than 60s)."
    )
    scope: str = "read"
    default_permission: str = "auto"
    source: str = "notion"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "ISO timestamp or 'today'/'1h'/'24h'/'7d'",
                },
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
                "keyword": {"type": "string", "description": "optional substring filter on title/snippet"},
            },
            "required": ["since"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        uid = UUID(user_id)
        freshness = await self.ensure_fresh(uid)

        users_repo = UsersRepository(db.raw)
        tz_name = await users_repo.get_timezone(uid)
        start_ts = resolve_since(inputs.get("since", "today"), ZoneInfo(tz_name))

        limit = int(inputs.get("limit", 50))
        keyword = inputs.get("keyword")

        async with db.acquire() as conn:
            sql = """
                SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
                FROM activity_events
                WHERE user_id = $1::uuid AND source = 'notion' AND occurred_at >= $2
            """
            args: list[Any] = [user_id, start_ts]
            if keyword:
                sql += " AND (title ILIKE $3 OR COALESCE(snippet, '') ILIKE $3)"
                args.append(f"%{keyword}%")
            sql += f" ORDER BY occurred_at DESC LIMIT ${len(args) + 1}"
            args.append(limit)
            rows = await conn.fetch(sql, *args)

        events = [dict(r) for r in rows]
        citations = [
            Citation(
                source_type=f"notion_{r['event_type']}",
                provider="notion",
                ref_id=str(r["id"]),
                title=r["title"],
                actor=r.get("actor"),
                excerpt=r.get("snippet"),
                occurred_at=r["occurred_at"].isoformat() if r.get("occurred_at") else None,
            )
            for r in events
        ]
        return CapabilityResult(
            summary=f"found {len(events)} notion events since {inputs['since']}",
            content={"events": events, "freshness": freshness.model_dump()},
            citations=citations,
        )


CAPABILITY = _NotionRecentActivity()
```

- [ ] **Step 5: Export from plugin __init__**

Edit `services/agent-orchestration/app/plugins/notion/__init__.py` — match the discovery pattern (likely a list of `CAPABILITIES = [...]` or auto-imported submodules). If the registry walks the package, just having the module exist is enough.

- [ ] **Step 6: Run tests to verify pass**

```bash
uv run pytest tests/capabilities/test_notion_recent_activity.py -v
```
Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add services/agent-orchestration/app/plugins/notion/ services/agent-orchestration/tests/capabilities/test_notion_recent_activity.py
git commit -m "feat(agent-orchestration): connector.notion.recent_activity capability with freshness"
```

---

## Task 1.5 — Update `activity.query` to use timezone-aware `resolve_since`

**Files:**
- Modify: `services/agent-orchestration/app/plugins/internal/activity.py`
- Test: `services/agent-orchestration/tests/capabilities/test_activity_query_timezone.py`

- [ ] **Step 1: Write the failing test**

```python
# services/agent-orchestration/tests/capabilities/test_activity_query_timezone.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from app.plugins.internal.activity import CAPABILITY as ACTIVITY_QUERY


@pytest.mark.asyncio
@freeze_time("2026-04-19T18:30:00+00:00")
async def test_today_in_kolkata_includes_evening_event(db_pool):
    """At 11pm IST on Apr 19 (= 17:30 UTC), an event from 11:55pm IST on Apr 18
    (= 18:25 UTC) should be EXCLUDED from 'today' (it's yesterday in IST).
    An event from 12:05am IST on Apr 19 (= 18:35 UTC of Apr 18) should be INCLUDED."""
    user_id = uuid4()

    async with db_pool.acquire() as conn:
        # Set user timezone to IST
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, timezone) VALUES ($1, $2, 'x', 'Asia/Kolkata')",
            user_id, f"{user_id}@test.local",
        )
        # Insert two notion events
        await conn.execute(
            """INSERT INTO activity_events (id, user_id, source, event_type, external_id, title, occurred_at, raw_ref)
               VALUES
                 (gen_random_uuid(), $1, 'notion', 'page_edited', 'old', 'Yesterday IST',
                  '2026-04-18T18:25:00+00:00', '{}'::jsonb),
                 (gen_random_uuid(), $1, 'notion', 'page_edited', 'new', 'Today IST',
                  '2026-04-18T18:35:00+00:00', '{}'::jsonb)""",
            user_id,
        )

    result = await ACTIVITY_QUERY(
        user_id=str(user_id),
        project_id=None,
        org_id=None,
        inputs={"since": "today", "source": "notion"},
    )
    titles = {e["title"] for e in result.content}
    assert titles == {"Today IST"}  # 'Yesterday IST' is filtered out

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/capabilities/test_activity_query_timezone.py -v
```
Expected: fail (existing code uses `NOW() - INTERVAL '1 day'` which doesn't respect TZ).

- [ ] **Step 3: Update `activity.py`**

Edit `services/agent-orchestration/app/plugins/internal/activity.py`:

```python
# Replace the body of __call__ with:
async def __call__(
    self,
    *,
    user_id: str,
    project_id: str | None,
    org_id: str | None,
    inputs: dict[str, Any],
) -> CapabilityResult:
    from uuid import UUID
    from zoneinfo import ZoneInfo
    from app.repositories.users import UsersRepository
    from app.util.since import resolve_since

    limit = int(inputs.get("limit", 50))
    source = inputs.get("source", "all")
    keyword = inputs.get("keyword")

    users_repo = UsersRepository(db.raw)
    tz = ZoneInfo(await users_repo.get_timezone(UUID(user_id)))
    start_ts = resolve_since(inputs.get("since", "today"), tz)

    async with db.acquire() as conn:
        base_sql = """
            SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
            FROM activity_events
            WHERE user_id = $1::uuid AND occurred_at >= $2
        """
        args: list[Any] = [user_id, start_ts]
        if project_id:
            base_sql += f" AND project_id = ${len(args) + 1}::uuid"
            args.append(project_id)
        if source and source != "all":
            base_sql += f" AND source = ${len(args) + 1}"
            args.append(source)
        if keyword:
            base_sql += (
                f" AND to_tsvector('english', title || ' ' || COALESCE(snippet, '')) "
                f"@@ plainto_tsquery('english', ${len(args) + 1})"
            )
            args.append(keyword)
        base_sql += f" ORDER BY occurred_at DESC LIMIT ${len(args) + 1}"
        args.append(limit)
        rows = await conn.fetch(base_sql, *args)

    events = [dict(r) for r in rows]
    citations = [
        Citation(
            source_type=f"{r['source']}_{r['event_type']}",
            provider=r["source"],
            ref_id=str(r["id"]),
            title=r["title"],
            actor=r.get("actor"),
            excerpt=r.get("snippet"),
            occurred_at=r["occurred_at"].isoformat() if r.get("occurred_at") else None,
        )
        for r in events
    ]
    return CapabilityResult(
        summary=f"found {len(events)} activity events",
        content=events,
        citations=citations,
    )
```

Delete the `_INTERVAL_MAP` and `_parse_since` helper — they're replaced by `resolve_since`.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/capabilities/test_activity_query_timezone.py -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add services/agent-orchestration/app/plugins/internal/activity.py services/agent-orchestration/tests/capabilities/test_activity_query_timezone.py
git commit -m "fix(agent-orchestration): timezone-aware 'today' in activity.query"
```

---

## Task 1.6 — End-to-end regression test for the original bug

**Files:**
- Test: `services/agent-orchestration/tests/regressions/test_notion_recent_edit_visible.py`
- Create: `services/agent-orchestration/tests/regressions/__init__.py` (empty)

- [ ] **Step 1: Write the regression test**

```python
# services/agent-orchestration/tests/regressions/test_notion_recent_edit_visible.py
"""Regression test for the original bug:

User edited a Notion page 10 minutes before asking 'what happened in my
Notion today?' — got 'no activity found.' This test simulates the same
scenario end-to-end and asserts the edit appears in the answer.

Scope: capability layer only (mocks Notion API + freshen route). The full
chat → planner → capability path is tested in apps/web Playwright.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_notion_edit_10min_ago_is_visible_in_recent_activity(db_pool, monkeypatch):
    user_id = uuid4()

    # Set up: user with IST timezone
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, timezone) VALUES ($1, $2, 'x', 'Asia/Kolkata')",
            user_id, f"{user_id}@test.local",
        )

    # Simulate the freshen mixin succeeding and writing the freshly-edited page
    # to activity_events (this is what NotionSyncWorker would do).
    edit_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO activity_events
               (id, user_id, source, event_type, external_id, title, occurred_at, raw_ref)
               VALUES (gen_random_uuid(), $1, 'notion', 'page_edited', 'edited-page',
                       'My recent edit', $2, '{}'::jsonb)""",
            user_id, edit_time,
        )
        await conn.execute(
            """INSERT INTO connector_sync_state (user_id, source, last_synced_at, last_status, cursor)
               VALUES ($1, 'notion', NOW(), 'ok', '{}'::jsonb)""",
            user_id,
        )

    # Stub the freshen mixin so it sees fresh state and skips the call
    fake_client = AsyncMock()
    fake_client.sync_state_one.return_value = {
        "source": "notion",
        "last_synced_at": datetime.now(timezone.utc),
        "last_status": "ok",
        "last_error": None,
        "last_event_at": edit_time,
    }
    monkeypatch.setattr("app.capabilities._freshen_mixin._client", fake_client)

    from app.plugins.notion.recent_activity import CAPABILITY
    result = await CAPABILITY(
        user_id=str(user_id), project_id=None, org_id=None,
        inputs={"since": "today"},
    )

    titles = [e["title"] for e in result.content["events"]]
    assert "My recent edit" in titles, (
        "Regression: a Notion page edited 10 minutes ago must be visible in "
        "'what happened today' — this was the original Apr 19 bug."
    )
    assert result.content["freshness"]["sync_status"] == "ok"

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM connector_sync_state WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
```

- [ ] **Step 2: Run to verify it passes** (it should — Phase 1 above wired everything)

```bash
uv run pytest tests/regressions/test_notion_recent_edit_visible.py -v
```
Expected: PASS. If it fails, iterate on Tasks 1.1–1.5.

- [ ] **Step 3: Commit**

```bash
git add services/agent-orchestration/tests/regressions/
git commit -m "test(agent-orchestration): regression test for the original Notion staleness bug"
```

---

# Phase 2 — Other connector workers + capabilities

Each subphase is a separate, parallelizable PR with the same shape as Phase 1. Worker file goes in `services/connector-manager/app/sync/<source>.py`, capability in `services/agent-orchestration/app/plugins/<source>/recent_activity.py`. Tests mirror the Notion ones.

For each connector below:
- Read the existing client at `connectors/<source>/src/client.py` to understand its API
- Add a `list_recent(since=, limit=)` method that calls the right vendor endpoint
- Implement the `<Source>SyncWorker` (copy from `notion.py`, swap the client + mapper)
- Register it via `sync_registry.register(<Source>SyncWorker())`
- Add `connector.<source>.recent_activity` capability (copy from notion's, swap source name)
- Wire into lifespan with a temporary `<source>_poll_loop_v2(60)` (Phase 3 replaces this)
- Test pattern matches Phase 1 tests — happy path + auth_failed + idempotency

## Task 2A.1 — `SlackClient.list_recent`

**Files:**
- Modify: `connectors/slack/src/client.py`
- Test: `connectors/slack/tests/test_client_list_recent.py`

- [ ] **Step 1: Read the existing Slack client**

```bash
cat connectors/slack/src/client.py
```
Note channel listing + `conversations.history` patterns. Slack messages live per-channel — `list_recent` must fan out across channels.

- [ ] **Step 2: Write the failing test**

```python
# connectors/slack/tests/test_client_list_recent.py
from __future__ import annotations

import pytest
import respx
from httpx import Response

from slack.src.client import SlackClient


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_aggregates_messages_across_channels():
    respx.get("https://slack.com/api/conversations.list").mock(
        return_value=Response(200, json={
            "ok": True,
            "channels": [
                {"id": "C1", "name": "general"},
                {"id": "C2", "name": "engineering"},
            ],
        })
    )
    respx.get("https://slack.com/api/conversations.history").mock(
        return_value=Response(200, json={
            "ok": True,
            "messages": [
                {"ts": "1700000001.0", "text": "hello", "user": "U1"},
            ],
        })
    )

    client = SlackClient(access_token="xoxb-test")
    msgs = await client.list_recent(limit=10)
    assert len(msgs) == 2  # 1 message per channel × 2 channels
    assert all("channel_id" in m for m in msgs)


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_filters_by_since():
    respx.get("https://slack.com/api/conversations.list").mock(
        return_value=Response(200, json={"ok": True, "channels": [{"id": "C1", "name": "x"}]})
    )
    respx.get("https://slack.com/api/conversations.history").mock(
        return_value=Response(200, json={
            "ok": True,
            "messages": [
                {"ts": "1700000001.0", "text": "old", "user": "U1"},
                {"ts": "1800000000.0", "text": "new", "user": "U1"},
            ],
        })
    )

    from datetime import datetime, timezone
    client = SlackClient(access_token="xoxb-test")
    since = datetime.fromtimestamp(1750000000, tz=timezone.utc)
    msgs = await client.list_recent(limit=10, since=since)
    assert len(msgs) == 1
    assert msgs[0]["text"] == "new"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd connectors/slack
uv run pytest tests/test_client_list_recent.py -v
```
Expected: AttributeError.

- [ ] **Step 4: Add `list_recent` to SlackClient**

Append to `connectors/slack/src/client.py`:

```python
async def list_recent(
    self,
    *,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    """Aggregate messages across all joined channels, optionally filtered
    by `since`. Each message dict is annotated with `channel_id`."""
    messages: list[dict] = []
    oldest = str(since.timestamp()) if since else None

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. List joined channels
        resp = await client.get(
            "https://slack.com/api/conversations.list",
            headers=self._headers,
            params={"types": "public_channel,private_channel", "limit": 200},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise httpx.HTTPStatusError(
                f"slack error: {data.get('error')}",
                request=resp.request, response=resp,
            )
        channels = data.get("channels", [])

        # 2. For each channel, pull recent history
        for ch in channels:
            if len(messages) >= limit:
                break
            params = {"channel": ch["id"], "limit": min(100, limit - len(messages))}
            if oldest:
                params["oldest"] = oldest
            resp = await client.get(
                "https://slack.com/api/conversations.history",
                headers=self._headers, params=params,
            )
            if resp.status_code != 200:
                continue  # skip silently per-channel; surface failure at aggregate level
            data = resp.json()
            if not data.get("ok"):
                continue
            for m in data.get("messages", []):
                m["channel_id"] = ch["id"]
                m["channel_name"] = ch.get("name")
                messages.append(m)

    return messages[:limit]
```

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/test_client_list_recent.py -v
```
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add connectors/slack/src/client.py connectors/slack/tests/
git commit -m "feat(slack): SlackClient.list_recent — aggregate across channels"
```

---

## Task 2A.2 — `SlackSyncWorker`

**Files:**
- Create: `services/connector-manager/app/sync/slack.py`
- Test: `services/connector-manager/tests/sync/test_slack.py`

- [ ] **Step 1: Write the failing test** — same shape as `test_notion.py` but with Slack-specific page mock. Reuse the three test scenarios: writes activity_events on success, records auth_failed on 401, idempotent on repeated call.

- [ ] **Step 2: Run to verify failure** (`ImportError`).

- [ ] **Step 3: Implement** — copy `services/connector-manager/app/sync/notion.py`, swap:
  - `source = "slack"`
  - Import `SlackClient` instead of `NotionClient`
  - Replace `_map_notion_page` with `_map_slack_message` (extract `ts`, `text`, `channel_id`, `user` → activity_events fields)
  - `external_id` is `f"{channel_id}:{ts}"` (Slack messages are unique per channel + ts)

```python
# services/connector-manager/app/sync/slack.py
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.security import decrypt_token
from app.sync import registry as sync_registry
from app.sync.base import SyncResult, categorize_error

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from slack.src.client import SlackClient  # noqa: E402

logger = get_logger(__name__)


class SlackSyncWorker:
    source = "slack"

    async def freshen(
        self, user_id: UUID, *, since: datetime | None = None, force: bool = False
    ) -> SyncResult:
        conn_repo = ConnectorsRepository(db.raw)
        activity_repo = ActivityEventsRepository(db.raw)
        state_repo = ConnectorSyncStateRepository(db.raw)

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="slack")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest: datetime | None = None

        for row in connectors:
            try:
                token = decrypt_token(row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "slack", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = SlackClient(access_token=token)
            try:
                msgs = await client.list_recent(since=since, limit=200)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "slack", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for m in msgs:
                mapped = _map_slack_message(m)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(row["project_id"]) if row.get("project_id") else None,
                    source="slack",
                    event_type=mapped["event_type"],
                    key=mapped["key"],
                    title=mapped["title"],
                    snippet=mapped.get("snippet"),
                    actor=mapped.get("actor"),
                    actor_id=mapped.get("actor_id"),
                    occurred_at=mapped["occurred_at"],
                    raw_ref=mapped.get("raw_ref"),
                    external_id=mapped["key"],
                )
                if result["inserted"]:
                    rows_added += 1
                if newest is None or (mapped["occurred_at"] and mapped["occurred_at"] > newest):
                    newest = mapped["occurred_at"]

        await state_repo.record_success(user_id, "slack", last_event_at=newest, cursor={})
        return SyncResult(rows_added=rows_added, last_event_at=newest, status="ok")


def _map_slack_message(m: dict[str, Any]) -> dict[str, Any] | None:
    ts = m.get("ts")
    channel_id = m.get("channel_id")
    if not ts or not channel_id:
        return None
    occurred_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    text = (m.get("text") or "").strip()
    title = text[:120] if text else "(empty Slack message)"
    snippet = text if len(text) > 120 else None

    return {
        "event_type": "message_posted",
        "key": f"{channel_id}:{ts}",
        "title": title,
        "snippet": snippet,
        "actor": None,
        "actor_id": m.get("user"),
        "occurred_at": occurred_at,
        "raw_ref": {
            "channel_id": channel_id,
            "channel_name": m.get("channel_name"),
            "ts": ts,
        },
    }


async def slack_poll_loop_v2(interval_sec: int) -> None:
    """Temporary cron — Phase 3 replaces with adaptive scheduler."""
    import asyncio
    from app.repositories.connectors import ConnectorsRepository

    logger.info("slack_poll_loop_v2_started", interval_sec=interval_sec)
    worker = SlackSyncWorker()
    while True:
        try:
            conn_repo = ConnectorsRepository(db.raw)
            user_ids = {str(r["user_id"]) for r in await conn_repo.list_connected(tool="slack")}
            for uid in user_ids:
                try:
                    await worker.freshen(UUID(uid))
                except Exception as e:  # noqa: BLE001
                    logger.error("slack_freshen_crashed", user_id=uid, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("slack_poll_v2_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)


sync_registry.register(SlackSyncWorker())
```

- [ ] **Step 4: Run tests to verify pass.**

- [ ] **Step 5: Wire into lifespan**

Edit `services/connector-manager/app/main.py`:
- Replace `from app.sync.slack_sync import slack_sync_loop` (existing, indexes `connector_index`) — KEEP this; it's a different feature
- Add: `from app.sync.slack import slack_poll_loop_v2`
- Add to lifespan: `bg_tasks.append(asyncio.create_task(slack_poll_loop_v2(60)))`

- [ ] **Step 6: Commit**

```bash
git add services/connector-manager/app/sync/slack.py services/connector-manager/app/main.py services/connector-manager/tests/sync/test_slack.py
git commit -m "feat(connector-manager): SlackSyncWorker + slack_poll_loop_v2"
```

---

## Task 2A.3 — `connector.slack.recent_activity` capability

**Files:**
- Create: `services/agent-orchestration/app/plugins/slack/recent_activity.py`
- Test: `services/agent-orchestration/tests/capabilities/test_slack_recent_activity.py`

- [ ] **Step 1: Copy** `services/agent-orchestration/app/plugins/notion/recent_activity.py` to `slack/recent_activity.py`. Replace:
  - Class name: `_SlackRecentActivity`
  - `name = "connector.slack.recent_activity"`
  - `source = "slack"`
  - SQL filter: `source = 'slack'`
  - Description: "List Slack messages posted in a time window..."

- [ ] **Step 2: Test** — copy `test_notion_recent_activity.py` to `test_slack_recent_activity.py`, swap `notion`→`slack` in fixtures and assertions.

- [ ] **Step 3: Run, commit.**

```bash
git add services/agent-orchestration/app/plugins/slack/ services/agent-orchestration/tests/capabilities/test_slack_recent_activity.py
git commit -m "feat(agent-orchestration): connector.slack.recent_activity capability"
```

---

## Task 2B — Gmail (worker + capability)

Same shape as 2A. Vendor specifics:
- Add `GmailClient.list_recent` using `users.history.list` with `startHistoryId = cursor.history_id`. On 404 (history expired), fall back to `users.messages.list?q=newer_than:1d` and re-anchor. Return list of message dicts.
- `external_id` = Gmail message id
- `_map_gmail_message`: title = `Subject:` header, snippet = Gmail's `snippet` field, occurred_at = `internalDate` (epoch ms)
- Cursor stored: `{"history_id": "..."}`
- Worker file: `services/connector-manager/app/sync/gmail.py`
- Capability: `services/agent-orchestration/app/plugins/gmail/recent_activity.py`

Tests mirror Notion's three scenarios.

Commit: `feat(connector-manager): GmailSyncWorker + connector.gmail.recent_activity`

---

## Task 2C — GDrive (worker + capability)

Same shape as 2A. Vendor specifics:
- Add `GDriveClient.list_recent` using `changes.list?pageToken={cursor.page_token}`. On expired-token error, call `changes.getStartPageToken` and re-anchor.
- `external_id` = file id (Drive `fileId` from change record)
- `_map_gdrive_change`: title = `name`, snippet = `mimeType`, occurred_at = `modifiedTime`, actor_id = `lastModifyingUser.emailAddress`
- Cursor: `{"page_token": "..."}`
- Worker: `services/connector-manager/app/sync/gdrive.py` (do NOT touch the existing `gdrive_sync.py` — that's the FTS index sync, a separate feature)
- Capability: `services/agent-orchestration/app/plugins/gdrive/recent_activity.py`

Commit: `feat(connector-manager): GDriveSyncWorker + connector.gdrive.recent_activity`

---

## Task 2D — GitHub (worker + capability)

Same shape as 2A. Vendor specifics:
- Add `GitHubClient.list_recent` using `users/{user}/events` and per-installation `repos/{repo}/events`, filtered by `id > cursor.last_event_id`. Sorted by event id desc.
- `external_id` = GitHub event id
- `_map_github_event`: title = synthesized from event type + repo (`"alice opened PR #42 in foo/bar"`), occurred_at = `created_at`, actor_id = `actor.login`
- Cursor: `{"last_event_id": "..."}`
- Worker: `services/connector-manager/app/sync/github.py`
- Capability: `services/agent-orchestration/app/plugins/github/recent_activity.py`

Commit: `feat(connector-manager): GitHubSyncWorker + connector.github.recent_activity`

---

# Phase 3 — Adaptive scheduler

Replaces the per-source `<source>_poll_loop_v2(60)` calls with one scheduler that computes per-`(user, source)` cadence and dispatches accordingly.

## Task 3.1 — `compute_cadence_state` helper

**Files:**
- Create: `services/connector-manager/app/sync/scheduler.py`
- Test: `services/connector-manager/tests/sync/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

```python
# services/connector-manager/tests/sync/test_scheduler.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from app.sync.scheduler import compute_cadence_state, CadenceState


@freeze_time("2026-04-19T18:30:00+00:00")
def test_active_when_recent_user_query():
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        last_event_at=None,
        consecutive_fails=0,
    )
    assert state == CadenceState(interval_sec=60, label="active")


@freeze_time("2026-04-19T18:30:00+00:00")
def test_active_when_recent_event_within_24h():
    state = compute_cadence_state(
        last_user_query_at=None,
        last_event_at=datetime.now(timezone.utc) - timedelta(hours=2),
        consecutive_fails=0,
    )
    assert state.interval_sec == 60


@freeze_time("2026-04-19T18:30:00+00:00")
def test_idle_when_neither():
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(hours=5),
        last_event_at=datetime.now(timezone.utc) - timedelta(days=3),
        consecutive_fails=0,
    )
    assert state == CadenceState(interval_sec=300, label="idle")


@freeze_time("2026-04-19T18:30:00+00:00")
@pytest.mark.parametrize("fails,expected_sec", [
    (3, 120), (4, 240), (5, 480), (6, 960), (7, 1800), (10, 1800),
])
def test_backoff_caps_at_30min(fails, expected_sec):
    state = compute_cadence_state(
        last_user_query_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        last_event_at=None,
        consecutive_fails=fails,
    )
    assert state.interval_sec == expected_sec
    assert state.label == "erroring"
```

- [ ] **Step 2: Run to verify failure** (ImportError).

- [ ] **Step 3: Implement**

```python
# services/connector-manager/app/sync/scheduler.py
"""Adaptive cadence scheduler.

For each (user, source) pair, compute the right poll interval based on:
- recent user attention (queries against the source)
- recent activity (events ingested in the last 24h)
- error state (exponential backoff if consecutive_fails >= 3)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.sync import registry as sync_registry

logger = get_logger(__name__)


class CadenceState(NamedTuple):
    interval_sec: int
    label: str


_BACKOFF = [120, 240, 480, 960, 1800]  # capped at 30 min


def compute_cadence_state(
    *,
    last_user_query_at: datetime | None,
    last_event_at: datetime | None,
    consecutive_fails: int,
) -> CadenceState:
    now = datetime.now(timezone.utc)

    if consecutive_fails >= 3:
        idx = min(consecutive_fails - 3, len(_BACKOFF) - 1)
        return CadenceState(interval_sec=_BACKOFF[idx], label="erroring")

    is_active = (
        (last_user_query_at and (now - last_user_query_at) < timedelta(hours=1))
        or (last_event_at and (now - last_event_at) < timedelta(hours=24))
    )
    if is_active:
        return CadenceState(interval_sec=60, label="active")

    return CadenceState(interval_sec=300, label="idle")


async def scheduler_tick() -> None:
    """One scheduler tick — for every (user, source) pair, dispatch freshen
    if interval has elapsed since last_synced_at."""
    state_repo = ConnectorSyncStateRepository(db.raw)
    conn_repo = ConnectorsRepository(db.raw)

    # Iterate every connected (user, source) pair
    for source in sync_registry.all_sources():
        worker = sync_registry.get(source)
        if worker is None:
            continue
        connectors = await conn_repo.list_connected(tool=source)
        user_ids = {str(r["user_id"]) for r in connectors}

        for uid_str in user_ids:
            uid = UUID(uid_str)
            state = await state_repo.get(uid, source) or {}
            cadence = compute_cadence_state(
                last_user_query_at=None,  # Phase 3 follow-up: read from a query-log table
                last_event_at=state.get("last_event_at"),
                consecutive_fails=state.get("consecutive_fails", 0),
            )

            now = datetime.now(timezone.utc)
            last = state.get("last_synced_at")
            elapsed = (now - last).total_seconds() if last else float("inf")
            if elapsed < cadence.interval_sec:
                continue

            try:
                await worker.freshen(uid)
            except Exception as e:  # noqa: BLE001
                logger.error("scheduler_freshen_crashed",
                             user_id=uid_str, source=source, error=str(e))


async def scheduler_loop() -> None:
    """Master scheduler loop — runs every 30s and dispatches per-source ticks."""
    logger.info("scheduler_loop_started")
    while True:
        try:
            await scheduler_tick()
        except Exception as e:  # noqa: BLE001
            logger.error("scheduler_loop_tick_crashed", error=str(e))
        await asyncio.sleep(30)
```

- [ ] **Step 4: Run tests to verify pass.**

- [ ] **Step 5: Replace per-source `_v2` loops with the scheduler**

Edit `services/connector-manager/app/main.py`:
- Remove all `<source>_poll_loop_v2(60)` task creations
- Add: `bg_tasks.append(asyncio.create_task(scheduler_loop()))`

Optionally delete the `_v2` functions from each `app/sync/<source>.py`.

- [ ] **Step 6: Commit**

```bash
git add services/connector-manager/app/sync/scheduler.py services/connector-manager/app/main.py services/connector-manager/app/sync/notion.py services/connector-manager/app/sync/slack.py services/connector-manager/app/sync/gmail.py services/connector-manager/app/sync/gdrive.py services/connector-manager/app/sync/github.py services/connector-manager/tests/sync/test_scheduler.py
git commit -m "feat(connector-manager): adaptive cadence scheduler — replaces per-source poll loops"
```

---

# Phase 4 — Frontend

## Task 4.1 — React Query hook for sync-state

**Files:**
- Create: `apps/web/lib/queries/connectors.ts` (extend if exists)

- [ ] **Step 1: Read the existing queries file**

```bash
cat apps/web/lib/queries/connectors.ts
```

- [ ] **Step 2: Add hooks**

```ts
// Append to apps/web/lib/queries/connectors.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export type SyncStateItem = {
  source: string;
  last_synced_at: string | null;
  last_status: 'never' | 'ok' | 'auth_failed' | 'vendor_error' | 'network_error';
  last_error: string | null;
  last_event_at: string | null;
};

export function useSyncState() {
  return useQuery<{ items: SyncStateItem[] }>({
    queryKey: ['connectors', 'sync-state'],
    queryFn: () => apiClient.get('/api/connectors/sync-state').then(r => r.data),
    refetchInterval: 10_000,  // 10s poll for chip freshness
  });
}

export function useFreshen(source: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.post(`/api/tools/${source}/freshen`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['connectors', 'sync-state'] }),
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/lib/queries/connectors.ts
git commit -m "feat(web): useSyncState + useFreshen React Query hooks"
```

---

## Task 4.2 — `<ConnectorFreshnessChip>` component

**Files:**
- Create: `packages/design-system/src/connector-freshness-chip.tsx`
- Test: `apps/web/__tests__/connector-freshness-chip.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// apps/web/__tests__/connector-freshness-chip.test.tsx
import { render, screen } from '@testing-library/react';
import { ConnectorFreshnessChip } from '@axis/design-system/connector-freshness-chip';

describe('ConnectorFreshnessChip', () => {
  it('renders green when last_status=ok and synced recently', () => {
    render(<ConnectorFreshnessChip source="notion" state={{
      source: 'notion',
      last_synced_at: new Date().toISOString(),
      last_status: 'ok',
      last_error: null,
      last_event_at: null,
    }} />);
    expect(screen.getByText(/synced/i)).toHaveClass(/green|emerald/i);
  });

  it('renders amber when last_synced_at is older than 2 minutes', () => {
    const oldTs = new Date(Date.now() - 5 * 60_000).toISOString();
    render(<ConnectorFreshnessChip source="notion" state={{
      source: 'notion',
      last_synced_at: oldTs,
      last_status: 'ok',
      last_error: null,
      last_event_at: null,
    }} />);
    expect(screen.getByText(/synced/i)).toHaveClass(/amber|yellow/i);
  });

  it('renders red with reconnect CTA when last_status=auth_failed', () => {
    render(<ConnectorFreshnessChip source="notion" state={{
      source: 'notion',
      last_synced_at: null,
      last_status: 'auth_failed',
      last_error: 'token expired',
      last_event_at: null,
    }} />);
    expect(screen.getByRole('button', { name: /reconnect/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement**

```tsx
// packages/design-system/src/connector-freshness-chip.tsx
import * as React from 'react';
import type { SyncStateItem } from '@axis/web/lib/queries/connectors';

type Props = {
  source: string;
  state: SyncStateItem;
  onReconnect?: () => void;
};

function relativeTime(iso: string | null): string {
  if (!iso) return 'never synced';
  const ageSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (ageSec < 60) return `synced ${ageSec}s ago`;
  if (ageSec < 3600) return `synced ${Math.floor(ageSec / 60)}m ago`;
  return `synced ${Math.floor(ageSec / 3600)}h ago`;
}

export function ConnectorFreshnessChip({ source, state, onReconnect }: Props) {
  if (state.last_status === 'auth_failed') {
    return (
      <button
        onClick={onReconnect}
        className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 hover:bg-red-200"
      >
        Reconnect {source}
      </button>
    );
  }

  const ageSec = state.last_synced_at
    ? (Date.now() - new Date(state.last_synced_at).getTime()) / 1000
    : Infinity;
  const stale = ageSec > 120 || state.last_status !== 'ok';
  const colorClass = stale
    ? 'bg-amber-100 text-amber-700'
    : 'bg-emerald-100 text-emerald-700';

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${colorClass}`}>
      {relativeTime(state.last_synced_at)}
    </span>
  );
}
```

- [ ] **Step 4: Run tests to verify pass.**

- [ ] **Step 5: Commit**

```bash
git add packages/design-system/src/connector-freshness-chip.tsx apps/web/__tests__/connector-freshness-chip.test.tsx
git commit -m "feat(design-system): ConnectorFreshnessChip component"
```

---

## Task 4.3 — `<RefreshButton>` component

**Files:**
- Create: `packages/design-system/src/refresh-button.tsx`

- [ ] **Step 1: Implement** (test follows the same pattern as 4.2)

```tsx
// packages/design-system/src/refresh-button.tsx
import * as React from 'react';
import { useFreshen } from '@axis/web/lib/queries/connectors';

export function RefreshButton({ source }: { source: string }) {
  const freshen = useFreshen(source);
  return (
    <button
      onClick={() => freshen.mutate()}
      disabled={freshen.isPending}
      className="text-xs underline hover:text-blue-700 disabled:opacity-50"
      aria-label={`Refresh ${source}`}
    >
      {freshen.isPending ? 'Refreshing…' : 'Refresh'}
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/design-system/src/refresh-button.tsx
git commit -m "feat(design-system): RefreshButton component"
```

---

## Task 4.4 — Wire chip + button into Connections page

**Files:**
- Modify: `apps/web/app/(app)/connections/page.tsx`

- [ ] **Step 1: Add to each connector card**

Inside the existing card render, alongside the existing connect/disconnect controls:

```tsx
import { ConnectorFreshnessChip } from '@axis/design-system/connector-freshness-chip';
import { RefreshButton } from '@axis/design-system/refresh-button';
import { useSyncState } from '@/lib/queries/connectors';

// In the component body:
const { data } = useSyncState();
const stateBySource = Object.fromEntries((data?.items ?? []).map(s => [s.source, s]));

// In each card's JSX (where connector status is shown):
{stateBySource[connector.source] && (
  <div className="flex items-center gap-2">
    <ConnectorFreshnessChip
      source={connector.source}
      state={stateBySource[connector.source]}
      onReconnect={() => router.push(`/connections/${connector.source}/oauth`)}
    />
    <RefreshButton source={connector.source} />
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/app/\(app\)/connections/page.tsx
git commit -m "feat(web): freshness chip + refresh button on Connections page"
```

---

## Task 4.5 — Sidebar status dot

**Files:**
- Modify: `apps/web/components/sidebar.tsx`

- [ ] **Step 1: Add the dot**

```tsx
import { useSyncState } from '@/lib/queries/connectors';

function ConnectionsStatusDot() {
  const { data } = useSyncState();
  const items = data?.items ?? [];
  if (items.some(i => i.last_status === 'auth_failed')) {
    return <span className="w-2 h-2 rounded-full bg-red-500" aria-label="connection broken" />;
  }
  if (items.some(i => i.last_status !== 'ok')) {
    return <span className="w-2 h-2 rounded-full bg-amber-500" aria-label="connection issues" />;
  }
  return <span className="w-2 h-2 rounded-full bg-emerald-500" aria-label="all connections ok" />;
}

// Render <ConnectionsStatusDot /> next to the "Connections" nav item.
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/sidebar.tsx
git commit -m "feat(web): sidebar status dot for connector health"
```

---

## Task 4.6 — Chat-answer freshness footer + render-layer auth_failed alert

**Files:**
- Modify: the existing chat answer renderer (likely `apps/web/components/chat/message.tsx` or `apps/web/app/(app)/chat/...`)

- [ ] **Step 1: Find the renderer**

```bash
grep -rln "freshness" apps/web/ --include='*.tsx' --include='*.ts' | head
```
If no match, find where capability results are rendered into the chat UI and add freshness handling there.

- [ ] **Step 2: Render the inline chip when freshness is present**

In the capability-result rendering branch:

```tsx
{result.content?.freshness && (
  <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
    <span className="capitalize">{result.content.freshness.source}</span>
    <ConnectorFreshnessChip
      source={result.content.freshness.source}
      state={{
        source: result.content.freshness.source,
        last_synced_at: result.content.freshness.last_synced_at,
        last_status: result.content.freshness.sync_status,
        last_error: result.content.freshness.error_message,
        last_event_at: null,
      }}
      onReconnect={() => router.push(`/connections/${result.content.freshness.source}/oauth`)}
    />
  </div>
)}

{result.content?.freshness?.sync_status === 'auth_failed' && (
  <Alert variant="warning" className="mt-2">
    {result.content.freshness.source} isn't responding — your connection
    needs to be refreshed.
    <button onClick={() => router.push(`/connections/${result.content.freshness.source}/oauth`)}>
      Reconnect now
    </button>
  </Alert>
)}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/chat/  apps/web/app/\(app\)/chat/
git commit -m "feat(web): chat-answer freshness footer + render-layer auth_failed alert"
```

---

## Task 4.7 — Connected-sources pill bar reflects freshness

**Files:**
- Modify: the existing pill bar component (find via `grep -rln "Connected sources" apps/web/`)

- [ ] **Step 1: Cross-reference each pill with sync state** — pill turns red if `last_status=auth_failed`, click opens reconnect.

- [ ] **Step 2: Commit.**

---

## Task 4.8 — Playwright E2E smoke

**Files:**
- Create: `apps/web/tests/e2e/notion-recent-activity.spec.ts`

- [ ] **Step 1: Write the spec**

```ts
import { test, expect } from '@playwright/test';

test('asking "what happened in Notion today" returns the recent edit', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name=email]', 'admin@raweval.com');
  await page.fill('[name=password]', process.env.E2E_PASSWORD!);
  await page.click('button[type=submit]');
  await page.waitForURL('/');

  // Assumes Notion is already connected and a page was edited within last 5 min via fixture
  await page.goto('/chat');
  await page.fill('textarea', 'what happened in my Notion today?');
  await page.keyboard.press('Enter');

  await expect(page.locator('text=My recent edit')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('[data-testid="freshness-chip"]')).toContainText(/synced \d+s ago/i);
});
```

- [ ] **Step 2: Add `data-testid="freshness-chip"`** to the chip in Task 4.2 if not already present.

- [ ] **Step 3: Run**

```bash
cd apps/web
pnpm playwright test tests/e2e/notion-recent-activity.spec.ts
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/tests/e2e/notion-recent-activity.spec.ts packages/design-system/src/connector-freshness-chip.tsx
git commit -m "test(web): Playwright smoke for Notion recent_activity"
```

---

# Phase 5 — Cleanup

## Task 5.1 — Delete old `notion_poll.py`

**Files:**
- Delete: `services/connector-manager/app/sync/notion_poll.py`
- Modify: `services/connector-manager/app/main.py`

- [ ] **Step 1: Verify `notion.py` covers everything**

```bash
grep -n "notion_poll" services/connector-manager/app/main.py
```
Should be no remaining references.

- [ ] **Step 2: Delete the file**

```bash
git rm services/connector-manager/app/sync/notion_poll.py
```

- [ ] **Step 3: Smoke test**

```bash
cd services/connector-manager
uv run uvicorn app.main:app --reload --port 8002
```
Expected: clean startup, no ImportError.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(connector-manager): remove obsolete notion_poll.py — replaced by NotionSyncWorker"
```

---

## Task 5.2 — Drop `notion_poll_enabled` config flag

**Files:**
- Modify: `services/connector-manager/app/config.py`
- Modify: `services/connector-manager/app/main.py`
- Modify: `.env.example`

- [ ] **Step 1: Add a per-source kill switch instead** (per spec §10.1)

```python
# services/connector-manager/app/config.py — replace:
#   notion_poll_enabled: bool = True
#   notion_poll_interval_sec: int = 900
# With:
connector_sync_enabled: dict[str, bool] = {
    "slack": True,
    "notion": True,
    "gmail": True,
    "gdrive": True,
    "github": True,
}
```

- [ ] **Step 2: Use it in the scheduler**

In `services/connector-manager/app/sync/scheduler.py:scheduler_tick`, skip sources where `settings.connector_sync_enabled.get(source, True) is False`.

- [ ] **Step 3: Update `.env.example`** — remove `NOTION_POLL_ENABLED`, document new map syntax.

- [ ] **Step 4: Commit**

```bash
git add services/connector-manager/app/config.py services/connector-manager/app/sync/scheduler.py services/connector-manager/app/main.py .env.example
git commit -m "chore(connector-manager): replace notion_poll_enabled with per-source kill switch map"
```

---

# Definition of done (Phase 1 overall)

- [ ] Regression test `tests/regressions/test_notion_recent_edit_visible.py` passes
- [ ] All five connectors (Notion, Slack, Gmail, GDrive, GitHub) expose `recent_activity` and `freshen` capabilities
- [ ] Frontend chip renders correctly in three placements (Connections page, chat answer, sidebar dot)
- [ ] Render-layer alert appears when sync_status=auth_failed (Task 4.6)
- [ ] `make lint` clean across all touched services
- [ ] `make test` clean across all touched services
- [ ] Playwright smoke `notion-recent-activity.spec.ts` passes
- [ ] Old `notion_poll.py` deleted, `notion_poll_enabled` config removed
