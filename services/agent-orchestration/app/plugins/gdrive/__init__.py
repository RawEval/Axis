"""Google Drive plugin — search, read content, create doc, recent activity."""
from app.capabilities.gdrive import CAPABILITIES
from app.capabilities.gdrive_recent_activity import CAPABILITY as _recent_activity

CAPABILITIES = [*CAPABILITIES, _recent_activity]
