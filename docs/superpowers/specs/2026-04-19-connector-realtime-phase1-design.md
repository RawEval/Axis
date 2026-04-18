# Connector Real-Time Rewrite — Phase 1 Design

| Field | Value |
|---|---|
| Status | **Draft for review** |
| Author | Claude (with admin@raweval.com) |
| Date | 2026-04-19 |
| Scope | Phase 1 of connector real-time work — polling + on-query freshen + parity + UI freshness chip |
| Out of scope | Webhook ingestion infrastructure (deferred to Phase 2 spec, likely landing alongside use-case-driven proactive surfaces) |
| Related ADRs | 005 (agentic architecture), 007 (activity feed), 009 (positioning pivot — proactive workspace), 010 (org + RBAC) |

## 1. Background

### 1.1 The reported bug

A user edited a Notion page, asked the assistant "what happened in my Notion today?" ten minutes later, and got back **"no activity found."** Notion was connected, the OAuth token was valid, the edit was visible in Notion's web UI.

### 1.2 What the audit found

The bug is not specific to Notion. It is the visible symptom of an architectural pattern repeated across the connector layer:

| # | Defect | File |
|---|---|---|
| 1 | `activity.query` reads the local `activity_events` table, never the live vendor API. Edits younger than the last poll are invisible. | `services/agent-orchestration/app/plugins/internal/activity.py:80-100` |
| 2 | The Notion poll calls `search(query="", limit=20)` with no `last_edited_time` sort. Notion returns top-20 by relevance/access — a freshly-edited page may not appear. | `services/connector-manager/app/sync/notion_poll.py:70` + `connectors/notion/src/client.py:24-32` |
| 3 | Sync errors are swallowed. Token expired, vendor 5xx, network timeout — all logged as warnings, then the loop continues. The user sees "no activity found," indistinguishable from "nothing happened." | `notion_poll.py:71-78` |
| 4 | Poll cadence is 15 minutes (`notion_poll_interval_sec = 900`). Not real-time by any definition. | `services/connector-manager/app/config.py:15-16` |
| 5 | "Today" is computed as `NOW() - INTERVAL '1 day'` in the database (UTC). Near midnight in a non-UTC timezone, the user's "today" is filtered out. | `activity.py:82,123-136` |
| 6 | **Only Notion has a background sync at all.** Slack, Gmail, GitHub, GDrive, and Linear have no `recent_activity` capability and no sync into `activity_events`. The same query against any of them returns empty by design. | `services/agent-orchestration/app/capabilities/*.py` (search-only) |

### 1.3 Why this matters for Axis specifically

ADR 009 positions Axis as **the proactive workspace layer for teams** — software that "watches in the background and surfaces what the user would otherwise miss." Silent staleness is therefore not an ordinary bug; it is an existential contradiction with the product's positioning. A "no activity found" answer that is actually "we didn't check recently" undermines the trust that the proactive promise depends on.

## 2. Goals

1. When a user asks "what happened in <connector> today/this hour/etc.", the answer reflects reality within ~1–2 seconds — not the state of a 15-minute-old cache.
2. Every connector (Slack, Notion, Gmail, GDrive, GitHub, Linear) exposes the same `recent_activity` shape. Feature parity is non-negotiable.
3. The user can tell, at a glance, whether each connector is fresh, stale, or broken — and force a refresh manually if they want to.
4. The agent never says "no activity found" when sync actually failed. Empty states are honest.
5. The original Notion bug is covered by an automated regression test that would have caught it.

## 3. Non-goals (Phase 2)

- Webhook ingestion infrastructure (public webhook endpoint in `api-gateway`, signature verification, replay/dedup, subscription renewal cron for Drive/Gmail watch channels, dev tunneling). Deferred to Phase 2.
- Proactive push notifications fired without a user query. Deferred — these depend on the webhook layer and sit naturally with the use-case-driven feature work.
- New connectors. Phase 1 covers parity for the existing five plus Linear (which appears in capabilities but lacks a worker today).

## 4. Architecture overview

Three concentric freshness layers. Each is independently understandable.

