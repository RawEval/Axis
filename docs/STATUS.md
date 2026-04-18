# Axis — Status report

**Last updated:** 2026-04-16 · ALL 10 SESSIONS COMPLETE — Phase 1 shipped
**Purpose:** single-page accounting of what is done, what is pending, what is deferred. Update this whenever anything changes.

---

## TL;DR

- Infrastructure, data model, auth, orgs+RBAC, projects, BYO credentials (multi-scope), the **real agent reasoning loop with tool-use** (ADR 005 supervisor), the web workbench UI, and the mobile skeletons are all **shipped and verified**.
- **All 5 Phase-1 connectors are wired end-to-end:** Notion, Slack, Gmail, Google Drive, GitHub each have OAuth start + callback routes, an HTTP client, a `/tools/<tool>/search` endpoint in connector-manager, and a `connector.<tool>.search` capability in agent-orchestration. Real consent URLs verified against the live service for every provider.
- **Activity firehose is populated by real ingestion:** Slack Events API webhook (signed) writes mentions and messages into `activity_events`; a background Notion poll runs every 15 min on the connector-manager lifespan; a Phase-1 relevance engine + `unanswered_message` signal detector writes `proactive_surfaces` from stale Slack mentions; `GET /activity` exposes the feed to the web, and the `/feed` page renders both suggestions and recent events.
- **Gmail Pub/Sub push is deferred** — it needs Google Cloud Pub/Sub infrastructure that isn't local-dev friendly. Gmail activity will land when a production GCP project is set up; the agent can already read Gmail via the `connector.gmail.search` capability today.
- The supervisor loop produces real `agent_tasks` + `agent_task_steps` + `agent_citations` + `agent_messages` rows per run. Stub-mode (no `ANTHROPIC_API_KEY`) walks the `activity.query` capability deterministically so the whole pipeline keeps working without provider credentials.
- **The eval moat is live:** real Haiku-as-judge with 3 rubric templates (action / summarisation / proactive_surface) scoring every agent run into `eval_results`; a `/corrections` endpoint captures user feedback; the short-loop synthesizes a per-user system-prompt delta from recent corrections and caches it in `user_prompt_deltas`; the agent-orchestration supervisor fetches the delta on the critical path and prepends it to its system prompt. Correction feedback now changes agent behavior on the next run. Verified live with `claude-haiku-4-5` returning real reasons like "The response directly answers the user's question about workspace activity today by citing a specific Notion edit with timestamp, editor name, and content details." → composite 5.00.
- **Three-tier memory is live:** Qdrant per-user episodic collections, Neo4j entity graph, Postgres procedural tier, hybrid retrieval with recency decay, auto-write of every /run turn as episodic memory, `memory.retrieve` capability wired into the supervisor loop. **Verified end-to-end:** a follow-up prompt "what did you tell me about samir earlier?" now triggers `memory_retrieve` → returns 3 rows (semantic Samir→Q3 roadmap edge + both prior turns) → agent synthesizes a coherent recall answer with memory citations. `/memory` page renders the real rows with tier filter, search, and delete.
- **Real Sonnet + real Haiku across the stack:** with a valid `ANTHROPIC_API_KEY` the supervisor uses `claude-sonnet-4-5` for tool-use, `claude-haiku-4-5` for eval scoring, and `claude-haiku-4-5` for short-loop delta synthesis. Stub fallback path still exists for local dev without credentials.
- **Mobile apps** are compiling skeletons — 4 tabs, design tokens, real API client. Production polish is next-session work.

---

## Shipped ✓

