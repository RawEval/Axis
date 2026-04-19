"""Resolve a 'since' input ('today', '1h', ISO string, ...) to an absolute
UTC datetime in the user's local timezone.

Used by activity.query and every connector recent_activity capability so
'today' means 'today in the user's wall-clock', not 'today in DB UTC'.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_RELATIVE = {
    "1h": timedelta(hours=1),
    "1 hour": timedelta(hours=1),
    "last hour": timedelta(hours=1),
    "24h": timedelta(days=1),
    "1d": timedelta(days=1),
    "1 day": timedelta(days=1),
    "7d": timedelta(days=7),
    "1 week": timedelta(days=7),
    "this week": timedelta(days=7),
    "30d": timedelta(days=30),
    "1 month": timedelta(days=30),
    "this month": timedelta(days=30),
}


def resolve_since(value: str, user_tz: ZoneInfo) -> datetime:
    s = (value or "").strip().lower()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(user_tz)

    if s == "today":
        local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(timezone.utc)

    if s == "yesterday":
        local_midnight_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return (local_midnight_today - timedelta(days=1)).astimezone(timezone.utc)

    if s in _RELATIVE:
        return now_utc - _RELATIVE[s]

    # Try ISO 8601 (with or without timezone)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=user_tz)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    # Fallback: treat as 'today'
    local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc)
