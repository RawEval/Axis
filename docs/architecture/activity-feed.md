# Activity Feed — user-level "what happened today"

**Decision date:** 2026-04-16
**Status:** Design (Phase 2 implementation)
**ADR number:** 007

## Context

Your message was specific: "if they give a chat about what happened today or what has happened in the last one hour, or think of the most extensive use cases... Ideally, this would get a notification for all the work for all the apps they have connected and all the things which are done."

Translation: Axis needs an **event stream** that captures everything flowing through the user's connected tools and agent runs, at user-level (across all projects). When the user asks "what happened in the last hour," the agent reads this stream instead of re-polling every connector from scratch.

This doubles as the data source for the proactive layer (spec §6.3) — the signal detectors run over the activity stream, not over raw connector data.

## Decision

Introduce `activity_events` — a firehose table that every event in the user's workspace flows into.

## Schema

```sql
CREATE TABLE activity_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL,          -- slack | notion | gmail | gdrive | github | linear | axis
    event_type TEXT NOT NULL,      -- message | mention | edit | commit | draft | run | …
    actor TEXT,                    -- the human or bot that did it
    actor_id TEXT,                 -- provider-native id when available
    title TEXT NOT NULL,           -- one-line summary ("Aditi posted in #product")
    snippet TEXT,                  -- short body excerpt
    raw_ref JSONB,                 -- provider-native IDs to re-fetch full context
    importance_score NUMERIC(3,2), -- 0.0 to 1.0, filled by the relevance engine
    occurred_at TIMESTAMPTZ NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_user_recent ON activity_events (user_id, occurred_at DESC);
CREATE INDEX idx_activity_project_recent ON activity_events (project_id, occurred_at DESC);
CREATE INDEX idx_activity_source ON activity_events (user_id, source, occurred_at DESC);
```

**Design choices:**
- `user_id` first: the primary query is "give me everything for this user."
- `project_id` nullable: some events are user-wide (agent runs in 'all' mode).
- `raw_ref` not the full body: we don't persist the content of every message — just IDs to re-fetch via the connector when needed. This respects the spec's data retention rules (§10) and keeps the table small.
- `importance_score` populated async: the proactive monitor scores events against the user's relevance profile and surfaces high-score ones.

## Event sources

### From connectors (ingested by `proactive-monitor` via webhooks / poll)

| Source | Event types |
|---|---|
| `slack` | `message`, `mention`, `reaction`, `channel_join`, `thread_reply` |
| `notion` | `page_created`, `page_edited`, `comment_added` |
| `gmail` | `email_received`, `email_replied`, `thread_muted`, `label_added` |
| `gdrive` | `doc_created`, `doc_edited`, `doc_shared`, `comment` |
| `github` | `commit`, `pr_opened`, `pr_merged`, `issue_opened`, `review_requested` |
| `linear` | `issue_created`, `issue_moved`, `comment`, `due_date_changed` |
| `gcalendar` | `event_created`, `event_starting_soon`, `event_ended` |

### From Axis itself

| Source | Event types |
|---|---|
| `axis` | `agent_run_completed`, `permission_granted`, `permission_denied`, `connector_connected`, `connector_disconnected`, `write_action_executed`, `proactive_surface_shown` |

These give the user a complete audit trail: every action Axis took on their behalf is a row in the activity stream alongside the events from their connected tools.

## Query patterns

### "What happened today?"

```sql
SELECT source, event_type, title, snippet, occurred_at
FROM activity_events
WHERE user_id = $1
  AND occurred_at >= NOW() - INTERVAL '1 day'
ORDER BY occurred_at DESC
LIMIT 100;
```

### "What happened in the last hour across all my apps?"

```sql
SELECT *
FROM activity_events
WHERE user_id = $1
  AND occurred_at >= NOW() - INTERVAL '1 hour'
ORDER BY occurred_at DESC;
```

### "Summarize Slack activity this week"

