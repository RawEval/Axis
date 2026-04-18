# Axis — TODO (session-by-session plan)

**Updated:** 2026-04-16 · after the alignment audit
**Source of truth:** this doc + [`STATUS.md`](./STATUS.md) + [`alignment-audit.md`](./alignment-audit.md)
**Rule:** when you ship an item, strike it through and add a one-line note (date + file touched). Do not delete items.

This is the file you keep open between sessions. Every item has:
- **Severity** — 🔴 critical · 🟠 high · 🟡 medium · 🟢 low
- **Effort** — rough hours
- **Touch** — files/dirs that change
- **ADR** — design reference
- **Accept** — one-line acceptance criteria

---

## Session 1 — alignment audit + foundations · ✅ SHIPPED

- **✅ Alignment audit doc** · `docs/alignment-audit.md`
- **✅ TODO.md (this file)** · `docs/TODO.md`
- **✅ Migration 009: rich history schema** · `infra/docker/init/postgres/009_rich_history.sql` — `agent_messages` + `agent_citations` + `citation_spans` + `agent_messages_hydrated` view, project-scoped
- **✅ Rich history wired in agent-orchestration** · `services/agent-orchestration/app/repositories/messages.py` + updated `main.py::run` — every `/run` persists the user message, the assistant message, and one row per citation (plus spans when the UI produces them). Verified end-to-end.
- **✅ Eval engine fire-and-forget** · `services/eval-engine/app/main.py` + `services/agent-orchestration/app/clients/eval.py` + `asyncio.create_task` in `main.py::run` — eval_results row lands within 5s of every `/run`. **Hardened in Session 5.8:** the background scorer now forwards `citations` and `plan` to the judge's context so the rubric isn't blind to the agent's sources. Composite jumped from 3.0 to 5.0 on the same turn after the fix.
- **✅ Chat page renders citations** · `apps/web/components/chat/cited-response.tsx` + updated `app/(app)/chat/page.tsx` — highlighted spans inline, sources panel below, clickable source links.

## Session 2 — supervisor + tool-use (the big leverage point) · ✅ SHIPPED 2026-04-15

The single highest-value session. Upgraded the planner from a single Sonnet call to Claude tool-use, and wired Notion reads as the first real capability.

- **✅ Capability registry** · `services/agent-orchestration/app/capabilities/` · `base.py` Capability protocol + Citation + CapabilityResult, `registry.py` auto-discovery via `_autoload`, 3 initial capabilities: `memory.retrieve`, `activity.query`, `connector.notion.search`
- **✅ Supervisor node** · `services/agent-orchestration/app/graphs/planner.py` · `supervise` node runs Claude `tools=` + `tool_use` loop to `MAX_ITERATIONS=5`, dispatches tool_use blocks to registry, appends `tool_result` back to messages; falls through to `_stub_supervise` when no `ANTHROPIC_API_KEY`
- **✅ Notion client wired into capability** · `connector.notion.search` calls `ConnectorManagerClient.notion_search()` → `/tools/notion/search` in connector-manager, which owns the token decryption. Agent orchestration never sees plaintext tokens.
- **✅ Planner persists agent_tasks + agent_task_steps** · `services/agent-orchestration/app/repositories/tasks.py` — one row per `/run`, one step per plan entry (tool_use → `reader`, synthesise → `synthesise`). `main.py` wires it in alongside the existing `agent_actions` write.
- **✅ Source citations populated from tool_use results** · each capability result's `Citation` objects are collected into `AgentState['citations']` and persisted via `MessagesRepository.record_turn` into `agent_citations`. Verified with a seeded `activity_events` row → Notion-style citation landed in `agent_citations` with proper `occurred_at` timestamptz.
- **✅ Wire `clients/memory.py` and `clients/connector_manager.py`** · both httpx wrappers shipped and used by capabilities.
- **Accept:** ✅ `/run` end-to-end proven — POST returns `task_id`, `message_id`, `citations[]` with ref_id/title/actor, and DB shows 1 task + 1 step + 2 messages + 1 citation row per run. (Stub-mode run: 1 seeded activity_event, 9ms latency.)

