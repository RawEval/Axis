"""httpx helpers for cross-service calls.

- ``make_client`` returns an AsyncClient with production-sane limits.
- ``forward_request_id_headers`` extracts the correlation header from a
  Starlette Request for downstream propagation.
"""
from __future__ import annotations

import httpx
from starlette.requests import Request

from axis_common.middleware.request_id import REQUEST_ID_HEADER


def make_client(*, timeout_seconds: float, max_connections: int = 100, max_keepalive: int = 20) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout_seconds,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        ),
        http2=False,  # h2 requires the optional dependency; enable once installed
    )


def forward_request_id_headers(request: Request, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    rid = getattr(request.state, "request_id", None)
    if rid:
        headers[REQUEST_ID_HEADER] = rid
    return headers
