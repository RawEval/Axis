"""Shared helpers for downstream HTTP clients."""
from __future__ import annotations

from typing import Any

import httpx
from axis_common import get_logger
from axis_common.middleware.request_id import REQUEST_ID_HEADER
from fastapi import HTTPException, Request

logger = get_logger(__name__)


def propagate_headers(
    request: Request | None = None, extra: dict[str, str] | None = None
) -> dict[str, str]:
    """Build a header dict with X-Request-ID forwarded from the current request."""
    headers = dict(extra or {})
    if request is not None:
        rid = getattr(request.state, "request_id", None)
        if rid:
            headers[REQUEST_ID_HEADER] = rid
    return headers


async def forward(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json: Any | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """Call a downstream service and surface its status faithfully.

    Returns parsed JSON (dict or list). Raises HTTPException on any failure
    with the downstream status code preserved.
    """
    try:
        resp = await client.request(method, url, json=json, headers=headers, params=params)
    except httpx.TimeoutException as e:
        logger.warning("downstream_timeout", url=url, method=method)
        raise HTTPException(504, f"downstream timeout: {url}") from e
    except httpx.RequestError as e:
        logger.warning("downstream_unreachable", url=url, method=method, error=str(e))
        raise HTTPException(502, f"downstream unreachable: {url}") from e

    if resp.status_code >= 400:
        detail: Any
        try:
            body = resp.json()
            detail = body.get("detail", body) if isinstance(body, dict) else body
        except ValueError:
            detail = resp.text
        raise HTTPException(resp.status_code, detail)

    if resp.status_code == 204 or not resp.content:
        return {}
    return resp.json()
