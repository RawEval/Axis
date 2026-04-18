"""Capability registry — the pluggable tool surface the supervisor dispatches to.

Every capability declares a name, description, JSON schema, and an async
__call__ that executes the work. The registry is auto-populated at import
time from every module in this package that exposes a `CAPABILITY` object.

Adding a new tool is a one-file change: drop `app/capabilities/<name>.py`
with a `CAPABILITY = ...` at the bottom and it shows up in the supervisor
on the next restart.
"""
from axis_common import get_logger

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.capabilities.registry import Registry, get_registry

__all__ = [
    "Capability",
    "CapabilityResult",
    "Citation",
    "Registry",
    "get_registry",
]

_logger = get_logger(__name__)
