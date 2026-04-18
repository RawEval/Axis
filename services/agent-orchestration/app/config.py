from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-agent-orchestration"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model_sonnet: str = "claude-sonnet-4-5"
    anthropic_model_haiku: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.2
    anthropic_timeout_ms: int = 120000

    # Limits from spec §6.7
    agent_max_concurrent_subagents: int = 5
    agent_max_tokens_per_run: int = 16000
    agent_plan_timeout_seconds: int = 30
    agent_execution_timeout_seconds: int = 180

    # Downstream services the orchestrator calls
    connector_manager_url: str = "http://localhost:8002"
    memory_service_url: str = "http://localhost:8004"
    eval_engine_url: str = "http://localhost:8003"


settings = Settings()
