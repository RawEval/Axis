"""Adaptive cadence scheduler — replaces per-source poll loops.

For each (user, source) pair, computes the right poll interval based on:
- recent user attention (placeholder: always None until a query-log lands)
- recent activity (events ingested in the last 24h)
- error state (exponential backoff if consecutive_fails >= 3)

One scheduler_loop runs every 30s, iterating every (registered_source ×
connected_user) pair, dispatching freshen() only when the per-pair
interval has elapsed since last_synced_at.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.sync import registry as sync_registry

logger = get_logger(__name__)


class CadenceState(NamedTuple):
    interval_sec: int
    label: str


_BACKOFF_SECS = [120, 240, 480, 960, 1800]  # exponential, capped at 30 min


def compute_cadence_state(
    *,
    last_user_query_at: datetime | None,
    last_event_at: datetime | None,
    consecutive_fails: int,
) -> CadenceState:
    """Decide poll interval for a single (user, source) pair."""
    if consecutive_fails >= 3:
        idx = min(consecutive_fails - 3, len(_BACKOFF_SECS) - 1)
        return CadenceState(interval_sec=_BACKOFF_SECS[idx], label="erroring")

    now = datetime.now(timezone.utc)
    is_active = (
        (last_user_query_at is not None and (now - last_user_query_at) < timedelta(hours=1))
        or (last_event_at is not None and (now - last_event_at) < timedelta(hours=24))
    )
    if is_active:
        return CadenceState(interval_sec=60, label="active")
    return CadenceState(interval_sec=300, label="idle")


async def scheduler_tick(*, _pool: object = None) -> dict[str, int]:
    """One full scheduler pass — iterate every registered source and every
    connected user. Returns counters for observability.

    `_pool` is for tests — defaults to the global db.raw.
    """
    pool = _pool or db.raw
    state_repo = ConnectorSyncStateRepository(pool)
    conn_repo = ConnectorsRepository(pool)

    dispatched = 0
    skipped = 0
    crashed = 0

    for source in sync_registry.all_sources():
        worker = sync_registry.get(source)
        if worker is None:
            continue
        connectors = await conn_repo.list_connected(tool=source)
        user_ids = {str(r["user_id"]) for r in connectors}

        for uid_str in user_ids:
            uid = UUID(uid_str)
            state = await state_repo.get(uid, source) or {}
            cadence = compute_cadence_state(
                last_user_query_at=None,  # TODO: query-log table
                last_event_at=state.get("last_event_at"),
                consecutive_fails=state.get("consecutive_fails", 0),
            )

            now = datetime.now(timezone.utc)
            last = state.get("last_synced_at")
            elapsed = (now - last).total_seconds() if last is not None else float("inf")
            if elapsed < cadence.interval_sec:
                skipped += 1
                continue

            try:
                await worker.freshen(uid)
                dispatched += 1
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "scheduler_freshen_crashed",
                    user_id=uid_str, source=source, error=str(e),
                )
                crashed += 1

    return {"dispatched": dispatched, "skipped": skipped, "crashed": crashed}


async def scheduler_loop(interval_sec: int = 30) -> None:
    """Master scheduler loop — runs every 30s and dispatches per-source ticks."""
    logger.info("scheduler_loop_started", interval_sec=interval_sec)
    while True:
        try:
            counts = await scheduler_tick()
            if counts["dispatched"] > 0 or counts["crashed"] > 0:
                logger.info("scheduler_tick", **counts)
        except Exception as e:  # noqa: BLE001
            logger.error("scheduler_loop_tick_crashed", error=str(e))
        await asyncio.sleep(interval_sec)
