# Axis Codebase Audit — 2026-04-15

**Scope:** Full-repo audit following initial scaffold, before shipping the real vertical. Performed by a code-reviewer subagent against the spec (§6, §8, §10) and production-readiness standards.

This document captures the findings so they survive across sessions.

---

## P0 — Fix immediately

### 1. RLS footgun
`001_init.sql` enables Row-Level Security on every table but defines zero `CREATE POLICY` statements. **Works locally** because the dev role owns the tables (implicit `BYPASSRLS`). **Breaks silently on Supabase/managed Postgres** where the connection role is not the owner — every query returns `[]` with no error.

**Fix:** `003_rls.sql` disables RLS across all nine tables. See [`rls-decision.md`](./rls-decision.md).

### 2. `/agent/run` 504s on every call
`services/api-gateway/app/main.py` creates **one** `httpx.AsyncClient` with a 5-second timeout. Agent runs budgeted at 120s per `.env` never reach downstream before the client aborts.

**Fix:** dual-client pattern — `http_client_short` (5s) for auth/connectors, `http_client_long` (120s) for `/agent/run`.

### 3. JWT `change-me` default
Both `auth-service` and `api-gateway` Settings default `jwt_secret` to `"change-me"`. Nothing fails at boot if the env var is missing.

**Fix:** Pydantic field validator that raises in non-dev environments if the secret is the default, empty, or starts with `"change-me"`.

---

## P1 — Security

### 4. JWT in `localStorage`
`apps/web/lib/auth.ts` stores the access token in `localStorage` and mirrors to a non-`HttpOnly` cookie. `apps/web/CLAUDE.md` itself mandates `HttpOnly`. XSS = token exfil.

**Fix:** auth-service sets `HttpOnly, Secure, SameSite=Strict` cookie on register/login. Web middleware reads it. Browser JS never sees the token. Deferred to a follow-up because it touches both backend and frontend and we're prioritizing the vertical slice this session.

### 5. Bcrypt blocking the event loop
`passlib.hash` at 12 rounds blocks ~250ms per call. Called directly from async routes, so login pinning the event loop under load.

**Fix:** wrap `hash_password` / `verify_password` in `fastapi.concurrency.run_in_threadpool`.

### 6. `decode_token` doesn't distinguish expired vs invalid
Callers can't differentiate "refresh needed" from "bad signature". Frontend can't implement a refresh flow.

**Fix:** raise `TokenExpiredError(ValueError)` vs `InvalidTokenError(ValueError)` sub-exceptions.

### 7. Rate limiting missing
`.env` has `RATE_LIMIT_*` vars. `api-gateway/CLAUDE.md` says rate limiting is its job. Zero implementation.

**Fix:** slowapi on `/auth/register`, `/auth/login`, `/agent/run`. Deferred past this session.

### 8. WebSocket has no auth
`/ws` accepts any connection and echoes.

**Fix:** require JWT via query param (`?token=...`). Close immediately if invalid. Deferred until we actually wire WebSocket events.

### 9. Email enumeration on register
`409 "email already registered"` reveals registered emails.

**Fix:** return 202 + generic success, require email verification via notification-service. Deferred — Phase 2 when Resend is wired.

### 10. SQL injection — confirmed safe
All `asyncpg.execute`/`fetch` calls use `$1, $2` parameters. No string interpolation anywhere. ✓

---

## P1 — Consistency

### 11. Service layout divergence
Six of eight services do not follow `services/CLAUDE.md`. Table:

| Service | Settings | lifespan | db.py | repos | CORS | /readyz | Structured logs |
|---|---|---|---|---|---|---|---|
| auth-service | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| api-gateway | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (stub) | ✗ |
| agent-orchestration | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| connector-manager | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| eval-engine | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| memory-service | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| notification-service | ✗ | ✗ | — | — | — | ✗ | Fastify default |
| proactive-monitor | ✗ `os.environ` | — | — | — | — | N/A | ✗ |

**Fix:** build `packages/py-common` with shared Settings base, logging init, middleware, errors. Normalize every Python service to consume it.

### 12. `cors_origins` implemented differently across services
`auth-service` uses `@property`; `api-gateway` uses a module function after Pydantic v2 stripped the property. **Pydantic v2 BaseSettings does not expose `@property` as attributes** — the api-gateway hit this bug during the first scaffold.

**Fix:** both should use a plain module-level helper.

### 13. `REPO_ROOT = parents[3]` duplicated
Two services hard-code `parents[3]`. If directory depth changes, silent breakage.

**Fix:** shared helper in `py-common`.

---

## P2 — Production hardening

### 14. No structured logging
Every service uses Python stdlib logging (or none). No JSON output, no correlation IDs, no request tracing.

**Fix:** structlog configured centrally in `py-common`. Every log line emits `request_id`, `service`, `user_id` where applicable.

### 15. No correlation IDs
`api-gateway/CLAUDE.md` states `X-Request-ID` must flow. `expose_headers=["X-Request-ID"]` in CORS. Nothing actually generates or forwards the header.

**Fix:** `RequestIdMiddleware` in `py-common` — generates UUID if missing, stores in contextvar, injects into response header and downstream httpx calls.

### 16. No global error middleware
Unhandled exceptions return FastAPI default. No Sentry.

**Fix:** error handler in `py-common` that catches everything, logs with `exc_info`, returns sanitized 500. Optional Sentry SDK wiring behind `SENTRY_DSN`.

### 17. `/readyz` is stubbed
api-gateway `/readyz` returns `ready` unconditionally. Auth-service has no `/readyz` at all.

**Fix:** real readiness probe — pings DB pool, counts open connections, returns 503 if pool is exhausted.

