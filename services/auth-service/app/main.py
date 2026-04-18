"""Axis Auth Service — register, login, JWT issuance."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from axis_common import (
    ErrorMiddleware,
    RequestIdMiddleware,
    configure_logging,
    cors_origins_from,
    get_logger,
    make_health_router,
)

from app.config import settings
from app.db import db
from app.routes import auth

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("auth_service_startup")
    try:
        yield
    finally:
        await db.close()
        logger.info("auth_service_shutdown")


app = FastAPI(
    title="Axis Auth Service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(make_health_router(service=settings.service_name, db=db))
app.include_router(auth.router, tags=["auth"])
