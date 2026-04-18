"""Axis Eval Engine — LLM-as-judge scoring + correction loop (spec §6.6).

Scoring pipeline:
  /score → load rubric → judge.haiku.judge(rubric, context)
         → persist eval_results row
         → fire-and-forget short-loop recompute so the next agent run sees
           an updated system-prompt delta

Correction loop:
  /corrections → persist correction_signals row
               → fire-and-forget short-loop recompute for that user
  /prompt-deltas/{user_id} → agent-orchestration reads the current delta
                             and prepends it to its supervisor system prompt
"""
from __future__ import annotations

import asyncio
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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.db import db
from app.judges.haiku import judge as haiku_judge
from app.repositories.corrections import (
    CORRECTION_TYPES,
    CorrectionsRepository,
    PromptDeltasRepository,
)
from app.rubrics import get_rubric

configure_logging(service=settings.service_name, level=settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("eval_engine_startup")
    try:
        yield
    finally:
        await db.close()
        logger.info("eval_engine_shutdown")


app = FastAPI(
    title="Axis Eval Engine",
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


class ScoreRequest(BaseModel):
    action_id: str
    user_id: str | None = None
    project_id: str | None = None
    rubric_type: str = Field(
        default="action",
        pattern="^(summarisation|action|proactive_surface)$",
    )
    prompt: str | None = None
    output: str
    context: dict[str, Any] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    action_id: str
    composite_score: float
    scores: list[dict[str, Any]]
    flagged: bool
    model: str
    stub: bool


# ---------------- Score endpoint ----------------


@app.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest) -> ScoreResponse:
    rubric = get_rubric(req.rubric_type)
    if rubric is None:
        raise HTTPException(400, f"unknown rubric_type: {req.rubric_type}")

    context = {
        "prompt": req.prompt,
        "output": req.output,
        **req.context,
    }

    scores_list, composite, model, is_stub = await haiku_judge(rubric, context)

    flagged = (
        composite < settings.eval_flag_threshold
        or any(
            int(s.get("score", 5)) < settings.eval_dimension_flag_threshold
            for s in scores_list
        )
    )

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO eval_results (action_id, rubric_type, scores, composite_score, flagged)
            VALUES ($1::uuid, $2, $3::jsonb, $4, $5)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            req.action_id,
            req.rubric_type,
            json.dumps(scores_list),
            composite,
            flagged,
        )

    logger.info(
        "score_persisted",
        action_id=req.action_id,
        rubric=req.rubric_type,
        composite=composite,
        flagged=flagged,
        model=model,
        row_inserted=bool(row),
    )

    # Fire-and-forget: if this turn was flagged, schedule a short-loop
    # recompute for the user. Never blocks the caller.
    if flagged and req.user_id:
        from app.loops.short import refresh_prompt_delta
        asyncio.create_task(_safe_refresh(req.user_id))

    return ScoreResponse(
        action_id=req.action_id,
        composite_score=composite,
        scores=scores_list,
        flagged=flagged,
        model=model,
        stub=is_stub,
    )


async def _safe_refresh(user_id: str) -> None:
    try:
        from app.loops.short import refresh_prompt_delta
        await refresh_prompt_delta(user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("short_loop_refresh_failed", user_id=user_id, error=str(e))


# ---------------- Correction endpoint ----------------


class CorrectionRequest(BaseModel):
    user_id: str
    action_id: str
    project_id: str | None = None
    correction_type: str = Field(..., pattern="^(wrong|rewrite|memory_update|scope)$")
    note: str | None = None


class CorrectionResponse(BaseModel):
    id: str
    created_at: str


@app.post("/corrections", response_model=CorrectionResponse)
async def submit_correction(req: CorrectionRequest) -> CorrectionResponse:
    if req.correction_type not in CORRECTION_TYPES:
        raise HTTPException(400, f"unknown correction_type: {req.correction_type}")
    repo = CorrectionsRepository(db.raw)
    row = await repo.record(
        user_id=req.user_id,
        action_id=req.action_id,
        project_id=req.project_id,
        correction_type=req.correction_type,
        note=req.note,
    )
    logger.info(
        "correction_recorded",
        user_id=req.user_id,
        action_id=req.action_id,
        correction_type=req.correction_type,
        correction_id=row["id"],
    )
    # Fire-and-forget short-loop refresh so the next /run picks up the new delta.
    asyncio.create_task(_safe_refresh(req.user_id))
    return CorrectionResponse(**row)


# ---------------- Prompt delta endpoint ----------------


class PromptDeltaResponse(BaseModel):
    user_id: str
    delta: str
    source_corrections: list[str]
    model: str | None = None
    token_count: int | None = None
    updated_at: str | None = None


@app.get("/prompt-deltas/{user_id}", response_model=PromptDeltaResponse)
async def get_prompt_delta(user_id: str) -> PromptDeltaResponse:
    repo = PromptDeltasRepository(db.raw)
    row = await repo.get(user_id)
    if row is None:
        return PromptDeltaResponse(
            user_id=user_id,
            delta="",
            source_corrections=[],
            model=None,
            token_count=None,
            updated_at=None,
        )
    return PromptDeltaResponse(
        user_id=str(row["user_id"]),
        delta=row["delta"],
        source_corrections=[str(x) for x in (row.get("source_corrections") or [])],
        model=row.get("model"),
        token_count=row.get("token_count"),
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else None,
    )


@app.post("/prompt-deltas/{user_id}/refresh", response_model=PromptDeltaResponse)
async def refresh_delta(user_id: str) -> PromptDeltaResponse:
    from app.loops.short import refresh_prompt_delta
    await refresh_prompt_delta(user_id)
    return await get_prompt_delta(user_id)
