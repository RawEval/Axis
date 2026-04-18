"""Capability registry — maps tool names to live Capability instances.

Auto-populates from TWO sources:
  1. ``app/capabilities/*.py`` — legacy flat modules (CAPABILITY or CAPABILITIES)
  2. ``app/plugins/*/`` — new plugin directories (each __init__.py exports CAPABILITIES)

The plugin system is the preferred way to add new capabilities.
The legacy flat modules are kept for backward compatibility.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from axis_common import get_logger

from app.capabilities.base import Capability, anthropic_tool

logger = get_logger(__name__)


class Registry:
    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}

    def add(self, cap: Capability) -> None:
        if cap.name in self._caps:
            return  # dedupe — same cap from capabilities/ and plugins/
        self._caps[cap.name] = cap
        logger.info("capability_registered", name=cap.name, scope=cap.scope)

    def get(self, name: str) -> Capability | None:
        if name in self._caps:
            return self._caps[name]
        undot = name.replace("_", ".")
        return self._caps.get(undot)

    def all(self) -> list[Capability]:
        return list(self._caps.values())

    def anthropic_tools(self) -> list[dict[str, Any]]:
        return [anthropic_tool(c) for c in self._caps.values()]

    def by_connector(self) -> dict[str, list[Capability]]:
        """Group capabilities by connector name (e.g. 'slack', 'notion')."""
        groups: dict[str, list[Capability]] = {}
        for cap in self._caps.values():
            parts = cap.name.split(".")
            connector = parts[1] if len(parts) >= 3 else parts[0]
            groups.setdefault(connector, []).append(cap)
        return groups


_registry = Registry()


def _autoload() -> None:
    """Load capabilities from both app/capabilities/ and app/plugins/."""
    # Source 1: legacy flat capabilities/*.py
    import app.capabilities as caps_pkg

    for modinfo in pkgutil.iter_modules(caps_pkg.__path__):
        if modinfo.name in {"base", "registry", "__init__"}:
            continue
        full = f"app.capabilities.{modinfo.name}"
        try:
            mod = importlib.import_module(full)
        except Exception as e:  # noqa: BLE001
            logger.error("capability_import_failed", module=full, error=str(e))
            continue
        caps_list = getattr(mod, "CAPABILITIES", None) or []
        cap_single = getattr(mod, "CAPABILITY", None)
        if caps_list:
            for c in caps_list:
                if isinstance(c, Capability):
                    _registry.add(c)
            continue
        if cap_single is not None and isinstance(cap_single, Capability):
            _registry.add(cap_single)

    # Source 2: plugin directories (app/plugins/*)
    try:
        import app.plugins as plugins_pkg

        for modinfo in pkgutil.iter_modules(plugins_pkg.__path__):
            if modinfo.name.startswith("_"):
                continue
            full = f"app.plugins.{modinfo.name}"
            try:
                mod = importlib.import_module(full)
            except Exception as e:  # noqa: BLE001
                logger.error("plugin_import_failed", plugin=full, error=str(e))
                continue
            caps_list = getattr(mod, "CAPABILITIES", None) or []
            for c in caps_list:
                if isinstance(c, Capability):
                    _registry.add(c)
            if caps_list:
                logger.info("plugin_loaded", plugin=modinfo.name, capabilities=len(caps_list))
    except ImportError:
        logger.warning("plugins_package_not_found")


def get_registry() -> Registry:
    if not _registry.all():
        _autoload()
    return _registry
