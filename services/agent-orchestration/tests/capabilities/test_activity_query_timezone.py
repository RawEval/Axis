"""Regression test for the timezone defect in activity.query.

Before this fix, activity.query used `NOW() - INTERVAL '1 day'` (DB UTC),
so a user in IST (+5:30) querying 'today' near midnight UTC would either
miss events from their actual 'today' or include events from yesterday.
After the fix, 'today' is computed in the user's local timezone.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from freezegun import freeze_time


async def _seed_user(db_pool, user_id, tz):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, timezone)
               VALUES ($1, $2, 'placeholder', $3)""",
            user_id, f"{user_id}@test.local", tz,
        )


async def _cleanup(db_pool, user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM activity_events WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)


@freeze_time("2026-04-19T17:30:00+00:00")  # 11pm IST on Apr 19
async def test_today_in_kolkata_filters_by_user_local_midnight(db_pool, monkeypatch):
    """At 11pm IST on Apr 19 (= 17:30 UTC), 'today' for a Kolkata user
    started at 00:00 IST Apr 19 = 18:30 UTC Apr 18.

    - Event at 18:25 UTC Apr 18 (= 11:55pm IST Apr 18) → YESTERDAY in IST → EXCLUDED
    - Event at 18:35 UTC Apr 18 (= 12:05am IST Apr 19) → TODAY in IST → INCLUDED
    """
    user_id = uuid4()
    await _seed_user(db_pool, user_id, "Asia/Kolkata")
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO activity_events
                   (user_id, source, event_type, external_id, title, occurred_at, raw_ref)
                   VALUES
                     ($1, 'notion', 'page_edited', 'old', 'Yesterday IST',
                      '2026-04-18T18:25:00+00:00', '{}'::jsonb),
                     ($1, 'notion', 'page_edited', 'new', 'Today IST',
                      '2026-04-18T18:35:00+00:00', '{}'::jsonb)""",
                user_id,
            )

        from app import db as db_module
        monkeypatch.setattr(db_module.db, "_pool", db_pool)

        from app.plugins.internal.activity import CAPABILITY as ACTIVITY_QUERY
        result = await ACTIVITY_QUERY(
            user_id=str(user_id),
            project_id=None,
            org_id=None,
            inputs={"since": "today", "source": "notion"},
        )
        titles = {e["title"] for e in result.content}
        assert titles == {"Today IST"}, f"got {titles}"
    finally:
        await _cleanup(db_pool, user_id)


@freeze_time("2026-04-19T17:30:00+00:00")
async def test_today_in_utc_uses_utc_midnight(db_pool, monkeypatch):
    """Sanity: a UTC user's 'today' starts at 00:00 UTC. Events from earlier
    UTC-day are excluded."""
    user_id = uuid4()
    await _seed_user(db_pool, user_id, "UTC")
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO activity_events
                   (user_id, source, event_type, external_id, title, occurred_at, raw_ref)
                   VALUES
                     ($1, 'notion', 'page_edited', 'before', 'Yesterday UTC',
                      '2026-04-18T23:59:00+00:00', '{}'::jsonb),
                     ($1, 'notion', 'page_edited', 'after', 'Today UTC',
                      '2026-04-19T00:01:00+00:00', '{}'::jsonb)""",
                user_id,
            )

        from app import db as db_module
        monkeypatch.setattr(db_module.db, "_pool", db_pool)

        from app.plugins.internal.activity import CAPABILITY as ACTIVITY_QUERY
        result = await ACTIVITY_QUERY(
            user_id=str(user_id),
            project_id=None,
            org_id=None,
            inputs={"since": "today", "source": "notion"},
        )
        titles = {e["title"] for e in result.content}
        assert titles == {"Today UTC"}, f"got {titles}"
    finally:
        await _cleanup(db_pool, user_id)
