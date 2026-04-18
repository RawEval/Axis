"""Thin wrapper re-exporting axis_common.security bound to this service's JWT config."""
from __future__ import annotations

from typing import Any

from axis_common import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token as _create,
    decode_token as _decode,
    hash_password as _hash,
    verify_password as _verify,
)

from app.config import settings


async def hash_password(password: str) -> str:
    return await _hash(password)


async def verify_password(plain: str, hashed: str) -> bool:
    return await _verify(plain, hashed)


def create_access_token(*, subject: str, claims: dict[str, Any] | None = None) -> str:
    return _create(
        subject=subject,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expiry_minutes=settings.jwt_expiry_minutes,
        issuer=settings.jwt_issuer,
        claims=claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    return _decode(
        token,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
    )


__all__ = [
    "InvalidTokenError",
    "TokenExpiredError",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
