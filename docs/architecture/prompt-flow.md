# Prompt → Response — End-to-end flow

**Status:** current as of 2026-04-16
**Audience:** anyone onboarding to the Axis codebase

This doc traces the exact path a user's typed prompt takes through Axis. Every layer is named, every file path is real. Read top to bottom.

## The big picture

```
         ┌─────────────────────────┐
         │  User types in Chat UI  │
         └───────────┬─────────────┘
                     │
                     ▼
    [L0] apps/web/app/(app)/chat/page.tsx
         state: `prompt` in useState
         onSubmit → run.mutateAsync(prompt)
                     │
                     ▼
    [L1] apps/web/lib/queries/agent.ts::useRunAgent
         React Query mutation
         → api.post<RunResponse>('/agent/run', { prompt })
                     │
                     ▼
    [L2] apps/web/lib/api.ts::apiFetch
         - reads JWT from localStorage (or cookie)
         - injects Authorization: Bearer <token>
         - injects X-Axis-Project: <active-project-uuid>     ← NEW in projects change
         - fetch POST http://localhost:8000/agent/run
                     │
                     ▼
    [L3] apps/web/middleware.ts
         - runs at edge; allows /login /signup through
         - redirects to /login if no axis.token cookie
                     │
                     ▼
    [L4] services/api-gateway/app/main.py
         Middleware stack (outside → in):
           RequestIdMiddleware  — uuid X-Request-ID
           ErrorMiddleware      — sanitized 500s
           CORSMiddleware       — explicit allowlist
                     │
                     ▼
    [L5] services/api-gateway/app/routes/agent.py::run
         - Depends(CurrentUser) → JWT decode (deps.py)
         - Depends(CurrentProject) → X-Axis-Project header → DB lookup  ← NEW
         - construct AgentOrchestrationClient with the LONG httpx pool (120s)
         - propagate X-Request-ID + X-Axis-Project downstream
                     │
                     ▼
    [L6] services/agent-orchestration/app/main.py::run
         - receives {user_id, project_id, prompt}
         - invokes planner_graph.ainvoke(state)
         - trusts user_id from the gateway (no JWT decode here)
                     │
                     ▼
    [L7] services/agent-orchestration/app/graphs/planner.py
         LangGraph state machine:

         START
           │
           ▼
         route_project (new)     — resolves project_ids[] based on header mode
           │
           ▼
         retrieve_context        — pulls memory from memory-service (future)
           │
           ▼
         parse_and_synthesise    — Sonnet 4.5 call with cached system prompt
           │         │             and (future) connector tool use
           ▼         ▼
         (fan-out if multi-project) ── merge_results ── END
                     │
                     ▼
    [L8] anthropic.messages.create
         - model = settings.anthropic_model_sonnet
         - system prompt has cache_control: ephemeral (prompt caching)
         - (future) tools array wired up from connector manifests
                     │
                     ▼
    [L9] services/agent-orchestration/app/repositories/actions.py
         INSERT INTO agent_actions (user_id, project_id, prompt, plan, result)
                     │
                     ▼
    [L10] Return RunResponse back through the stack
         - api-gateway passes it to the web client
         - React Query resolves the mutation
         - Chat page renders the response
```

## Layer-by-layer detail

### L0 — Chat UI

**File:** `apps/web/app/(app)/chat/page.tsx`

A client component with a textarea and a "Run" button. Owns `prompt` state locally. On submit, calls `run.mutateAsync(prompt)`. The result is displayed as formatted JSON under the textarea (real app will render Markdown + source trace — Phase 2 improvement).

### L1 — React Query hook

**File:** `apps/web/lib/queries/agent.ts::useRunAgent`

Wraps the HTTP call so the chat component stays thin. React Query gives us: optimistic updates, retry/backoff, deduplication, cache invalidation of `['agent', 'history']` on success.

### L2 — Typed API wrapper

**File:** `apps/web/lib/api.ts::apiFetch`

Central fetch wrapper. Responsibilities:

1. Read JWT from storage
2. Inject `Authorization: Bearer <jwt>` header
3. **[new]** Inject `X-Axis-Project: <uuid>` from the Zustand store
4. Handle 401 by clearing the token and redirecting to `/login`
5. Parse errors into `ApiError` with downstream `detail`

### L3 — Next.js middleware

**File:** `apps/web/middleware.ts`

