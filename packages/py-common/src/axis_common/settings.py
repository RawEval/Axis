"""Shared BaseSettings class for Axis services.

Every service's Settings should extend AxisBaseSettings and add its own fields.
Loads env vars from the repo root .env (or override via model_config).

Includes safety validators so we fail loud on dangerous defaults in prod.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` until a directory with pnpm-workspace.yaml is found."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pnpm-workspace.yaml").exists():
            return candidate
    # fallback: 3 levels up from this file (packages/py-common/src/axis_common/settings.py)
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _repo_root()


class AxisBaseSettings(BaseSettings):
    """Base settings shared by every Python service.

    Services extend this and add their own fields. The env_file loader walks
    the repo root so a single .env drives the whole monorepo.
    """

    model_config = SettingsConfigDict(
        env_file=[str(REPO_ROOT / ".env"), str(REPO_ROOT / ".env.local")],
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core ---------------------------------------------------------------
    environment: str = "dev"
    log_level: str = "info"
    service_name: str = "axis-service"

    # --- Databases ----------------------------------------------------------
    postgres_url: str = "postgresql://axis:axis@localhost:5433/axis"
    postgres_pool_min: int = 2
    postgres_pool_max: int = 20
    redis_url: str = "redis://localhost:6379/0"

    # --- Security -----------------------------------------------------------
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    jwt_issuer: str = "axis-auth"

    # --- CORS ---------------------------------------------------------------
    cors_allowed_origins: str = "http://localhost:3001,http://localhost:3000"

    # --- HTTP timeouts ------------------------------------------------------
    http_client_timeout_ms: int = 5000
    long_request_timeout_ms: int = 120000

    # --- Observability ------------------------------------------------------
    sentry_dsn: str = ""

    @field_validator("postgres_url")
    @classmethod
    def _valid_pg(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(f"postgres_url must start with postgresql:// (got: {v[:20]}...)")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def _safe_jwt_secret(cls, v: str) -> str:
        env = os.environ.get("ENVIRONMENT", "dev").lower()
        danger = (not v) or v.startswith("change-me") or len(v) < 32
        if danger and env not in ("dev", "development", "test"):
            raise ValueError(
                f"jwt_secret is unset or too weak ({len(v)} chars) "
                f"and ENVIRONMENT={env}. Refusing to start."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        lv = v.lower()
        if lv not in ("debug", "info", "warning", "error", "critical"):
            raise ValueError(f"invalid log_level: {v}")
        return lv


def cors_origins_from(csv: str) -> list[str]:
    return [o.strip() for o in csv.split(",") if o.strip()]
