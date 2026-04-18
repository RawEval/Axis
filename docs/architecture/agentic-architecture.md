# Agentic Architecture — supervisor + workers + capabilities

**Decision date:** 2026-04-16
**Status:** Design (Phase 2 implementation)
**ADR number:** 005

## Context

Phase 1 ships a single-node planner: one Sonnet call answers one prompt. That works for "summarize this Slack thread" but collapses for anything real:

- "Research our top 3 competitors and post a Slack summary tonight"
- "Find every mention of the pricing decision across the last 60 days and draft a decision doc"
- "Our deploy pipeline is broken — look at the GitHub Actions logs, cross-reference with the Linear ticket, and draft a Slack incident update"

These aren't single prompts. They're **tasks** that decompose into sub-tasks, each of which may need different capabilities (browse a webpage, clone a repo, run a grep, call an API, do math). A single Sonnet call is the wrong abstraction. We need an orchestrator that decomposes, dispatches to specialists, and merges results.

## Decision

**Adopt the supervisor + worker pattern in LangGraph**, with a **capability registry** that plugs in new tools/skills without touching the orchestrator.

```
                    ┌─────────────────────┐
                    │     Supervisor      │
                    │  (Sonnet 4.5)       │
                    │  - decomposes task  │
                    │  - dispatches       │
                    │  - gates writes     │
                    │  - synthesizes      │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┬───────────────┐
              │               │               │               │
              ▼               ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Reader   │    │ Writer   │    │ Research │    │ Code     │
        │ agent    │    │ agent    │    │ agent    │    │ agent    │
        │(Haiku)   │    │(Sonnet)  │    │(Sonnet)  │    │(Sonnet)  │
        └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
             │               │               │               │
             └───────────────┴───────────────┴───────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │  Capability   │
                      │   registry    │
                      ├───────────────┤
                      │ connector.*   │
                      │ web.fetch     │
                      │ web.search    │
                      │ git.clone     │
                      │ code.run      │
                      │ math.solve    │
                      │ memory.*      │
                      └───────────────┘
```

## Core concepts

### 1. Task

A **task** is one agent run from the user's point of view. It maps to one `agent_actions` row today; in Phase 2 it will map to one `agent_tasks` row plus many `agent_task_steps` rows.

```sql
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,  -- NULL if 'all'-mode; see projects-model.md
    prompt TEXT NOT NULL,
    scope TEXT NOT NULL,        -- explicit | all | auto
    status TEXT NOT NULL,       -- planning | running | awaiting_confirmation | done | failed
    plan JSONB,                 -- the supervisor's decomposed plan
    result JSONB,               -- final synthesised output
    tokens_used INT,
    latency_ms INT,
    created_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE agent_task_steps (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    parent_step_id UUID REFERENCES agent_task_steps(id),  -- for sub-steps
    agent_role TEXT NOT NULL,   -- reader | writer | research | code | math
    capability TEXT,            -- e.g. 'connector.notion.search'
    input JSONB,
    output JSONB,
    status TEXT NOT NULL,       -- pending | running | done | failed | skipped
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

### 2. Agent role

A **role** is a class of LLM worker. Each role has:
- A base model (Sonnet for writes, Haiku for reads/extracts)
- A system prompt template
- A set of capabilities it is allowed to use
- A token budget per step

Phase-2 roles:

| Role | Model | Typical capabilities |
|---|---|---|
| `reader` | Haiku | `connector.*.read`, `memory.retrieve`, `web.fetch` |
| `writer` | Sonnet | `connector.*.write` (always gated) |
| `research` | Sonnet | `web.search`, `web.fetch`, `connector.*.search` |
| `code` | Sonnet | `git.clone`, `git.grep`, `code.run` (sandboxed) |
| `math` | Haiku | `python.exec` with numpy/sympy |
| `summarise` | Haiku | pure LLM; no capabilities |
| `synthesise` | Sonnet | pure LLM; no capabilities |

New roles are added in `services/agent-orchestration/app/agents/<role>.py`. The supervisor sees the role list at startup and can dispatch to any of them.

### 3. Capability

A **capability** is a typed function the agent can call. Capabilities are plug-ins — you add one without touching the planner, the supervisor just sees more options.

```python
# packages/py-common/src/axis_common/capabilities/base.py  (future)
class Capability(Protocol):
    name: str                   # 'connector.notion.search'
    description: str            # shown to the LLM as tool_use description
    schema: dict                # JSON schema for inputs
    scopes: list[str]           # 'read' | 'write' | 'execute'
    default_permission: str     # 'auto' | 'ask' | 'always-gate'

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str,
        task_id: str,
        step_id: str,
        input: dict,
    ) -> dict: ...
```

### 4. Capability registry

Capabilities live in `services/agent-orchestration/app/capabilities/` and register themselves at import time. At startup the orchestrator builds a `{name: Capability}` map and exposes the set as Anthropic tool-use schemas in every supervisor call.

Per-request, capabilities are **filtered** by:
1. Permission grants (see `permissions-model.md`) — if the user hasn't granted `connector.gmail.read` for this project, the capability is hidden from the supervisor.
2. Project connectors — tools that aren't connected in this project are hidden.
3. User plan — free tier gets read-only capabilities; Pro unlocks writes; Team unlocks code execution.

### 5. Configurable per task

A task can declare **which capabilities it needs** via the frontend:

```json
POST /agent/run
{
  "prompt": "Research our top 3 competitors and draft a Slack post",
  "config": {
    "capabilities": ["web.search", "web.fetch", "connector.slack.write"],
    "roles": ["research", "writer"],
    "max_steps": 10,
    "max_tokens": 8000,
    "max_cost_usd": 0.50
  }
}
```

If `config` is absent, the supervisor uses sensible defaults (all read capabilities + summarise/synthesise; writes only if the prompt clearly asks for one).

## Topology

```
START
  ↓
