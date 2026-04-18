# CLAUDE.md — packages/py-common

Shared Python library imported by every backend service. **Read this before adding anything new to a service's boilerplate** — it probably belongs here instead.

## What lives here

- `settings.py` — `AxisBaseSettings` + safety validators (JWT default-detect, postgres URL shape, log level)
- `logging.py` — structlog setup, correlation ID contextvars, console vs JSON auto-switch
- `middleware/request_id.py` — `RequestIdMiddleware` (UUID per request, X-Request-ID header)
- `middleware/errors.py` — `ErrorMiddleware` (sanitize 500s, log stack traces)
- `errors.py` — `AxisHTTPException`, `ErrorPayload`
- `security.py` — password hashing in threadpool, JWT create/decode with `TokenExpiredError` vs `InvalidTokenError`
- `db.py` — `DatabasePool` asyncpg wrapper with `is_healthy()`
- `health.py` — `make_health_router()` — shared /healthz + /readyz
- `http.py` — `make_client()` httpx factory with sane limits; `forward_request_id_headers()`

## Rules

1. **Pure library.** No server, no FastAPI `app`, no env reads at import time. Services own the app lifecycle; we provide building blocks.
2. **Breaking changes require updating every consumer in the same commit.** All eight Python services import from here.
3. **No circular deps.** `packages/py-common` can import stdlib, `fastapi`, `starlette`, `httpx`, `structlog`, `pydantic`, `asyncpg`, `python-jose`, `passlib`. Nothing from `services/` or `apps/`.
4. **Type-hint everything.** Consumers rely on us as reference types.
5. **Add tests in `packages/py-common/tests/`**, not in a consumer.
6. **Settings extensibility.** Services subclass `AxisBaseSettings` and add fields. Never inline overrides for shared fields like `postgres_url` or `jwt_secret` — if they differ, the env var differs.

## When to add something here

- When two or more services need the same helper
- When the audit calls out a pattern as inconsistent
- When a new cross-cutting concern lands (tracing, metrics, feature flags)

## When NOT to add

- Service-specific business logic
- Route handlers
- Repositories (each service owns its own SQL)

## Changing the shared BaseSettings

The `_safe_jwt_secret` validator refuses to boot if `ENVIRONMENT!=dev` and the secret looks default. **Do not relax this.** Services that need their own secret should set `JWT_SECRET` in env, not extend the validator.

## Don't

- Don't import from `services/*` (circular).
- Don't mutate module-level state from multiple services (use contextvars).
- Don't add a dep without confirming it's really shared.
- Don't leak request context across requests — always `clear_request_context()` in finally.
