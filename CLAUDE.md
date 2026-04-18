# CLAUDE.md — Axis

Read this first every time you work in this repo. It is the single source of architectural truth for Claude Code. If you're about to make a change that contradicts anything here, stop and surface the conflict to the user before proceeding.

## What Axis is

Axis is **the proactive workspace layer for teams** (positioning pivot — ADR 009, `docs/architecture/009-positioning-pivot.md`, supersedes the original spec's "one app, connect everything" framing).

It watches Slack, Notion, Gmail, Drive, GitHub, Linear in the background and surfaces what the user would otherwise miss. Writes are gated with a diff preview and rollback for 30 days. BYO OAuth credentials are a first-class feature for compliance-sensitive teams. The data model is organized around **organizations with role-based delegation** (ADR 010, `docs/architecture/org-and-rbac.md`), not a single user with a project list.

Pre-seed, RawEval Inc, Bengaluru. The original spec is at `docs/axis_full_spec.docx` (v1.0, 2025) — treat it as historical context; when the spec and the ADR 009 pivot disagree, **ADR 009 wins**.

**Rule zero for every UI/UX choice:** roles are permission tiers, never job titles. We ship `owner / admin / manager / member / viewer` — we do not ship "President," "CEO," "VP," or any other seniority label anywhere in the product. Roles describe what a person *can do*, not what they *are*. See `docs/architecture/org-and-rbac.md` for the full model.

## Reference map

Before touching architecture, check the relevant ADR:

| ADR | File | Scope |
|---|---|---|
| 002 | `docs/architecture/projects-model.md` | Projects (superseded by ADR 010 — projects now belong to orgs) |
| 003 | `docs/architecture/byo-credentials.md` | Bring-your-own OAuth credentials |
| 004 | `docs/architecture/project-router.md` | Cross-project prompt routing |
| 005 | `docs/architecture/agentic-architecture.md` | Supervisor + workers + capability registry |
| 006 | `docs/architecture/permissions-model.md` | Claude-Code-style interactive grants |
| 007 | `docs/architecture/activity-feed.md` | User-level firehose |
| 008 | `docs/architecture/streaming-real-time.md` | SSE + WebSocket for live updates |
| 009 | `docs/architecture/009-positioning-pivot.md` | **The product's positioning** — read first |
| 010 | `docs/architecture/org-and-rbac.md` | **Orgs, roles, delegation** — the new top-level data model |

External pitch: `docs/pitch/one-pager.md`. Use-case catalog: `docs/architecture/use-cases.md`.

## Repo layout (monorepo)

```
apps/          — user-facing apps
  web/         — Next.js 14 (App Router) + TS + Tailwind + Zustand + React Query
  mobile-ios/  — Swift + SwiftUI (Phase 2)
  mobile-android/ — Kotlin + Compose (Phase 2)
  desktop/     — Phase 3 stub

services/      — Python (uv) + Node microservices
  api-gateway/         FastAPI · port 8000 · auth, routing, WebSocket
  agent-orchestration/ FastAPI + LangGraph · port 8001
  connector-manager/   FastAPI · port 8002 · OAuth + sync
  eval-engine/         FastAPI · port 8003 · LLM-as-judge
  memory-service/      FastAPI · port 8004 · Neo4j + Qdrant
  notification-service/ Node Fastify · port 8005 · APNs/FCM/email
  auth-service/        FastAPI · port 8006 · register/login/JWT
  proactive-monitor/   Celery worker (no HTTP) · spec §6.3

packages/      — shared libraries
  design-system/  Tailwind tokens + React components
  shared-types/   TS types mirroring the Pydantic models in services
  kmm-shared/     Kotlin Multiplatform business logic

connectors/    — one module per tool (slack/notion/gmail/gdrive/github in P1)
infra/         — docker-compose, railway, terraform, k8s
docs/          — architecture, API, runbooks, full spec
scripts/       — bootstrap, dev, seed
```

## Ports (local dev)

| Service | Port | Health |
|---|---|---|
| web | 3001 | http://localhost:3001 |
| api-gateway | 8000 | /healthz |
| agent-orchestration | 8001 | /healthz |
| connector-manager | 8002 | /healthz |
| eval-engine | 8003 | /healthz |
| memory-service | 8004 | /healthz |
| notification-service | 8005 | /healthz |
| auth-service | 8006 | /healthz |
| postgres | 5432 | axis/axis/axis |
| redis | 6379 | — |
| qdrant | 6333/6334 | http://localhost:6333/dashboard |
| neo4j | 7687 / 7474 (UI) | neo4j / axis-dev-password |
| mailhog | 8025 (UI) | — |

The Next.js web app runs on **3001** (not 3000) because another Next.js server already owns 3000 on this machine.

## Core architectural invariants (do not violate)

1. **Every write action requires user confirmation.** Non-negotiable in Phase 1. Spec §6.2. Exception: trust-level-high users can auto-confirm low-risk writes (Notion append, GitHub comment). Sends are *always* gated.
2. **All OAuth tokens encrypted at rest (AES-256).** Never log them. Decrypt only in memory during connector calls. Spec §10.
3. **Per-user data isolation at the DB level.** Row-level security on every Postgres table. Per-user Qdrant namespaces. Zero cross-user data leakage by architecture.
4. **Eval layer runs on every agent action.** Haiku-as-judge scoring. Spec §6.6 — "the core moat." Never skip it for performance.
5. **Trust is earned.** Progressive unlock for write autonomy. Low trust = confirm everything. High trust earned over weeks.
6. **Correction signals are gold.** Every dismiss/correct feeds the long-loop fine-tuning dataset. Never discard them.

## Tech stack (pinned)

- **Frontend:** Next.js 14.2.5, React 18.3, TS 5.5, Tailwind 3.4, Zustand 4.5, React Query 5.51
- **Backend (Python):** Python 3.12+, FastAPI 0.112+, Pydantic v2, uv (not pip/poetry), ruff
- **Backend (Node):** Node 20+, Fastify 4, pnpm 9, Turborepo 2, TypeScript 5.5
- **LLMs:** Claude Sonnet 4.5 (planning, writes) via `claude-sonnet-4-5`, Haiku 4.5 (summarise, eval) via `claude-haiku-4-5`. Never hard-code model names — read from `ANTHROPIC_MODEL_SONNET` / `ANTHROPIC_MODEL_HAIKU` env.
- **Databases:** Postgres 16 (Supabase in prod), Redis 7, Qdrant, Neo4j 5
- **Storage:** Cloudflare R2 (not S3 — keep egress free)
- **Hosting:** Railway in Phase 1, AWS multi-region Phase 2+

## Commands

```bash
# First-time setup
./scripts/bootstrap.sh

# Daily dev (from repo root)
make infra-up         # docker infra (postgres, redis, qdrant, neo4j, mailhog)
make dev              # web + services in parallel (or start each manually)
make test
make lint
make format

# Per-service Python
cd services/<name>
uv sync
uv run uvicorn app.main:app --reload --port <port>
uv run pytest

# Per-service Node (notification-service, web)
pnpm --filter @axis/web dev
pnpm --filter @axis/notification-service dev
```

## Conventions

- **Read before edit.** Always Read a file before Editing it, even if you "remember" it. Files change.
- **Match existing patterns.** New route = same structure as existing routes in the same service. New Python file = ruff-clean, Python 3.12 syntax, `from __future__ import annotations` if using forward refs.
- **No inline comments unless the *why* is non-obvious.** Well-named functions are the documentation.
- **All new Pydantic models mirror into `packages/shared-types`** when the model crosses the API boundary.
- **Every new route gets a test** in `services/<name>/tests/`. Minimum: happy path.
- **OpenAPI is the contract.** Frontend types generated from `/openapi.json` — never hand-written when a generator will do.
- **Service-to-service calls go through HTTP** for now (not a message bus). One `httpx.AsyncClient` per service, typed responses via Pydantic.
- **Environment config via pydantic-settings.** Never read `os.environ` directly in application code.
- **Secrets come from `.env`**, never hardcoded. `.env.example` must stay in sync with every new var.

## When you add something new

1. **New service** → copy the api-gateway layout (`app/main.py`, `app/config.py`, `app/routes/`, `Dockerfile`, `pyproject.toml`, `tests/`), add to `infra/docker/docker-compose.yml` if it runs in-cluster, add to `.github/workflows/ci.yml` matrix, add a CLAUDE.md in its folder.
2. **New connector** → write `connectors/<tool>/src/client.py` (vendor API wrapper, pure I/O), then OAuth at `services/connector-manager/app/oauth/<tool>.py`, then routes at `services/connector-manager/app/routes/tools.py` (`/tools/<tool>/*`), then capability classes at `services/agent-orchestration/app/capabilities/<tool>.py`. Update `apps/web/lib/queries/connectors.ts` + `apps/web/lib/capabilities.ts` + the `TOOLS` array on `apps/web/app/(app)/connections/page.tsx`. Full steps in `connectors/README.md`. **There is no `Connector` base class** — the deleted one is in git history if you really need to look.
3. **New web page** → add to `apps/web/app/<route>/page.tsx`, add to the Sidebar nav in `apps/web/components/sidebar.tsx`.
4. **New DB table** → add migration to `infra/docker/init/postgres/` (numbered), update `packages/shared-types` if it crosses the API.
5. **New env var** → add to both `.env.example` AND the service's `app/config.py` Settings class.

## Things NOT to do

- **No dead code.** Anywhere. If a class, file, function, route, hook, or component isn't imported / called / mounted by something live, delete it — don't leave it as a placeholder, don't leave it as a "future use" stub, don't leave it as a base-class-nobody-inherits-from. Discovered scaffolding from a half-finished initiative? Delete it in the same PR you discovered it. The deleted code is in git history; you can always bring it back.
- Do not add feature flags for hypothetical future work. Delete unused code.
- Do not write backwards-compat shims or re-export stubs. If something moved, update callers.
- Do not add error handling for scenarios that cannot happen. Trust Pydantic + FastAPI's validation at the boundary.
- Do not introduce a new database, queue, or cache without explicit user approval. Four stores is already a lot.
- Do not hardcode model names, URLs, or credentials. Every string like that goes to env.
- Do not commit `.env` files, `*.pem`, `*.key`, or anything in `secrets/`.
- Do not skip the eval step on "simple" agent actions. All actions are evaluated.
- Do not bypass the write-confirmation gate without changing trust level first.

## Ground truth files

- Full spec: `docs/axis_full_spec.docx`
- Data model: `infra/docker/init/postgres/001_init.sql` + `packages/shared-types/src/index.ts`
- Architecture diagrams: `docs/architecture/overview.md`, `docs/architecture/agent-flow.md`
- Runbook: `docs/runbooks/local-dev.md`