```
                      ┌─────────────────────────────────┐
   Vendor API         │  POLL (primary in Phase 1)      │
   (live calls)       │  - Per-source SyncWorker        │
                      │  - 60s active / 5min idle / exp │
                      │    backoff on errors            │
                      │  - Writes activity_events       │
                      │  - Updates connector_sync_state │
                      └────────────┬────────────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │  activity_events     │ ◄─── single read source
                        │  + connector_sync_   │      for activity.query and
                        │    state             │      every recent_activity capability
                        └──────────┬───────────┘
                                   ▲
   User asks         ┌─────────────┴──────────────────┐
   "what happened    │  ON-QUERY FRESHEN  (~1–2s)     │
   today?"      ──▶  │  capability checks last_synced │
                     │  if stale >60s: synchronous    │
                     │  freshen() before reading      │
                     │  bounded 8s timeout            │
                     └────────────────────────────────┘
                                   ▲
   User clicks       ┌─────────────┴──────────────────┐
   refresh in UI ──▶ │  MANUAL FRESHEN (escape hatch) │
                     │  POST /api/tools/<src>/freshen │
                     │  same code path as on-query    │
                     └─────────────────────────────────┘
```

Key properties:

- **One read path for the agent.** `activity.query` and every `connector.<X>.recent_activity` capability read only from `activity_events`. They do not call vendor APIs directly. This keeps the capability layer simple and consistent.
- **Three write paths, one writer interface.** Poll, on-query freshen, and manual refresh all call the same per-source `SyncWorker.freshen()` method. There is no separate "live" code path.
- **Cache is no longer the freshness bottleneck.** On-query freshen tops up the gap between polls. The cache exists for query speed and history, not as the only source of truth.

## 5. Per-connector capability parity

After Phase 1, every connector exposes the same capability shape:

| Capability | Slack | Notion | Gmail | GDrive | GitHub | Linear |
|---|---|---|---|---|---|---|
| `connector.<X>.recent_activity` *(time-windowed feed)* | new | fixed | new | new | new | new |
| `connector.<X>.search` *(keyword)* | exists | exists | exists | exists | exists | new |
| `connector.<X>.freshen` *(force live sync now)* | new | new | new | new | new | new |
| Background poll → `activity_events` | new | fixed | new | new | new | new |

### 5.1 `recent_activity` contract

Inputs:
- `since` — ISO timestamp or relative ("today", "1h", "24h"). Required.
- `limit` — default 50, max 200.
- `keyword` — optional, applied as substring match on `title`/`snippet`.

Behavior:
1. Call `ensure_fresh(user_id)` — runs the freshen mixin (§7.1).
2. Read from `activity_events` filtered by `(user_id, source, occurred_at >= since)`.
3. Return rows + a `freshness` field: `{ last_synced_at, sync_status: "ok"|"stale"|"auth_failed"|"vendor_error"|"network_error", error_message?: string }`.

The agent uses `freshness` to be honest in its response — e.g. *"I checked Slack 3 seconds ago — no activity. Last successful sync was 14:32."*

### 5.2 `freshen` contract

Inputs:
- `force` — default false. If false, skip if `last_synced_at < 60s ago`.
- `since` — optional. If provided, sync extends back at least to this timestamp (for back-fill).

Behavior:
1. Call vendor API live (per-source — see §6.4).
2. Write new rows to `activity_events` (idempotent via the unique constraint in §6.2).
3. Update `connector_sync_state`: `last_synced_at`, `last_status`, `last_error`, `consecutive_fails`.
4. Return `(rows_added, status, last_synced_at, error?)`.

### 5.3 Why a separate capability per connector instead of a single `activity.query` that fans out

Because the LLM picks tools by name, and "what happened in *Slack* today" should be a single targeted call, not a fanout across all six connectors. The fanout case ("what happened today" with no source) is handled by the existing `activity.query`, which now reads the same `activity_events` table that the per-connector capabilities populate.

### 5.4 Why `freshen` is its own capability

Because the manual "Refresh" button in the UI is also a `freshen` call. Same code path for user-triggered and agent-triggered refresh.

## 6. Sync engine and data model

### 6.1 New table: `connector_sync_state`

