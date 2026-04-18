"""Rubric registry — maps ``rubric_type`` strings to Rubric instances.

Judges look rubrics up by key; the /score endpoint validates that the
requested key exists before dispatching.
"""
from __future__ import annotations

from app.rubrics.action import RUBRIC as ACTION
from app.rubrics.base import Dimension, Rubric
from app.rubrics.proactive import RUBRIC as PROACTIVE
from app.rubrics.summarisation import RUBRIC as SUMMARISATION

RUBRICS: dict[str, Rubric] = {
    ACTION.key: ACTION,
    SUMMARISATION.key: SUMMARISATION,
    PROACTIVE.key: PROACTIVE,
}


def get_rubric(key: str) -> Rubric | None:
    return RUBRICS.get(key)


__all__ = ["Dimension", "Rubric", "RUBRICS", "get_rubric"]
