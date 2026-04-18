"""Plugin system — organized capability modules per connector.

Each subdirectory is a "plugin" that exports one or more Capability
objects. The registry auto-discovers all plugins at startup by walking
this package recursively.

Structure:
    plugins/
        slack/          6 capabilities (search, channel_summary, thread, user, post, react)
        notion/         2 capabilities (search, append)
        gdrive/         3 capabilities (search, read_content, create_doc)
        gmail/          1 capability (search)
        github/         1 capability (search)
        internal/       3 capabilities (activity_query, memory_retrieve, universal_search)

Each plugin's __init__.py exports CAPABILITIES: list[Capability].
The plugin registry loads them all into the flat capability registry
that Claude sees as tools.

Adding a new plugin:
    1. Create plugins/<name>/__init__.py
    2. Define one or more Capability dataclasses
    3. Export CAPABILITIES = [cap1, cap2, ...]
    4. The registry picks them up automatically — no wiring needed
"""
