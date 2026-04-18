# CLAUDE.md — services/agent-orchestration

The brain. LangGraph-based planner and executor. Breaks user prompts into sub-tasks, dispatches to specialized sub-agents (read, write, research, summarise, synthesise), assembles results. Spec §6.2 and §6.7.

## Responsibilities

- Parse prompts into structured intent (tools, entities, action type)
- Retrieve context from memory-service
- Build an execution plan (multi-step for complex tasks, shown to user before executing)
- Dispatch sub-agents in parallel (max 5 concurrent per spec §6.7)
- Synthesize results with source tracing
- Emit live updates via Redis pub/sub for the api-gateway WebSocket
- Handle the write-confirmation gate

## Not responsibilities

- Do not verify JWTs — trust `user_id` from api-gateway.
- Do not talk to Slack/Notion/Gmail directly. All tool calls go through the connector modules.
- Do not score outputs — that is eval-engine.
- Do not persist memory — that is memory-service.

## Tech

- **LangGraph** for stateful multi-step workflows
- **CrewAI** for role-based multi-agent patterns (used when task is strongly role-typed, e.g., "researcher + writer")
- **Claude Sonnet 4.5** for planning and complex writes (via `langchain-anthropic`)
- **Claude Haiku 4.5** for summarization/synthesis (high volume, cost-sensitive)
- **Redis** for sub-agent state + pub/sub streaming

Never hardcode model names. Read from `settings.anthropic_model_sonnet` and `settings.anthropic_model_haiku`.

## Layout

```
app/
├── main.py
├── config.py
├── graphs/
│   └── planner.py       parse_intent → retrieve_context → plan → execute → synthesise
├── agents/
│   ├── read.py          reads any connected tool
│   ├── write.py         writes with confirmation gate
│   ├── research.py      web + docs research
│   ├── summarise.py     Haiku-backed summarization
│   └── synthesise.py    Sonnet-backed multi-source synthesis
├── tools/
│   └── connectors.py    LangGraph tool adapters that call connector-manager
└── clients/
    ├── memory.py
    ├── eval.py
    └── connector_manager.py
```

## The core loop

```
prompt → parse_intent (Sonnet)
       → retrieve_context (memory-service)
       → plan (Sonnet) — user approves on complex tasks
       → execute (fan out to sub-agents, max 5 parallel)
          ├─ read_agent(tool)
          ├─ research_agent
          └─ write_agent(tool) ← pauses for confirmation
       → synthesise (Sonnet for writes, Haiku for reads)
       → persist AgentAction
       → fire-and-forget eval score (eval-engine)
       → return result + task tree to client
```

## Confirmation gate

Every write action requires one of:
1. Explicit user confirmation (default, trust=low)
2. Auto-confirm for low-risk writes when trust_level=high (Notion append, GitHub comment, Linear comment)

Gmail send, GitHub force-push, Drive destructive edits are **always** gated regardless of trust.

Pause points are represented in the LangGraph state as `pending_confirmations: list[ConfirmationRequest]`. The graph halts; the api-gateway WebSocket pushes them to the client; the user approves; a follow-up POST resumes the graph.

## Dev

```bash
cd services/agent-orchestration
uv run uvicorn app.main:app --reload --port 8001
```

## Don't

- Don't add a sixth concurrent sub-agent. Cap is 5 per spec §6.7.
- Don't block on tool calls — everything is `async`. Use `asyncio.gather` for fan-out.
- Don't silently swallow sub-agent errors. Retry once, fallback to simpler single-step, surface failure to user.
- Don't skip the eval step to save tokens. The eval is the moat.
- Don't implement tool-specific logic here. Use the connectors.
