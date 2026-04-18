"""Rate-limiting configuration — Redis-backed token bucket via slowapi.

Per-route limits configurable via Settings:
  RATE_LIMIT_AGENT_RUN   — /agent/run (default 10/min per user)
  RATE_LIMIT_AUTH_LOGIN   — /auth/login (default 5/min per IP)
  RATE_LIMIT_CORRECTIONS  — /eval/corrections (default 20/min per user)
  RATE_LIMIT_DEFAULT      — everything else (default 60/min per user)

The key function picks user_id from the JWT when available, otherwise
falls back to the client IP. This prevents a single compromised or
bot-driven token from exhausting the cluster while still allowing
unauthed routes (login, signup) to rate-limit by IP.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def _key_func(request: Request) -> str:
    """Extract a rate-limit key.

    JWT-authed routes: the user_id is set on the request state by the
    auth dependency BEFORE slowapi checks. For unauthed routes (login,
    signup), we fall back to the client IP.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    storage_uri=settings.rate_limit_storage,
    default_limits=[settings.rate_limit_default],
)
