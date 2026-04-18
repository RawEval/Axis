"""Axis API Gateway — FastAPI entrypoint.

Request flow (outside-in):
  client
    → RequestIdMiddleware (UUID + contextvar)
    → ErrorMiddleware (sanitize 500s)
    → CORSMiddleware (explicit methods/headers)
    → route handlers
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from axis_common import (
    ErrorMiddleware,
    RequestIdMiddleware,
    configure_logging,
    cors_origins_from,
    get_logger,
    make_health_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import db
from app.routes import (
    activity,
    admin,
    agent,
    auth,
    connectors,
    eval as eval_routes,
    feed,
    invites,
    memory,
    oauth_apps,
    orgs,
    permissions,
    projects,
    writes,
    ws,
)

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)

_limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)


GRACEFUL_SHUTDOWN_TIMEOUT_SEC = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    short = settings.http_client_timeout_ms / 1000
    long = settings.long_request_timeout_ms / 1000
    # verify=False for local dev with self-signed certs on connector-manager.
    # Production uses real certs so this is safe.
    ssl_verify = settings.environment not in ("dev", "development", "test")
    app.state.http_client = httpx.AsyncClient(timeout=short, limits=_limits, verify=ssl_verify)
    app.state.http_client_long = httpx.AsyncClient(timeout=long, limits=_limits, verify=ssl_verify)
    await db.connect()
    logger.info("api_gateway_startup", short_timeout=short, long_timeout=long)
    try:
        yield
    finally:
        # Drain in-flight requests — give them GRACEFUL_SHUTDOWN_TIMEOUT_SEC
        # before we close pools. Uvicorn stops accepting new connections on
        # SIGTERM, so this window lets active requests finish.
        logger.info(
            "api_gateway_draining",
            timeout_sec=GRACEFUL_SHUTDOWN_TIMEOUT_SEC,
        )
        await asyncio.sleep(GRACEFUL_SHUTDOWN_TIMEOUT_SEC)
        await app.state.http_client.aclose()
        await app.state.http_client_long.aclose()
        await db.close()
        logger.info("api_gateway_shutdown")


app = FastAPI(
    title="Axis API Gateway",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Axis-Project"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestIdMiddleware)

# Rate limiting — Redis-backed token bucket via slowapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.ratelimit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from axis_common import init_observability
init_observability(
    app,
    service_name=settings.service_name,
    sentry_dsn=settings.sentry_dsn,
    environment=settings.environment,
)

app.include_router(make_health_router(
    service=settings.service_name,
    db=db,
    redis_url=settings.redis_url,
))
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(oauth_apps.router, prefix="/oauth-apps", tags=["oauth-apps"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
app.include_router(feed.router, prefix="/feed", tags=["feed"])
app.include_router(activity.router, prefix="/activity", tags=["activity"])
app.include_router(eval_routes.router, prefix="/eval", tags=["eval"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])
app.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
app.include_router(writes.router, prefix="/writes", tags=["writes"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(ws.router)
