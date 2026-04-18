"""Postgres pool for api-gateway (read-mostly)."""
from __future__ import annotations

from axis_common import DatabasePool

from app.config import settings

db = DatabasePool(
    dsn=settings.postgres_url,
    min_size=settings.postgres_pool_min,
    max_size=settings.postgres_pool_max,
)


async def get_pool():
    """Compat shim for existing repository constructors."""
    return db.raw
