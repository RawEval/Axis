"""asyncpg pool helper.

Instantiate once per service. The ``DatabasePool`` class gives you:

    pool = DatabasePool(dsn=..., min_size=..., max_size=...)
    await pool.connect()   # in lifespan startup
    async with pool.acquire() as conn:
        ...
    await pool.close()     # in lifespan shutdown
    ok = await pool.is_healthy()

It also publishes the underlying asyncpg.Pool as ``pool.raw`` so repositories
that want the native object can grab it without wrapping.
"""
from __future__ import annotations

import asyncpg

from axis_common.logging import get_logger

logger = get_logger(__name__)


class DatabasePool:
    def __init__(self, dsn: str, *, min_size: int = 2, max_size: int = 20, command_timeout: float = 10) -> None:
        self._dsn = dsn
        self._min = min_size
        self._max = max_size
        self._command_timeout = command_timeout
        self._pool: asyncpg.Pool | None = None

    @property
    def raw(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("pool not initialized — call connect() first")
        return self._pool

    async def connect(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min,
                max_size=self._max,
                command_timeout=self._command_timeout,
            )
            logger.info("db_pool_connected", min=self._min, max=self._max)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("db_pool_closed")

    def acquire(self):
        return self.raw.acquire()

    async def is_healthy(self) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                val = await conn.fetchval("SELECT 1")
            return val == 1
        except Exception as e:  # noqa: BLE001
            logger.warning("db_health_check_failed", error=str(e))
            return False
