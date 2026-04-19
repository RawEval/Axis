from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from app.util.since import resolve_since


@freeze_time("2026-04-19T17:30:00+00:00")
def test_today_in_kolkata_is_midnight_local_in_utc():
    # 11pm IST on Apr 19 = 17:30 UTC. "Today" started 00:00 IST Apr 19 = 18:30 UTC on Apr 18.
    result = resolve_since("today", ZoneInfo("Asia/Kolkata"))
    assert result == datetime(2026, 4, 18, 18, 30, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
def test_today_in_utc_is_midnight_utc():
    result = resolve_since("today", ZoneInfo("UTC"))
    assert result == datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
def test_yesterday_in_pt_starts_at_local_midnight_yesterday():
    # PT = UTC-7 on this date. "Yesterday" = 00:00 PT Apr 18 = 07:00 UTC Apr 18
    result = resolve_since("yesterday", ZoneInfo("America/Los_Angeles"))
    assert result == datetime(2026, 4, 18, 7, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-04-19T18:30:00+00:00")
@pytest.mark.parametrize("phrase,hours_ago", [
    ("1h", 1), ("1 hour", 1), ("last hour", 1),
    ("24h", 24), ("1d", 24), ("1 day", 24),
    ("7d", 24 * 7), ("1 week", 24 * 7),
])
def test_relative_phrases_are_tz_independent(phrase, hours_ago):
    result_utc = resolve_since(phrase, ZoneInfo("UTC"))
    result_kol = resolve_since(phrase, ZoneInfo("Asia/Kolkata"))
    assert result_utc == result_kol


def test_iso_string_passthrough():
    result = resolve_since("2026-04-15T10:00:00+00:00", ZoneInfo("UTC"))
    assert result == datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
