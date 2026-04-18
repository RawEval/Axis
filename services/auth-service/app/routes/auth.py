from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.deps import get_current_user_id, get_user_repo
from app.models import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserPublic,
)
from app.repositories.users import UserRepository
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()


def _claims_for(user: dict) -> dict:
    return {"email": user["email"], "plan": user.get("plan", "free")}


def _client_info(req: Request) -> tuple[str | None, str | None]:
    ip = req.client.host if req.client else None
    ua = req.headers.get("user-agent")
    return ip, ua


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    req: Request,
    repo: UserRepository = Depends(get_user_repo),
) -> RegisterResponse:
    if await repo.email_exists(body.email):
        raise HTTPException(409, "email already registered")
    password_hash = await hash_password(body.password)
    user = await repo.create(
        email=body.email,
        password_hash=password_hash,
        name=body.name,
    )
    ip, ua = _client_info(req)
    await repo.log_login_event(
        user_id=str(user["id"]),
        email=body.email,
        event_type="success",
        ip=ip,
        user_agent=ua,
    )
    token = create_access_token(subject=str(user["id"]), claims=_claims_for(user))
    return RegisterResponse(user_id=str(user["id"]), access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    req: Request,
    repo: UserRepository = Depends(get_user_repo),
) -> TokenResponse:
    user = await repo.get_by_email(body.email)
    ip, ua = _client_info(req)

    if user is None:
        await repo.log_login_event(
            user_id=None, email=body.email, event_type="failure", ip=ip, user_agent=ua
        )
        raise HTTPException(401, "invalid email or password")

    if UserRepository.is_locked(user):
        await repo.log_login_event(
            user_id=str(user["id"]),
            email=body.email,
            event_type="lockout",
            ip=ip,
            user_agent=ua,
        )
        raise HTTPException(423, "account temporarily locked, try again later")

    is_valid = False
    if user["password_hash"]:
        is_valid = await verify_password(body.password, user["password_hash"])

    if not is_valid:
        count = await repo.mark_login_failure(str(user["id"]), settings.max_login_attempts)
        await repo.log_login_event(
            user_id=str(user["id"]),
            email=body.email,
            event_type="failure",
            ip=ip,
            user_agent=ua,
        )
        remaining = max(0, settings.max_login_attempts - count)
        if remaining == 0:
            raise HTTPException(423, "account locked after too many failed attempts")
        raise HTTPException(401, f"invalid email or password ({remaining} attempts left)")

    await repo.mark_login_success(str(user["id"]))
    await repo.log_login_event(
        user_id=str(user["id"]),
        email=body.email,
        event_type="success",
        ip=ip,
        user_agent=ua,
    )
    token = create_access_token(subject=str(user["id"]), claims=_claims_for(user))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
async def me(
    user_id: str = Depends(get_current_user_id),
    repo: UserRepository = Depends(get_user_repo),
) -> UserPublic:
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return UserPublic(
        id=str(user["id"]),
        email=user["email"],
        name=user.get("name"),
        plan=user["plan"],
        created_at=user["created_at"],
    )
