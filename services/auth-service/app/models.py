"""Pydantic request/response models for auth routes."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.config import settings


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=settings.password_min_length, max_length=128)
    name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = settings.jwt_expiry_minutes * 60


class RegisterResponse(TokenResponse):
    user_id: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str | None
    plan: str
    created_at: datetime