```sql
CREATE TABLE connector_sync_state (
  user_id           UUID NOT NULL,
  source            TEXT NOT NULL,  -- 'slack'|'notion'|'gmail'|'gdrive'|'github'|'linear'
  last_synced_at    TIMESTAMPTZ,
  last_status       TEXT NOT NULL DEFAULT 'never',  -- 'ok'|'auth_failed'|'vendor_error'|'network_error'|'never'
  last_error        TEXT,
  last_event_at     TIMESTAMPTZ,    -- newest activity_events.occurred_at we've seen
  consecutive_fails INT  NOT NULL DEFAULT 0,
  cursor            JSONB,          -- per-vendor pagination state (Slack ts, Gmail historyId, etc.)
  PRIMARY KEY (user_id, source)
);

CREATE INDEX connector_sync_state_status_idx
  ON connector_sync_state (last_status) WHERE last_status != 'ok';
```

Migration file: `infra/docker/init/postgres/0NN_connector_sync_state.sql` (next available number).

This is the single source of truth for "is data fresh?" The freshness chip, the on-query freshen mixin, and the cron scheduler all read it.

### 6.2 `activity_events` — additive change only

```sql
ALTER TABLE activity_events
  ADD COLUMN external_id TEXT,
  ADD CONSTRAINT activity_events_source_external_uniq
    UNIQUE (user_id, source, external_id);

UPDATE activity_events SET external_id = id::text WHERE external_id IS NULL;
ALTER TABLE activity_events ALTER COLUMN external_id SET NOT NULL;
```

Migration file: `infra/docker/init/postgres/0NN_activity_events_external_id.sql`.

The existing `id` column stays as the primary key. `external_id` is the vendor's stable identifier (Notion page id, Slack message ts + channel id, Gmail message id, GitHub event id, Drive change id, Linear issue update id) — used to make ingest idempotent so retries and overlapping syncs do not duplicate rows.

### 6.3 SyncWorker — one shape, six implementations

`services/connector-manager/app/sync/base.py`:

```python
class SyncWorker(Protocol):
    source: str

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
    ) -> SyncResult: ...

class SyncResult(BaseModel):
    rows_added: int
    last_event_at: datetime | None
    status: Literal["ok", "auth_failed", "vendor_error", "network_error"]
    error_message: str | None = None
```

One concrete worker per source: `services/connector-manager/app/sync/<source>.py`. Each calls its connector client, maps vendor responses to `activity_events` rows, upserts using the unique constraint, and updates `connector_sync_state`.

The cron loop (`services/connector-manager/app/sync/scheduler.py`) and the `/tools/<source>/freshen` HTTP endpoint both call the same `freshen()` method. There is no separate "live" code path.

### 6.4 Per-source vendor API mapping

| Source | Endpoint(s) used | Cursor stored |
|---|---|---|
| **Slack** | `conversations.list` (channels user is in) → `conversations.history` per channel since `cursor.oldest_ts` | `oldest_ts` per channel |
| **Notion** | `/v1/search` with `sort: { timestamp: "last_edited_time", direction: "descending" }`, paginated (see §6.5) | `next_cursor` from last full sweep + `last_edited_time` of newest seen page |
| **Gmail** | `users.history.list` with `startHistoryId = cursor.history_id`. On `404 NotFound` (history expired), fall back to `users.messages.list` with `q="newer_than:1d"` and re-anchor `history_id` from latest message | `history_id` |
| **GDrive** | `changes.list` with `pageToken = cursor.page_token`. Refresh `pageToken` from `changes.getStartPageToken` if expired | `page_token` |
| **GitHub** | `users/{user}/events` (public events) + per-installation `repos/{repo}/events` for connected repos, filtered by `id > cursor.last_event_id` | `last_event_id` |
| **Linear** | GraphQL `viewer.assignedIssues(filter: {updatedAt: {gt: cursor.updated_at}})` + `viewer.subscribedIssues` | `updated_at` of newest seen issue |

### 6.5 Notion-specific fix (defect #2)

`connectors/notion/src/client.py` gains a `list_recent` method:

```python
async def list_recent(
    self,
    *,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    pages: list[dict] = []
    cursor: str | None = None
    async with httpx.AsyncClient(timeout=15.0) as client:
        while len(pages) < limit:
            resp = await client.post(
                f"{NOTION_API_BASE}/search",
                headers=self._headers,
                json={
                    "query": "",
                    "page_size": min(100, limit - len(pages)),
                    "sort": {
                        "direction": "descending",
                        "timestamp": "last_edited_time",
                    },
                    **({"start_cursor": cursor} if cursor else {}),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            for hit in data["results"]:
                edited = parse(hit["last_edited_time"])
                if since and edited < since:
                    return pages
                pages.append(hit)
            cursor = data.get("next_cursor")
            if not data.get("has_more") or not cursor:
                break
    return pages
```

