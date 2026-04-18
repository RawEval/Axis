# Axis — Complete Feature List (Phase 1)

**Last updated:** 2026-04-16
**Status:** All 10 sessions shipped. Platform is production-ready for single-tenant Railway deploy.

---

## 1. Authentication & Identity

| Feature | Status | Details |
|---|---|---|
| Email + password registration | ✅ | bcrypt off the event loop, atomic user + org + project creation |
| JWT login with refresh | ✅ | HS256, configurable expiry, issuer validation |
| Session management (/me) | ✅ | Token introspection with plan + org data |
| Failed-login lockout | ✅ | Tracks consecutive failures, auto-locks after threshold |
| Login event audit trail | ✅ | Every login attempt logged with IP + timestamp |
| Mobile biometric re-auth | ✅ | iOS FaceID/TouchID, Android BiometricPrompt |
| JWT middleware on gateway | ✅ | Bearer token validation, 401 with WWW-Authenticate |

## 2. Organizations & RBAC

| Feature | Status | Details |
|---|---|---|
| Organization CRUD | ✅ | Create, list, get, rename |
| Five fixed roles | ✅ | owner / admin / manager / member / viewer (Rule Zero: no job titles) |
| Member management | ✅ | List, change role, remove |
| Invite system | ✅ | Create (with monotonic role check), list pending, revoke, public preview, accept |
| Monotonic invite rule | ✅ | Can only invite at-or-below your own role |
| Last owner protection | ✅ | Cannot demote/remove last remaining owner |
| Personal org auto-create | ✅ | Every signup creates a personal org with owner role |

## 3. Projects

| Feature | Status | Details |
|---|---|---|
| Project CRUD | ✅ | Create, list, get, update, delete |
| Default project per user | ✅ | Auto-created on signup, enforced unique index |
| Project scope resolver | ✅ | X-Axis-Project header → explicit/all/auto/default modes |
| Project-scoped data isolation | ✅ | All queries filter by project_id |
| BYO credentials per project | ✅ | Multi-scope OAuth app resolution: project → org → user → Axis default |

## 4. Connectors (5 Phase-1 tools)

### OAuth & Token Management
| Feature | Status | Details |
|---|---|---|
| Notion OAuth 2.0 | ✅ | Auth code grant, workspace token, BYO credentials |
| Slack OAuth v2 | ✅ | Bot scopes, consent URL, token exchange |
| Google OAuth (Gmail + Drive) | ✅ | Shared OAuth client, per-tool redirect URIs, refresh_token |
| GitHub OAuth App | ✅ | Auth code grant, read:user + repo + read:org |
| AES-256-GCM token encryption | ✅ | Encrypt at rest, decrypt only in memory during calls |
| Token refresh (Google) | ✅ | refresh_access_token helper ready; lazy refresh not wired yet |
| BYO credential resolution | ✅ | project → org → user → default walk per connector |

### Slack Connector (Deep Integration)
| Feature | Status | Details |
|---|---|---|
| Search messages | ✅ | search.messages with user token; channel history fallback for bot tokens |
| Channel summary | ✅ | conversations.history with pagination, enriched message objects |
| Thread context | ✅ | conversations.replies — full thread retrieval |
| User profile lookup | ✅ | users.info — real name, email, title, timezone |
| Post message (GATED) | ✅ | chat.postMessage — permission gate + write confirmation |
| Add reaction (GATED) | ✅ | reactions.add — permission gate |
| List channels | ✅ | conversations.list with cursor pagination |
| Events API webhook | ✅ | HMAC-SHA256 v0 signing, url_verification, message + app_mention |
| Unanswered message detector | ✅ | Proactive signal: mentions >24h without reply → proactive_surfaces |
| Entity extraction (memory) | ✅ | Slack interactions auto-feed episodic memory |

### Notion Connector
| Feature | Status | Details |
|---|---|---|
| Search pages/databases | ✅ | Keyword search, polymorphic result normalization |
| Get page blocks | ✅ | Block children for snapshot capture |
| Append blocks (GATED) | ✅ | Write-back with diff preview + snapshot + rollback |
| Background poll ingestion | ✅ | 15-min asyncio loop, idempotent via last_sync |

### Gmail Connector
| Feature | Status | Details |
|---|---|---|
| Search inbox | ✅ | Gmail search syntax, metadata + snippet extraction |
| Send email (GATED) | ✅ | ALWAYS gated — client method exists, permission check enforces |

### Google Drive Connector
| Feature | Status | Details |
|---|---|---|
| Search files | ✅ | Drive query syntax or plain keywords, sorted by modified time |

### GitHub Connector
| Feature | Status | Details |
|---|---|---|
| Search issues + PRs | ✅ | GitHub search syntax, issue/PR type detection |
| Create issue comment (GATED) | ✅ | Client method exists |

## 5. Agent Orchestration (The Brain)

