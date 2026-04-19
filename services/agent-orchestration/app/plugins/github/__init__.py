"""GitHub plugin — search + recent activity capabilities."""
from app.capabilities.github import CAPABILITY
from app.capabilities.github_recent_activity import CAPABILITY as _recent_activity

CAPABILITIES = [CAPABILITY, _recent_activity]
