"""Correlation ID middleware.

Generates a UUID if X-Request-ID is absent, binds it to structlog contextvars,
and echoes it back on every response. Downstream httpx calls should forward
it via `axis_common.http.forward_request_id_headers(...)`.
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from axis_common.logging import bind_request_context, clear_request_context

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = rid
        bind_request_context(request_id=rid)
        try:
            response = await call_next(request)
        finally:
            clear_request_context()
        response.headers[REQUEST_ID_HEADER] = rid
        return response
