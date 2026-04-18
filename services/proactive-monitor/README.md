# proactive-monitor

Celery worker that runs the relevance engine in the background. See spec §6.3.

```bash
uv sync
uv run celery -A app.worker worker -l info -Q proactive
```
