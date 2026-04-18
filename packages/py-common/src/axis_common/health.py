"""Shared health + readiness router.

Usage:

    app.include_router(make_health_router(
        service="memory-service",
        db=db_pool,
        redis_url="redis://localhost:6379/0",
        qdrant_url="http://localhost:6333",
        neo4j_driver=neo4j_driver,
    ))

Every probe is optional — pass only the stores the service uses. /readyz
reports per-store status and returns 503 if any probe fails.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Response, status

if TYPE_CHECKING:
    from axis_common.db import DatabasePool


def make_health_router(
    *,
    service: str,
    db: "DatabasePool | None" = None,
    redis_url: str = "",
    qdrant_url: str = "",
    neo4j_driver: Any = None,
) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": service}

    @router.get("/readyz", include_in_schema=False)
    async def readyz(response: Response) -> dict[str, object]:
        checks: dict[str, object] = {"service": service, "status": "ready"}
        all_ok = True

        if db is not None:
            ok = await db.is_healthy()
            checks["db"] = "ok" if ok else "down"
            if not ok:
                all_ok = False

        if redis_url:
            checks["redis"] = await _probe_redis(redis_url)
            if checks["redis"] != "ok":
                all_ok = False

        if qdrant_url:
            checks["qdrant"] = await _probe_qdrant(qdrant_url)
            if checks["qdrant"] != "ok":
                all_ok = False

        if neo4j_driver is not None:
            checks["neo4j"] = await _probe_neo4j(neo4j_driver)
            if checks["neo4j"] != "ok":
                all_ok = False

        if not all_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            checks["status"] = "not_ready"
        return checks

    return router


async def _probe_redis(url: str) -> str:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(url, decode_responses=True)
        try:
            pong = await client.ping()
            return "ok" if pong else "down"
        finally:
            await client.aclose()
    except Exception:  # noqa: BLE001
        return "down"


async def _probe_qdrant(url: str) -> str:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{url}/collections")
            return "ok" if resp.status_code < 400 else "down"
    except Exception:  # noqa: BLE001
        return "down"


async def _probe_neo4j(driver: Any) -> str:
    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            return "ok" if record and record["n"] == 1 else "down"
    except Exception:  # noqa: BLE001
        return "down"