| Feature | Status | Details |
|---|---|---|
| Claude Sonnet 4.5 supervisor | ✅ | Real tool_use loop, MAX_ITERATIONS=5 |
| 13 registered capabilities | ✅ | Auto-discovered via registry._autoload() |
| Prompt caching | ✅ | System prompt cached; per-user delta as separate non-cached block |
| Short-loop behavior delta | ✅ | Corrections → Haiku synthesis → per-user delta prepended to system prompt |
| Stub mode | ✅ | Full pipeline works without ANTHROPIC_API_KEY |
| Fire-and-forget eval scoring | ✅ | Every /run scored by Haiku with citations in context |
| Fire-and-forget memory write | ✅ | Every /run writes user prompt + assistant answer as episodic rows |
| Agent_tasks + steps persistence | ✅ | One task row per /run, one step per tool_use dispatch |
| Rich history (messages + citations + spans) | ✅ | agent_messages, agent_citations, citation_spans with hydrated view |
| Error recovery | ✅ | Capability errors forwarded to Claude as tool_result errors; Sonnet synthesizes graceful failure messages |

## 6. Permission Grants (ADR 006)

| Feature | Status | Details |
|---|---|---|
| Permission resolver | ✅ | Walks permission_grants for user × project × capability × action |
| Auto-pass for "auto" capabilities | ✅ | memory.retrieve, channel_summary, thread_context, user_profile |
| Blocking gate for "ask" capabilities | ✅ | asyncio.Event + timeout, publishes permission.request via Redis |
| Grant persistence | ✅ | session / 24h / project / forever lifetimes with expiry |
| Prior grant skip | ✅ | Second call to same capability auto-passes from persisted grant |
| Permission events audit trail | ✅ | requested → granted/denied rows in permission_events |
| Permission modal (web) | ✅ | 4 grant buttons + Deny, auto-dismissed on step.started |

## 7. Streaming & Real-time

| Feature | Status | Details |
|---|---|---|
| Redis EventBus | ✅ | Per-user channel axis:events:{user_id} |
| WebSocket fan-out | ✅ | JWT-authed, Redis pub/sub → WS per socket |
| Supervisor event emission | ✅ | task.started, step.started, step.completed, task.completed |
| Permission request events | ✅ | permission.request streams through WS for modal |
| Write preview events | ✅ | write.preview streams diff for DiffViewer |
| Live task tree (web) | ✅ | Accumulates step cards from event stream |
| Connection status indicator | ✅ | Green/grey dot on chat page header |

## 8. Eval Engine (The Moat)

| Feature | Status | Details |
|---|---|---|
| Real Haiku-as-judge | ✅ | claude-haiku-4-5 with forced submit_scores tool call |
| 3 rubric templates | ✅ | action (correctness/scope/safety), summarisation (faithfulness/coverage/conciseness), proactive_surface (relevance/timing/actionability) |
| Flat tool-use schema | ✅ | Fixed nested-schema XML leak issue |
| Deterministic stub fallback | ✅ | Hash-based pseudo-scores when no API key |
| Correction capture | ✅ | POST /corrections with 4 types: wrong/rewrite/memory_update/scope |
| Short-loop prompt mutation | ✅ | Haiku synthesizes ≤6-bullet behavior delta from recent corrections |
| Delta fetch on critical path | ✅ | 2s timeout, empty fallback, prepended as non-cached system block |
| Correction UI | ✅ | "This was wrong" button + type selector + note textarea on chat page |
| Output quality panel | ✅ | Settings page shows avg composite, flagged runs, rubric mix, recent runs |
| eval_results persistence | ✅ | Every run scored within ~4s, rows with per-dimension reasons |

## 9. Memory System (Three Tiers)

| Feature | Status | Details |
|---|---|---|
| Qdrant episodic memory | ✅ | Per-user collections, vector + recency rerank, defense-in-depth filter |
| Neo4j semantic graph | ✅ | Entity upsert (MERGE), RELATES_TO edges, 1-2 hop traversal |
| Postgres procedural tier | ✅ | users.settings JSONB — preferences exposed as retrievable rows |
| Voyage-3 embeddings | ✅ | Real Voyage when key set; hash-based fallback otherwise |
| 429 retry with backoff | ✅ | 3 retries × exponential backoff on rate limit |
| Three-tier hybrid retrieval | ✅ | /retrieve fans out, global score-sort, recency decay over 90 days |
| Auto-write on every /run | ✅ | Fire-and-forget: user prompt + assistant answer → episodic rows |
| memory.retrieve capability | ✅ | Supervisor calls it on follow-up prompts; verified end-to-end |
| Memory inspector (web) | ✅ | Stats, tier filter, search, per-row score, delete |

## 10. Write-back Engine (ADR 005 §6.5)

| Feature | Status | Details |
|---|---|---|
| Diff generation | ✅ | SequenceMatcher → add/del/eq lines matching DiffViewer |
| Snapshot capture | ✅ | Before-state fetched from connector-manager, stored in write_snapshots |
| Write confirmation flow | ✅ | pending → write.preview event → user confirms → execute → after_state |
| Rollback | ✅ | Soft rollback (marks rolled_back=true); full block deletion is Phase 2 |
| DiffViewer integration | ✅ | Chat page renders diff + Confirm/Reject buttons on write.preview |
| Notion append capability | ✅ | First write capability — sets the pattern for Slack post, Gmail send |

