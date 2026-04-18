"""WebSocket endpoint — live agent progress via Redis pub/sub fan-out.

Auth: JWT passed as ``?token=`` query param (WebSockets can't carry
Authorization headers from the browser). On connect we subscribe to
``axis:events:{user_id}`` where the supervisor publishes task/step/
permission events, and forward each message to the client as JSON.

Bidirectional payload (client → server):
  - ``{"type":"ping"}``  heartbeat → server replies with ``pong``

Server → client payload: whatever the supervisor published, plus a
``hello`` envelope on first connect.
"""
from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from axis_common import InvalidTokenError, TokenExpiredError, decode_token, get_logger
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.config import settings

router = APIRouter()
logger = get_logger(__name__)


def _user_channel(user_id: str) -> str:
    return f"axis:events:{user_id}"


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = Query(default=None)) -> None:
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_token(
            token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
        )
    except (TokenExpiredError, InvalidTokenError) as e:
        logger.info("ws_reject_invalid_token", error=str(e))
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("sub")
    if not user_id:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    await ws.send_json({"type": "hello", "user_id": user_id})

    # Dedicated Redis connection per socket — pub/sub is sticky.
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(_user_channel(user_id))
    logger.info("ws_subscribed", user_id=user_id)

    async def _pump_redis_to_ws() -> None:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                parsed = json.loads(data)
            except (ValueError, TypeError):
                parsed = {"type": "raw", "data": str(data)}
            await ws.send_json(parsed)

    async def _pump_ws_client() -> None:
        while True:
            msg = await ws.receive_text()
            try:
                data = json.loads(msg)
            except (ValueError, TypeError):
                continue
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    pump_redis = asyncio.create_task(_pump_redis_to_ws())
    pump_client = asyncio.create_task(_pump_ws_client())

    try:
        done, pending = await asyncio.wait(
            {pump_redis, pump_client},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception() if not task.cancelled() else None
            if exc and not isinstance(exc, WebSocketDisconnect):
                logger.warning("ws_pump_error", error=str(exc))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe(_user_channel(user_id))
            await pubsub.close()
            await redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass
        logger.info("ws_disconnected", user_id=user_id)
