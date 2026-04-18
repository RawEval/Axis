"""Axis Memory Service — three-tier memory graph (spec §6.4).

Tiers:
  - episodic    Qdrant per-user collection (vector + recency rerank)
  - semantic    Neo4j entity graph (substring match + 2-hop neighbors)
  - procedural  Postgres ``users.settings`` (how the user likes things done)

Routes:
  POST /retrieve             three-tier hybrid retrieval
  POST /episodic             write one episodic turn
  POST /semantic/entity      upsert one entity
  POST /semantic/relate      upsert an edge
  PATCH /procedural          merge keys into users.settings
  GET  /stats/{user_id}      counts per tier (for the web inspector)
  DELETE /episodic/{pid}     drop an episodic point
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from axis_common import (
    ErrorMiddleware,
    RequestIdMiddleware,
    configure_logging,
    cors_origins_from,
    get_logger,
    make_health_router,
)
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.db import db
from app.graph.client import (
    close_driver,
    count_entities,
    delete_entity,
    relate,
    upsert_entity,
)
from app.tiers import episodic as episodic_tier
from app.tiers import procedural as procedural_tier
from app.tiers import semantic as semantic_tier
from app.vector.client import (
    count_episodic,
    delete_episodic,
    upsert_episodic,
)
from app.vector.embed import provider_label

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("memory_service_startup", embeddings=provider_label())
    try:
        yield
    finally:
        await close_driver()
        await db.close()
        logger.info("memory_service_shutdown")


app = FastAPI(
    title="Axis Memory Service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestIdMiddleware)

from app.graph.client import get_driver as _get_neo4j_driver

app.include_router(make_health_router(
    service=settings.service_name,
    db=db,
    qdrant_url=settings.qdrant_url,
    neo4j_driver=_get_neo4j_driver(),
))


# ---------------- Retrieve ----------------


class RetrieveRequest(BaseModel):
    user_id: str
    query: str
    project_id: str | None = None
    tier: str | None = None  # 'episodic' | 'semantic' | 'procedural' | None=all
    limit: int = Field(default=10, ge=1, le=50)


class MemoryRow(BaseModel):
    id: str
    tier: str
    type: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.post("/retrieve", response_model=list[MemoryRow])
async def retrieve(req: RetrieveRequest) -> list[MemoryRow]:
    results: list[dict[str, Any]] = []

    if req.tier in (None, "any", "episodic"):
        try:
            rows = await episodic_tier.retrieve(
                user_id=req.user_id,
                query=req.query,
                project_id=req.project_id,
                limit=req.limit,
            )
            results.extend(rows)
        except Exception as e:  # noqa: BLE001
            logger.warning("episodic_retrieve_failed", error=str(e))

    if req.tier in (None, "any", "semantic"):
        try:
            rows = await semantic_tier.retrieve(
                user_id=req.user_id, query=req.query, limit=req.limit
            )
            results.extend(rows)
        except Exception as e:  # noqa: BLE001
            logger.warning("semantic_retrieve_failed", error=str(e))

    if req.tier in (None, "any", "procedural"):
        try:
            rows = await procedural_tier.retrieve(
                user_id=req.user_id, query=req.query, limit=req.limit
            )
            results.extend(rows)
        except Exception as e:  # noqa: BLE001
            logger.warning("procedural_retrieve_failed", error=str(e))

    # Global rerank: episodic uses vector+recency (<=1), semantic/procedural
    # are already in the same range. A proper hybrid would normalize per
    # tier but for Phase 1 score-sort is good enough.
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    clipped = results[: req.limit]
    logger.info(
        "memory_retrieved",
        user_id=req.user_id,
        tier=req.tier or "all",
        returned=len(clipped),
    )
    return [MemoryRow(**r) for r in clipped]


# ---------------- Episodic write ----------------


class EpisodicWriteRequest(BaseModel):
    user_id: str
    project_id: str | None = None
    role: str = Field(..., pattern="^(user|assistant|tool|note)$")
    content: str
    action_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class EpisodicWriteResponse(BaseModel):
    id: str
    tier: str = "episodic"


@app.post("/episodic", response_model=EpisodicWriteResponse)
async def write_episodic(req: EpisodicWriteRequest) -> EpisodicWriteResponse:
    if not req.content.strip():
        raise HTTPException(400, "content is empty")
    try:
        point_id = await upsert_episodic(
            user_id=req.user_id,
            project_id=req.project_id,
            role=req.role,
            content=req.content,
            action_id=req.action_id,
            tags=req.tags,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("episodic_write_failed", error=str(e))
        raise HTTPException(500, f"episodic write failed: {e}") from e
    return EpisodicWriteResponse(id=point_id)


@app.delete("/episodic/{point_id}")
async def delete_episodic_row(
    point_id: str, user_id: str = Query(...)
) -> dict[str, Any]:
    await delete_episodic(user_id=user_id, point_id=point_id)
    return {"ok": True, "id": point_id}


# ---------------- Semantic write ----------------


class EntityUpsertRequest(BaseModel):
    user_id: str
    name: str
    kind: str = Field(..., pattern="^(person|project|topic|doc|tool)$")
    attrs: dict[str, Any] = Field(default_factory=dict)


@app.post("/semantic/entity")
async def write_entity(req: EntityUpsertRequest) -> dict[str, Any]:
    row = await upsert_entity(
        user_id=req.user_id, name=req.name, kind=req.kind, attrs=req.attrs
    )
    return {"ok": True, "entity": row}


class RelateRequest(BaseModel):
    user_id: str
    src_name: str
    src_kind: str
    dst_name: str
    dst_kind: str
    label: str = "mentions"
    weight: float = 1.0


@app.post("/semantic/relate")
async def write_edge(req: RelateRequest) -> dict[str, Any]:
    await relate(
        user_id=req.user_id,
        src_name=req.src_name,
        src_kind=req.src_kind,
        dst_name=req.dst_name,
        dst_kind=req.dst_kind,
        label=req.label,
        weight=req.weight,
    )
    return {"ok": True}


@app.delete("/semantic/entity")
async def drop_entity(
    user_id: str = Query(...),
    name: str = Query(...),
    kind: str = Query(...),
) -> dict[str, Any]:
    ok = await delete_entity(user_id=user_id, name=name, kind=kind)
    return {"ok": ok}


# ---------------- Procedural write ----------------


class ProceduralPatchRequest(BaseModel):
    user_id: str
    keys: dict[str, Any]


@app.patch("/procedural")
async def patch_procedural(req: ProceduralPatchRequest) -> dict[str, Any]:
    async with db.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET settings = COALESCE(settings, '{}'::jsonb) || $2::jsonb
            WHERE id = $1::uuid
            """,
            req.user_id,
            json.dumps(req.keys),
        )
    return {"ok": True, "merged_keys": list(req.keys.keys())}


# ---------------- Stats ----------------


@app.get("/stats/{user_id}")
async def stats(user_id: str) -> dict[str, Any]:
    episodic = await count_episodic(user_id)
    try:
        semantic = await count_entities(user_id)
    except Exception:  # noqa: BLE001
        semantic = 0
    return {
        "user_id": user_id,
        "episodic_count": episodic,
        "semantic_count": semantic,
        "embedding_provider": provider_label(),
    }