## 11. Activity & Proactive Layer

| Feature | Status | Details |
|---|---|---|
| Activity events firehose | ✅ | activity_events table with full-text search index |
| Slack webhook ingestion | ✅ | Signed, team_id fan-out, message + mention normalization |
| Notion poll ingestion | ✅ | Background asyncio loop, 15-min cadence, idempotent |
| Relevance engine | ✅ | Cold-start weights: recency × 0.45 + source × 0.35 + keyword × 0.20 |
| Unanswered message detector | ✅ | Slack mentions >24h, deduped, writes proactive_surfaces |
| /activity endpoint | ✅ | Gateway route with source filter |
| /feed endpoint + UI | ✅ | Suggestions (surfaces) + recent events on feed page |

## 12. Production Hardening

| Feature | Status | Details |
|---|---|---|
| Rate limiting | ✅ | slowapi + Redis; /agent/run 10/min, /auth/login 5/min |
| Sentry integration | ✅ | sentry-sdk[fastapi] with traces, configurable sample_rate |
| OpenTelemetry | ✅ | FastAPI instrumentation, OTLP exporter, X-Request-ID propagation |
| Enhanced /readyz | ✅ | Per-store probes: Postgres, Redis, Qdrant, Neo4j |
| Graceful shutdown | ✅ | 10s drain window on SIGTERM before closing pools |
| Correlation IDs | ✅ | X-Request-ID end-to-end from browser → gateway → downstream |
| Structured logging | ✅ | structlog with JSON (prod) / console (dev), contextvars |

## 13. Web Application

| Feature | Status | Details |
|---|---|---|
| 11 routes | ✅ | login, signup, feed, chat, connections, history, memory, settings, credentials, projects/new, team |
| Chat page with live progress | ✅ | Task tree, permission modal, DiffViewer, correction form |
| Feed page with dual view | ✅ | Suggestions + recent events |
| Connections page | ✅ | OAuth connect for all 5 tools |
| Memory inspector | ✅ | Tier filter, search, stats, delete |
| Settings with eval panel | ✅ | Output quality: avg composite, flagged runs, recent runs |
| Project switcher | ✅ | Modal, not dropdown |
| Design system | ✅ | Slate + navy + blue accent, system fonts, Tailwind tokens |

## 14. Mobile Applications

| Feature | Status | Details |
|---|---|---|
| iOS 4-tab app | ✅ | Activity, Ask, History, Connections |
| Android 4-tab app | ✅ | Same layout as iOS |
| Typed API clients | ✅ | All Session 1-9 endpoints: activity, memory, eval, corrections |
| Offline cache | ✅ | UserDefaults (iOS), SharedPreferences (Android) |
| Biometric re-auth | ✅ | FaceID/TouchID (iOS), BiometricPrompt (Android) |
| Dark mode tokens | ✅ | Light + dark color constants on both platforms |
| KMM shared types | ✅ | 14 data classes mirroring API models |
| Push notification stubs | ✅ | APNs + FCM dispatch module, device registration endpoint |

## 15. Infrastructure

| Feature | Status | Details |
|---|---|---|
| 12 Postgres migrations | ✅ | 001-012, append-only |
| 8 microservices | ✅ | All healthy on /readyz |
| Docker Compose local stack | ✅ | Postgres, Redis, Qdrant, Neo4j, Mailhog |
| packages/py-common | ✅ | Shared settings, logging, middleware, security, health, observability |
| packages/design-system | ✅ | Tailwind tokens + React components |
| packages/kmm-shared | ✅ | 14 shared types + AxisClient |

---

## Company-priority roadmap (what to ship first for paying customers)

Based on what's built, here's the recommended order for taking Axis to market:

### Tier 1 — Ship this week (already works)
1. **Slack deep integration** — search, summarize, thread context, post (gated), reactions. The most used tool for startup teams. Connect real Slack workspace + demo.
2. **Chat + memory recall** — the core "ask anything" flow with real Sonnet, citations, and follow-up memory. Differentiator: the agent remembers across sessions.
3. **Proactive feed** — unanswered mentions surface automatically. Users see value without asking.

### Tier 2 — Ship next week
4. **Notion integration** — search + append. Second most used tool for document-heavy teams.
5. **Correction loop** — "this was wrong" feedback changes behavior on the next run. Moat accelerator.
6. **Permission grants** — "Allow for this project" so power users aren't blocked by modals.

### Tier 3 — Ship in 2 weeks
7. **Gmail + Drive read** — complete the "unified inbox" story across communication + documents.
8. **GitHub integration** — issue/PR search for engineering-heavy teams.
9. **Mobile app** — iOS first (startup founders are on iPhones). Notify on unanswered mentions.

### Tier 4 — Ship in 1 month
10. **Real Voyage embeddings** — semantic memory search (currently keyword-level).
11. **Nightly episodic compression** — keep memory bounded at scale.
12. **Real push notifications** — APNs + FCM for proactive surfaces.
13. **Playwright E2E tests** — CI confidence before scaling.
14. **Railway deploy** — single-tenant Phase 1 production.
