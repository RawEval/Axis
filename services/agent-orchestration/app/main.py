"""Axis Agent Orchestration — FastAPI entrypoint.

/run does:
  1. validate
  2. run the LangGraph planner (single-node for now) via Anthropic Sonnet
  3. persist the rich message history (user + assistant + citations + spans)
  4. persist the aggregate agent_actions row (backward-compat)
  5. fire-and-forget a score request to eval-engine
  6. return the hydrated response to api-gateway
"""
from __future__ import annotations

import asyncio
import json
import time
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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.clients.eval import score_action
from app.clients.memory import MemoryClient
from app.events import close_client as close_event_bus, publish as publish_event
from app.permissions import resolve_pending
from app.repositories.writes import WritesRepository
from app.config import settings
from app.db import db
from app.graphs.planner import build_planner_graph
from app.repositories.actions import AgentActionsRepository
from app.repositories.messages import MessagesRepository
from app.repositories.tasks import TasksRepository

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)

planner_graph = build_planner_graph()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("agent_orchestration_startup")
    try:
        yield
    finally:
        await close_event_bus()
        await db.close()
        logger.info("agent_orchestration_shutdown")


app = FastAPI(
    title="Axis Agent Orchestration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(make_health_router(service=settings.service_name, db=db))


# ---------------- Schemas ----------------


class RunRequest(BaseModel):
    user_id: str
    prompt: str
    project_ids: list[str] = []
    project_scope: str = "default"
    # Async execution controls — the UI sets these from the time-limit popup
    mode: str = "sync"              # 'sync' | 'background'
    time_limit_sec: int | None = None  # user-selected: 300 | 600 | 900 | None=no limit
    notify_on_complete: bool = True


class CitationPayload(BaseModel):
    id: str | None = None
    source_type: str
    provider: str | None = None
    ref_id: str | None = None
    url: str | None = None
    title: str | None = None
    actor: str | None = None
    excerpt: str | None = None
    occurred_at: str | None = None
    spans: list[dict[str, Any]] = []


class FreshnessPayload(BaseModel):
    source: str
    last_synced_at: str | None = None
    sync_status: str = "never"
    error_message: str | None = None


class RunResponse(BaseModel):
    action_id: str
    task_id: str
    message_id: str | None = None     # None when mode='background' (not yet complete)
    project_id: str | None
    project_scope: str
    status: str = "completed"         # 'completed' | 'processing' | 'failed'
    output: str
    plan: list[dict]
    citations: list[CitationPayload]
    freshness_by_source: dict[str, FreshnessPayload] = {}
    tokens_used: int
    latency_ms: int


# ---------------- Task status (for background tasks) ----------------


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    """Check the status of a background task. The UI polls this when
    mode='background' and shows the result when status='done'."""
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.id, t.prompt, t.status, t.plan, t.result,
                   t.tokens_used, t.latency_ms, t.created_at, t.completed_at,
                   m.content AS output, m.id AS message_id
            FROM agent_tasks t
            LEFT JOIN agent_messages m ON m.task_id = t.id AND m.role = 'assistant'
            WHERE t.id = $1::uuid
            ORDER BY m.created_at DESC NULLS LAST
            LIMIT 1
            """,
            task_id,
        )
    if row is None:
        raise HTTPException(404, "task not found")
    result = row.get("result")
    if isinstance(result, str):
        result = json.loads(result)
    return {
        "task_id": str(row["id"]),
        "prompt": row["prompt"],
        "status": row["status"],
        "output": row.get("output") or (result or {}).get("output") or "",
        "message_id": str(row["message_id"]) if row.get("message_id") else None,
        "tokens_used": row["tokens_used"],
        "latency_ms": row["latency_ms"],
        "created_at": row["created_at"].isoformat(),
        "completed_at": row["completed_at"].isoformat() if row.get("completed_at") else None,
    }


@app.get("/tasks")
async def list_tasks(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """List recent tasks for a user — shows both running and completed."""
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, prompt, status, tokens_used, latency_ms, created_at, completed_at
            FROM agent_tasks
            WHERE user_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    return [
        {
            "task_id": str(r["id"]),
            "prompt": r["prompt"][:200],
            "status": r["status"],
            "tokens_used": r["tokens_used"],
            "latency_ms": r["latency_ms"],
            "created_at": r["created_at"].isoformat(),
            "completed_at": r["completed_at"].isoformat() if r.get("completed_at") else None,
        }
        for r in rows
    ]


# ---------------- Write confirm / rollback ----------------


@app.post("/writes/{write_action_id}/confirm")
async def confirm_write(write_action_id: str) -> dict[str, Any]:
    """User clicked Confirm on the DiffViewer — execute the write."""
    writes_repo = WritesRepository(db.raw)
    row = await writes_repo.get(write_action_id)
    if row is None:
        raise HTTPException(404, "write action not found")
    if row["confirmed_by_user"]:
        return {"ok": True, "status": "already_confirmed"}
    if row["rolled_back"]:
        raise HTTPException(409, "write was already rolled back")

    ok = await writes_repo.confirm(write_action_id)
    if not ok:
        raise HTTPException(409, "could not confirm — race condition")

    # Execute the actual write through connector-manager.
    from app.clients.connector_manager import ConnectorManagerClient
    cm = ConnectorManagerClient()
    diff = row.get("diff") or {}
    if isinstance(diff, str):
        import json as _json
        diff = _json.loads(diff)
    tool = row["tool"]
    execute_result: dict[str, Any] = {"ok": False}

    if tool == "notion":
        text = diff.get("text") or ""
        children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}] if text else []
        if children:
            execute_result = await cm.notion_append(
                user_id=str(row.get("action_id", "")),
                project_id=str(row.get("project_id", "")),
                page_id=str(row["target_id"]),
                children=children,
            )

    # Store after-state if the write succeeded
    if execute_result.get("ok"):
        try:
            after = await cm.notion_get_blocks(
                user_id=str(row.get("action_id", "")),
                project_id=str(row.get("project_id", "")),
                page_id=str(row["target_id"]),
            )
            await writes_repo.set_after_state(
                write_action_id, after.get("blocks") or []
            )
        except Exception:  # noqa: BLE001
            pass

    return {"ok": True, "status": "confirmed", "execute_result": execute_result}


@app.post("/writes/{write_action_id}/rollback")
async def rollback_write(write_action_id: str) -> dict[str, Any]:
    """User clicked Rollback — restore the before-state."""
    writes_repo = WritesRepository(db.raw)
    row = await writes_repo.get(write_action_id)
    if row is None:
        raise HTTPException(404, "write action not found")
    if not row["confirmed_by_user"]:
        raise HTTPException(409, "write was never confirmed — nothing to rollback")
    if row["rolled_back"]:
        return {"ok": True, "status": "already_rolled_back"}

    before_state = row.get("before_state")
    if before_state is None:
        raise HTTPException(500, "no snapshot found — cannot rollback")
    if isinstance(before_state, str):
        import json as _json
        before_state = _json.loads(before_state)

    # Rollback only supports Notion in Phase 1 — for other tools we'd
    # need provider-specific rollback logic.
    tool = row["tool"]
    if tool != "notion":
        raise HTTPException(501, f"rollback not implemented for {tool}")

    # Notion rollback: delete the appended blocks by restoring the snapshot.
    # Since Notion doesn't have a "replace all blocks" API, the best we can
    # do is mark rolled_back=true and tell the user. A real rollback would
    # need to diff the after_state against before_state and delete the delta
    # blocks individually — that's Phase 2 work.
    ok = await writes_repo.rollback(write_action_id)
    return {
        "ok": ok,
        "status": "rolled_back",
        "note": "Marked as rolled back. Full block deletion is a Phase 2 feature.",
    }


@app.post("/writes/{write_id}/choose-target")
async def choose_write_target(write_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """User picked one of the staged target_options on a pending write —
    persist the choice and republish a write.preview event so the UI moves
    on to the diff confirmation step."""
    chosen = body.get("chosen")
    if not chosen or not chosen.get("id"):
        raise HTTPException(400, "chosen target missing or malformed")
    repo = WritesRepository(db.raw)
    updated = await repo.choose_target(write_id, chosen)
    if not updated:
        raise HTTPException(404, "write not found or already executed")
    diff = updated.get("diff") or {}
    if isinstance(diff, str):
        diff = json.loads(diff)
    user_id = updated.get("user_id")
    if user_id is not None:
        await publish_event(
            user_id=str(user_id),
            project_id=str(updated["project_id"]) if updated.get("project_id") else None,
            event_type="write.target_chosen",
            payload={"write_id": write_id, "chosen": chosen, "diff": diff},
        )
    return {"ok": True, "write_id": write_id, "target_id": chosen["id"]}


# ---------------- Permission resolve ----------------


class PermissionResolveRequest(BaseModel):
    pending_id: str
    granted: bool
    lifetime: str = "session"   # session | 24h | project | forever


@app.post("/permissions/resolve")
async def permissions_resolve(body: PermissionResolveRequest) -> dict[str, Any]:
    ok = resolve_pending(
        pending_id=body.pending_id,
        granted=body.granted,
        lifetime=body.lifetime,
    )
    return {"ok": ok, "pending_id": body.pending_id}


# ---------------- Endpoint ----------------


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    start = time.monotonic()
    logger.info(
        "agent_run_start",
        user_id=req.user_id,
        mode=req.mode,
        time_limit=req.time_limit_sec,
        prompt_len=len(req.prompt),
    )

    if req.mode == "background":
        # Background mode: create a pending task, return immediately,
        # finish in a detached asyncio task, notify via WebSocket.
        tasks_repo = TasksRepository(db.raw)
        actions_repo = AgentActionsRepository(db.raw)
        persisted = await actions_repo.record(
            user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            prompt=req.prompt,
            plan=[],
            output="",
            sources=[],
            tokens_used=0,
            latency_ms=0,
        )
        task_row = await tasks_repo.record(
            user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            prompt=req.prompt,
            scope=req.project_scope,
            plan=[],
            output="",
            tokens_used=0,
            latency_ms=0,
            status="running",
            model=None,
        )
        asyncio.create_task(
            _run_background(req, persisted["id"], task_row["id"], start)
        )
        return RunResponse(
            action_id=persisted["id"],
            task_id=task_row["id"],
            message_id=None,
            project_id=req.project_ids[0] if req.project_ids else None,
            project_scope=req.project_scope,
            status="processing",
            output="Working on it — this may take a few minutes. You'll be notified when it's ready.",
            plan=[],
            citations=[],
            tokens_used=0,
            latency_ms=0,
        )

    # Sync mode: run on the critical path (default, fast queries)
    return await _run_sync(req, start)


async def _run_sync(req: RunRequest, start: float) -> RunResponse:
    """Standard synchronous execution — user waits for the result."""
    state = await planner_graph.ainvoke(
        {
            "user_id": req.user_id,
            "prompt": req.prompt,
            "project_ids": req.project_ids,
            "project_scope": req.project_scope,
        }
    )
    return await _persist_and_respond(req, state, start)


async def _run_background(
    req: RunRequest, action_id: str, task_id: str, start: float
) -> None:
    """Background execution — runs detached, publishes result via events."""
    try:
        state = await planner_graph.ainvoke(
            {
                "user_id": req.user_id,
                "prompt": req.prompt,
                "project_ids": req.project_ids,
                "project_scope": req.project_scope,
            }
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        output = state.get("output", "")
        plan = state.get("plan", [])
        citations = state.get("citations", [])
        tokens = state.get("tokens_used", 0)

        # Update the task row with the result
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE agent_tasks
                SET status = $2, result = $3::jsonb, plan = $4::jsonb,
                    tokens_used = $5, latency_ms = $6, completed_at = NOW()
                WHERE id = $1::uuid
                """,
                task_id,
                "failed" if state.get("error") else "done",
                json.dumps({"output": output, "tokens_used": tokens, "latency_ms": latency_ms}),
                json.dumps(plan),
                tokens,
                latency_ms,
            )
            await conn.execute(
                """
                UPDATE agent_actions
                SET result = $2::jsonb, plan = $3::jsonb
                WHERE id = $1::uuid
                """,
                action_id,
                json.dumps({"output": output, "tokens_used": tokens, "latency_ms": latency_ms}),
                json.dumps(plan),
            )

        # Persist rich history
        messages_repo = MessagesRepository(db.raw)
        await messages_repo.record_turn(
            user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            action_id=action_id,
            task_id=task_id,
            user_prompt=req.prompt,
            assistant_content=output,
            assistant_metadata={"tokens_used": tokens, "latency_ms": latency_ms, "plan": plan},
            citations=citations,
        )

        # Publish completion event so the UI picks it up
        await publish_event(
            user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            event_type="background.completed",
            action_id=action_id,
            task_id=task_id,
            payload={
                "output_preview": output[:500],
                "tokens_used": tokens,
                "latency_ms": latency_ms,
                "citations": len(citations),
                "plan_len": len(plan),
            },
        )

        # Fire-and-forget eval + memory
        asyncio.create_task(_score_background(
            action_id=action_id, user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            prompt=req.prompt, output=output, citations=citations, plan=plan,
        ))
        asyncio.create_task(_remember_turn(
            user_id=req.user_id,
            project_id=req.project_ids[0] if req.project_ids else None,
            action_id=action_id, prompt=req.prompt, output=output,
        ))

        logger.info("background_run_done", task_id=task_id, latency_ms=latency_ms)
    except Exception as e:  # noqa: BLE001
        logger.error("background_run_failed", task_id=task_id, error=str(e))
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE agent_tasks SET status = 'failed', completed_at = NOW() WHERE id = $1::uuid",
                task_id,
            )
        await publish_event(
            user_id=req.user_id,
            event_type="background.failed",
            task_id=task_id,
            payload={"error": str(e)},
        )


