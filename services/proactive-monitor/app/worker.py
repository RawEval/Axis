"""Celery worker for proactive signal processing (spec §6.3)."""
from __future__ import annotations

import os

from celery import Celery

app = Celery(
    "axis-proactive-monitor",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
app.conf.task_routes = {"axis.proactive.*": {"queue": "proactive"}}


@app.task(name="axis.proactive.scan_user")
def scan_user(user_id: str) -> dict:
    """Scan all connected tools for a user and emit candidate surfaces."""
    # TODO: pull recent activity from vector store, score against relevance profile
    return {"user_id": user_id, "surfaces": []}


@app.task(name="axis.proactive.morning_brief")
def morning_brief(user_id: str) -> dict:
    """Build the daily digest for a user."""
    return {"user_id": user_id, "digest": []}
