"""Qdrant client — per-user episodic memory collections.

Isolation model: every user gets their own collection, named
``{prefix}_episodic_{user_id_hex}``. Cross-user reads are impossible by
construction because the collection name itself encodes the user.
Defense in depth: every search and every payload also carries a
``user_id`` field that we filter on, so a programming bug that mixes
collection names still can't leak rows.

Payload schema (per point):
    user_id: str            the owning user (always filtered)
    project_id: str | None  optional project scope
    role: str               'user' | 'assistant' | 'tool'
    content: str            the text we embedded
    action_id: str | None   link back to agent_actions for provenance
    occurred_at: str        ISO8601
    tags: list[str]         free-form labels
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from axis_common import get_logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from app.config import settings
from app.vector.embed import EMBED_DIM, embed_text

logger = get_logger(__name__)

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        kwargs: dict[str, Any] = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        _client = AsyncQdrantClient(**kwargs)
    return _client


def collection_name(user_id: str) -> str:
    safe = user_id.replace("-", "")
    return f"{settings.qdrant_collection_prefix}_episodic_{safe}"


async def ensure_collection(user_id: str) -> None:
    """Idempotent — create the per-user collection if it doesn't exist."""
    client = get_client()
    name = collection_name(user_id)
    try:
        await client.get_collection(collection_name=name)
        return
    except Exception:  # noqa: BLE001
        pass
    await client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(
            size=EMBED_DIM,
            distance=qm.Distance.COSINE,
        ),
    )
    # Index on user_id so cross-collection accidents still can't leak.
    await client.create_payload_index(
        collection_name=name,
        field_name="user_id",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=name,
        field_name="project_id",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )
    logger.info("qdrant_collection_created", user_id=user_id, name=name)


async def upsert_episodic(
    *,
    user_id: str,
    project_id: str | None,
    role: str,
    content: str,
    action_id: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Embed + upsert one row into the user's episodic collection.

    Returns the Qdrant point id (uuid4) so the caller can link it back.
    """
    await ensure_collection(user_id)
    vector = await embed_text(content)
    point_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "user_id": user_id,
        "project_id": project_id,
        "role": role,
        "content": content,
        "action_id": action_id,
        "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
        "tags": tags or [],
    }
    client = get_client()
    await client.upsert(
        collection_name=collection_name(user_id),
        points=[
            qm.PointStruct(id=point_id, vector=vector, payload=payload)
        ],
    )
    return point_id


async def search_episodic(
    *,
    user_id: str,
    query: str,
    project_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Hybrid defense: user_id both encoded in the collection AND filtered."""
    await ensure_collection(user_id)
    vector = await embed_text(query)
    must: list[qm.FieldCondition] = [
        qm.FieldCondition(key="user_id", match=qm.MatchValue(value=user_id))
    ]
    if project_id:
        must.append(
            qm.FieldCondition(
                key="project_id", match=qm.MatchValue(value=project_id)
            )
        )
    client = get_client()
    # qdrant-client 1.10+ deprecated ``search`` in favour of ``query_points``.
    result = await client.query_points(
        collection_name=collection_name(user_id),
        query=vector,
        limit=limit,
        query_filter=qm.Filter(must=must),
        with_payload=True,
    )
    return [
        {
            "id": str(h.id),
            "score": float(h.score),
            **(h.payload or {}),
        }
        for h in result.points
    ]


async def delete_episodic(*, user_id: str, point_id: str) -> bool:
    client = get_client()
    await client.delete(
        collection_name=collection_name(user_id),
        points_selector=qm.PointIdsList(points=[point_id]),
    )
    return True


async def count_episodic(user_id: str) -> int:
    try:
        client = get_client()
        result = await client.count(
            collection_name=collection_name(user_id), exact=True
        )
        return int(result.count)
    except Exception:  # noqa: BLE001
        return 0
