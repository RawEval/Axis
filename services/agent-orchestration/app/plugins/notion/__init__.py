"""Notion plugin — search + append + recent_activity capabilities."""
from app.capabilities.notion import CAPABILITY as _search
from app.capabilities.notion_recent_activity import CAPABILITY as _recent_activity
from app.capabilities.notion_write import CAPABILITY as _append

CAPABILITIES = [_search, _append, _recent_activity]