route_project        ← Phase 1 (project scope)
  ↓
hydrate_context      ← Phase 2: pull user+project profile + memory
  ↓
supervise            ← Phase 2: Sonnet supervisor; loops with tool_use
  ├─ tool_use: capability "a" → workers execute → results
  ├─ tool_use: capability "b" → workers execute → results
  └─ tool_use: permission_required → pause, emit event, wait for grant
  ↓
synthesise           ← Phase 2: final answer
  ↓
persist              ← write agent_tasks + agent_task_steps
  ↓
eval_score (async)   ← fire-and-forget to eval-engine
  ↓
END
```

## Supervisor loop

Claude's tool_use API drives the loop:

```python
while True:
    resp = await client.messages.create(
        model=SONNET,
        system=supervisor_system_prompt(project, role_list, capability_list),
        tools=capability_schemas_for(user_id, project_id),
        messages=history,
    )
    if resp.stop_reason == "end_turn":
        return synthesise(history)

    for block in resp.content:
        if block.type == "tool_use":
            cap = registry[block.name]
            if requires_permission(cap, user_id, project_id):
                yield {"type": "permission_request", "capability": cap.name, ...}
                grant = await wait_for_grant()  # blocks on client confirmation
                if not grant:
                    result = {"error": "permission denied"}
                else:
                    result = await cap(user_id, project_id, ..., input=block.input)
            else:
                result = await cap(user_id, project_id, ..., input=block.input)
            history.append({"role": "user", "content": [{"type": "tool_result", ...}]})
```

The pause-ask-resume semantics require streaming the request ID back to the user while the graph is in a `awaiting_confirmation` state. Covered in `streaming-real-time.md`.

## Configurability hooks

### Per-task config

Already described: frontend sends `config` on `/agent/run`.

### Per-project config

`projects.settings` JSONB can carry:

```json
{
  "default_capabilities": ["web.search", "connector.notion.read"],
  "allowed_roles": ["reader", "research", "summarise"],
  "max_cost_per_task_usd": 0.25,
  "default_trust_level": "medium"
}
```

These become the **defaults** for every task in that project.

### Per-user config

`users.settings` JSONB:

```json
{
  "default_project_config": { ... },
  "capabilities_never_ask": ["connector.notion.read"],  // auto-grant
  "capabilities_always_gate": ["connector.gmail.send"], // always confirm
  "preferred_models": {"supervisor": "claude-sonnet-4-5"}
}
```

## Example: multi-agent task

Prompt: *"Research competitor Acme, clone their public repo, find every mention of 'pricing', draft a Slack summary."*

```
supervisor plans:
  step 1: research.web_search("Acme competitor product pricing")
  step 2: research.web_fetch(top 3 results)
  step 3: code.git_clone("github.com/acme/public")
  step 4: code.grep("pricing", cloned repo)
  step 5: summarise(research + grep output)
  step 6: writer.slack_draft(#product, summary)
  step 7: [pause for user confirmation on step 6]

supervisor dispatches:
  - step 1+2 run in parallel (research agent, 2 concurrent sub-steps)
  - step 3 runs (code agent invokes git.clone capability)
  - step 4 runs (code agent invokes git.grep capability, blocks on step 3)
  - step 5 runs (summarise role, Haiku)
  - step 6 drafts the message (writer role, Sonnet)
  - step 7 emits permission_request → client shows DiffViewer → user approves
  - step 6 actually executes via connector.slack.write
```

## Safety rails

1. **Max concurrent sub-agents = 5** (spec §6.7).
2. **Max total steps per task = 20** by default; configurable up per project/user.
3. **Max total tokens per task** enforced at the supervisor level. If the budget is blown, the task pauses and asks the user whether to continue.
4. **Destructive capabilities always gated regardless of auto-grant**: `connector.gmail.send`, `connector.github.merge`, `git.push`, `code.run` writes outside a sandbox, any delete.
5. **Capability sandbox**: `code.run` executes in an ephemeral container (gVisor or Firecracker) with no network by default. Network + filesystem scopes are explicit capabilities.

## Migration path from Phase 1

Today: `parse_and_synthesise` is a single node. Phase 2 replaces it with the supervisor loop but keeps the same graph surface so the existing request shape doesn't change. The supervisor gracefully degrades to a single-call if the prompt doesn't require tools.

## Open questions

- **Which MCP servers do we bundle?** Notion's hosted MCP (`mcp.notion.com/mcp`) is already an option. GitHub and Slack don't have first-party MCP servers yet — do we run our own or use the REST APIs? Decision deferred; REST is fine until an MCP server is clearly better.
- **Cost enforcement granularity**: per task or per user per month? Start per-task (simpler), graduate to monthly budgets in Phase 3.
- **How do capabilities expose their state to users?** Each capability should return a short user-visible summary (`"Cloned github.com/acme/public (243 files)"`) that the live task tree surfaces.
- **Cross-project capabilities in 'all' mode**: does a single task get one supervisor that sees all projects, or one per project with a final merger? Propose: one supervisor per project, merger synthesises the final answer. See `project-router.md`.

## See also

- `permissions-model.md` — how grants work
- `activity-feed.md` — what agents read from
- `streaming-real-time.md` — how progress flows back
- `projects-model.md` — the scope of a task
- `use-cases.md` — what tasks actually look like
