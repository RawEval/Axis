from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-auth-service"

    # Auth-specific
    password_min_length: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30


settings = Settings()
