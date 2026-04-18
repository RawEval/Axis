# CLAUDE.md — services/api-gateway

The edge of Axis. Every client request hits this service first. **Nothing else is exposed to the public internet.** Read `services/CLAUDE.md` first for shared patterns.

## Responsibilities

- JWT verification (not issuance — that's auth-service)
- Request routing to downstream services via httpx
- WebSocket fan-out for live agent execution updates and proactive surfaces
- CORS (only `NEXT_PUBLIC_APP_URL` in prod)
- Rate limiting (Redis-backed token bucket — to be added)
- Request/response logging with correlation IDs

## Not responsibilities

- Do not issue JWTs. Proxy `/auth/*` → auth-service.
- Do not run agent logic. Proxy `/agent/run` → agent-orchestration.
- Do not touch connector OAuth. Proxy `/connectors/*` → connector-manager.
- Do not score evals. Proxy `/eval/*` → eval-engine.
- Do not hold business logic. This service is a *pass-through with policy*.

## Routes

| Path | Method | Auth | Downstream |
|---|---|---|---|
| `/healthz`, `/readyz` | GET | public | local |
| `/auth/register` | POST | public | auth-service |
| `/auth/login` | POST | public | auth-service |
| `/auth/me` | GET | bearer | auth-service |
| `/agent/run` | POST | bearer | agent-orchestration |
| `/agent/history` | GET | bearer | local (Postgres) |
| `/connectors` | GET | bearer | connector-manager |
| `/connectors/{tool}/connect` | POST | bearer | connector-manager |
| `/connectors/{tool}` | DELETE | bearer | connector-manager |
| `/feed` | GET | bearer | local (Postgres) |
| `/feed/{id}/accept` | POST | bearer | proactive-monitor (later) |
| `/feed/{id}/dismiss` | POST | bearer | proactive-monitor (later) |
| `/ws` | WS | bearer (query) | local — fan-out hub |

## Auth dependency

Every protected route uses `Depends(get_current_user_id)`. It:
1. Reads `Authorization: Bearer <jwt>`
2. Verifies signature + expiry against `JWT_SECRET`
3. Returns `user_id` (the JWT `sub` claim)
4. Raises 401 on any failure

Never trust `user_id` from the request body. Always take it from the dependency.

## Downstream clients

Each downstream service has a typed client in `app/clients/<service>.py`:

```python
# app/clients/auth.py
class AuthClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self._c = client
        self._b = base_url

    async def register(self, email: str, password: str) -> dict: ...
    async def login(self, email: str, password: str) -> dict: ...
    async def me(self, token: str) -> dict: ...
```

One `httpx.AsyncClient` is created in the lifespan and injected via `Depends(get_auth_client)`. Timeouts default to 5s.

## Config

```python
class Settings(BaseSettings):
    auth_service_url: str = "http://localhost:8006"
    agent_orchestration_url: str = "http://localhost:8001"
    connector_manager_url: str = "http://localhost:8002"
    eval_engine_url: str = "http://localhost:8003"
    memory_service_url: str = "http://localhost:8004"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = ["http://localhost:3001"]
```

## Dev

```bash
cd services/api-gateway
uv run uvicorn app.main:app --reload --port 8000
open http://localhost:8000/docs
```

## Do

- Surface errors from downstream services faithfully (preserve their status codes when it makes sense).
- Propagate `X-Request-ID` to downstream calls for tracing.
- Return 504 if a downstream service times out.

## Don't

- Don't call Claude API from here. That's agent-orchestration's job.
- Don't touch Qdrant or Neo4j. Those belong to memory-service.
- Don't implement business logic. If a route needs more than "verify auth, call downstream, return response," the logic belongs in the downstream service.