The existing `search(query, limit)` method stays as-is — it still serves `connector.notion.search` for keyword queries. `list_recent` serves the poll path and the on-query freshen path.

### 6.6 Adaptive cadence

The cron scheduler computes per-source state once per minute and dispatches accordingly:

| State | Poll interval | How "state" is determined |
|---|---|---|
| **Active** | 60s | Any user query in last 1h, OR any `activity_events` row in last 24h |
| **Idle** | 5 min | Neither of the above |
| **Erroring** | exponential backoff: 2 → 4 → 8 → 16 → 30 min (capped) | `consecutive_fails ≥ 3`. Resets on first success. |

Vendor API hits are proportional to actual user attention. A workspace not opened for a week does not burn Notion API quota every minute.

### 6.7 Error model

| Category | Triggers | UI behavior | Capability response surface |
|---|---|---|---|
| `auth_failed` | 401, 403, refresh-token rejected | Red chip + "Reconnect <source>" CTA | "<Source> sync failed — your connection needs to be reauthorized" |
| `vendor_error` | 5xx, 429, vendor-specific error envelopes | Amber chip + "Retrying…" | "<Source> is having issues right now (last successful sync HH:MM) — answer may be incomplete" |
| `network_error` | TCP reset, DNS failure, connect timeout, read timeout | Amber chip + "Retrying…" | Same as `vendor_error` |

Errors do not crash the worker — they update `connector_sync_state.last_status` and surface through the freshness chip and capability responses. They are also logged with `logger.error` (not `warning`) so they appear in standard error dashboards.

## 7. Capability wiring (agent-orchestration side)

### 7.1 The `FreshenBeforeRead` mixin

`services/agent-orchestration/app/capabilities/_freshen_mixin.py`:

```python
class FreshenBeforeRead:
    source: str
    stale_after: timedelta = timedelta(seconds=60)

    async def ensure_fresh(self, user_id: UUID) -> Freshness:
        state = await sync_state_repo.get(user_id, self.source)
        if (state
            and state.last_status == "ok"
            and state.last_synced_at
            and (utcnow() - state.last_synced_at) < self.stale_after):
            return Freshness.from_state(state)

        try:
            await connector_manager.post(
                f"/tools/{self.source}/freshen",
                json={"user_id": str(user_id), "force": False},
                timeout=8.0,
            )
        except httpx.TimeoutException:
            pass  # surface stale freshness rather than block the user

        return Freshness.from_state(
            await sync_state_repo.get(user_id, self.source)
        )
```

Properties:
- **Bounded timeout (8s).** Slow vendors return cached data + stale freshness, not a hung request.
- **Idempotent freshen.** The unique constraint in §6.2 ensures concurrent freshens do not duplicate rows. Concurrent readers either see old `last_synced_at` (and trigger another freshen — vendor call is cheap) or see the new state (consistent).
- **`force=False` on the agent path.** The mixin already decided the data is stale, but a concurrent request may have freshened in the meantime. Letting the endpoint re-check `last_synced_at < 60s` server-side avoids redundant vendor calls. The manual UI refresh button (§8.1) sends `force=true` because the user explicitly asked for a fresh call.

### 7.2 Every `recent_activity` capability uses the mixin

```python
class NotionRecentActivity(FreshenBeforeRead, Capability):
    source = "notion"
    name = "connector.notion.recent_activity"
    scope = "read"
    permission = "auto"

    async def __call__(self, *, user_id, inputs, ...):
        freshness = await self.ensure_fresh(user_id)
        rows = await activity_repo.recent(
            user_id, "notion",
            since=resolve_since(inputs["since"], user_id),  # see §7.3
            limit=inputs.get("limit", 50),
            keyword=inputs.get("keyword"),
        )
        return CapabilityResult(
            summary=f"{len(rows)} Notion events since {inputs['since']}",
            data={"events": rows, "freshness": freshness.dict()},
            citations=[Citation(...) for r in rows],
        )
```

The other five connectors are byte-for-byte equivalent except for `source` and the implementation of `freshen` in `connector-manager`.