async def _persist_and_respond(req: RunRequest, state: dict[str, Any], start: float) -> RunResponse:
    """Shared persistence logic for both sync and background modes."""
    latency_ms = int((time.monotonic() - start) * 1000)
    active_project_id = state.get("active_project_id")
    output = state.get("output", "")
    tokens_used = state.get("tokens_used", 0)
    plan = state.get("plan", [])
    citations_from_state: list[dict[str, Any]] = state.get("citations", [])

    actions_repo = AgentActionsRepository(db.raw)
    persisted = await actions_repo.record(
        user_id=req.user_id,
        project_id=active_project_id,
        prompt=req.prompt,
        plan=plan,
        output=output,
        sources=[{"type": c.get("source_type"), "url": c.get("url"), "title": c.get("title")} for c in citations_from_state],
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )

    tasks_repo = TasksRepository(db.raw)
    task_row = await tasks_repo.record(
        user_id=req.user_id,
        project_id=active_project_id,
        prompt=req.prompt,
        scope=req.project_scope,
        plan=plan,
        output=output,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        status="failed" if state.get("error") else "done",
        model=state.get("model"),
    )

    messages_repo = MessagesRepository(db.raw)
    turn = await messages_repo.record_turn(
        user_id=req.user_id,
        project_id=active_project_id,
        action_id=persisted["id"],
        task_id=task_row["id"],
        user_prompt=req.prompt,
        assistant_content=output,
        assistant_metadata={"tokens_used": tokens_used, "latency_ms": latency_ms, "model": state.get("model"), "plan": plan},
        citations=citations_from_state,
    )

    logger.info("agent_run_done", action_id=persisted["id"], task_id=task_row["id"], tokens=tokens_used, latency_ms=latency_ms)

    asyncio.create_task(_score_background(
        action_id=persisted["id"], user_id=req.user_id, project_id=active_project_id,
        prompt=req.prompt, output=output, citations=citations_from_state, plan=plan,
    ))
    asyncio.create_task(_remember_turn(
        user_id=req.user_id, project_id=active_project_id,
        action_id=persisted["id"], prompt=req.prompt, output=output,
    ))

    return RunResponse(
        action_id=persisted["id"],
        task_id=task_row["id"],
        message_id=turn["assistant_message_id"],
        project_id=active_project_id,
        project_scope=req.project_scope,
        status="completed",
        output=output,
        plan=plan,
        citations=[CitationPayload(**c) for c in turn["citations"]],
        freshness_by_source={
            src: FreshnessPayload(**fr)
            for src, fr in (state.get("freshness_by_source") or {}).items()
        },
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )


async def _remember_turn(
    *,
    user_id: str,
    project_id: str | None,
    action_id: str,
    prompt: str,
    output: str,
) -> None:
    """Persist user prompt + assistant response as two episodic rows."""
    client = MemoryClient()
    try:
        await client.write_episodic(
            user_id=user_id,
            project_id=project_id,
            role="user",
            content=prompt,
            action_id=action_id,
        )
        await client.write_episodic(
            user_id=user_id,
            project_id=project_id,
            role="assistant",
            content=output,
            action_id=action_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("episodic_write_failed", action_id=action_id, error=str(e))


async def _score_background(
    *,
    action_id: str,
    user_id: str,
    project_id: str | None,
    prompt: str,
    output: str,
    citations: list[dict[str, Any]],
    plan: list[dict[str, Any]],
) -> None:
    """Runs detached from /run — never blocks the user on scoring."""
    try:
        await score_action(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            rubric_type="action",
            prompt=prompt,
            output=output,
            citations=citations,
            plan=plan,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("eval_background_failed", action_id=action_id, error=str(e))