Runs at the edge. Redirects unauthenticated requests to `/login` unless the path is public. Does not decode the JWT — only checks the cookie exists. Real verification happens at the backend.

### L4 — API gateway middleware stack

**File:** `services/api-gateway/app/main.py`

Three middlewares, applied outside-in:

1. `RequestIdMiddleware` — generates `X-Request-ID` UUID if absent, binds to structlog contextvar, echoes on response
2. `ErrorMiddleware` — catches anything unhandled, logs with stack trace + request_id, returns sanitized `{"detail": "internal server error"}` 500
3. `CORSMiddleware` — explicit method + header allowlist

All come from `packages/py-common` so every service uses the same stack.

### L5 — `/agent/run` route handler

**File:** `services/api-gateway/app/routes/agent.py::run`

Dependencies injected by FastAPI:

- `CurrentUser` → decodes JWT, returns `user_id` (`deps.py::get_current_user_id`)
- **[new]** `CurrentProject` → reads `X-Axis-Project` header, validates ownership, returns `project_id`
- `get_long_http_client` → the 120-second pool for agent runs

Then builds `AgentOrchestrationClient` with propagated headers (request-id, project-id) and calls `.run()`.

### L6 — Agent orchestration receives

**File:** `services/agent-orchestration/app/main.py::run`

No JWT decode here. Trusts `user_id` from the gateway (defense-in-depth: the orchestration service is only reachable from the gateway's VPC subnet in prod). Kicks off the LangGraph planner.

### L7 — LangGraph planner

**File:** `services/agent-orchestration/app/graphs/planner.py`

A state machine. Phase 1 ships with:

```
START → route_project → parse_and_synthesise → END
```

Phase 2 adds `retrieve_context`, `plan`, `execute`, `eval_score_async`. Phase 3 adds fan-out + merge for multi-project.

Every node gets an `AgentState` dict, mutates it, passes it along.

### L8 — Anthropic call

**File:** `services/agent-orchestration/app/graphs/planner.py::parse_and_synthesise`

Direct call to `anthropic.messages.create`:

```python
resp = await client.messages.create(
    model=settings.anthropic_model_sonnet,
    max_tokens=settings.anthropic_max_tokens,
    temperature=settings.anthropic_temperature,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ],
    messages=[{"role": "user", "content": state["prompt"]}],
)
```

Key production considerations:

- **Prompt caching** on the system prompt. 1.25× write cost, 0.1× read cost. Breakeven: 2 reads.
- **Model name from env**, never hardcoded. Allows overriding per tier (Haiku for free, Sonnet for Pro).
- **Tools (Phase 2)**: each connected tool exposes a JSON schema. Attached to `tools=[...]` in the call. Sonnet decides when to call them; the orchestrator executes and returns results in a loop.
- **Streaming (Phase 2)**: switch to `messages.stream(...)` + Server-Sent Events back to the client. UI renders tokens as they arrive.

### L9 — Persist the action

**File:** `services/agent-orchestration/app/repositories/actions.py::record`

One INSERT into `agent_actions`. Includes `user_id`, `project_id`, `prompt`, the plan (list of steps), and the result blob (output, sources, tokens_used, latency_ms). Returns the new row's id + timestamp.

### L10 — Return path

`RunResponse` bubbles back through orchestration → gateway → React Query → the chat component. The UI renders it and calls `queryClient.invalidateQueries(['agent', 'history'])` so the history page refreshes.

## What's missing today (the honest list)

| Gap | Where | Plan |
|---|---|---|
| No connector tool use | planner.py's single node | Phase 2 — attach each connected tool as a JSON schema + execute tool_use blocks |
| No memory retrieval | no call to memory-service | Phase 2 — add `retrieve_context` node before parse_and_synthesise |
| No streaming | `ainvoke` waits for terminal state | Phase 2 — switch to `astream_events` + SSE |
| No eval scoring | eval-engine is stubbed, no fire-and-forget call | Phase 2 — background task after INSERT |
| No per-user rate limiting | no middleware | Phase 2 — slowapi with Redis backend |
| No retries on connector failures | no retry logic | Phase 2 — exponential backoff with max 1 retry per §6.7 |
| No cross-project synthesis | no fan-out branch | Phase 3 — see project-router.md |

## See also

- `projects-model.md` — the data model
- `project-router.md` — the "user level 2" classifier
- `byo-credentials.md` — user-supplied OAuth app credentials
- `use-cases.md` — what users actually do with this pipeline
