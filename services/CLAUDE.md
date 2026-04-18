# CLAUDE.md — services/

Shared patterns for every backend service. **Read before editing any service.**

## Service inventory

| Service | Lang | Port | Owns |
|---|---|---|---|
| api-gateway | Python/FastAPI | 8000 | Auth verification, request routing, rate limiting, WebSocket fan-out |
| agent-orchestration | Python/LangGraph | 8001 | Prompt parsing, planning, sub-agent execution, result synthesis |
| connector-manager | Python/FastAPI | 8002 | OAuth flows, token encryption, sync scheduling, health monitoring |
| proactive-monitor | Python/Celery | — | Background signal processing, relevance scoring, morning brief |
| eval-engine | Python/FastAPI | 8003 | LLM-as-judge rubric scoring, correction processing |
| memory-service | Python/FastAPI | 8004 | Neo4j graph + Qdrant vector + three-tier memory retrieval |
| notification-service | Node/Fastify | 8005 | APNs + FCM push, Resend email |
| auth-service | Python/FastAPI | 8006 | User register/login, JWT issuance, session management |

## Standard Python service layout

Every FastAPI service follows this structure exactly:

```
services/<name>/
├── pyproject.toml       uv managed, ruff configured, >= Python 3.12
├── Dockerfile           multi-stage uv-based
├── README.md            one paragraph + run command
├── CLAUDE.md            specific architectural notes
├── .env.example         service-specific env vars (optional, fall back to root)
├── app/
│   ├── __init__.py
│   ├── main.py          FastAPI() app, lifespan, middleware, include_router
│   ├── config.py        pydantic-settings Settings class
│   ├── db.py            asyncpg pool (if the service touches Postgres)
│   ├── deps.py          FastAPI dependencies (get_db, get_current_user, …)
│   ├── security.py      password hashing, JWT helpers (auth-service only)
│   ├── models.py        Pydantic request/response models OR app/schemas/
│   ├── clients/         httpx clients for downstream services (if any)
│   ├── repositories/    DB repository classes — one per table
│   └── routes/          one module per resource (health, agent, connectors, …)
└── tests/
    ├── conftest.py
    └── test_<route>.py
```

## Standard patterns

### 1. Settings (every service)

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    log_level: str = "info"
    postgres_url: str = "postgresql://axis:axis@localhost:5432/axis"
    # service-specific fields here

settings = Settings()
```

Never call `os.environ[...]` from application code. Add to Settings and the root `.env.example`.

### 2. Health (every service)

```python
# app/routes/health.py
@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "<name>"}
```

### 3. DB pool (if the service uses Postgres)

```python
# app/db.py
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.postgres_url, min_size=1, max_size=10)
    return _pool
```

Wire it in `main.py` lifespan to open/close the pool.

### 4. Auth dependency (every protected service)

```python
# app/deps.py
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from app.config import settings

async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload["sub"]
    except JWTError as e:
        raise HTTPException(401, "invalid token") from e
```

### 5. Repositories (never raw SQL in routes)

One class per table in `app/repositories/`. Raw SQL is fine — we are not using an ORM. Keep queries in one place so we can add RLS, caching, and metrics uniformly.

### 6. Inter-service calls

Always go through `httpx.AsyncClient` with a 5-second default timeout, typed responses, and retries on transient errors. A client for each downstream lives in `app/clients/<service>.py`. The base URL comes from Settings (`agent_orchestration_url: str = "http://localhost:8001"`).

### 7. Errors

Raise `HTTPException(status_code, "short-lowercase-message")`. Let FastAPI render it. Don't return error dicts manually. 4xx for client mistakes, 5xx for our bugs.

### 8. Tests

Every route gets at least a happy-path test in `tests/test_<route>.py` using FastAPI `TestClient`. Integration tests that need Postgres use the real running Docker container — we are not mocking the DB.

## Standard Node service layout (notification-service only for now)

```
services/notification-service/
├── package.json           type: "module"
├── tsconfig.json          extends ../../tsconfig.base.json
├── Dockerfile
├── src/
│   ├── index.ts           Fastify app bootstrap
│   ├── config.ts          env via zod
│   ├── push/              APNs + FCM
│   ├── email/             Resend
│   └── routes/            Fastify routes
└── test/
```

## Do

- Follow the layout above to the letter. If you need a new pattern, add it here first.
- Keep service boundaries clean. If you catch yourself importing from another service, stop. Extract into `packages/` or call via HTTP.
- Emit structured logs via `structlog` (Python) or Fastify's logger (Node). No `print`, no `console.log`.
- Default timeouts on every outbound call (DB, HTTP, LLM). No unbounded waits.

## Don't

- Don't add a new service without user approval. Eight is already a lot.
- Don't share Python modules across services except via a proper package in `packages/`.
- Don't block the event loop. Everything async. Use `run_in_threadpool` for CPU-bound work.
- Don't swallow exceptions. Log and re-raise or convert to HTTPException.
- Don't import from `agents/`, `graphs/`, or `routes/` across services. Each service is its own world.
