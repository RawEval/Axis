# CLAUDE.md — connectors/

One module per external tool. Each implements the same four-capability `Connector` protocol. Spec §07.

## The protocol

Defined in `connectors/_base/connector.py`:

```python
class Connector(ABC):
    tool_name: str
    supports_write: bool = False

    async def index(self, user_id, since=None) -> list[dict]: ...
    async def listen(self, user_id) -> None: ...
    async def query(self, user_id, query) -> list[dict]: ...
    async def write(self, user_id, action) -> dict: ...  # override if supports_write
```

| Method | Purpose |
|---|---|
| `index` | Pull all (or incremental since last cursor) content into the user's Qdrant namespace |
| `listen` | Subscribe to real-time updates — webhook, Pub/Sub, polling, file watcher |
| `query` | Answer a specific structured question (not LLM — this is API calls) |
| `write` | Push an action back to the tool. Must include a rollback-able diff. |

## Inventory

**Phase 1 (launch):**
- `slack/` — OAuth 2 + Events API + chat.postMessage
- `notion/` — OAuth 2 + 15-min poll + pages/databases write
- `gmail/` — OAuth 2 + Pub/Sub push + draft/send (send ALWAYS requires confirmation)
- `gdrive/` — OAuth 2 + Drive push + Docs create/edit
- `github/` — OAuth 2 + webhooks + commit file / PR comment (MD write-back is the core UX)

**Phase 2 (90 days) — `_phase2/`:**
- `linear/`, `gcalendar/`, `jira/`, `airtable/`, `local-fs/`

**Phase 3 (180 days):**
- Confluence, HubSpot, Figma, Zoom/Meet, Obsidian

## Adding a new connector

1. Copy an existing `<tool>/` directory as scaffold.
2. Implement the four methods from `connectors/_base/connector.py`.
3. Add pyproject.toml with the minimal vendor SDK dependency.
4. Register OAuth start/callback in `services/connector-manager/app/oauth/<tool>.py`.
5. Add sync task in `services/connector-manager/app/sync/tasks.py`.
6. Add to the tool matrix in `connectors/README.md`.
7. Add Phase + priority to the spec if the tool isn't already listed (§07).
8. **Write integration tests** that hit a sandbox account. No mocks for connector logic — too risky.

## Layout (per tool)

```
connectors/<tool>/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── connector.py     implements Connector
│   ├── client.py        thin wrapper around the vendor SDK
│   └── mapping.py       vendor object → Axis canonical type
└── tests/
    └── test_connector.py   uses sandbox credentials
```

## Rules

- **Writes are diffed before execution.** Connector returns a `{before, after}` diff; the execution layer shows it; user confirms; only then does `write()` actually fire.
- **Never log OAuth tokens.** Even encrypted.
- **Always take a snapshot before a destructive write** (Drive, Notion, GitHub). Store the snapshot ID in `write_actions.snapshot_id` for 30-day rollback.
- **Connector is stateless.** All state (tokens, cursors, last-sync) lives in Postgres, owned by connector-manager.
- **Use vendor SDKs where mature.** (`slack-sdk`, `google-api-python-client`, `pygithub`) Hand-roll HTTP only when the SDK is missing a feature.

## Don't

- Don't call Claude from a connector. Connectors are pure I/O.
- Don't import from `services/` — connectors are libraries, not services.
- Don't add a new connector without user approval. Connectors have maintenance cost (§15 risk: "connector API maintenance graveyard").
- Don't silently retry indefinitely on 4xx — bubble it up as a health-yellow signal.