### 7.3 Timezone fix (defect #5)

`services/agent-orchestration/app/plugins/internal/activity.py` — replace the SQL interval with an absolute timestamp computed in the user's timezone:

```python
async def __call__(self, *, user_id, inputs, ...):
    user_tz = ZoneInfo(await user_repo.get_timezone(user_id))  # default 'UTC'
    start_ts = resolve_since(inputs.get("since", "today"), user_tz)
    rows = await conn.fetch("""
        SELECT id, source, event_type, title, snippet, actor, occurred_at, raw_ref
        FROM activity_events
        WHERE user_id = $1::uuid AND occurred_at >= $2
          ...
    """, user_id, start_ts)
```

`resolve_since` table:

| `since` input | Computed against |
|---|---|
| `"today"` | Midnight today in user's TZ → converted to UTC |
| `"yesterday"` | Midnight yesterday → midnight today, user's TZ → UTC |
| `"1h"`, `"24h"`, `"7d"` | Now minus delta (TZ-independent) |
| ISO-8601 timestamp | Parsed as-is |

A new `users.timezone TEXT NOT NULL DEFAULT 'UTC'` column stores the value. Migration: `0NN_users_timezone.sql`. The frontend already collects the user's timezone in the settings page; that field is wired to write this column.

### 7.4 `activity.query` becomes a thin orchestrator

When the user asks "what happened today" without naming a source, `activity.query` dispatches to all enabled per-source `recent_activity` capabilities in parallel via `asyncio.gather`, merges results by `occurred_at`, and includes a per-source freshness footer.

When the user names a source ("what happened in Slack today"), the LLM picks `connector.slack.recent_activity` directly. Single targeted call, no fanout.

## 8. Frontend

### 8.1 New components

**`packages/design-system/src/connector-freshness-chip.tsx`**

```tsx
<ConnectorFreshnessChip source="notion" />
```

Reads `GET /api/connectors/sync-state` (React Query, polled every 10s). Renders one of:
- **Green** — `synced 14s ago`
- **Amber** — `synced 3m ago` (when `last_synced_at > 2 min` OR `last_status` is `vendor_error`/`network_error`)
- **Red** — `Reconnect Notion` (when `last_status` is `auth_failed`)

**`packages/design-system/src/refresh-button.tsx`**

```tsx
<RefreshButton source="notion" />
```

Click → `POST /api/tools/notion/freshen` with `force=true` (always — the user explicitly asked for fresh data, so the endpoint must not skip even if `last_synced_at < 60s`). Optimistic spinner, re-renders the chip on success. Errors surface as a toast with the specific reason from `last_error`.

### 8.2 Three placements

| Where | What's shown | Why |
|---|---|---|
| **Connections page** (`apps/web/app/(app)/connections/page.tsx`) — per connector card | Chip + manual refresh button | Primary management surface — all six sources visible, any can be force-refreshed |
| **Chat answer** — when the agent reports activity from source X | Inline chip below the answer block, e.g. `Notion · synced 3s ago` | Builds trust — user sees freshness without asking |
| **Sidebar status dot** — next to "Connections" nav item | Green if all sources `ok`, amber if any stale, red if any `auth_failed` | At-a-glance health from any page |

### 8.3 New API surface (api-gateway, both routes are thin proxies to connector-manager)

```
GET  /api/connectors/sync-state                 → list[{source, last_synced_at, status, error?}]
POST /api/tools/<source>/freshen                → {status, last_synced_at, rows_added}
```

Both auth-gated via the existing JWT middleware. No new auth surface.

### 8.4 Render-layer enforcement of honest empty states

When a `recent_activity` capability returns `freshness.status: "auth_failed"`, the chat renderer shows an inline alert (*"Notion isn't responding — your connection needs to be refreshed"*) with a one-click reconnect button — independent of whatever the LLM wrote into its answer. The agent never gets to silently say "no activity found" when sync failed; the rendering layer prevents it.

### 8.5 Connected-sources pill bar

The chat input already has a pill bar showing which connectors will be queried for the next message. After Phase 1, those pills reflect freshness — a `auth_failed` Notion pill is red, and clicking it offers reconnect *before* the user sends a query. The broken state is caught at the front of the funnel, not the back.