### Foundation
- **18 Postgres tables** via 8 migrations — users, projects, orgs, members, invites, connectors, oauth_apps (multi-scope), activity_events, agent_tasks, capabilities, permission_grants, write_actions, login_events, proactive_surfaces, memory, and more. See `infra/docker/init/postgres/001_init.sql` through `008_multi_scope_oauth_apps.sql`.
- **8 microservices** running locally: api-gateway (8000), agent-orchestration (8001), connector-manager (8002), eval-engine (8003), memory-service (8004), notification-service (8005), auth-service (8006), proactive-monitor (Celery, no HTTP). All report `db: ok` on `/readyz`.
- **packages/py-common** — shared BaseSettings, structlog config with correlation IDs, Request-ID middleware, error middleware, health router, asyncpg pool wrapper, JWT helpers with threadpool-offloaded bcrypt.
- **Correlation IDs (`X-Request-ID`) flow end-to-end** from browser → gateway → downstream services.

### Auth
- `auth-service` — register, login, `/me`, bcrypt (off the event loop), JWT with `iss` + `exp`, failed-login tracking with lockout, login event audit.
- Atomic signup: creates user + personal organization (as `owner`) + default project in one transaction.
- `api-gateway` JWT middleware with `TokenExpiredError` vs `InvalidTokenError` distinction.
- **7 auth-service unit tests + 6 api-gateway tests passing.**
- Web: login, signup, middleware redirect, Zustand-backed active-project/active-org stores, React Query hooks.

### Organizations + RBAC (ADR 010)
- Five fixed roles: `owner / admin / manager / member / viewer`. **No job titles anywhere**, enforced by rule zero in the ADR + root CLAUDE.md.
- `/orgs` CRUD — list, create, get, rename.
- `/orgs/{id}/members` — list, change role, remove.
- `/orgs/{id}/invites` — create, list pending, revoke.
- `/invites/{token}` — public preview (for signup pre-fill), `POST /invites/{token}/accept` (authed).
- Monotonic invite rule: you can only invite at-or-below your own role.
- Last-owner protection: can't demote or remove the sole owner.
- Web: `/team` page with Members rendered as a **graph**, not a table. Invite modal with role-description selector.

### Projects (ADR 002, superseded by ADR 010)
- Projects belong to organizations.
- `project_members` for per-project role overrides.
- `default_grant` column: `org` (inherit) or `explicit` (invite-only).
- `/projects` CRUD on the gateway. Web: `/projects/new`.

### Credentials — multi-scope BYO OAuth (ADR 003, extended in migration 008)
- New unified `oauth_apps` table supports three scopes: **user / org / project**.
- Resolution order: **project → org → user → Axis default**.
- Backend routes at `/oauth-apps` support `scope=user|org|project&id=<identity>` on all verbs.
- Notion flow uses the new multi-scope resolver and returns `credential_source` on `/connect`.
- AES-256-GCM encryption at rest for client secrets.
- Existing `user_oauth_apps` data is preserved (Phase 2 can migrate fully).
- Web: `/credentials` page — currently only covers **user scope** (old UI). Scope selector for org/project is pending (see Pending).

### Notion connector — the only real one
- OAuth 2.0 authorize URL builder with BYO client_id support.
- Code exchange with BYO client_secret support.
- Token revoke helper.
- `/oauth/notion/start` returns `{consent_url, using_byo_app, credential_source}`.
- `/oauth/notion/callback` **now returns a 302 redirect** to `{WEB_APP_URL}/connections?status=connected` instead of raw JSON.
- `connectors/notion/src/client.py` — search, get_page, get_page_blocks, append_blocks, create_page, plus `paragraph_block` + `heading_block` helpers.
- **End-to-end verified:** login → connect → consent URL generated → (with real creds) OAuth round-trip → token encrypted and persisted → redirect back to `/connections` with a success banner.

### Agent orchestration — supervisor + tool-use (ADR 005) · shipped Session 2
- LangGraph planner: `route_project` → `supervise` (the real agent).
- **Supervisor node** runs a Claude tool-use loop up to `MAX_ITERATIONS=5` — calls Anthropic with `tools=registry.anthropic_tools()`, dispatches each `tool_use` block to a Capability, appends `tool_result` blocks back into the message history, loops until `stop_reason='end_turn'`.
- **Capability registry** (`app/capabilities/`) with protocol + auto-discovery. Three capabilities wired:
  - `memory.retrieve` — calls memory-service.
  - `activity.query` — queries `activity_events` directly with whitelisted interval literals.
  - `connector.notion.search` — calls connector-manager `/tools/notion/search` (which owns the encrypted-token decryption; agent-orchestration never sees plaintext tokens).