### 18. CORS wildcards
`allow_methods=["*"]` + `allow_headers=["*"]` + `allow_credentials=True`. Too permissive for prod.

**Fix:** explicit allowlist. Methods: `GET,POST,DELETE,OPTIONS`. Headers: `Authorization,Content-Type,X-Request-ID`.

### 19. No httpx connection limits
Default httpx has no pool cap. Under burst load we leak connections.

**Fix:** `httpx.Limits(max_keepalive_connections=20, max_connections=100)` + `http2=True`.

### 20. Postgres port mismatch
`api-gateway/app/config.py` default was `5433` (correct post-port-remap), older reference was `5432`. Grep the repo.

**Fix:** single source of truth via env var; validator that asserts `postgresql://`.

---

## P1 — Feature gaps vs spec

| Spec § | Feature | Status | Phase |
|---|---|---|---|
| 6.1 | Connect layer (OAuth, encryption, health) | 0% | P1 |
| 6.2 | Prompt engine (intent, plan, execute, trace) | ~5% | P1 |
| 6.3 | Proactive intelligence | ~2% | P2 |
| 6.4 | Memory 3-tier | 0% | P2 |
| 6.5 | Write-back engine (diff, snapshot, rollback) | 0% | P1 |
| 6.6 | Eval + correction loop | ~3% | P1 |
| 6.7 | Multi-agent orchestration | ~5% | P3 |

**P1 order:** §6.1 (connectors) → §6.2 (prompt engine) → §6.5 (write-back) → §6.6 (eval loop) → §6.4 (memory) → §6.7 (multi-agent) → §6.3 (proactive).

**This session:** shipping a real end-to-end vertical on §6.1 + §6.2 for Notion (user explicitly named it). Everything else stubbed cleanly with interfaces + TODOs.

---

## P2 — Tests

Test coverage is **1 test** across the whole backend (`api-gateway/tests/test_health.py`).

Minimum baseline:
- `auth-service/tests/test_auth.py` — register, duplicate, login, wrong password, lockout, `/me` with valid/expired/bad token
- `api-gateway/tests/test_proxy.py` — proxy to auth-service via respx, 401 without token, correlation id propagation
- `apps/web/__tests__/middleware.test.ts` — unauth redirect, public path allowlist

Covered: task #18.

---

## Top 10 Fixes — ROI ranked

| # | Fix | ROI |
|---|---|---|
| 1 | RLS disable + document | P0: prevents silent prod outage |
| 2 | Dual httpx timeouts | P0: unblocks /agent/run |
| 3 | JWT secret validator | P0: prevents default-secret prod deploy |
| 4 | Bcrypt off event loop | 10× login throughput |
| 5 | Request-ID middleware | Unlocks tracing day one |
| 6 | CORS lockdown | Prevents cross-origin CSRF |
| 7 | Postgres port alignment | Prevents dev/prod split |
| 8 | Normalize stub services | Prevents a day's friction per service |
| 9 | Baseline tests (auth) | Prevents 80% of auth regressions |
| 10 | HttpOnly cookie refactor | Prevents XSS → token theft |

---

## Deferred to next session

- HttpOnly cookie auth (#4 of audit top 10) — touches web + auth-service
- slowapi rate limiting — not urgent pre-launch
- Full RLS policies (Phase 2, when on Supabase)
- Email verification flow — needs Resend wired in notification-service
- Refresh tokens — spec mentions; not P1 MVP
- WebSocket auth + real events — no consumer until P2 mobile
- Real eval engine with Haiku-as-judge — stub for now, vertical-slice next
- Real memory service with Qdrant/Neo4j — stub for now

---

## Research notes (2026-04-15 web searches)

**Notion MCP** — Notion hosts an official MCP server at `https://mcp.notion.com/mcp` using OAuth 2.1 + PKCE, refresh token rotation, 1-hour access token TTL. Python SDK: `mcp` on PyPI, `FastMCP` server interface. Supports the full page/database/comment surface. We will use the hosted server as our Notion client — no need to run our own MCP server for Notion reads/writes.

**Anthropic SDK + prompt caching** — supported on `claude-sonnet-4-5` and `claude-haiku-4-5`. Min 1024 tokens. Cache references tools + system + messages in that order. Cache write is 1.25×, read is 0.1× base price. Use on the LangGraph system prompt + tool definitions to save on every agent run. Starting Feb 2026, caches are workspace-isolated.

**LangGraph + FastAPI** — production template exists (wassim249/fastapi-langgraph-agent). Pattern: Client → FastAPI → LangGraph Agent → Tools (MCP-ready) → LLM Providers. Use `checkpointer` for stateful conversations, Redis-backed.

**FastAPI rate limiting** — slowapi is the standard. Redis backend for distributed setups. Decorator-based. Supports dynamic limits per-user / per-key.

**MCP Python SDK** — `mcp` package. `FastMCP` for servers (resources/tools/prompts). Client-side: `mcp.client.stdio`, `mcp.client.sse`, `mcp.client.streamable_http`. For Notion we use the SSE/streamable-HTTP transport pointed at `mcp.notion.com/mcp`.

## Sources

- [Notion MCP — Getting started](https://developers.notion.com/docs/get-started-with-mcp)
- [Notion's hosted MCP server: an inside look](https://www.notion.com/blog/notions-hosted-mcp-server-an-inside-look)
- [Anthropic Prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [MCP Python SDK on GitHub](https://github.com/modelcontextprotocol/python-sdk)
- [FastAPI + LangGraph production template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
- [SlowAPI](https://github.com/laurentS/slowapi)
