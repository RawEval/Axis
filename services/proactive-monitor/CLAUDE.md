# CLAUDE.md — services/proactive-monitor

Celery worker (no HTTP). Background signal processing and relevance scoring. Spec §6.3 — this is the differentiator.

## Responsibilities

- Scan each user's connected tools on a cadence (and on webhook events)
- Detect signals: unanswered messages, stale docs, contradictions, unrecorded decisions, approaching deadlines, follow-up candidates
- Score candidates using the relevance engine (recency × relationship × topic overlap)
- Drop anything below the user's threshold
- Persist high-scoring surfaces to `proactive_surfaces` table
- Trigger notification-service to deliver them (respecting user's rate cap)
- Run the morning brief digest job
- Compress episodic memories older than 90 days (nightly)
- Feed accept/dismiss signals back into the per-user relevance weights

## Signal detectors

| Signal | Logic |
|---|---|
| `unanswered_message` | Slack DM/mention > 24h with no user reply |
| `stale_doc` | Notion/Drive doc referenced in recent conversations but not updated in 14+ days |
| `contradiction` | Two docs/messages making conflicting statements on same entity (semantic diff) |
| `unrecorded_decision` | Decision language detected in a conversation with no PR/ticket/doc reference |
| `approaching_deadline` | Calendar event or Linear due date within 48h with no activity |
| `followup_candidate` | Commitment language ("I'll get back to you") with no subsequent action |

## Relevance scoring

```
score = (recency_weight × recency_score)
      + (relationship_weight × relationship_score)
      + (topic_weight × topic_overlap)
```

Weights personalize per user from accept/dismiss history. Cold-start defaults in `app/relevance/defaults.py`.

## Layout

```
app/
├── worker.py              Celery entrypoint + task routing
├── config.py
├── signals/
│   ├── unanswered.py
│   ├── stale_doc.py
│   ├── contradiction.py
│   ├── decision.py
│   ├── deadline.py
│   └── followup.py
├── relevance/
│   ├── engine.py          compute score
│   ├── weights.py         per-user weight updates
│   └── defaults.py
├── brief/
│   └── morning.py         daily digest job
└── clients/
    ├── memory.py
    ├── connector_manager.py
    └── notification.py
```

## Tasks

- `axis.proactive.scan_user(user_id)` — per-user full scan
- `axis.proactive.on_slack_event(user_id, event)` — webhook-triggered
- `axis.proactive.morning_brief(user_id)` — digest
- `axis.proactive.compress_episodic(user_id)` — nightly memory compression

## Dev

```bash
cd services/proactive-monitor
uv run celery -A app.worker worker -l info -Q proactive
uv run celery -A app.worker beat -l info       # scheduler in another terminal
```

## Don't

- Don't fire notifications above the user's daily cap (default 5).
- Don't surface the same candidate twice within a rolling 72h window.
- Don't increase default cap without evidence — ChatGPT Pulse got paused for this. Spec §15.
- Don't score before the relevance engine has 10+ accept/dismiss signals from the user. Cold-start with conservative defaults.