```sql
SELECT *
FROM activity_events
WHERE user_id = $1
  AND source = 'slack'
  AND occurred_at >= NOW() - INTERVAL '7 days'
ORDER BY importance_score DESC NULLS LAST, occurred_at DESC
LIMIT 50;
```

### "What did I do yesterday?"

```sql
SELECT *
FROM activity_events
WHERE user_id = $1
  AND actor_id = $2  -- the user's own provider IDs
  AND occurred_at BETWEEN NOW() - INTERVAL '2 days' AND NOW() - INTERVAL '1 day'
ORDER BY occurred_at DESC;
```

These queries run client-side when the agent needs to answer a "what happened" prompt. The agent then synthesizes a natural-language answer from the rows.

## How agents use activity

A new capability `activity.query` plugs into the agent:

```python
@register("activity.query")
class ActivityQueryCapability:
    description = "Query the user's activity stream (Slack/Gmail/Drive/GitHub/Notion events) by time range, source, or keyword."
    schema = {
        "type": "object",
        "properties": {
            "since": {"type": "string", "description": "ISO timestamp or 'last hour'/'today'/'this week'"},
            "until": {"type": "string"},
            "source": {"type": "string", "enum": ["slack","notion","gmail","gdrive","github","linear","all"]},
            "project_id": {"type": "string"},
            "keyword": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
    }
    scopes = ["read"]
    default_permission = "auto"  # reading own activity is safe

    async def __call__(self, **ctx): ...
```

When the user prompts *"Summarize what happened in the last hour,"* the supervisor dispatches a single `activity.query` call with `since='last hour'`, gets ~50 rows, and hands them to the `summarise` agent for the answer.

This is way cheaper than re-polling every connector: the activity table is already indexed and the agent works with pre-digested summaries.

## Retention

- Default: **90 days** of activity events per user. After that, rows are compressed into weekly summaries and the originals are deleted.
- Pro plan: 1 year.
- Export: users can export their activity stream as JSONL from Settings → Export.

## Real-time updates

The activity stream doubles as the notification firehose. When a row is inserted (from a webhook, a poll, or an agent run), `proactive-monitor`:
1. Scores it via the relevance engine
2. If `importance_score > user.notification_threshold`, emits a notification event
3. `notification-service` delivers push/email per user preferences

This closes the loop: user connects tools → tool events flow into activity → high-signal events become notifications → user can ask follow-up questions that the agent answers from the same activity table.

## Privacy

- Activity events are per-user. Never aggregated across users.
- Stored in the per-user namespace when we move to Supabase with RLS.
- Never used for training without opt-in (spec §10).
- User can delete their entire activity stream with one click (cascades from `DELETE FROM users`).

## Ingestion pipeline

```
           ┌─────────────────┐
           │ tool webhook OR │
           │ scheduled poll  │
           └────────┬────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ proactive-monitor  │
          │ (Celery worker)    │
          │                    │
          │ - normalise event  │
          │ - extract summary  │
          │ - insert row       │
          └─────┬──────────────┘
                │
                ├──▶ activity_events  (the firehose)
                │
                ▼
          ┌────────────────────┐
          │ relevance engine   │
          │ - score            │
          │ - maybe surface    │
          └─────┬──────────────┘
                │
                ▼
          ┌────────────────────┐
          │ notification-      │
          │ service (if high)  │
          └────────────────────┘
```

## Not in scope

- **Raw body persistence**. We keep IDs and summaries. Full bodies are re-fetched on demand via the connectors. This keeps the table small and keeps us out of the "email hoarder" business.
- **Cross-user aggregation**. Each user's stream is isolated.
- **Real-time per-event push** to the web UI. Phase 2 ships polling-based refresh on the feed; Phase 3 ships SSE on the activity stream.

## See also

- `agentic-architecture.md` — how capabilities consume activity
- `streaming-real-time.md` — event delivery mechanics
- `projects-model.md` — project scope for events
- `axis_full_spec.docx` §6.3 — proactive intelligence layer (the original spec)
