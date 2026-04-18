# Project Router — the "user level 2"

**Decision date:** 2026-04-16
**Status:** Active
**ADR number:** 004

## Context

Once users have more than one project, every incoming prompt has an ambiguity: **which project is this about?** The user typing "summarize what happened in Slack this week" could mean their internal ops project, their Acme engagement, or both.

Forcing the user to pick a project every time works but is hostile. The whole point of Axis is to reduce cognitive load, not add more. We need a routing layer that figures out project scope from the context of the request.

## Design

The project router is the **first node** in the LangGraph planner. It runs before intent parsing. It answers one question: **which project(s) should this agent run execute against?**

Three modes, in priority order:

1. **Explicit pin (always wins)** — the UI has an active project selected. The frontend sends `X-Axis-Project: <uuid>`. The router returns `[<uuid>]`. Zero overhead, zero ambiguity.

2. **All projects mode** — the UI sent `X-Axis-Project: all`. The router returns every project_id the user owns. The orchestrator fans out and merges.

3. **Auto mode** — no header or the header says `auto`. The router runs a Haiku classifier:
   - Input: the user prompt + `[{id, name, description, active_tool_names}, …]` for every project the user owns
   - Prompt: "Which project(s) below is the user asking about? Return JSON: `{projects: [ids], confidence: 0-1, reason: string}`"
   - Fallback: if confidence < 0.6, ask the user a clarifying question inline instead of guessing

## Why Haiku, not Sonnet

Classification is a high-volume low-stakes task:
- Short input (prompt + project metadata)
- Short output (list of IDs)
- Runs on every agent call (before the "real" Sonnet call)
- Latency budget: 200ms

Haiku 4.5 nails this. Cost is trivial (~$0.0001 per classification). Per spec §8.4.

## Schema additions

No new tables. The router reads from `projects` for the owner's project list.

For caching, we reuse the existing prompt cache breakpoint — the project list is a stable "tools" block that barely changes, so it caches across runs of the same user's sessions.

## State additions

The `AgentState` typed dict gains:

```python
class AgentState(TypedDict, total=False):
    user_id: str
    project_ids: list[str]        # NEW: populated by route_project node
    project_scope: str             # NEW: 'explicit' | 'all' | 'auto'
    ambiguous: bool                # NEW: router flags low-confidence classifications
    prompt: str
    # … existing fields
```

## Graph topology

```
START
  ↓
route_project    ← new node (Haiku classifier or trivial lookup)
  ↓
  ├─ if len(project_ids) == 0 → clarify_user → END (asks "which project?")
  ├─ if len(project_ids) == 1 → parse_and_synthesise (current node)
  └─ if len(project_ids) > 1  → fan_out (N parallel agent runs) → merge_results → END
```

The fan-out branch is where the multi-project "ask about all my projects" experience lives. Each sub-run is a full single-project execution with its own connector tool calls. The merger is a second Sonnet call that takes the N project-scoped outputs and produces one unified answer.

## Examples

### Case 1 — explicit pin

```
User in UI: active project = "Acme Engagement"
Prompt: "Draft a Notion page summarizing this week"
X-Axis-Project: 7c2f…
  → route_project returns ["7c2f…"]
  → parse_and_synthesise runs with Acme's Notion credentials
  → response: "Here's a draft Notion page for your Acme engagement…"
```

### Case 2 — all projects

```
User in UI: active project = "All projects"
Prompt: "What follow-ups am I owing anyone?"
X-Axis-Project: all
  → route_project returns [project_1, project_2, project_3]
  → fan_out: three parallel reads of connector data
  → merge: Sonnet composes one answer organized by project
  → response: "You owe 3 follow-ups — 1 in Internal Ops (@aditi, Slack), 2 in Acme (contract doc, Drive; status update, Gmail)…"
```

### Case 3 — auto classification

```
User in UI: no active project selected
Prompt: "What did Aditi say about the vendor renewal?"
X-Axis-Project: auto
  → Haiku classifier sees: "vendor renewal" + projects [Internal Ops, Acme, Personal]
  → returns {projects: ["internal-ops-uuid"], confidence: 0.83, reason: "vendor context is company-internal"}
  → parse_and_synthesise runs in Internal Ops
  → response: "From Slack yesterday: Aditi said she pushed the renewal to Q3…"
```

### Case 4 — auto, low confidence

```
Prompt: "Did we make a decision on the pricing?"
  → Haiku returns {projects: ["acme-uuid", "internal-ops-uuid"], confidence: 0.44, reason: "pricing applies to both contexts"}
  → confidence < 0.6 → clarify node fires
  → response: "I see 'pricing' discussed in both Internal Ops and Acme Engagement. Which one?"
```

## What we ship Phase 1 vs defer

**Ship this turn:**
- `route_project` node with explicit pin + all-mode branches
- `AgentState` plumbing for `project_ids` and `project_scope`
- The gateway forwards `X-Axis-Project` to orchestration
- Frontend sends the header from a Zustand-backed active-project store
- If mode is `auto` with a single project, trivially pick it (covers 100% of new-user case)

**Defer:**
- Haiku classifier for auto mode (need real multi-project users to tune it)
- Clarify node (blocks on streaming infra)
- Fan-out + merge (need a SynthesisResult typed interface first)

## Non-goals

- Cross-project writes in a single action. A single agent action targets one project. Multi-project fan-out is N separate actions merged at the end.
- Implicit sharing. The router never reveals data from Project A to Project B even when answering a multi-project query. Each sub-run stays isolated; the merger only sees the sub-outputs, not the raw connector data.

## See also

- `projects-model.md`
- `prompt-flow.md`
