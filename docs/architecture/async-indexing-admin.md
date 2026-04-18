# Architecture Evolution — Async Indexing, Background Tasks, Admin Dashboard

**Date:** 2026-04-18
**Problem:** The supervisor loop is fully synchronous. A "search 1000 Drive files" query blocks the user for 30+ seconds. Connector data is fetched on-demand every time instead of pre-indexed.

---

## Problem Breakdown

### 1. Speed: synchronous tool calls are too slow

Current: user asks "find the pricing doc" → Claude calls `connector.gdrive.search` → connector-manager calls Drive API → paginated results → return to Claude → synthesize.

For 1000 files, that's 10+ API pages at 100/page, 15s each = **150 seconds minimum**. Unusable.

### 2. Scale: no local search index

Every search hits the live provider API. If 10 users ask 10 questions each about their Drive files, that's 100 API calls to Google in real-time. Rate limits, latency, cost.

### 3. Completeness: no background data capture

We ingest Slack events via webhook and Notion via 15-min poll, but Gmail, Drive, and GitHub have no background ingestion. The only data we have is what the user explicitly queries.

### 4. Visibility: no admin view

No way to see: how many users, how many runs, which connectors are healthy, what's the average latency, which capabilities fail most, what's the eval quality trend.

---

## Solution: Three-Layer Architecture

```
LAYER 1: BACKGROUND SYNC (pre-index)
  Continuously pulls connector data → local index (Qdrant + Postgres FTS)
  User queries hit LOCAL data, not provider APIs
  
LAYER 2: ASYNC TASK EXECUTION
  Supervisor detects "this will take time" → spawns background task
  Returns immediately with task_id → streams progress via WS
  User sees result when ready (notification)

LAYER 3: ADMIN DASHBOARD
  System-wide metrics, connector health, usage analytics, eval trends
```

---

## Layer 1: Connector Data Index

### New table: `connector_index`

```sql
CREATE TABLE connector_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,           -- slack | notion | gmail | gdrive | github
    resource_type TEXT NOT NULL,  -- message | page | email | file | issue | pr
    resource_id TEXT NOT NULL,    -- provider-native ID
    title TEXT,
    body TEXT,                    -- full text content for FTS
    url TEXT,
    author TEXT,
    author_id TEXT,
    occurred_at TIMESTAMPTZ,
    metadata JSONB,              -- provider-specific fields
    embedding VECTOR(1024),      -- Voyage vector for semantic search (future)
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, tool, resource_id)
);

CREATE INDEX idx_connector_index_fts 
    ON connector_index USING gin(to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(body,'')));
CREATE INDEX idx_connector_index_user_tool 
    ON connector_index (user_id, tool, occurred_at DESC);
CREATE INDEX idx_connector_index_project 
    ON connector_index (project_id, tool) WHERE project_id IS NOT NULL;
```

### Background sync workers

Each connector gets a sync task that runs periodically:

| Connector | Sync Method | Frequency | What it indexes |
|---|---|---|---|
| Slack | Events API (already live) + backfill | Real-time + daily full | Messages, threads |
| Notion | Poll (already live) + deep index | 15 min + daily full | Pages with block content |
| Gmail | messages.list pagination | Hourly | Emails (subject + snippet + from/to) |
| Drive | files.list + changes.list | Hourly + delta via changes API | File metadata + content for Docs |
| GitHub | events API + search | Hourly | Issues, PRs, comments |

### How search changes

Before (slow):
```
User → Claude → connector.gdrive.search → connector-manager → Drive API → paginate → return
```

After (fast):
```
User → Claude → connector.gdrive.search → Postgres FTS on connector_index → instant results
                                           ↑
                                    Background worker keeps this fresh
```

---

## Layer 2: Async Task Execution

### When does the supervisor go async?

The supervisor stays synchronous for simple queries (1-2 tool calls, <10s). For complex ones:

- Query touches >1 connector ("search Slack AND Notion AND Drive")
- Query requires deep pagination ("find all files mentioning pricing")
- User explicitly asks for a report/export

### How it works

```
POST /run → supervisor starts
         → detects complexity (>2 tools or explicit "generate report")
         → creates agent_tasks row with status='running'
         → returns immediately: {task_id, status: "processing", output: "Working on it..."}
         → spawns asyncio.create_task(background_supervisor(...))
         → streams progress via Redis events
         → when done: updates agent_tasks.status='done', publishes task.completed
         → WS delivers final result to client
```

### New: `POST /run` can return early

```python
class RunResponse(BaseModel):
    action_id: str
    task_id: str
    message_id: str | None       # None if async (not yet complete)
    status: str                   # 'completed' | 'processing'
    output: str                   # full output or "Working on it..."
    ...
```

---

## Layer 3: Admin Dashboard

### Admin API routes (api-gateway)

| Endpoint | Purpose |
|---|---|
| `GET /admin/stats` | System-wide metrics: users, runs, connectors, avg latency |
| `GET /admin/users` | All users with last_active, run_count, connector_count |
| `GET /admin/connectors` | All connectors across all users with health |
| `GET /admin/runs` | Recent agent runs with latency, tokens, eval scores |
| `GET /admin/eval` | Eval quality trends: avg composite, flagged %, by rubric |
| `GET /admin/errors` | Recent errors from all services |
| `GET /admin/index-status` | Background sync status per connector per user |

### Admin web page

New route: `/admin` — accessible only to users with `owner` role on any org.

---

## Implementation Plan

1. Migration 013: `connector_index` table
2. Background sync infrastructure in connector-manager
3. Update capabilities to search local index first, fall back to live API
4. Async task mode in supervisor
5. Admin API routes
6. Admin web page
