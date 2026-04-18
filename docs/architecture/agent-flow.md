# Agent Execution Flow

Maps spec §6.2 and §6.7 into concrete service calls.

```
User prompt
    │
    ▼
API Gateway (/agent/run)
    │
    ▼
Agent Orchestration
    │
    ├─▶ parse_intent       (Sonnet 4.5)
    │      → action type, tools, entities, time range
    │
    ├─▶ retrieve_context   (Memory Service)
    │      → episodic + semantic + procedural
    │
    ├─▶ plan               (Sonnet 4.5)
    │      → multi-step plan shown to user for complex tasks
    │
    ├─▶ execute            (LangGraph → sub-agents in parallel, max 5)
    │      ├─ read_agent   (any connector)
    │      ├─ research     (web / docs)
    │      └─ write_agent  (requires confirmation gate)
    │
    ├─▶ synthesise         (Sonnet 4.5 for writes, Haiku 4.5 for summaries)
    │
    └─▶ eval               (Eval Engine — Haiku-as-judge, async)
           → surfaces quality indicator, logs for correction loop
```

## Confirmation gates

Default: pause before any write. User approves or modifies the diff preview.
Trust level 'high' (earned) → auto-confirm low-risk writes (Notion append,
GitHub comment). Sends are *always* gated regardless of trust level.