**Session 2 cleanup shipped along the way:**
- Fixed `activity.query` asyncpg bug: interval was bound as str (fails on asyncpg's timedelta codec); now inlined from a whitelisted `_INTERVAL_MAP`.
- Fixed `MessagesRepository.record_turn`: capabilities return `occurred_at` as ISO strings, but asyncpg needs `datetime` — added `_to_datetime` coercion helper.

## Session 3 — the other 4 connectors · ✅ SHIPPED 2026-04-16

All five Phase-1 connectors now go through the same Notion-pattern pipeline: OAuth module → start/callback routes → HTTP client → `/tools/<tool>/search` endpoint → capability in agent-orchestration.

- **✅ Slack connector** · `services/connector-manager/app/oauth/slack.py` (OAuth v2 bot scopes), `connectors/slack/src/client.py` (search.messages + channels.history fallback + chat.postMessage + auth.test), `/tools/slack/search` with automatic channel-history fallback when the bot token can't hit search.messages, capability `connector.slack.search`.
- **✅ Gmail connector** · `services/connector-manager/app/oauth/google.py` (shared with Drive — one OAuth flow, per-tool scope lists), `connectors/gmail/src/client.py` (messages.list + metadata get + send), `/tools/gmail/search`, capability `connector.gmail.search`. `gmail.send` is ALWAYS gated upstream.
- **✅ Google Drive connector** · reuses the shared Google OAuth module, `connectors/gdrive/src/client.py` (files.list with `_to_drive_query` auto-wrapping plain keywords), `/tools/gdrive/search`, capability `connector.gdrive.search`.
- **✅ GitHub connector** · `services/connector-manager/app/oauth/github.py` (OAuth App, read:user + repo + read:org scopes), `connectors/github/src/client.py` (search/issues + get_pr + create_issue_comment + authenticated_user), `/tools/github/search`, capability `connector.github.search`.
- **✅ Capability registry entries for all four** · `services/agent-orchestration/app/capabilities/` auto-discovers them. Live registry now has 7 capabilities (3 general + 4 connectors + notion × 1 = 8 actually: memory.retrieve, activity.query, connector.{notion,slack,gmail,gdrive,github}.search).
- **✅ 501 stubs removed from `oauth.py`** · `_not_implemented` helper deleted; each tool has real start + callback.
- **Accept:** ✅ All 5 Phase-1 connectors return valid consent URLs from the live connector-manager. Verified against live service for Slack, Gmail, Drive, GitHub. Agent supervisor sees all 7 capabilities in its `tools=` array. End-to-end `/run` still green.

**Session 3 cleanup shipped along the way:**
- Added `gmail_oauth_redirect_uri` + `gdrive_oauth_redirect_uri` per-tool settings so the shared Google OAuth client can route callbacks to the right connector.
- Removed the now-obsolete `google_oauth_redirect_uri` and `google_scopes` settings.
- `ConnectorManagerClient` refactored with a `_tool_search` helper + per-tool thin wrappers — adding connector #6 in the future is a 10-line change.

## Session 4 — activity ingestion + proactive surfaces · ✅ SHIPPED 2026-04-16

Unblocked the Feed page and the §6.3 pillar.

- **✅ Slack Events API webhook** · `services/connector-manager/app/routes/webhooks.py` with v0 HMAC-SHA256 signature verification, `url_verification` handshake, `ConnectorsRepository.find_by_workspace` to map `team_id` → (user_id, project_id) fanout, `_map_slack_event` normalizer for `message` + `app_mention`.
- **✅ Notion poll** · `services/connector-manager/app/sync/notion_poll.py` as a background asyncio loop off the connector-manager lifespan. Walks every connected Notion workspace every `NOTION_POLL_INTERVAL_SEC` (default 900s), short-circuits on `last_sync`, upserts pages via the shared `ActivityEventsRepository`. `POST /sync/notion/run` for manual local triggering. Deliberately not Celery — the worker count stays at one service for Phase 1.
- **❌ Gmail push subscription** · deferred to post-launch. Pub/Sub needs a real GCP project + subscription infra that isn't local-dev friendly. The agent can already read Gmail on demand via `connector.gmail.search`, so the firehose gap is bounded.
- **✅ Relevance engine** · `services/connector-manager/app/proactive/relevance.py` with cold-start weights (`recency=0.45 + source=0.35 + keyword=0.20`), per-source priors (Slack mentions top out at 0.95), linear recency decay from 1h → 72h.
- **✅ Signal detector: unanswered_message** · `services/connector-manager/app/proactive/unanswered.py` scans Slack mentions >24h old with no subsequent channel reply, writes `proactive_surfaces` rows keyed on `proposed_action->>'event_id'` for dedup. Verified end-to-end: `{seen:1, created:1}` on first run, `{seen:1, created:0, skipped:1}` on re-run (idempotent). `POST /proactive/detect/unanswered` for manual triggering.
- **❌ Morning brief job** · deferred — the relevance engine + unanswered detector already populate the feed; the daily digest is a notification-delivery feature that pairs better with the notification-service work.
- **✅ Shared writer** · `services/connector-manager/app/repositories/activity.py` — `ActivityEventsRepository.upsert` dedupes on `(user_id, source, raw_ref->>'key')` so webhook re-delivery and poll re-runs are idempotent. Both the Slack webhook and the Notion poll write through this one class.
- **✅ `/activity` endpoint + web page** · `services/api-gateway/app/routes/activity.py` exposes the firehose scoped to the active project, with optional `?source=` filter. `apps/web/app/(app)/feed/page.tsx` now renders both "Suggestions" (proactive surfaces) and "Recent events" (activity firehose) in one view with a shared React Query hook at `apps/web/lib/queries/activity.ts`.
- **Accept:** ✅ Signed Slack `app_mention` ingested into `activity_events`, unanswered detector wrote `proactive_surfaces`, `GET /activity` returned the firehose via JWT. Idempotency and signature verification both proven.

**Session 4 notes:**
- The proactive subpackage lives at `services/connector-manager/app/proactive/` rather than in `services/proactive-monitor/` per ADR 007. This is deliberate Phase-1 pragmatism — proactive-monitor is still a Celery stub with no running process, and putting two functions there would mean standing up a whole new worker. The subpackage is self-contained so the migration is a move, not a rewrite.
- Slack signing secret is currently `REPLACE` in `.env.example`. For local smoke-tests the webhook was verified with a real HMAC-SHA256 signature computed from that placeholder value.

## Session 5 — eval + correction loop (the moat) · ✅ SHIPPED 2026-04-16

The moat is live. Every agent run is scored against a real rubric, every user correction fires a short-loop refresh, and the agent's system prompt updates between runs.

- **✅ Real Haiku-as-judge in eval-engine** · `services/eval-engine/app/judges/haiku.py` calls `claude-haiku-4-5` with a forced `submit_scores` tool call so scores always parse. Prompt caching on the rubric system prompt. Deterministic stub fallback when the key is a placeholder (exercises the full pipeline in local dev without spending tokens). Rubric templates in `app/rubrics/` — `action.py` (weights 0.5/0.25/0.25), `summarisation.py` (0.5/0.3/0.2), `proactive.py` (0.4/0.3/0.3), plus `base.py` with the `Rubric` + `Dimension` dataclasses and a `tool_schema()` builder that emits the Anthropic tool-use JSON Schema per rubric.
- **✅ /corrections endpoint** · `POST /corrections` in eval-engine + `POST /eval/corrections` proxy in api-gateway + `CorrectionsRepository` in `services/eval-engine/app/repositories/corrections.py`. Four correction types: `wrong / rewrite / memory_update / scope`. Rows land in `correction_signals` (project-scoped).
- **✅ Short-loop prompt mutation** · `services/eval-engine/app/loops/short.py::refresh_prompt_delta` reads the last `short_loop_window_size` (default 20) corrections, asks Haiku for a ≤6-bullet behavior delta, and caches the result in `user_prompt_deltas` (new migration `010_prompt_deltas.sql`). Stub fallback echoes correction notes verbatim so the loop still closes without a real key. Refresh is triggered on every `/corrections` POST and on every flagged `/score` run via `asyncio.create_task`.
- **✅ Agent-orchestration pulls the delta** · `app/clients/eval.py::fetch_prompt_delta` with a 2s timeout + empty-string fallback. `app/graphs/planner.py::supervise` calls it on the critical path of every run and appends the delta as a second system block (kept out of the cache-control so new corrections invalidate instantly while the base prompt stays cache-hot).
- **✅ Correction capture UI** · `apps/web/app/(app)/chat/page.tsx` — "This was wrong" button on every last result, expanding into a type selector + note textarea. Submits via the new `useSubmitCorrection` hook in `apps/web/lib/queries/eval.ts`.
- **✅ Eval dashboard surface** · `/settings` page has a new "Output quality" panel reading from `GET /eval/scores` — shows average composite, flagged-run count, rubric mix, and a recent-runs list with per-run composite badges.
- **❌ Long-loop JSONL export** · deferred until we have R2 credentials. The raw `correction_signals` rows are the training pairs; export job is 20 lines when the bucket exists.
- **Accept:** ✅ `POST /eval/corrections` via the gateway → `correction_signals` row → short-loop refresh fires → `GET /prompt-deltas/{user_id}` returns the synthesized delta with `source_corrections` pointing at the new row → `/run` fetches the delta and prepends it to the system prompt (verified: after filing a correction "Always cite the Notion URL inline, not just the title", the delta returned on the next fetch contains the bullet).

**Session 5 notes:**
- The short loop uses `asyncio.create_task` instead of Celery because the critical path is already short and fire-and-forget is good enough for single-instance deploys. When we scale out we swap this for a Redis queue without touching the surface area.
- The Haiku judge is called with `tool_choice={"type":"tool","name":"submit_scores"}` so the model is forced into structured output. Every rubric's `tool_schema()` enumerates its dimensions as required properties — omitting one crashes the parse and we fall back to the stub score (then log loudly). This matches "don't let the judge drift silently."
- Migration `010_prompt_deltas.sql` is additive — no destructive changes.

## Session 6 — memory system · ✅ SHIPPED 2026-04-16

Three-tier memory is live end-to-end. Episodic rows land automatically, semantic entities resolve in the graph, and a follow-up prompt pulls prior turns through the `memory.retrieve` capability.

- **✅ Qdrant client + per-user namespace** · `services/memory-service/app/vector/client.py` with `ensure_collection`, `upsert_episodic`, `search_episodic` (using `query_points` for qdrant-client 1.10+), `delete_episodic`, `count_episodic`. Collection name `{prefix}_episodic_{user_id_hex}` and a mandatory `user_id` payload filter for defense-in-depth. Payload indices on `user_id` and `project_id`.
- **✅ Neo4j driver + entity graph** · `app/graph/client.py` with `upsert_entity` (MERGE on user_id + name + kind), `relate` (RELATES_TO with incrementing weight), `search_entities`, `traverse_neighbors` (plain 1-2 hop pattern, no APOC dependency so it runs on Neo4j community), `delete_entity`, `count_entities`. Async driver.
- **✅ Embedding client** · `app/vector/embed.py` — Voyage (`voyage-3`, 1024-dim) when the key is real, deterministic hash-based fallback otherwise so local dev + CI exercise the full upsert/retrieve path without spending tokens. Tightened placeholder detection catches `pa-replace-me` so `provider_label()` reflects the actual provider.
- **✅ Three-tier retrieval API** · `app/tiers/episodic.py` (vector similarity × 0.7 + recency decay × 0.3 over 90 days), `app/tiers/semantic.py` (substring match + 2-hop neighbor traversal), `app/tiers/procedural.py` (reads `users.settings` JSONB). `/retrieve` fans out, re-sorts globally by score, clips to limit. `/episodic`, `/semantic/entity`, `/semantic/relate`, `PATCH /procedural`, `GET /stats/{user_id}`, delete routes.
- **✅ Auto-write on every /run** · `agent-orchestration/app/main.py::_remember_turn` fires two episodic writes (user + assistant) as a detached asyncio task after each /run. Memory grows automatically with no explicit API calls.
- **✅ `memory.retrieve` capability wired** · now calls the real memory-service `/retrieve` with `project_id` scope. Agent sees 3-hit results on follow-up prompts; verified with a real Sonnet run that pulled episodic + semantic rows and synthesized a coherent recall answer.
- **✅ /memory inspector UI** · `apps/web/app/(app)/memory/page.tsx` — stats panel (episodic count, semantic count, embedding provider), tier filter chips, search box, results table with per-row score badges, delete button on episodic rows. New `useMemoryStats`, `useMemorySearch`, `useDeleteEpisodic` hooks. Gateway proxy at `/memory/*` → memory-service.
- **❌ Nightly episodic compression** · deferred — rows >90 days summarized into semantic notes (Celery beat). Schema supports it via `memory_episodic_decay_days`; job itself is follow-on work.
- **Accept:** ✅ run "did samir edit any notion docs today about Q3 planning" → 1 episodic row stored via fire-and-forget. Follow-up "what did you tell me about samir earlier?" → supervisor called `memory_retrieve` → returned 3 rows (1 semantic + 2 episodic) → agent synthesized the recall answer with 3 memory citations. Memory inspector shows all rows via gateway proxy.

**Session 6 notes:**
- Found a qdrant-client API change mid-session: 1.10+ deprecates `AsyncQdrantClient.search()` in favour of `query_points()`. Fixed in `app/vector/client.py`.
- Found a Neo4j kwarg collision: `session.run()`'s first positional is `query`, so passing `query=...` as a Cypher parameter errors. Renamed the param to `needle` in `search_entities`.
- Dropped the `apoc.path.subgraphNodes` branch in `traverse_neighbors` because Neo4j community doesn't ship APOC — replaced with a portable variable-length pattern match.
- Verified against the live Anthropic API (real `claude-sonnet-4-5` + `claude-haiku-4-5`), not stub mode. One real /run costs ~1100 tokens for a tool-use loop that hits memory, synthesizes, and scores itself.

## Session 1 verification sweep (post-Session-6)

After the Anthropic key update, re-verified Sessions 1-5 end-to-end:
- ✅ Session 2 supervisor: real Sonnet tool-use loop calling `activity_query`, output "Today you had one activity event: Samir edited the Q3 Planning roadmap..." — 1116 tokens, 4049ms.
- ✅ Session 5.2 Haiku judge: flat `{dim}_score` / `{dim}_reason` schema (nested schema confused the model into leaking XML parameter syntax); real composite 5.00 with substantive per-dimension reasons once citations were forwarded to the judge context.
- ✅ Session 5.4 short-loop delta: real Haiku synthesized "- Keep responses under 3 sentences\n- Always cite the Notion URL inline when referencing documents, not just the title" from 2 corrections in 1094 tokens.
- ✅ Session 1 fire-and-forget eval: hardened to forward `citations` and `plan` to the judge's context — fixed a scoring bug where the judge penalized every response as "unverifiable" because it couldn't see the real sources. Composite jumped 3.0 → 5.0 on identical output.

## Session 7 — streaming + permission grants · ✅ SHIPPED 2026-04-16

Real-time agent events + permission-gated tool_use, proven end-to-end through the gateway with JWT auth.

- **✅ Redis EventBus** · `services/agent-orchestration/app/events.py` — async Redis pub/sub, `publish()` with channel `axis:events:{user_id}`, event schema with `type/user_id/project_id/action_id/payload/ts`. Fire-and-forget, never blocks the supervisor.
- **✅ Supervisor instrumented** · `planner.py::supervise` publishes `task.started → step.started → step.completed → task.completed` at each lifecycle point with the action_id, step count, tool name, summary, and output preview.
- **✅ Permission resolver + blocking gate** · `services/agent-orchestration/app/permissions.py` — `check_and_gate()` walks `permission_grants` (project → user scope), auto-passes `auto` capabilities, blocks `ask`/`always_gate` via `asyncio.Event` keyed on a `pending_id`, publishes `permission.request` event, awaits user decision with `PERMISSION_TIMEOUT_SEC=120`. On grant: persists `permission_grants` row with lifetime + expiry. On deny/timeout: returns `GateDecision(granted=False)` and the supervisor sends a tool_result error to Claude. `POST /permissions/resolve` endpoint unblocks the pending event.
- **✅ WebSocket fan-out** · `services/api-gateway/app/routes/ws.py` — replaced the echo stub. JWT-authed WS subscribes to `axis:events:{user_id}` via a dedicated `redis.asyncio` connection per socket. Dual-pump pattern (`_pump_redis_to_ws` + `_pump_ws_client`) with clean disconnect/unsubscribe.
- **✅ Live task tree component** · `apps/web/components/chat/live-task-tree.tsx` — `accumulateSteps` collapses the event stream into per-step cards with status badges (running/done/error/denied/awaiting_permission). Renders between the prompt panel and the result panel on the chat page. Automatically cleared 1.5s after `task.completed`.
- **✅ Permission modal** · `apps/web/components/chat/permission-modal.tsx` — intercepts the latest `permission.request` from `useLiveEvents()`, renders capability name + description + inputs + 4 grant buttons (once / project / 24h / forever) + Deny. Calls `POST /permissions/resolve` via the gateway. Dismissed automatically when a subsequent `step.started` for the same capability appears.
- **✅ Gateway proxy** · `POST /permissions/resolve` in `services/api-gateway/app/routes/permissions.py` forwards to agent-orchestration.
- **✅ Prior grants skip the gate** · verified: second run of the same Notion search auto-passed with no `permission.request` event because the `lifetime=project` grant from the first run was found by `_find_prior_grant()`.
- **Accept:** ✅ Verified end-to-end through the gateway:
  1. JWT-authed WS connects, receives `hello`
  2. `/agent/run` fires, supervisor publishes `task.started`
  3. Tool-use block hits the gate → `permission.request` streams through WS
  4. Test script POSTs `/permissions/resolve` (via gateway, JWT-authed) with `lifetime=project`
  5. Gate unblocks, supervisor publishes `step.started → step.completed → task.completed`
  6. `permission_grants` row persists with `project_id` scope
  7. Next run of the same capability auto-passes with no gate event

**Session 7 notes:**
- The pending-events map (`_PENDING`, `_DECISIONS`) is in-process only. If multiple agent-orchestration replicas run behind a load balancer, pending events must move to Redis hashes. Single-instance deploys (Railway Phase 1) work today.
- `redis>=5.0.8` added to `pyproject.toml` for both agent-orchestration and api-gateway.
- The `ws.ts` lib was updated to append `?token=` from `getToken()` so the browser WS handshake passes JWT automatically.

## Session 8 — write-back engine · ✅ SHIPPED 2026-04-16

- **✅ write_snapshots migration** · `011_write_snapshots.sql` with `before_state`/`after_state` JSONB, 30-day expiry.
- **✅ WritesRepository** · `create_pending`, `confirm`, `set_after_state`, `rollback`, `get`, `list_for_project`. All idempotent.
- **✅ Diff generator** · `app/writeback/diff.py` — `compute_diff` (SequenceMatcher → add/del/eq lines), `blocks_to_text` (Notion blocks → text), `capture_notion_snapshot` (fetches before-state via connector-manager).
- **✅ Notion write endpoints** · `/tools/notion/blocks` + `/tools/notion/append` in connector-manager. Both use decrypt-token pattern.
- **✅ connector.notion.append capability** · scope=write, default_permission=ask. Captures snapshot → diff → pending row → `write.preview` event. Does NOT execute — returns "pending confirmation" to Claude.
- **✅ /writes/{id}/confirm + rollback** · agent-orchestration endpoints. Confirm executes via connector-manager + stores after_state. Rollback is soft (marks row, full block deletion is Phase 2).
- **✅ Gateway proxy** · `/writes/{id}/confirm` + `/writes/{id}/rollback`.
- **✅ DiffViewer wiring** · chat page intercepts `write.preview` events, renders the existing DiffViewer with Confirm/Reject buttons.
- **❌ Conflict detection** · deferred to Phase 2.
- **Accept:** ✅ diff verified (3 eq + 1 add), 8 capabilities registered, all routes compile. Full write execution requires a connected Notion workspace.

## Session 9 — production hardening · ✅ SHIPPED 2026-04-16

- **✅ Rate limiting** · `slowapi` + Redis-backed token bucket on api-gateway. `/agent/run` 10/min, `/auth/login` 5/min, `/eval/corrections` 20/min, default 60/min. Key function extracts user_id from JWT (falls back to IP for unauthed routes). `RATE_LIMIT_*` settings in `app/config.py`. Verified: 429 returned on attempt 6 of `/auth/login`.
- **✅ Sentry integration** · `sentry-sdk[fastapi]` added to `packages/py-common`. `init_observability()` in `axis_common.observability` calls `sentry_sdk.init()` with FastAPI + Starlette integrations, configurable `traces_sample_rate`, `release` tag from service name. Wired into api-gateway. Degrades gracefully when `SENTRY_DSN` is empty — logs "sentry_skipped_no_dsn".
- **✅ OpenTelemetry trace exporter** · `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp-proto-grpc` added to py-common. `init_observability()` configures a `TracerProvider` with `service.name` resource, instruments FastAPI, optionally ships spans via OTLP to `OTEL_EXPORTER_OTLP_ENDPOINT`. Console-only when no endpoint is set.
- **✅ Enhanced `/readyz`** · `make_health_router` now accepts optional `redis_url`, `qdrant_url`, `neo4j_driver` and probes each on `/readyz`. Verified: api-gateway returns `{db:"ok", redis:"ok"}`, memory-service returns `{db:"ok", qdrant:"ok", neo4j:"ok"}`.
- **✅ Graceful shutdown** · api-gateway lifespan `finally` block now waits `GRACEFUL_SHUTDOWN_TIMEOUT_SEC` (10s) before closing pools, letting in-flight requests drain. Uvicorn stops accepting new connections on SIGTERM; the window lets active work finish.
- **❌ E2E Playwright tests** · deferred — requires the web app dev server + a fresh DB seed + real credentials. One CI-level test is follow-on work.
- **Accept:** ✅ rate limit 429 verified, `/readyz` returns per-store status for all 4 stores, Sentry + OTel init logged cleanly. Playwright deferred.

## Session 10 — mobile Phase 2 · ✅ SHIPPED 2026-04-16

- **✅ KMM shared types** · `packages/kmm-shared/src/commonMain/kotlin/com/raweval/axis/models/Models.kt` — 14 data classes matching the Pydantic models: LoginResponse, Me, Project, Surface, ActivityEvent, Citation, PlanStep, RunResponse, ConnectorTile, MemoryRow, MemoryStats, EvalScore, EvalResult, LiveEvent. `AxisClient.kt` expanded with all Session 1-9 endpoints (activity, memory, eval, corrections) + token/project header injection.
- **✅ iOS offline cache** · `AxisAPI.swift` — UserDefaults-backed `cache(key:data:)` + `cached(key:as:)` generic helpers. Phase 2 migration path for Core Data. New API methods: `activity()`, `memorySearch()`, `memoryStats()`, `submitCorrection()`. Response models: `ActivityEvent`, `MemoryRow`, `MemoryStats`.
- **✅ Android offline cache** · `AxisApi.kt` — SharedPreferences-backed `cacheJson(key:)` + `cachedJson(key:)`. Phase 2 migration path for Room. New API methods matching iOS: `activity()`, `memorySearch()`, `memoryStats()`, `submitCorrection()`. Response models: `ActivityEvent`, `MemoryRow`, `MemoryStats`.
- **✅ Push notifications** · `services/notification-service/src/push/dispatch.ts` — APNs + FCM dispatch module (log-only stubs until `APNS_KEY_PATH`/`FCM_CREDENTIALS_PATH` are set). `POST /push` reads `user_devices` from Postgres and fans out. `POST /devices/register` upserts a device token (platform + token). `POST /devices/revoke` removes one. Migration 012 for `user_devices` table (already existed from migration 001; schema compatible).
- **✅ Biometric re-auth** · iOS: `BiometricAuth.swift` wrapping `LAContext` (FaceID/TouchID). Android: `BiometricGate.kt` wrapping AndroidX `BiometricPrompt`. Both fall through silently when biometrics unavailable so simulator/emulator dev isn't blocked.
- **✅ Dark mode** · iOS: `Tokens.swift` extended with dark-mode color constants (`canvasDark`, `raisedDark`, `inkDark`, `edgeDark`) + `adaptive(light:dark:)` helper using `UIColor { traitCollection }`. Android: `Tokens.kt` extended with `CanvasDark`, `RaisedDark`, `InkDark`, `EdgeDark`, `SubtleDark`, `InkSecondaryDark`.
- **✅ Accessibility audit** · `docs/mobile/accessibility-audit.md` — per-platform checklist of what works (tab labels, standard controls) and what needs Phase 2 work (custom semantics, Dynamic Type, color contrast on InkTertiary, touch target sizes, screen-curtain testing).
- **Accept:** ✅ KMM has 14 shared types + expanded client. Both mobile apps have new API methods, cache layer, biometric gate, dark mode tokens. Push dispatch stubs compile and read device tokens from DB. Accessibility audit documented.

---

## Parking lot — deferred with reason

These are **not** on the session list because they're intentionally out of scope for Phase 1. They stay in the parking lot; move them to a session only when a user actually blocks on them.

- **RLS policies** — app-level isolation for Phase 1 per ADR `rls-decision.md`. Revisit when we move to Supabase.
- **SSO / SCIM / SAML** — Phase 3 enterprise.
- **Guest users + cross-org sharing** — Phase 2 when the first customer asks.
- **Linear / Google Calendar / Jira / Airtable / Local-FS** — Phase 2 per spec §07.
- **Confluence / HubSpot / Figma / Zoom / Obsidian** — Phase 3.
- **Fine-tuned Llama 3 intent parsing** (spec §8.4) — long-term.
- **Multi-model routing** — ADR 009 notes this as "compliance bullet only."
- **Autonomous task chains / scheduled tasks** — anti-use-case until a trusted flow is running.
- **Per-capability custom permissions** (Linear-style fine-grained) — 5 fixed tiers are enough.
- **Credentials UI for org + project scope** — backend done, web picks it up in a small follow-up.
- **Per-project Members page** — backend exists, web picks it up in a small follow-up.

---

## How to use this file

1. **Pick a session.** Read its items top to bottom.
2. **Do the work.** Every item has the files it touches.
3. **Update this file.** Strike through completed items with a `~~` wrap and add a one-line note (date, files touched, anything surprising).
4. **Update `STATUS.md`.** Move items from Pending to Shipped.
5. **Re-audit occasionally.** When a whole session finishes, spawn a new audit subagent against this doc to catch drift.

The order above is roughly dependency-ordered. Session 2 (supervisor) is the biggest unlock — every later session benefits from it. Ship it first after the current one.
