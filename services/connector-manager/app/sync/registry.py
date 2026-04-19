"""In-process registry of SyncWorker instances, keyed by source.

Workers self-register at import time (each worker module ends with
`registry.register(<Worker>())`). Routes look workers up here.
"""
from __future__ import annotations

from app.sync.base import SyncWorker

_workers: dict[str, SyncWorker] = {}


def register(worker: SyncWorker) -> None:
    _workers[worker.source] = worker


def get(source: str) -> SyncWorker | None:
    return _workers.get(source)


def all_sources() -> list[str]:
    return sorted(_workers.keys())