## 9. Testing

| Layer | What is covered | Where |
|---|---|---|
| Unit — `SyncWorker` per connector | Pagination, sort order, `since`-cutoff stops paginating, idempotent re-ingest, error categorization (401→`auth_failed`, 5xx→`vendor_error`, timeout→`network_error`) | `services/connector-manager/tests/sync/test_<source>.py` (one file per connector, vendor API mocked with `respx`) |
| Unit — `FreshenBeforeRead` mixin | Cache-hit path skips call, stale path triggers freshen, freshen timeout returns stale freshness without raising | `services/agent-orchestration/tests/capabilities/test_freshen_mixin.py` |
| Integration — sync_state lifecycle | `ok` → `vendor_error` → backoff → `auth_failed` → reconnect → `ok`. Real Postgres, vendor API mocked. | `services/connector-manager/tests/test_sync_lifecycle.py` |
| **Regression test for the original bug** | Insert a row into Notion-mock with `last_edited_time = now`, run `connector.notion.recent_activity` with `since="today"`, assert the row is returned. Done with both server TZ=UTC and TZ=Asia/Kolkata. | `services/agent-orchestration/tests/capabilities/test_notion_recent_activity.py` |
| Frontend | Chip renders correct color/text for each `last_status`; refresh button POSTs to right endpoint; `auth_failed` shows reconnect CTA | `apps/web/__tests__/connector-freshness-chip.test.tsx` |
| E2E (smoke) | Connect mock-Notion, edit a page, ask "what happened in Notion today", assert the edit appears in the answer | `apps/web/tests/e2e/notion-recent-activity.spec.ts` |

## 10. Rollout

No feature flag. CLAUDE.md forbids them for hypothetical work, and this is the only correct behavior — a flag would only let us run with the bug.

1. **DB migrations** land first as a separate PR — `connector_sync_state`, `activity_events.external_id`, `users.timezone`. Reversible; verifiable in isolation.
2. **Per-connector worker PRs** — one PR per connector. Each brings: `SyncWorker` class, `recent_activity` capability, `freshen` capability, route in connector-manager, tests.
   - **Order:** Notion first (the bug we are fixing; validates the pattern end-to-end). Then Slack, Gmail, GDrive, GitHub, Linear in parallel.
3. **Frontend PR** — chip + refresh button + sidebar dot + chat-answer freshness footer. Lands after at least Notion + one other source are in.
4. **Cleanup PR** — remove `services/connector-manager/app/sync/notion_poll.py` (replaced by the new SyncWorker shape) and drop the `notion_poll_enabled` config flag.

### 10.1 Per-source operational kill switch

A `connector_sync_enabled[source]` setting (per-source map in `services/connector-manager/app/config.py`) lets ops disable sync for a single source if a vendor misbehaves in production. This is not a feature flag; it is an operational kill switch for known failure modes (vendor outage, runaway cost).

### 10.2 Definition of done

- The regression test for the original bug (edit Notion → ask → see the edit) passes.
- All six connectors expose `recent_activity` and `freshen` capabilities.
- The freshness chip renders correctly in all three placements.
- The agent never says "no activity found" when sync failed (enforced by the render-layer alert in §8.4).
- `make lint` and `make test` pass across all touched services.

## 11. Phase 2 — explicitly out of scope (captured for the next spec)

The following are not in Phase 1. They are listed here so they are not lost.

- **Webhook ingestion infrastructure** — public webhook endpoint in `api-gateway`, per-vendor signature verification, `events_seen` dedup table, replay buffer, dev tunneling story (Cloudflare Tunnel / ngrok).
- **Subscription lifecycle management** — Slack Events app reinstall flow, GitHub repo/org webhook setup, Drive/Gmail watch channel renewal cron (channels expire every 7 days), Linear webhooks.
- **Notion webhook scope verification** — Notion's webhook API is in beta with limited event coverage. Phase 2 needs to confirm what is actually available before deciding whether to add Notion to the webhook path or leave it polling-only forever.
- **Proactive surfaces** — push notifications fired without a user query, the activity firehose dashboard, the proactive cards on the home screen. These consume the webhook stream and naturally co-design with the use-case-driven feature work in the next session.

## 12. Open questions

None blocking Phase 1. Items above in §11 are deferred deliberately, not unanswered.
