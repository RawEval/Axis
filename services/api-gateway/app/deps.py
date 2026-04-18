"""FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

import httpx
from axis_common import InvalidTokenError, TokenExpiredError, decode_token
from fastapi import Depends, Header, HTTPException, Request, status

from app.config import settings


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


async def get_current_user_id(token: str = Depends(get_bearer_token)) -> str:
    try:
        payload = decode_token(
            token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
        )
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="expired"'
            },
        ) from e
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(401, "token missing subject")
    return str(sub)


CurrentUser = Annotated[str, Depends(get_current_user_id)]
BearerToken = Annotated[str, Depends(get_bearer_token)]


class ProjectScope:
    """Resolved project scope for a request.

    The frontend sends ``X-Axis-Project`` with one of:
      - a specific UUID → explicit pin → ``ids=[uuid]``
      - "all"          → fan out over every project the user owns
      - "auto"         → let the agent classifier decide (Phase 2)
      - missing        → fall back to the user's default project

    Only the gateway resolves this. Downstream services trust the
    ``project_id`` list from the request body.
    """

    def __init__(self, *, mode: str, ids: list[str]) -> None:
        self.mode = mode  # 'explicit' | 'all' | 'auto' | 'default'
        self.ids = ids

    @property
    def primary(self) -> str | None:
        return self.ids[0] if self.ids else None


async def get_project_scope(
    user_id: str = Depends(get_current_user_id),
    x_axis_project: str | None = Header(default=None, alias="X-Axis-Project"),
) -> ProjectScope:
    """Resolve the project scope from the ``X-Axis-Project`` header.

    Reads the user's projects from Postgres to validate ownership when an
    explicit UUID is sent, and to enumerate for 'all' mode.
    """
    from app.db import db
    from app.repositories.projects import ProjectsRepository

    repo = ProjectsRepository(db.raw)

    if not x_axis_project:
        default = await repo.get_default(user_id)
        if default is None:
            raise HTTPException(500, "user has no default project")
        return ProjectScope(mode="default", ids=[str(default["id"])])

    header_val = x_axis_project.strip().lower()
    if header_val == "all":
        rows = await repo.list_for_user(user_id)
        return ProjectScope(mode="all", ids=[str(r["id"]) for r in rows])
    if header_val == "auto":
        # Phase 1: degrade to default project until the LLM classifier ships.
        default = await repo.get_default(user_id)
        if default is None:
            raise HTTPException(500, "user has no default project")
        return ProjectScope(mode="auto", ids=[str(default["id"])])

    # Explicit UUID — verify ownership.
    row = await repo.get(user_id, x_axis_project)
    if row is None:
        raise HTTPException(404, "project not found or not owned")
    return ProjectScope(mode="explicit", ids=[str(row["id"])])


CurrentProject = Annotated[ProjectScope, Depends(get_project_scope)]


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if client is None:
        raise HTTPException(503, "http client not initialized")
    return client


def get_long_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient | None = getattr(request.app.state, "http_client_long", None)
    if client is None:
        raise HTTPException(503, "long http client not initialized")
    return client
