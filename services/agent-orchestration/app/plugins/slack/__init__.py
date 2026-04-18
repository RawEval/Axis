"""Slack plugin — 6 capabilities (search, summary, thread, user, post, react)."""
from app.capabilities.slack import CAPABILITIES

# Re-export for the plugin registry
CAPABILITIES = CAPABILITIES
