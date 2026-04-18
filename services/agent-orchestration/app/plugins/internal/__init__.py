"""Internal plugins — activity, memory, universal search."""
from app.capabilities.activity import CAPABILITY as _activity
from app.capabilities.memory import CAPABILITY as _memory
from app.capabilities.universal_search import CAPABILITY as _universal

CAPABILITIES = [_activity, _memory, _universal]
