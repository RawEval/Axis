"""Axis shared Python library.

Consumed by every FastAPI service. Exports:

- Settings — Pydantic base with JWT/Postgres/CORS + safety validators
- logging  — structlog setup with correlation ID support
- middleware — RequestIdMiddleware, ErrorMiddleware
- errors  — unified HTTPError models
- db      — asyncpg pool helpers
- security — JWT + bcrypt (run_in_threadpool-safe)
- healthz — shared health/ready router

Import: `from axis_common import ...`
"""
from axis_common.errors import ErrorPayload, AxisHTTPException
from axis_common.logging import bind_request_context, configure_logging, get_logger
from axis_common.middleware import (
    ErrorMiddleware,
    RequestIdMiddleware,
    REQUEST_ID_HEADER,
)
from axis_common.settings import AxisBaseSettings, cors_origins_from
from axis_common.security import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from axis_common.db import DatabasePool
from axis_common.health import make_health_router
from axis_common.observability import init_observability

__all__ = [
    "AxisBaseSettings",
    "AxisHTTPException",
    "DatabasePool",
    "ErrorMiddleware",
    "ErrorPayload",
    "InvalidTokenError",
    "REQUEST_ID_HEADER",
    "RequestIdMiddleware",
    "TokenExpiredError",
    "bind_request_context",
    "configure_logging",
    "cors_origins_from",
    "create_access_token",
    "decode_token",
    "get_logger",
    "hash_password",
    "init_observability",
    "make_health_router",
    "verify_password",
]
