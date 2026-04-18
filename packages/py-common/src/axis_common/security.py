"""Password hashing and JWT issuance.

All bcrypt operations run in a threadpool so they don't block the event loop.
Token decoding distinguishes expired vs invalid so clients can trigger a
refresh flow without ambiguity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.concurrency import run_in_threadpool
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class TokenError(Exception):
    """Base for all JWT decode failures."""


class TokenExpiredError(TokenError):
    """Token signature valid but expiry has passed."""


class InvalidTokenError(TokenError):
    """Token was malformed, had bad signature, wrong issuer, etc."""


def _hash_sync(password: str) -> str:
    return _pwd.hash(password)


def _verify_sync(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_hash_sync, password)


async def verify_password(plain: str, hashed: str) -> bool:
    return await run_in_threadpool(_verify_sync, plain, hashed)


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str = "HS256",
    expiry_minutes: int = 60,
    issuer: str = "axis-auth",
    claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
        "iss": issuer,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(
    token: str,
    *,
    secret: str,
    algorithm: str = "HS256",
    issuer: str | None = "axis-auth",
) -> dict[str, Any]:
    try:
        options = {"verify_aud": False}
        if issuer:
            return jwt.decode(
                token,
                secret,
                algorithms=[algorithm],
                issuer=issuer,
                options=options,
            )
        return jwt.decode(token, secret, algorithms=[algorithm], options=options)
    except ExpiredSignatureError as e:
        raise TokenExpiredError("token expired") from e
    except JWTError as e:
        raise InvalidTokenError(str(e) or "invalid token") from e
