"""Admin routes — system-wide metrics, connector health, usage analytics.

Accessible to any authenticated user with 'owner' role on any org.
Phase 1: read-only dashboard data. Phase 2: user management, config.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import db
from app.deps import CurrentUser

router = APIRouter()


async def _require_admin(user_id: str) -> None:
    """Check that the user is an owner of at least one org."""
    async with db.acquire() as conn:
        row = await conn.fetchval(
            """
            SELECT 1 FROM organization_members
            WHERE user_id = $1::uuid AND role = 'owner' AND removed_at IS NULL
            LIMIT 1
            """,
            user_id,
        )
    if row is None:
        raise HTTPException(403, "admin access requires owner role on at least one organization")


@router.get("/stats")
async def system_stats(user_id: CurrentUser) -> dict[str, Any]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        orgs = await conn.fetchval("SELECT COUNT(*) FROM organizations")
        projects = await conn.fetchval("SELECT COUNT(*) FROM projects")
        runs = await conn.fetchval("SELECT COUNT(*) FROM agent_actions")
        connectors = await conn.fetchval("SELECT COUNT(*) FROM connectors WHERE status='connected'")
        evals = await conn.fetchval("SELECT COUNT(*) FROM eval_results")
        corrections = await conn.fetchval("SELECT COUNT(*) FROM correction_signals")
        indexed = await conn.fetchval("SELECT COUNT(*) FROM connector_index WHERE stale=FALSE")
        avg_latency = await conn.fetchval(
            "SELECT ROUND(AVG((result->>'latency_ms')::numeric)) FROM agent_actions WHERE result->>'latency_ms' IS NOT NULL"
        )
        avg_composite = await conn.fetchval(
            "SELECT ROUND(AVG(composite_score)::numeric, 2) FROM eval_results"
        )
    return {
        "users": users,
        "organizations": orgs,
        "projects": projects,
        "total_runs": runs,
        "connected_tools": connectors,
        "eval_scores": evals,
        "corrections": corrections,
        "indexed_resources": indexed,
        "avg_latency_ms": int(avg_latency) if avg_latency else None,
        "avg_eval_composite": float(avg_composite) if avg_composite else None,
    }


@router.get("/users")
async def list_users(user_id: CurrentUser, limit: int = 100) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.id, u.email, u.name, u.plan, u.created_at, u.last_login_at,
                   (SELECT COUNT(*) FROM agent_actions aa WHERE aa.user_id = u.id) AS run_count,
                   (SELECT COUNT(*) FROM connectors c WHERE c.user_id = u.id AND c.status='connected') AS connector_count
            FROM users u
            ORDER BY u.created_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "name": r["name"],
            "plan": r["plan"],
            "created_at": r["created_at"].isoformat(),
            "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            "run_count": r["run_count"],
            "connector_count": r["connector_count"],
        }
        for r in rows
    ]


@router.get("/connectors")
async def all_connectors(user_id: CurrentUser) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.tool_name, c.status, c.health_status, c.workspace_name,
                   c.last_sync, c.created_at, u.email AS user_email,
                   p.name AS project_name
            FROM connectors c
            JOIN users u ON u.id = c.user_id
            LEFT JOIN projects p ON p.id = c.project_id
            ORDER BY c.tool_name, c.created_at DESC
            """
        )
    return [
        {
            "id": str(r["id"]),
            "tool": r["tool_name"],
            "status": r["status"],
            "health": r["health_status"],
            "workspace": r["workspace_name"],
            "last_sync": r["last_sync"].isoformat() if r["last_sync"] else None,
            "user_email": r["user_email"],
            "project": r["project_name"],
        }
        for r in rows
    ]


@router.get("/runs")
async def recent_runs(user_id: CurrentUser, limit: int = 50) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT aa.id, aa.prompt, aa.timestamp, u.email,
                   (aa.result->>'tokens_used')::int AS tokens,
                   (aa.result->>'latency_ms')::int AS latency_ms,
                   er.composite_score, er.flagged
            FROM agent_actions aa
            JOIN users u ON u.id = aa.user_id
            LEFT JOIN eval_results er ON er.action_id = aa.id
            ORDER BY aa.timestamp DESC
            LIMIT $1
            """,
            limit,
        )
    return [
        {
            "id": str(r["id"]),
            "prompt": r["prompt"][:200] if r["prompt"] else None,
            "timestamp": r["timestamp"].isoformat(),
            "user": r["email"],
            "tokens": r["tokens"],
            "latency_ms": r["latency_ms"],
            "composite_score": float(r["composite_score"]) if r["composite_score"] else None,
            "flagged": r["flagged"],
        }
        for r in rows
    ]


@router.get("/eval")
async def eval_trends(user_id: CurrentUser) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM admin_eval_trend
            LIMIT 90
            """
        )
    return [
        {
            "date": str(r["eval_date"]),
            "rubric": r["rubric_type"],
            "count": r["eval_count"],
            "avg_composite": float(r["avg_composite"]) if r["avg_composite"] else None,
            "flagged": r["flagged_count"],
            "flagged_pct": float(r["flagged_pct"]) if r["flagged_pct"] else None,
        }
        for r in rows
    ]


@router.get("/connector-health")
async def connector_health(user_id: CurrentUser) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM admin_connector_health")
    return [dict(r) for r in rows]


@router.get("/index-status")
async def index_status(user_id: CurrentUser) -> list[dict[str, Any]]:
    await _require_admin(user_id)
    async with db.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM admin_index_coverage")
    return [
        {
            "user_id": str(r["user_id"]),
            "email": r["email"],
            "tool": r["tool"],
            "resource_type": r["resource_type"],
            "indexed_rows": r["indexed_rows"],
            "last_indexed": r["last_indexed"].isoformat() if r["last_indexed"] else None,
            "stale_rows": r["stale_rows"],
        }
        for r in rows
    ]
