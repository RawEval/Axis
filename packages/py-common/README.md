# axis-common

Shared Python library for every Axis backend service.

## Why

After the 2026-04-15 audit, we had six of eight services diverging from the
standard layout in `services/CLAUDE.md`. Rather than copy-paste the same
Settings / logging / middleware / health boilerplate into every service, it
lives here. Every service imports from `axis_common` and extends.

## Exports

```python
from axis_common import (
    AxisBaseSettings,        # subclass in your config.py
    configure_logging,       # structlog setup with correlation IDs
    get_logger,
    RequestIdMiddleware,     # UUID per request, propagated downstream
    ErrorMiddleware,         # sanitized 500s with logged stack traces
    make_health_router,      # /healthz + /readyz with optional DB probe
    DatabasePool,            # asyncpg pool wrapper
    hash_password,           # bcrypt off the event loop
    verify_password,
    create_access_token,
    decode_token,
    InvalidTokenError,
    TokenExpiredError,
)
from axis_common.http import make_client, forward_request_id_headers
```

## Typical service wiring

```python
# services/<name>/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from axis_common import (
    DatabasePool,
    ErrorMiddleware,
    RequestIdMiddleware,
    configure_logging,
    cors_origins_from,
    make_health_router,
)

from app.config import settings
from app.routes import my_routes

configure_logging(service=settings.service_name, level=settings.log_level)
db = DatabasePool(settings.postgres_url, min_size=settings.postgres_pool_min, max_size=settings.postgres_pool_max)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    try:
        yield
    finally:
        await db.close()


app = FastAPI(title="My Service", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.include_router(make_health_router(service=settings.service_name, db=db))
app.include_router(my_routes.router)
```

## Typical service settings

```python
# services/<name>/app/config.py
from axis_common import AxisBaseSettings

class Settings(AxisBaseSettings):
    service_name: str = "my-service"
    # ... any service-specific fields

settings = Settings()
```

## Install

Each service depends on it as a path dep:

```toml
# services/<name>/pyproject.toml
[project]
dependencies = [
    "axis-common",
    ...
]

[tool.uv.sources]
axis-common = { path = "../../packages/py-common", editable = true }
```

## Running tests

```bash
cd packages/py-common
uv run pytest
```
