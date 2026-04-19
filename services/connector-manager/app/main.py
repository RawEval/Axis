"""Axis Connector Manager — OAuth flows, token storage, health monitoring, background sync."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

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
from app.routes import oauth, oauth_apps, tools, webhooks
from app.sync.gdrive_sync import gdrive_sync_loop
from app.sync.notion import notion_poll_loop_v2
from app.sync.slack_sync import slack_sync_loop

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("connector_manager_startup")
    bg_tasks: list[asyncio.Task] = []

    # Background sync loops — each indexes connector data into connector_index
    if settings.notion_poll_enabled:
        bg_tasks.append(asyncio.create_task(notion_poll_loop_v2(60)))
    bg_tasks.append(asyncio.create_task(slack_sync_loop(3600)))     # hourly
    bg_tasks.append(asyncio.create_task(gdrive_sync_loop(3600)))    # hourly

    try:
        yield
    finally:
        for t in bg_tasks:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        await db.close()
        logger.info("connector_manager_shutdown")


app = FastAPI(
    title="Axis Connector Manager",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Axis-User",
        "X-Axis-Project",
    ],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(make_health_router(service=settings.service_name, db=db))
app.include_router(oauth.router, tags=["oauth"])
app.include_router(oauth_apps.router, tags=["oauth-apps"])
app.include_router(tools.router, tags=["tools"])
app.include_router(webhooks.router, tags=["webhooks"])
