"""FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.db import db
from app.repositories.users import UserRepository
from app.security import InvalidTokenError, TokenExpiredError, decode_token


async def get_user_repo() -> UserRepository:
    return UserRepository(db.raw)


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
        payload = decode_token(token)
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="expired"'},
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
