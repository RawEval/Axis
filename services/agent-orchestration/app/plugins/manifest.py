"""Plugin manifest — generates a human-readable + machine-readable map
of every registered capability. The supervisor can use this to verify
that the right tools are available before calling Claude.

Usage:
    from app.plugins.manifest import generate_manifest
    manifest = generate_manifest()
    # Returns a dict keyed by connector with all capability metadata
"""
from __future__ import annotations

from typing import Any

from app.capabilities import get_registry


def generate_manifest() -> dict[str, Any]:
    """Build a structured manifest of all registered capabilities.

    This is what the admin dashboard and debug tools use to verify
    that every plugin is loaded and properly configured.
    """
    reg = get_registry()
    groups = reg.by_connector()

    manifest: dict[str, Any] = {
        "total_capabilities": len(reg.all()),
        "connectors": {},
    }

    for connector, caps in sorted(groups.items()):
        reads = [c for c in caps if c.scope == "read"]
        writes = [c for c in caps if c.scope in ("write", "execute")]
        manifest["connectors"][connector] = {
            "capabilities": len(caps),
            "reads": len(reads),
            "writes": len(writes),
            "tools": [
                {
                    "name": c.name,
                    "scope": c.scope,
                    "permission": c.default_permission,
                    "description": c.description[:120],
                    "inputs": list((c.input_schema or {}).get("properties", {}).keys()),
                }
                for c in sorted(caps, key=lambda x: x.name)
            ],
        }

    return manifest


def print_manifest() -> None:
    """Pretty-print the manifest for debugging."""
    import json

    m = generate_manifest()
    print(f"\n{'='*60}")
    print(f"  AXIS PLUGIN MANIFEST — {m['total_capabilities']} capabilities")
    print(f"{'='*60}\n")

    for connector, info in m["connectors"].items():
        print(f"  [{connector}] {info['capabilities']} caps ({info['reads']}R / {info['writes']}W)")
        for t in info["tools"]:
            perm = "AUTO" if t["permission"] == "auto" else "GATED"
            scope = "READ" if t["scope"] == "read" else "WRITE"
            print(f"    {scope:5} {perm:5}  {t['name']:45} inputs: {t['inputs']}")
        print()
