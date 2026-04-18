# Plugin System + Multi-Step Workflow Architecture

**Date:** 2026-04-18

---

## Plugin Directory Structure

```
services/agent-orchestration/app/
├── capabilities/              ← registry + base protocol (the engine)
│   ├── base.py                  Capability protocol, Citation, CapabilityResult
│   ├── registry.py              Auto-loads from capabilities/ AND plugins/
│   ├── activity.py              Internal: activity.query
│   ├── memory.py                Internal: memory.retrieve
│   ├── universal_search.py      Internal: connector.search (local index FTS)
│   ├── slack.py                 Slack: 6 capabilities
│   ├── notion.py                Notion: search
│   ├── notion_write.py          Notion: append (write)
│   ├── gdrive.py                Drive: 3 capabilities
│   ├── gmail.py                 Gmail: search
│   └── github.py                GitHub: search
│
├── plugins/                   ← organized per-connector (the catalog)
│   ├── __init__.py              Plugin system docs
│   ├── manifest.py              Generates human + machine-readable manifest
│   ├── slack/__init__.py        Re-exports 6 caps from capabilities/slack.py
│   ├── notion/__init__.py       Re-exports 2 caps (search + append)
│   ├── gdrive/__init__.py       Re-exports 3 caps (search + read + create)
│   ├── gmail/__init__.py        Re-exports 1 cap (search)
│   ├── github/__init__.py       Re-exports 1 cap (search)
│   └── internal/__init__.py     Re-exports 3 caps (activity, memory, universal)
```

**Why two layers:**
- `capabilities/` = the LOGIC (dataclass, __call__, client wiring)
- `plugins/` = the ORGANIZATION (per-connector grouping, manifest, future config)

Adding a new plugin:
1. Create `capabilities/<tool>.py` with a `CAPABILITY` or `CAPABILITIES` export
2. Create `plugins/<tool>/__init__.py` that imports and re-exports them
3. Done — the registry picks up both automatically

---

## How Claude Knows What Tools to Use

```
Every /run call:

  registry = get_registry()
  tools = registry.anthropic_tools()
  
  → builds a list of 16 tool dicts:
  [
    {
      "name": "connector_slack_search",
      "description": "Search the user's Slack workspace...",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Keywords to search for."},
          "limit": {"type": "integer", "default": 20}
        },
        "required": ["query"]
      }
    },
    ... 15 more
  ]

  → passed as tools= to Claude:
  
  resp = await client.messages.create(
      model="claude-sonnet-4-5",
      system=[base_prompt + user_delta],
      tools=tools,          ← Claude sees ALL 16 capabilities
      messages=messages,
  )
```

Claude reads every tool's `name`, `description`, and `input_schema` and
decides which to call based on the user's prompt. This IS the state-of-
the-art pattern — it's exactly how:

- **Dust.tt** registers "actions" with JSON Schema
- **OpenAI** function calling works
- **Claude Connectors** registers tools via MCP
- **LangGraph** exposes tools to the model

The model is not guessing. It sees the full catalog on every call.

---

## Example: "Create an analysis of all funding required in 2023"

**Prompt:** "Read my Slack and Google Sheets for anything about funding
requirements in 2023. Check if a16z was mentioned anywhere. Export a
summary report as a new Google Doc."

### Iteration 1: Claude reads the prompt + 16 tool descriptions

Claude decides: "I need to search Slack AND search Drive for funding info."

```
Response: stop_reason='tool_use'
  tool_use: connector_slack_search {query: "funding 2023 a16z"}
  tool_use: connector_gdrive_search {query: "funding 2023"}
```

Both run IN PARALLEL via asyncio.gather (2-5s instead of 10s sequential).

### Iteration 2: Claude sees the results, decides to read a specific Sheet

```
Response: stop_reason='tool_use'
  tool_use: connector_gdrive_read_content {file_id: "1abc...xyz"}
```

Reads the full content of the Google Sheet as CSV (up to 50KB).

### Iteration 3: Claude has all the data, creates the report

