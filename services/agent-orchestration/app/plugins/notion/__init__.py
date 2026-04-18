"""Notion plugin — search + append capabilities."""
from app.capabilities.notion import CAPABILITY as _search
from app.capabilities.notion_write import CAPABILITY as _append

CAPABILITIES = [_search, _append]
