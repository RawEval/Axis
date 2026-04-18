# agent-orchestration

LangGraph-based planner and executor. Breaks prompts into sub-tasks and dispatches
to specialised sub-agents per §6.7 of the spec.

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8001
```