```
Response: stop_reason='tool_use'
  tool_use: connector_gdrive_create_doc {
    title: "Funding Analysis 2023 — a16z",
    content: "## Summary\n\nBased on Slack discussions and the Q3 funding
    tracker sheet...\n\n### Key findings:\n1. Total funding required: $X\n
    2. a16z mentioned in 3 Slack threads...\n3. ..."
  }
```

Permission gate fires (write action) → user clicks "Allow" → Doc created.

### Iteration 4: Claude synthesizes the final answer

```
Response: stop_reason='end_turn'
  text: "I've analyzed your Slack messages and Google Sheets for 2023
  funding information. a16z was mentioned in 3 threads. I created a
  summary report here: [Funding Analysis 2023](https://docs.google.com/...)
  
  Key findings:
  - Total discussed funding: $2.5M across Q1-Q3
  - a16z was referenced by Alice in #fundraising on March 12..."
```

**Total: 4 iterations, ~15s, 5 tool calls, 1 new Google Doc created.**

### The data flow:

```
User prompt
    │
    ▼
Claude sees 16 tools
    │
    ├── Iteration 1 (parallel):
    │     connector.slack.search("funding 2023 a16z")
    │       → 8 Slack messages found
    │     connector.gdrive.search("funding 2023")
    │       → 3 Drive files found (including a Sheet)
    │
    ├── Iteration 2:
    │     connector.gdrive.read_content(file_id="...")
    │       → full CSV content of the funding tracker Sheet
    │
    ├── Iteration 3 (gated write):
    │     connector.gdrive.create_doc(title, content)
    │       → permission.request event → user approves
    │       → new Google Doc created, URL returned
    │
    └── Iteration 4:
          Claude synthesizes everything → final output with link
```

---

## Plugin Manifest (machine-readable)

```
AXIS PLUGIN MANIFEST — 16 capabilities

[slack] 6 caps (4R / 2W)
  READ  AUTO   connector.slack.search
  READ  AUTO   connector.slack.channel_summary
  READ  AUTO   connector.slack.thread_context
  READ  AUTO   connector.slack.user_profile
  WRITE GATED  connector.slack.post
  WRITE GATED  connector.slack.react

[notion] 2 caps (1R / 1W)
  READ  AUTO   connector.notion.search
  WRITE GATED  connector.notion.append

[gdrive] 3 caps (2R / 1W)
  READ  AUTO   connector.gdrive.search
  READ  AUTO   connector.gdrive.read_content
  WRITE GATED  connector.gdrive.create_doc

[gmail] 1 caps (1R / 0W)
  READ  AUTO   connector.gmail.search

[github] 1 caps (1R / 0W)
  READ  AUTO   connector.github.search

[internal] 3 caps (3R / 0W)
  READ  AUTO   activity.query
  READ  AUTO   memory.retrieve
  READ  AUTO   connector.search (universal FTS)
```

---

## Comparison with State-of-the-Art

| Feature | Axis | Dust.tt | Claude Connectors | OpenAI GPTs |
|---|---|---|---|---|
| Tool registry → model | tools= param with JSON Schema | "actions" with schema | MCP tool registry | function calling |
| Model picks tools | Yes (Claude auto-selects) | Yes (model auto-selects) | Yes (Claude auto-selects) | Yes (GPT auto-selects) |
| Multi-step chaining | Yes (5 iterations max) | Yes (configurable) | Yes (limited) | Yes (limited) |
| Parallel tool calls | Yes (asyncio.gather) | No (sequential) | No (sequential) | Yes (parallel function calls) |
| Permission gating | Yes (auto/ask/always_gate) | No | No | No |
| Write diff preview | Yes (DiffViewer) | No | No | No |
| Plugin manifest | Yes (auto-generated) | Partial | No | No |
| Background execution | Yes (mode=background) | No | No | No |

**Axis matches or exceeds every competitor on tool-use architecture.**
The plugin system is well-aligned with industry standards — the model
sees the full catalog, picks the right tools, and chains them across
iterations. The parallel dispatch + permission gating + background mode
are unique advantages.
