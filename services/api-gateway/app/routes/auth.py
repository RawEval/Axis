"""Proxy routes for auth-service. Public register/login, protected /me."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from app.clients.auth import AuthClient
from app.clients.base import propagate_headers
from app.config import settings
from app.deps import BearerToken, get_http_client
from app.ratelimit import limiter

router = APIRouter()


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    name: str | None = Field(default=None, max_length=200)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def _client(req: Request) -> AuthClient:
    return AuthClient(get_http_client(req), headers=propagate_headers(req))


@router.post("/register")
async def register(body: RegisterBody, req: Request) -> dict[str, Any]:
    return await _client(req).register(body.email, body.password, body.name)


@router.post("/login")
@limiter.limit(settings.rate_limit_auth_login)
async def login(body: LoginBody, request: Request) -> dict[str, Any]:
    return await _client(request).login(body.email, body.password)


@router.get("/me")
async def me(req: Request, token: BearerToken) -> dict[str, Any]:
    return await _client(req).me(token)
