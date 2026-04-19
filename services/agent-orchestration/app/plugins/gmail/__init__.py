"""Gmail plugin — search capability + recent_activity."""
from app.capabilities.gmail import CAPABILITY
from app.capabilities.gmail_recent_activity import CAPABILITY as _recent_activity

CAPABILITIES = [CAPABILITY, _recent_activity]
