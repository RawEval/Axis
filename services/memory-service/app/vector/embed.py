"""Embedding client — Voyage when configured, deterministic fallback otherwise.

We default to Voyage because their ``voyage-3`` retrieval model is the
per-token cost/quality sweet spot and they offer a generous free tier for
development. Swap via ``embedding_provider`` in Settings when we need
something else (Anthropic's embeddings, OpenAI, etc.).

Fallback path: a deterministic hash-based pseudo-embedding. It is *not*
semantically meaningful — a follow-up prompt asking about "pricing" will
not retrieve an earlier turn that mentioned "pricing" unless the token
sequences literally overlap. The fallback exists so local dev and CI
exercise the full upsert / retrieve / score path without a network call.
Production deploys always use Voyage.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import re
from typing import Any

import httpx
from axis_common import get_logger

from app.config import settings

logger = get_logger(__name__)

VOYAGE_EMBED_URL = "https://api.voyageai.com/v1/embeddings"
EMBED_DIM = 1024
# Voyage free tier is ~3 RPM on voyage-3. Retry 429s with exponential
# backoff before falling back to the hash stub — mixing real and stub
# vectors in one collection degrades retrieval.
VOYAGE_MAX_RETRIES = 3
VOYAGE_BACKOFF_SEC = 2.0


def _has_voyage_key() -> bool:
    key = (settings.voyage_api_key or "").strip()
    if not key:
        return False
    low = key.lower()
    if any(low.startswith(p) for p in ("replace", "change", "stub")):
        return False
    # Real voyage keys are ``pa-<long random>``; ``pa-replace-me`` is the
    # common placeholder shape and fails cleanly.
    if "replace" in low or "change" in low:
        return False
    return True


async def embed_text(text: str) -> list[float]:
    """Return a ``EMBED_DIM``-length float vector for a single string."""
    if not text or not text.strip():
        return [0.0] * EMBED_DIM
    if _has_voyage_key():
        try:
            return await _embed_voyage(text)
        except Exception as e:  # noqa: BLE001
            logger.warning("voyage_embed_failed_falling_back", error=str(e))
    return _deterministic_embed(text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if _has_voyage_key():
        try:
            return await _embed_voyage_batch(texts)
        except Exception as e:  # noqa: BLE001
            logger.warning("voyage_embed_batch_failed_falling_back", error=str(e))
    return [_deterministic_embed(t) for t in texts]


# ---------- Voyage ----------------------------------------------------------


async def _embed_voyage(text: str) -> list[float]:
    vectors = await _embed_voyage_batch([text])
    return vectors[0]


async def _embed_voyage_batch(texts: list[str]) -> list[list[float]]:
    headers = {
        "Authorization": f"Bearer {settings.voyage_api_key}",
        "Content-Type": "application/json",
    }
    backoff = VOYAGE_BACKOFF_SEC
    async with httpx.AsyncClient(timeout=20.0) as client:
        for attempt in range(VOYAGE_MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    VOYAGE_EMBED_URL,
                    headers=headers,
                    json={
                        "input": texts,
                        "model": settings.voyage_model,
                        "input_type": "document",
                    },
                )
                resp.raise_for_status()
                body = resp.json()
                break
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429 and attempt < VOYAGE_MAX_RETRIES:
                    logger.warning(
                        "voyage_rate_limited_backing_off",
                        attempt=attempt + 1,
                        sleep_sec=backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
    data = body.get("data") or []
    vectors = [item["embedding"] for item in data]
    return [_normalize(v) for v in vectors]


# ---------- Deterministic fallback ------------------------------------------


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _deterministic_embed(text: str) -> list[float]:
    """Hash tokens into ``EMBED_DIM`` buckets and L2-normalize.

    Tokens that literally repeat between two strings end up in the same
    buckets, so short overlapping strings score higher on cosine than
    disjoint ones. It's a keyword-match baseline dressed up as a vector —
    enough to smoke-test the plumbing, not enough to ship.
    """
    buckets = [0.0] * EMBED_DIM
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        buckets[0] = 1.0
        return buckets
    for tok in tokens:
        h = hashlib.sha256(tok.encode()).digest()
        # two overlapping buckets per token gives slightly smoother
        # similarity than a single-bucket hash
        a = int.from_bytes(h[:4], "big") % EMBED_DIM
        b = int.from_bytes(h[4:8], "big") % EMBED_DIM
        buckets[a] += 1.0
        buckets[b] += 0.5
    return _normalize(buckets)


def _normalize(v: list[float]) -> list[float]:
    if len(v) != EMBED_DIM:
        # pad or truncate so every caller gets consistent dims
        if len(v) < EMBED_DIM:
            v = v + [0.0] * (EMBED_DIM - len(v))
        else:
            v = v[:EMBED_DIM]
    norm = math.sqrt(sum(x * x for x in v))
    if norm <= 0:
        return v
    return [x / norm for x in v]


def provider_label() -> str:
    return "voyage" if _has_voyage_key() else "stub-hash"
