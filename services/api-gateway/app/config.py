from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-api-gateway"

    # Downstream services
    auth_service_url: str = "http://localhost:8006"
    agent_orchestration_url: str = "http://localhost:8001"
    connector_manager_url: str = "http://localhost:8002"
    eval_engine_url: str = "http://localhost:8003"
    memory_service_url: str = "http://localhost:8004"
    notification_service_url: str = "http://localhost:8005"

    # Rate limiting (slowapi + Redis backend)
    rate_limit_agent_run: str = "10/minute"
    rate_limit_auth_login: str = "5/minute"
    rate_limit_corrections: str = "20/minute"
    rate_limit_default: str = "60/minute"
    rate_limit_storage: str = "redis://localhost:6379/1"


settings = Settings()
