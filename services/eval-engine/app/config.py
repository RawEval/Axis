from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-eval-engine"

    anthropic_api_key: str = ""
    anthropic_model_haiku: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 1024

    eval_flag_threshold: float = 3.0
    eval_dimension_flag_threshold: int = 2
    eval_opt_out_default: bool = True

    # How many recent corrections the short-loop considers when generating
    # a per-user system-prompt delta. Too small → noisy; too large → stale.
    short_loop_window_size: int = 20


settings = Settings()
