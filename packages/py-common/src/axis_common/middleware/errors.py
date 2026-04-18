"""Global error middleware.

Catches anything unhandled, logs with stack trace + request_id, and returns
a sanitized JSON 500. Never leaks internals to the client.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from axis_common.logging import get_logger

logger = get_logger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as e:  # noqa: BLE001 — we really do want to catch all
            logger.error(
                "unhandled_error",
                path=request.url.path,
                method=request.method,
                exc_info=e,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "internal server error"},
            )
