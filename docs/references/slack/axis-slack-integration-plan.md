# Axis Slack Integration — Comprehensive Plan

## Vision

The Slack connector is the first "deep" integration. It doesn't just search — it acts as a full workspace agent that can:
1. **Read** — search messages, summarize channels, find unanswered questions, pull thread context
2. **Write** — post messages, reply in threads, add reactions (all gated)
3. **Learn** — every Slack interaction feeds into the memory system (episodic + semantic entities for people/channels/topics)
4. **Detect** — proactive signals from the firehose (unanswered mentions, stale threads, decision language)
5. **Evaluate** — every Slack-sourced action scored by the Haiku judge

## Multi-Agent Architecture

When a user asks "summarize #product this week and draft a reply to Alice's question":

```
Supervisor (Sonnet)
  ├── connector.slack.channel_summary  → reads #product history
  ├── memory.retrieve                  → pulls prior context about #product
  ├── connector.slack.thread_context   → gets Alice's thread
  ├── connector.slack.post             → GATED: drafts reply, shows diff
  └── synthesise                       → combines all results
```

Each tool call goes through the permission gate (Session 7) and the write confirmation flow (Session 8).

## Capabilities to Build

| Capability | Scope | Permission | Description |
|---|---|---|---|
| `connector.slack.search` | read | ask | Search messages by keyword (exists today) |
| `connector.slack.channel_summary` | read | auto | Summarize recent messages in a channel |
| `connector.slack.thread_context` | read | auto | Pull full thread replies for a given message |
| `connector.slack.user_profile` | read | auto | Look up a Slack user's real name + role |
| `connector.slack.post` | write | ask | Post a message to a channel (GATED) |
| `connector.slack.react` | write | ask | Add a reaction emoji (GATED) |

## Connector-Manager Endpoints to Add

| Endpoint | Method | Purpose |
|---|---|---|
| `/tools/slack/channels` | POST | List joined channels |
| `/tools/slack/history` | POST | Channel message history |
| `/tools/slack/thread` | POST | Thread replies |
| `/tools/slack/user` | POST | User profile lookup |
| `/tools/slack/post` | POST | Post message (GATED upstream) |
| `/tools/slack/react` | POST | Add reaction (GATED upstream) |

## Memory Integration

After every Slack capability call, fire-and-forget:
1. **Episodic**: store the query + result as a memory row
2. **Semantic**: extract entities (people mentioned, channels, topics) → Neo4j
   - `(:Person {name: "Alice"}) -[:ACTIVE_IN]-> (:Channel {name: "#product"})`
   - `(:Topic {name: "Q3 planning"}) -[:DISCUSSED_IN]-> (:Channel {name: "#product"})`

## Eval Integration

Every Slack-sourced agent action is scored by the Haiku judge via the existing fire-and-forget path. The `action` rubric applies (correctness × 0.5 + scope × 0.25 + safety × 0.25). Safety is extra important for write actions — the judge should catch any fabricated message content or unauthorized channel posting.

## Scopes Update

Current bot scopes in settings:
```
channels:history,channels:read,chat:write,groups:history,groups:read,
im:history,im:read,reactions:read,reactions:write,users:read
```

Need to add: `users:read.email,pins:read,files:read`