- **Rich persistence per `/run`:**
  - `agent_tasks` row (ADR 005) with prompt, scope, plan blob, status, latency.
  - `agent_task_steps` row per plan entry — `tool_use` → `reader`, synthesise → `synthesise`.
  - `agent_messages` (user + assistant) + `agent_citations` + `citation_spans` via `MessagesRepository`.
  - `agent_actions` backward-compat row also written.
- **Stub mode** (no `ANTHROPIC_API_KEY`): still walks `activity.query` deterministically so citations, rich history, and eval all get real rows to work with without provider credentials.
- Real Anthropic SDK client with prompt caching on the system prompt.
- Fire-and-forget eval score (`asyncio.create_task`) on every run — never on the critical path.
- `X-Request-ID` propagation through the orchestration service.

### Web UI (workbench)
- Complete refactor to a professional light theme: slate + navy + single-blue accent, Tailwind tokens, system-font stack, no glass, no neon.
- Application shell: minimal top bar (brand + project button + user menu) + navy nav rail (5 items: Ask / Activity / History / Connections / Team) + slim status bar showing backend connectivity.
- Project switcher as a **modal**, not a dropdown — clean list, advanced "all projects" mode only shown when the user has 2+ projects.
- User menu dropdown for user-level routes (Credentials, Memory, Settings, Sign out) — clean separation from project nav.
- 11 routes: `/login`, `/signup`, `/feed`, `/chat`, `/connections`, `/history`, `/memory`, `/settings`, `/credentials`, `/projects/new`, `/team`. All compile and render.
- Data tables for Activity, Connections, History. Graph for Team members.
- Connect flow **fixed**: clicking Connect now opens the OAuth consent URL in the top window. "Coming soon" badge on Slack/Gmail/Drive/GitHub. Success/error banner after the callback redirect.
- Hydration-safe rendering of client-only data (`useMounted` hook + `suppressHydrationWarning` where needed).

