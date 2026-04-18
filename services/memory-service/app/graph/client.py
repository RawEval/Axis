"""Neo4j semantic memory — entities + relationships per user.

Each user's subgraph is isolated by a mandatory ``user_id`` property on
every node and relationship. We do not use Neo4j database isolation
because community edition only supports one database — namespacing via
properties is the Phase 1 compromise.

Node shape:
    (:Entity {user_id, name, kind, attrs, updated_at})

Edge shape:
    (:Entity)-[:RELATES_TO {user_id, label, weight, updated_at}]->(:Entity)

``kind`` is one of ``person | project | topic | doc | tool``. ``attrs`` is
a small JSON blob (stringified) for provider-native ids and free-form
tags — Neo4j lets us filter on nested properties but we keep it shallow
because the store is for traversal, not full-text search.
"""
from __future__ import annotations

import json
from typing import Any

from axis_common import get_logger
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings

logger = get_logger(__name__)

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def upsert_entity(
    *,
    user_id: str,
    name: str,
    kind: str,
    attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge on (user_id, name, kind). Safe to call repeatedly per turn."""
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        result = await session.run(
            """
            MERGE (e:Entity {user_id: $user_id, name: $name, kind: $kind})
            ON CREATE SET e.created_at = datetime(), e.attrs = $attrs
            ON MATCH  SET e.updated_at = datetime(), e.attrs = coalesce($attrs, e.attrs)
            RETURN e.user_id AS user_id, e.name AS name, e.kind AS kind,
                   e.attrs AS attrs
            """,
            user_id=user_id,
            name=name,
            kind=kind,
            attrs=json.dumps(attrs or {}),
        )
        record = await result.single()
    return dict(record) if record else {}


async def relate(
    *,
    user_id: str,
    src_name: str,
    src_kind: str,
    dst_name: str,
    dst_kind: str,
    label: str,
    weight: float = 1.0,
) -> None:
    """Upsert a RELATES_TO edge; bumps weight on repeat mentions."""
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        await session.run(
            """
            MERGE (a:Entity {user_id: $user_id, name: $src_name, kind: $src_kind})
            MERGE (b:Entity {user_id: $user_id, name: $dst_name, kind: $dst_kind})
            MERGE (a)-[r:RELATES_TO {user_id: $user_id, label: $label}]->(b)
            ON CREATE SET r.weight = $weight, r.created_at = datetime()
            ON MATCH  SET r.weight = r.weight + $weight, r.updated_at = datetime()
            """,
            user_id=user_id,
            src_name=src_name,
            src_kind=src_kind,
            dst_name=dst_name,
            dst_kind=dst_kind,
            label=label,
            weight=weight,
        )


async def search_entities(
    *, user_id: str, query: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Case-insensitive name substring match, user-scoped."""
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        # ``query`` collides with session.run()'s first positional, so we
        # rename it ``needle`` in the Cypher params.
        result = await session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WHERE toLower(e.name) CONTAINS toLower($needle)
            RETURN e.name AS name, e.kind AS kind, e.attrs AS attrs
            ORDER BY e.updated_at DESC
            LIMIT $limit
            """,
            user_id=user_id,
            needle=query,
            limit=limit,
        )
        rows = [dict(r) async for r in result]
    for r in rows:
        try:
            r["attrs"] = json.loads(r.get("attrs") or "{}")
        except (ValueError, TypeError):
            r["attrs"] = {}
    return rows


async def traverse_neighbors(
    *, user_id: str, name: str, kind: str, depth: int = 2, limit: int = 20
) -> list[dict[str, Any]]:
    """Pull 1–2 hop neighbors of a given entity, user-scoped.

    Uses plain variable-length pattern matching instead of APOC so this
    works on Neo4j community without extra plugins.
    """
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        result = await session.run(
            """
            MATCH (seed:Entity {user_id: $user_id, name: $name, kind: $kind})
            MATCH path = (seed)-[:RELATES_TO*1..2]->(other:Entity {user_id: $user_id})
            WITH other, min(length(path)) AS hops
            RETURN other.name AS name, other.kind AS kind, hops
            ORDER BY hops ASC
            LIMIT $limit
            """,
            user_id=user_id,
            name=name,
            kind=kind,
            limit=limit,
        )
        rows = [dict(r) async for r in result]
    return rows


async def delete_entity(*, user_id: str, name: str, kind: str) -> bool:
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        result = await session.run(
            """
            MATCH (e:Entity {user_id: $user_id, name: $name, kind: $kind})
            DETACH DELETE e
            RETURN count(e) AS deleted
            """,
            user_id=user_id,
            name=name,
            kind=kind,
        )
        record = await result.single()
    return bool(record and record["deleted"] > 0)


async def count_entities(user_id: str) -> int:
    driver = get_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        result = await session.run(
            "MATCH (e:Entity {user_id: $user_id}) RETURN count(e) AS n",
            user_id=user_id,
        )
        record = await result.single()
    return int(record["n"]) if record else 0
