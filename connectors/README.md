# Connectors

Each connector is a thin async client around a vendor API. The wrapper lives in `connectors/<tool>/src/client.py`. The agent-facing logic — searches, reads, writes — lives in `services/connector-manager/app/routes/tools.py`, which imports the client and exposes HTTP endpoints under `/tools/<tool>/*`.

## Layout (per tool)

```
connectors/<tool>/
  src/client.py         # Vendor API wrapper. Imported by services.
  pyproject.toml        # Python deps for the client (e.g. slack-sdk).
```

## How a request flows

```
agent-orchestration capability  ──►  ConnectorManagerClient HTTP call
  ──►  /tools/<tool>/<op>  (services/connector-manager/app/routes/tools.py)
  ──►  client.py method    (connectors/<tool>/src/client.py)
  ──►  vendor API
```

Background indexing follows the same pattern via `services/connector-manager/app/sync/<tool>_sync.py`.

OAuth lives in `services/connector-manager/app/oauth/<tool>.py`. Webhook receivers live in `services/connector-manager/app/routes/webhooks.py`.

## Phase 1 (launch) — what's actually live

| Tool   | OAuth | Read endpoints                          | Write endpoints       | Real-time listener   |
|--------|-------|------------------------------------------|-----------------------|-----------------------|
| Slack  | ✓     | search, channels, history, thread, user  | post, react           | Events API webhook    |
| Notion | ✓     | search, get blocks                       | append blocks         | 15-min poll           |
| Gmail  | ✓     | search                                   | —                     | — (Pub/Sub planned)   |
| GDrive | ✓     | search, read                             | create-doc, append    | — (push planned)      |
| GitHub | ✓     | search                                   | —                     | — (webhooks planned)  |

`services/connector-manager/app/routes/tools.py` is the canonical list — this table summarizes; the route file is truth.

## Phase 2 (planned, not scaffolded)

Linear · Google Calendar · Jira · Airtable · Local Filesystem.

## Phase 3 (planned, not scaffolded)

Confluence · HubSpot · Figma · Zoom / Meet · Obsidian.

## Adding a new connector

1. Create `connectors/<tool>/src/client.py` with thin async methods around the vendor API.
2. Add `connectors/<tool>/pyproject.toml` with the SDK / httpx deps.
3. Add OAuth at `services/connector-manager/app/oauth/<tool>.py`.
4. Add HTTP routes at `services/connector-manager/app/routes/tools.py` (`/tools/<tool>/<op>`) that call the client.
5. Add capability classes at `services/agent-orchestration/app/capabilities/<tool>.py` so the agent can dispatch.
6. Add the tool to `apps/web/lib/queries/connectors.ts` `Tool` union and the `TOOLS` array on `apps/web/app/(app)/connections/page.tsx`.
7. Add the tool's capabilities to `apps/web/lib/capabilities.ts` so users can tune trust mode.
8. If the vendor supports real-time push: webhook handler in `services/connector-manager/app/routes/webhooks.py` + a `<tool>_sync.py` for backfill.

## Rules

- **No `Connector` base class.** Tried it; nothing inherited from it; ripped it out.
- **`client.py` is pure I/O.** No service code, no DB calls, no logging of tokens.
- **Writes go through the gating layer in agent-orchestration**, not the route handler. The route handler is the dumb executor.
- **No dead code.** If you scaffold and don't get to the implementation, delete the directory.
