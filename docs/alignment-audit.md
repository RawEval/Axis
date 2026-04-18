# Alignment audit — docs vs code

**Date:** 2026-04-16
**Method:** code-reviewer subagent walked every ADR + spec §6 + use-cases + every service directory
**Bottom line:** Phase 1 as described in the spec is **~15% implemented**. Auth, orgs/RBAC, projects, BYO OAuth, Notion OAuth, and the web shell are real. Everything that would make Axis "Axis" instead of "a ChatGPT wrapper" is either empty directories, stubs, or design-only ADRs.

This doc lives permanently in the repo. When a gap here gets closed, strike it through (don't delete). When the picture changes, add a dated note at the top.

---

## CRITICAL GAPS — fundamental product work

### 1. No agentic tool-use loop
`services/agent-orchestration/app/graphs/planner.py` has exactly two nodes (`route_project` → `parse_and_synthesise`). The Anthropic call is `client.messages.create(...)` with **no `tools=` parameter**. No supervisor, no worker fan-out, no capability registry, no tool_use loop.

- ADR 005 `agentic-architecture.md` describes supervisor + `reader/writer/research/code/summarise/synthesise` workers, max 5 concurrent, with the capability registry. **None of this exists as code.**
- `services/agent-orchestration/app/agents/` is an empty directory
- `services/agent-orchestration/app/tools/` is an empty directory
- The spec §6.2 "Tool selection" bullet is not met
- Per-service CLAUDE.md calls out the missing `clients/memory.py`, `clients/connector_manager.py`, `clients/eval.py` — they don't exist

### 2. Zero source tracing
`planner.py` line 136: `"sources": []` hard-coded. Every agent run stores an empty sources list. Spec §6.2 "Every output includes a collapsible 'Sources' section" is impossible.

### 3. Notion connector is orphaned
`connectors/notion/src/client.py` implements `search`, `get_page`, `get_page_blocks`, `append_blocks`, `create_page`. **Nothing imports this client from agent-orchestration.** OAuth works; the agent cannot actually read or write to the thing it just connected to.

### 4. Only 1 of 5 Phase-1 connectors
- ✅ Notion — OAuth flow implemented
- ❌ Slack — HTTP 501
- ❌ Gmail — HTTP 501
- ❌ Google Drive — HTTP 501
- ❌ GitHub — HTTP 501

`services/connector-manager/app/oauth/` contains only `notion.py`. Pattern is proven; four more connectors to write.

### 5. Eval engine is a stub returning 4.2
`services/eval-engine/app/main.py` lines 71–79 — the `/score` route returns `composite_score=4.2` literally. No Haiku judge, no rubric prompts, no insert into `eval_results`. The "core moat" from spec §6.6 is 0% built.

`app/judges/` and `app/rubrics/` are empty directories.

### 6. No correction capture
No `/corrections` route, no `correction_signals` insert path, no inline "this was wrong" UI on chat, no short-loop system-prompt mutation, no long-loop JSONL export. Spec §6.6 short-and-long-loop are 0% built.

### 7. Memory is a stub
`services/memory-service/app/main.py` line 72: `/retrieve` returns `[]`. No Qdrant client, no Neo4j driver, no episodic/semantic/procedural tier modules. `app/graph/`, `app/vector/`, `app/tiers/` are empty directories. Spec §6.4 is 0% built.

### 8. Proactive layer is a stub
`services/proactive-monitor/app/worker.py` is 27 lines. Two Celery tasks (`scan_user`, `morning_brief`) that return empty dicts with TODO comments. **None of the six signal detectors from spec §6.3** exist. `proactive_surfaces` table is never written to. The web feed always renders the empty state.

No `signals/`, `relevance/`, or `brief/` subpackages.

### 9. No write-back engine
Spec §6.5 "Write-back engine" = 0 lines of code. No diff-preview-before-write, no `write_actions` insert path, no 30-day snapshot/rollback, no conflict detection. The `DiffViewer` React component exists on the web but isn't wired to any backend output.

### 10. No streaming / live task tree
ADR 008 `streaming-real-time.md` is design only. No Redis pub/sub wiring between orchestration and gateway, no WebSocket fan-out, no SSE alternative, no Redis Stream replay on reconnect. The web `lib/ws.ts` exists but receives nothing.

### 11. No permission-grant runtime
ADR 006 schema exists (`permission_grants`, `permission_events`). Runtime behavior does not — no `pause → ask user → resume` flow, no permission modal, no short-loop grant lookup. Agent cannot legitimately ask "may I read your Gmail?"

### 12. `agent_tasks` / `agent_task_steps` tables unused
Migration 006 added these for the multi-step supervisor loop. Orchestrator still writes only the flat `agent_actions` row. The multi-step task tree has no persistence layer.

---

## HIGH-PRIORITY GAPS — block real user value

### 13. Chat page shows no citations or highlighted spans
`apps/web/app/(app)/chat/page.tsx` renders `{lastResult.output}` as a whitespace-pre-wrapped string. No citation rendering, no span highlighting, no source cards, no per-step task tree. Spec §8.1 "Task Tree" and "Diff Viewer" key components are not wired to real data.

### 14. Feed page always shows empty state
`apps/web/app/(app)/feed/page.tsx` queries `/feed` which reads `proactive_surfaces`. That table is never written. **The entire §6.3 pillar is unreachable from the UI**, not because of a bug, but because nothing upstream produces the data.

### 15. No activity ingestion
`activity_events` (ADR 007 `activity-feed.md`) is never populated. Even if the planner upgraded, there's nothing to synthesize from.

### 16. Sync scheduling nonexistent
`services/connector-manager/app/sync/` contains only `__init__.py`. No scheduler, no Celery beat, no poll tasks. Spec §6.1 "polling every 15 min for Notion" is not running.

---

## MEDIUM GAPS — polish / productionization

### 17. Connector health monitoring not wired
No red/yellow/green status updater, no 24h token re-validation loop. Connections UI has no live health signal.

### 18. History page cannot show real sources
Because `sources=[]` in every run, the History → "source traces and rollback" surface (spec §8.1, §6.5) is blank even when wired.

### 19. Episodic compression nightly job not implemented
Spec §6.4 "older than 90 days compressed" is a TODO.

### 20. Morning brief job is a stub
`worker.py::morning_brief` returns `{"digest": []}`. Notification-service never receives a digest payload.

### 21. Service-level gaps (STATUS.md confirms)
Rate limiting (slowapi+Redis), Sentry, OpenTelemetry exporter, graceful shutdown on SIGTERM — all pending.

---

## LOW GAPS — nice-to-have, deferrable

- Linear / Google Calendar / Jira / Airtable / Local-FS — Phase 2 per spec §07; not expected yet
- Confluence / HubSpot / Figma / Zoom / Obsidian — Phase 3; deferrable
- Phase 3 intent parsing via fine-tuned Llama 3 (spec §8.4) — long term
- Mobile KMM shared types, offline cache, push, dark mode, voice input — Phase 2
- Credentials UI org + project scope selector — backend ready, UI is user-scope only
- Real invite email via Resend — link-copy today

---

## Prompt walkthrough — 10 representative prompts from `use-cases.md`

This is the honest answer to "think like a user and check if the chat can handle it":

| # | Prompt | Status | Blocking dependency |
|---|---|---|---|
| 1 | "What happened in #product yesterday?" | ❌ | Slack connector + tool-use + ingestion |
| 2 | "Find the email from Samir about the vendor renewal" | ❌ | Gmail connector + tool-use |
| 3 | "Find the doc about Q3 planning" (Notion) | ⚠️ | Notion connected, client exists, planner doesn't call it |
| 4 | "Append today's standup notes to the team page" (Notion write) | ❌ | Write-back engine + DiffViewer wiring |
| 5 | "What follow-ups am I owing anyone this week?" (cross-project) | ❌ | Every connector + memory + followup detector |
| 6 | "Where did we decide to ship Feature X on Nov 1?" (audit) | ❌ | Cross-tool index + unrecorded-decision detector |
| 7 | "Summarize #product this week and draft a Notion update" | ❌ | Slack read + Notion write + supervisor loop |
| 8 | "Comment on PR #42 that this needs a second reviewer" | ❌ | GitHub connector + write-back |
| 9 | Morning brief at 8am | ❌ | `morning_brief` Celery task is a stub |
| 10 | "Show me every agent output where I corrected the summary" | ❌ | No correction capture exists |

**Zero prompts work today.** The only thing that works is generic free-form chat with Sonnet — i.e., what ChatGPT already does.

## Spec section status (§6 from `axis_full_spec.docx`)

| § | Name | Status |
|---|---|---|
| §6.1 | Connect Layer | ⚠️ Notion ✓, BYO OAuth ✓, 4 connectors ✗, webhooks ✗, Qdrant index ✗ |
| §6.2 | Prompt Engine | ❌ No tool selection, no multi-step plan, no source tracing, no slash commands |
| §6.3 | Proactive Intelligence | ❌ Zero — no detectors, no relevance engine, no morning brief |
| §6.4 | Memory System | ❌ Zero — no Qdrant, no Neo4j, no three-tier retrieval |
| §6.5 | Write-back Engine | ❌ Zero — no diff preview wired, no snapshots, no rollback |
| §6.6 | Eval + Correction | ❌ Zero — stub returns 4.2, no judge, no corrections |
| §6.7 | Multi-agent Orchestration | ❌ Zero — single LLM call, no decomposition, no task tree persistence |

---

## Critical path

If you only invest in 5 things:

1. **Wire Notion reads into the planner as the first real tool** — prove the supervisor pattern against one live connector. Unblocks prompts like "find the doc about Q3 planning."
2. **Implement the supervisor + tool-use loop in `planner.py`** — upgrade from a single Sonnet call to Claude tool-use with a typed `tools=` array. Start with 3-4 capabilities: `memory.retrieve`, `activity.query`, `connector.notion.search`, `connector.notion.append`.
3. **Ship the other 4 connectors** — Slack first (most-requested), then Gmail, Drive, GitHub. Each is ~1 day.
4. **Make eval-engine actually score** — real Haiku judge, real rubric prompts, writes to `eval_results`. Fire-and-forget from orchestration after every run.
5. **Activity ingestion worker for at least one connector** — so the feed page can finally show real data. Slack webhook → `activity_events` is the shortest path.

The supervisor + tool-use loop (#2) is the biggest single leverage point. Everything downstream depends on it.

---

## References

- [`STATUS.md`](./STATUS.md) — self-reported pending list (this audit matches it)
- [`TODO.md`](./TODO.md) — session-by-session plan derived from this audit
- `docs/architecture/agentic-architecture.md` — ADR 005 supervisor + workers design
- `docs/architecture/activity-feed.md` — ADR 007 activity firehose design
- `docs/architecture/use-cases.md` — ground-truth prompt list
- `docs/axis_full_spec.docx` — the canonical spec (§6 feature specs)
