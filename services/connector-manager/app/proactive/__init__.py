"""Phase 1 proactive layer — lives here until proactive-monitor grows its own runtime.

ADR 007 puts the relevance engine and signal detectors in
``services/proactive-monitor/``. That service is currently just a Celery
stub with no running process, no DB client, and no schedule. Putting the
Phase 1 detectors there would mean standing up a whole new worker just to
exercise a few functions. Instead we land them here alongside the
``activity_events`` writer (the data source) and wire a background loop
off the connector-manager lifespan. When proactive-monitor needs to fan
out at scale we move this subpackage wholesale — the module surface is
deliberately small.
"""
