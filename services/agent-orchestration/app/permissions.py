"""Permission resolver + blocking gate (ADR 006).

Every tool_use block goes through ``check_and_gate`` before the capability
runs. The resolver walks ``permission_grants`` for the user × project ×
capability × action tuple; ``auto``-permission capabilities pass through
automatically, ``ask`` waits for user approval via an inline interactive
event, ``always_gate`` always waits even when a prior grant exists for
the same scope.

Blocking model: when the gate fires, we:
  1. Insert a ``permission_events`` row with event_type='requested'
  2. Publish a ``permission.request`` event to the user's Redis channel
  3. Create an asyncio.Event keyed on the pending_id
  4. Await that event with a timeout (default 120s)
  5. Either the /permissions/resolve endpoint sets the event with a
     GateDecision, or we time out and deny
  6. If granted with a durable lifetime (project/24h/forever) we also
     persist a permission_grants row so future tool calls short-circuit

This is in-process only for Phase 1 — if multiple agent-orchestration
replicas run behind a load balancer, pending events must move to Redis
hashes. Single-instance deploys work today.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from axis_common import get_logger

from app.capabilities.base import Capability
from app.db import db
from app.events import publish as publish_event

logger = get_logger(__name__)

PERMISSION_TIMEOUT_SEC = 120.0


@dataclass
class GateDecision:
    granted: bool
    reason: str
    decision_source: str   # 'auto' | 'prior_grant' | 'user' | 'timeout' | 'denied' | 'auto_deny'
    pending_id: str | None = None


# pending_id → asyncio.Event, with the decision stored on the event via
# .decision attribute when set.
_PENDING: dict[str, asyncio.Event] = {}
_DECISIONS: dict[str, dict[str, Any]] = {}


async def check_and_gate(
    *,
    user_id: str,
    project_id: str | None,
    capability: Capability,
    inputs: dict[str, Any],
) -> GateDecision:
    """Return a GateDecision for a single tool_use dispatch.

    Callers must honor ``granted`` — never run the capability when False.
    ``reason`` is suitable for forwarding back to Claude as the tool_result
    error text.
    """
    perm = getattr(capability, "default_permission", "ask")
    action = getattr(capability, "scope", "read")

    if perm == "auto":
        return GateDecision(
            granted=True, reason="auto-granted", decision_source="auto"
        )

    if perm != "always_gate":
        prior = await _find_prior_grant(
            user_id=user_id,
            project_id=project_id,
            capability_name=capability.name,
            action=action,
        )
        if prior is not None:
            if prior["decision"] == "granted":
                return GateDecision(
                    granted=True,
                    reason=f"prior grant ({prior['lifetime']})",
                    decision_source="prior_grant",
                )
            return GateDecision(
                granted=False,
                reason=f"prior denial ({prior['lifetime']})",
                decision_source="denied",
            )

    # Need live approval. Publish a request and wait.
    pending_id = str(uuid.uuid4())
    event = asyncio.Event()
    _PENDING[pending_id] = event

    await _log_permission_event(
        user_id=user_id,
        project_id=project_id,
        capability_name=capability.name,
        action=action,
        event_type="requested",
        context={"pending_id": pending_id, "inputs": inputs},
    )
    await publish_event(
        user_id=user_id,
        project_id=project_id,
        event_type="permission.request",
        payload={
            "pending_id": pending_id,
            "capability": capability.name,
            "action": action,
            "description": getattr(capability, "description", ""),
            "inputs": inputs,
            "timeout_sec": PERMISSION_TIMEOUT_SEC,
        },
    )

    try:
        await asyncio.wait_for(event.wait(), timeout=PERMISSION_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        _PENDING.pop(pending_id, None)
        await _log_permission_event(
            user_id=user_id,
            project_id=project_id,
            capability_name=capability.name,
            action=action,
            event_type="denied",
            context={"pending_id": pending_id, "reason": "timeout"},
        )
        return GateDecision(
            granted=False,
            reason="permission request timed out",
            decision_source="timeout",
            pending_id=pending_id,
        )

    decision = _DECISIONS.pop(pending_id, None)
    _PENDING.pop(pending_id, None)

    if decision is None:
        return GateDecision(
            granted=False,
            reason="permission event set without decision",
            decision_source="auto_deny",
            pending_id=pending_id,
        )

    granted = bool(decision.get("granted"))
    lifetime = decision.get("lifetime") or "session"

    if granted and lifetime != "session":
        await _persist_grant(
            user_id=user_id,
            project_id=project_id,
            capability_name=capability.name,
            action=action,
            lifetime=lifetime,
        )

    await _log_permission_event(
        user_id=user_id,
        project_id=project_id,
        capability_name=capability.name,
        action=action,
        event_type="granted" if granted else "denied",
        context={
            "pending_id": pending_id,
            "lifetime": lifetime,
        },
    )

    return GateDecision(
        granted=granted,
        reason=f"user decision ({lifetime})"
        if granted
        else f"user denied ({lifetime})",
        decision_source="user",
        pending_id=pending_id,
    )


def resolve_pending(
    *, pending_id: str, granted: bool, lifetime: str
) -> bool:
    """Called by POST /permissions/resolve. Returns True if the pending
    request existed and was unblocked, False if already expired/unknown.
    """
    event = _PENDING.get(pending_id)
    if event is None:
        return False
    _DECISIONS[pending_id] = {"granted": granted, "lifetime": lifetime}
    event.set()
    return True


async def _find_prior_grant(
    *, user_id: str, project_id: str | None, capability_name: str, action: str
) -> dict[str, Any] | None:
    async with db.acquire() as conn:
        # Project-scoped grant takes priority over user-wide
        if project_id:
            row = await conn.fetchrow(
                """
                SELECT decision, lifetime, expires_at
                FROM permission_grants
                WHERE user_id = $1::uuid
                  AND project_id = $2::uuid
                  AND capability = $3 AND action = $4
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id,
                project_id,
                capability_name,
                action,
            )
            if row:
                return dict(row)
        row = await conn.fetchrow(
            """
            SELECT decision, lifetime, expires_at
            FROM permission_grants
            WHERE user_id = $1::uuid
              AND project_id IS NULL
              AND capability = $2 AND action = $3
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
            capability_name,
            action,
        )
    return dict(row) if row else None


async def _persist_grant(
    *,
    user_id: str,
    project_id: str | None,
    capability_name: str,
    action: str,
    lifetime: str,
) -> None:
    expires_at: datetime | None = None
    if lifetime == "24h":
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=24)
    async with db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO permission_grants
                (user_id, project_id, capability, action, decision, lifetime, expires_at)
            VALUES ($1::uuid, $2::uuid, $3, $4, 'granted', $5, $6)
            """,
            user_id,
            project_id if lifetime in ("project",) else None,
            capability_name,
            action,
            lifetime,
            expires_at,
        )


async def _log_permission_event(
    *,
    user_id: str,
    project_id: str | None,
    capability_name: str,
    action: str,
    event_type: str,
    context: dict[str, Any],
) -> None:
    try:
        async with db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO permission_events
                    (user_id, project_id, capability, action, event_type, context)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb)
                """,
                user_id,
                project_id,
                capability_name,
                action,
                event_type,
                json.dumps(context),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("permission_event_log_failed", error=str(e))
