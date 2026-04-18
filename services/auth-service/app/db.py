"""Postgres pool for auth-service. Thin wrapper over axis_common.DatabasePool."""
from __future__ import annotations

from axis_common import DatabasePool

from app.config import settings

db = DatabasePool(
    dsn=settings.postgres_url,
    min_size=settings.postgres_pool_min,
    max_size=settings.postgres_pool_max,
)
