"""Structlog configuration for Axis services.

All services emit JSON logs in non-dev environments, colorized console logs
in dev. Correlation IDs flow through via contextvars bound by RequestIdMiddleware.
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def _contextvars_processor(_: Any, __: str, event_dict: dict) -> dict:
    rid = _request_id_var.get()
    uid = _user_id_var.get()
    if rid is not None:
        event_dict["request_id"] = rid
    if uid is not None:
        event_dict["user_id"] = uid
    return event_dict


def configure_logging(*, service: str, level: str = "info", json_output: bool | None = None) -> None:
    """Configure structlog for the current process.

    Call once at service startup.

    Args:
        service: the service name (`axis-auth`, `axis-api-gateway`, ...)
        level: log level name (debug/info/warning/error)
        json_output: force JSON (prod) or console (dev). If None, auto-detects
            from ENVIRONMENT env var.
    """
    import os

    env = os.environ.get("ENVIRONMENT", "dev").lower()
    if json_output is None:
        json_output = env not in ("dev", "development", "test")

    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        _contextvars_processor,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind service name as a permanent key
    structlog.contextvars.bind_contextvars(service=service)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    return structlog.get_logger(name)


def bind_request_context(*, request_id: str | None = None, user_id: str | None = None) -> None:
    if request_id is not None:
        _request_id_var.set(request_id)
    if user_id is not None:
        _user_id_var.set(user_id)


def clear_request_context() -> None:
    _request_id_var.set(None)
    _user_id_var.set(None)
