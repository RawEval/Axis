"""Unified error types for Axis services."""
from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorPayload(BaseModel):
    detail: str
    code: str | None = None
    request_id: str | None = None


class AxisHTTPException(HTTPException):
    """HTTPException that also carries an error code for structured handling."""

    def __init__(self, status_code: int, detail: str, code: str | None = None) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
