"""Anthropic async client, lazily constructed once per process.

If ANTHROPIC_API_KEY is unset or looks like a placeholder, returns None and
the planner falls back to stub responses. This keeps local dev usable without
API credentials while still driving the full end-to-end machinery.
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

from app.config import settings

_client: AsyncAnthropic | None = None


def _is_real_key(key: str) -> bool:
    if not key:
        return False
    if "your_production" in key or "replace" in key.lower():
        return False
    return key.startswith("sk-ant-")


def get_client() -> AsyncAnthropic | None:
    global _client
    if _client is None and _is_real_key(settings.anthropic_api_key):
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client
