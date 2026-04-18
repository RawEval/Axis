# api-gateway

FastAPI gateway. Handles auth, rate limiting, request routing, and WebSocket connections.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
open http://localhost:8000/docs
```
