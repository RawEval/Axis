"""Slack plugin — search, summary, thread, user, post, react + recent_activity."""
from app.capabilities.slack import CAPABILITIES as _core_capabilities
from app.capabilities.slack_recent_activity import CAPABILITY as _recent_activity

CAPABILITIES = [*_core_capabilities, _recent_activity]
