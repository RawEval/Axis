"""Rubric protocol — a rubric is a typed scoring template.

Each rubric ships:
  - ``key``: matches the ``rubric_type`` in ScoreRequest
  - ``dimensions``: list of named 1–5 dimensions the judge scores
  - ``weights``: per-dimension weights that sum to 1.0 — used to compute
    the composite score from per-dimension scores
  - ``system_prompt``: the judge's role + rubric definition (cache-friendly)
  - ``build_user_prompt``: assembles the per-request payload the judge sees

The judge (``app/judges/haiku.py``) loads a Rubric, calls Claude with the
system prompt + per-request user prompt, then forces structured output via
a ``tool_use`` block so we always get parseable scores back even when the
model is feeling chatty.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Dimension:
    name: str
    description: str     # one sentence — what "5 out of 5" means
    weight: float


@dataclass(frozen=True)
class Rubric:
    key: str
    label: str
    dimensions: tuple[Dimension, ...]
    system_prompt: str
    build_user_prompt: Callable[[dict[str, Any]], str]

    def dim_names(self) -> list[str]:
        return [d.name for d in self.dimensions]

    def composite(self, scores: dict[str, float]) -> float:
        """Weighted average of the per-dimension scores.

        Missing dimensions are treated as 0 so a model that skips one is
        penalized; that's the point — we want the judge to hit every axis.
        """
        total = 0.0
        for d in self.dimensions:
            total += float(scores.get(d.name, 0.0)) * d.weight
        return round(total, 2)

    def tool_schema(self) -> dict[str, Any]:
        """Anthropic ``tool_use`` schema — flat ``{dim}_score`` + ``{dim}_reason``.

        The natural shape is nested — one object per dimension with
        ``score`` and ``reason`` keys. In practice Claude occasionally
        leaks XML parameter syntax into the values under a nested schema,
        producing strings like ``"\\n<parameter name=\\"score\\">1"``. A
        flat schema sidesteps the issue entirely.
        """
        properties: dict[str, Any] = {}
        required: list[str] = []
        for d in self.dimensions:
            properties[f"{d.name}_score"] = {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": d.description,
            }
            properties[f"{d.name}_reason"] = {
                "type": "string",
                "description": f"One sentence justifying the {d.name} score.",
            }
            required.append(f"{d.name}_score")
            required.append(f"{d.name}_reason")
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