### Mobile apps — compiling skeletons
- **iOS** (`apps/mobile-ios/`): 4-tab SwiftUI app (Activity / Ask / History / Tools) with Axis design tokens in `Design/Tokens.swift` and a real `AxisAPI.swift` client (JWT storage, X-Axis-Project header, typed responses).
- **Android** (`apps/mobile-android/`): 4-tab Compose app with matching tokens in `ui/Tokens.kt`, minimal `data/AxisApi.kt` client using `HttpURLConnection` + kotlinx.serialization.
- Both compile. Both are explicitly **Phase 2 skeletons** — no offline cache, no push, no biometric auth, no KMM shared types yet.
- Target spec: `docs/mobile/design.md` (350+ lines covering every screen, design principles, API contract, state strategy, offline, notifications, security, and what's explicitly NOT being built on mobile).

### Documentation (complete)
- **10 ADRs** under `docs/architecture/`:
  - 002 projects-model
  - 003 byo-credentials
  - 004 project-router
  - 005 agentic-architecture (supervisor + workers — design only)
  - 006 permissions-model (Claude-Code-style grants — design only)
  - 007 activity-feed (user-level firehose — design only)
  - 008 streaming-real-time (SSE + WebSocket — design only)
  - 009 positioning-pivot (retires "one app, connect everything")
  - 010 org-and-rbac (the org + role model)
  - Plus `audit-findings.md`, `prompt-flow.md`, `use-cases.md` (with 6 appendices), `rls-decision.md`, `overview.md`, `agent-flow.md`, `eval-loop.md`
- **Pitch**: `docs/pitch/one-pager.md` — investor/customer-ready, follows rule zero (no job titles).
- **Mobile**: `docs/mobile/design.md`.
- **CLAUDE.md files** in every key folder (root, services/, per-service, packages/, connectors/, infra/, docs/, apps/web, packages/py-common) — architectural guardrails for every session.

---

## Pending — the real work list

Items here are **designed** but not yet **implemented**. Each has an ADR or spec reference so next session can pick up without rediscovery.

### Connectors — Phase 1 complete

All five Phase-1 connectors wired end-to-end as of Session 3. Each goes through the same pattern:

- OAuth module in `services/connector-manager/app/oauth/<tool>.py` (Google is shared between Gmail + Drive)
- `/oauth/<tool>/start` + `/oauth/<tool>/callback` routes in `app/routes/oauth.py`
- HTTP client in `connectors/<tool>/src/client.py` (never sees encrypted tokens)
- `/tools/<tool>/search` endpoint in `app/routes/tools.py` (owns token decryption)
- `connector.<tool>.search` capability in `services/agent-orchestration/app/capabilities/<tool>.py`
- `ConnectorManagerClient.<tool>_search()` in agent-orchestration's client module

| Connector | OAuth | Client | /tools endpoint | Capability |
|---|---|---|---|---|
| **Notion** | ✅ | ✅ search/get/append/create | ✅ | ✅ |
| **Slack** | ✅ (v2 bot scopes) | ✅ search.messages + channels.history fallback + chat.postMessage | ✅ | ✅ |
| **Gmail** | ✅ (shared Google OAuth) | ✅ messages.list/get + send (gated) | ✅ | ✅ |
| **Google Drive** | ✅ (shared Google OAuth) | ✅ files.list with Drive query syntax | ✅ | ✅ |
| **GitHub** | ✅ (OAuth App) | ✅ search/issues + get_pr + create_issue_comment | ✅ | ✅ |
| **Linear** | designed only (P2) | — | — | — |

Real consent URLs returned by the live connector-manager for every provider. Token exchange + connector upsert + redirect-back-to-web-app path is identical across tools.

Remaining per-tool work (Session 4+): background sync (Slack Events API webhook, Notion poll, Gmail Pub/Sub push, Drive push, GitHub webhooks) to populate `activity_events`, and write-back flows for the gated writes.

### Agent reasoning — ADR 005 shipped; remaining work

**ADR 005 (`agentic-architecture.md`)** — supervisor tool-use is live. Remaining items:

- ✅ Supervisor node with Claude `tools=` + `tool_use` loop (Session 2)
- ✅ Capabilities registry with auto-discovery (Session 2)
- ✅ Actual read of connected tools — `connector.notion.search` proven end-to-end (Session 2)
- ✅ Citations tracing back to specific tool responses — `agent_citations` + `citation_spans` wired (Session 2)
- ❌ **Concurrent sub-agents** (spec §6.7 — max 5 in parallel). Today the supervisor loop is sequential. Fan-out with `asyncio.gather` is Session 3/4 work.
- ❌ Worker roles from ADR 005 (reader/writer/research/code/math/summarise). Today all steps are tagged `reader`; we still need specialized workers and a role-aware planner.
- ❌ Permission grants flow (ADR 006) — gated capabilities should pause the supervisor and push a confirmation event. Session 7.

### Proactive layer — Session 4 shipped; remaining work

**ADR 007 (`activity-feed.md`)** — the firehose + first detector are live. Remaining items below.

Shipped in Session 4:

- ✅ `ActivityEventsRepository` with dedup on `(user_id, source, raw_ref->>'key')` (`services/connector-manager/app/repositories/activity.py`)
- ✅ Slack Events API webhook with HMAC-SHA256 v0 signature verification, `url_verification` handshake, team-id → connector fan-out, and normalized event mapping (`services/connector-manager/app/routes/webhooks.py`)
- ✅ Background Notion poll — `asyncio` task wired off the connector-manager lifespan, walks every connected Notion workspace every `NOTION_POLL_INTERVAL_SEC` (default 900s), idempotent with `last_sync` short-circuit (`services/connector-manager/app/sync/notion_poll.py`)
- ✅ Cold-start relevance engine with recency + source priors + keyword weights (`services/connector-manager/app/proactive/relevance.py`)
- ✅ `unanswered_message` signal detector — Slack mentions > 24h old with no subsequent channel reply, deduped on `proposed_action->>'event_id'`, writes `proactive_surfaces` rows with confidence scores (`services/connector-manager/app/proactive/unanswered.py`)
- ✅ `GET /activity` on api-gateway with optional `source` filter (`services/api-gateway/app/routes/activity.py`)
- ✅ `/feed` web page now renders both Suggestions (proactive surfaces) and Recent events (activity firehose) in one view
- ✅ Manual trigger endpoints for local dev: `POST /sync/notion/run`, `POST /proactive/detect/unanswered`

End-to-end proven: signed Slack `app_mention` webhook → `activity_events` row → detector run → `proactive_surfaces` row → `GET /activity` returns the firehose rows with auth.

Remaining proactive work (Sessions 4.5+ and beyond):

- ❌ Gmail Pub/Sub push subscription (deferred — needs GCP Pub/Sub infrastructure, not local-dev friendly)
- ❌ Google Drive push notifications (same — paired with Gmail)
- ❌ GitHub webhook receiver (parallels the Slack webhook)
- ❌ Additional signal detectors: `stale_doc`, `contradiction`, `unrecorded_decision`, `approaching_deadline`, `followup_candidate`
- ❌ Daily morning brief job
- ❌ Notification delivery via notification-service (push/email)
- ❌ Per-user correction-driven weight updates (Session 5 — needs the correction loop first)
- ❌ Proactive layer migration to a real `proactive-monitor` runtime (currently the detector lives in connector-manager for Phase 1 pragmatism)

### Permissions — Claude-Code-style grants

**ADR 006 (`permissions-model.md`)** is schema + design only:

- ❌ Permission request/grant flow (task pauses, user approves inline)
- ❌ Grant scope (user / project / task / session)
- ❌ Grant lifetime (session / 24h / project / forever)
- ❌ Modal UX for in-flight permission requests

Without these, the agent has no way to ask the user "may I read your Gmail?" before doing it. The schema exists (`permission_grants` + `permission_events`).

### Streaming — real-time agent progress

**ADR 008 (`streaming-real-time.md`)** is design only:

- ❌ Redis pub/sub between orchestration and gateway
- ❌ WebSocket fan-out from gateway to web
- ❌ SSE alternative for mobile
- ❌ Replay from Redis Stream on reconnect
- ❌ Live task tree component wired to events

Today the web UI waits for the agent to finish before showing anything. Streaming unlocks the live task tree and permission interrupts.

### Eval engine — Session 5 shipped; remaining work

**Spec §6.6 + `eval-loop.md`:**

- ✅ **Real LLM-as-judge scoring with Haiku** — `services/eval-engine/app/judges/haiku.py` calls `claude-haiku-4-5` with a forced `submit_scores` tool call so the judge always returns parseable per-dimension scores. Prompt caching on the rubric system prompt. Deterministic stub fallback when `ANTHROPIC_API_KEY` is a placeholder.
- ✅ **Rubric prompt templates per action type** — `action` (correctness 0.5 / scope 0.25 / safety 0.25), `summarisation` (faithfulness 0.5 / coverage 0.3 / conciseness 0.2), `proactive_surface` (relevance 0.4 / timing 0.3 / actionability 0.3). Each ships a dataclass `Rubric`, a system prompt, a `build_user_prompt` function, and a `tool_schema()` for the judge's structured output.
- ✅ **Correction feedback loop** — `POST /corrections` captures user feedback into `correction_signals` (scoped to user + project + action). Four correction types: `wrong / rewrite / memory_update / scope`. Short-loop re-run fires as a `asyncio.create_task` so `/corrections` returns instantly.
- ✅ **Short-loop prompt mutation** — `services/eval-engine/app/loops/short.py` reads the last `short_loop_window_size` (default 20) corrections for a user, asks Haiku to synthesize a one-paragraph behavior delta, and caches it in `user_prompt_deltas` (migration 010). Stub fallback echoes correction notes as literal bullets so the loop still closes without a real key.
- ✅ **Agent-orchestration consumes the delta** — `app/clients/eval.py::fetch_prompt_delta` is called on the critical path of every supervisor run (2s timeout, empty-string on failure). When non-empty, the delta is appended as a second system block after the cached base prompt so the base stays cache-hot while user corrections update instantly.
- ✅ **Correction UI** — `/chat` page gets a "This was wrong" button on every last result. Button opens an inline correction form with type selector (wrong / rewrite / memory_update / scope) and optional note. Submits via `POST /eval/corrections` gateway proxy.
- ✅ **Output quality panel** — `/settings` page shows average composite score, flagged-run count, rubric mix, and a scrollable recent-runs list reading from the new `GET /eval/scores` gateway endpoint.

Deferred / future work:
- ❌ Per-user weight updates for the relevance engine — plumbed but the correction → weight delta function hasn't been implemented yet (Session 5.5+).
- ❌ Long-loop JSONL export to R2 for fine-tuning — needs R2 credentials, deferred until production deploy.
- ❌ "Output quality" composite-score trend chart — today it shows a single number; a sparkline would help track drift.

### Memory — Session 6 shipped; remaining work

**Spec §6.4:**

- ✅ **Qdrant integration for vector memory** — `services/memory-service/app/vector/client.py` with per-user `axis_episodic_{user_id}` collections, `ensure_collection`, `upsert_episodic`, `search_episodic` (via `query_points`), `delete_episodic`, `count_episodic`. Defense-in-depth filter on `user_id` payload even though the collection name already encodes it.
- ✅ **Neo4j integration for the semantic graph** — `app/graph/client.py` with `upsert_entity` (MERGE on `user_id + name + kind`), `relate` (RELATES_TO edges with incrementing weight), `search_entities` (substring, user-scoped), `traverse_neighbors` (1–2 hop pattern match, no APOC dependency), `delete_entity`, `count_entities`. Async neo4j driver.
- ✅ **Embedding client** — `app/vector/embed.py` with real Voyage (`voyage-3`, 1024-dim) when `VOYAGE_API_KEY` is set, deterministic hash-based fallback for local dev so the plumbing works without credentials. Placeholder detection catches `pa-replace-me`-style defaults.
- ✅ **Three-tier retrieval + write API** — `POST /retrieve` fans out to episodic + semantic + procedural tiers, global score-sort, global limit. `POST /episodic`, `POST /semantic/entity`, `POST /semantic/relate`, `PATCH /procedural`, `GET /stats/{user_id}`, `DELETE /episodic/{id}`, `DELETE /semantic/entity`. Procedural tier reads `users.settings` JSONB directly.
- ✅ **Auto-write on every /run** — `services/agent-orchestration/app/main.py::_remember_turn` is a fire-and-forget task that writes both the user prompt and the assistant response as episodic rows after every agent run. Memory grows automatically.
- ✅ **`memory.retrieve` capability wired** — now calls the real memory-service with `project_id` scope. Supervisor calls it when the user asks about anything they said before.
- ✅ **`/memory` inspector page** — shows stats (episodic count, semantic count, embedding provider), a keyword search box with tier filter tabs, a scrollable hits table with per-row score and a delete button on episodic rows. New React Query hooks in `apps/web/lib/queries/memory.ts`. Gateway proxy at `/memory/*` → memory-service.

Remaining:
- ❌ **Nightly episodic compression** — rows >90 days get summarized into semantic notes (Celery beat job). Schema supports it via the `memory_episodic_decay_days` setting; the job itself is Session 6.5+.
- ❌ **Named-entity extraction on every turn** — today semantic entities are only created when the agent explicitly calls `/semantic/entity`. A proper pipeline runs NER on each `agent_messages` row and auto-upserts entities + edges.
- ❌ **Voyage embeddings in production** — the key is still a placeholder; add a real key to `.env` when we cut over.

### Credentials UI for org + project scopes

Backend supports it. Web UI does not yet:

- ❌ `/credentials` page shows a scope selector (User / Org / Project)
- ❌ Permission check: only admin+ can save org creds; only manager+ can save project creds
- ❌ Each connector tile on the Connections page shows a badge indicating which scope of credentials is currently resolving

### Per-project Members page

Backend has `project_members`. Web UI has only the org-level Team page. Need:

- ❌ `/projects/{id}/team` page showing project members
- ❌ Separate invite flow for project-scoped membership
- ❌ Role override UI

### Real invite delivery

- ❌ Email delivery via `notification-service` + Resend/SMTP. Currently the modal returns a copyable link the admin pastes into Slack/iMessage manually. The DB flow + token validation + consume-on-accept all work; only the email sender is missing.

### Testing + CI

- ❌ Contract tests for `/orgs`, `/invites`, `/oauth-apps` multi-scope
- ❌ E2E playwright tests for the web flows
- ❌ CI pipeline on GitHub Actions running the smoke script
- ❌ Test coverage for the Notion OAuth callback redirect

### Production hardening

- ❌ Rate limiting (slowapi + Redis) — `.env` has the numbers, nothing enforces them
- ❌ Distributed tracing beyond correlation IDs (OpenTelemetry exporter)
- ❌ Secret management in prod (currently `.env` only; prod needs Doppler/AWS Secrets Manager)
- ❌ Sentry integration
- ❌ Real health probes on `/readyz` for Redis, Qdrant, Neo4j
- ❌ Background connection retry on DB pool drops
- ❌ Graceful shutdown + drain on SIGTERM

### Mobile — Phase 2 polish

Per `docs/mobile/design.md`:

- ❌ KMM shared types from `packages/kmm-shared`
- ❌ Offline cache (Core Data / Room)
- ❌ Biometric re-auth
- ❌ Dark mode
- ❌ Push notification registration (APNs + FCM)
- ❌ Accessibility audit (VoiceOver + TalkBack)
- ❌ iPad split view
- ❌ Voice input
- ❌ App Store + Play Store privacy labels

---

## Deferred — intentional scope cuts

These are documented-and-agreed deferrals, not oversights.

- **RLS policies** — ADR `rls-decision.md` disables RLS in favor of application-level isolation for Phase 1. Re-enabled when we move to Supabase.
- **Multi-model routing** — one note in ADR 009. Not a priority; Claude Sonnet + Haiku for Phase 1.
- **Voice / desktop / iPad widgets** — mobile design doc excludes them.
- **SSO / SCIM / domain-wide delegation** — Phase 3 enterprise.
- **Guest users** (cross-org collaborators) — Phase 2 when the first customer asks.
- **Cross-org resource sharing** — intentionally unsupported. Each org is an isolation boundary.
- **Autonomous multi-task chains** — anti-use-case. Every task is user-initiated.
- **Per-capability custom permissions** — the 5 fixed tiers are enough for Phase 1.
- **Real-time streaming to the web** — shipping the schema + design now; wiring comes after the supervisor loop is real.

---

## How to update this file

Whenever you ship, fix, or defer something:

1. Move the item from **Pending** to **Shipped** (or to **Deferred** with a reason)
2. Update the TL;DR at the top if the big picture changed
3. Note any new ADRs or runbooks created
4. Update the "Last updated" line

This is the one doc the user opens first.

---

## Quick links

- Positioning pivot — [`docs/architecture/009-positioning-pivot.md`](./architecture/009-positioning-pivot.md)
- Pitch — [`docs/pitch/one-pager.md`](./pitch/one-pager.md)
- Org + RBAC — [`docs/architecture/org-and-rbac.md`](./architecture/org-and-rbac.md)
- Use cases — [`docs/architecture/use-cases.md`](./architecture/use-cases.md)
- Mobile — [`docs/mobile/design.md`](./mobile/design.md)
- Audit findings — [`docs/architecture/audit-findings.md`](./architecture/audit-findings.md)
- Smoke test — `scripts/smoke.sh`
