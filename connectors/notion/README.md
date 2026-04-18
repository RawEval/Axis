# connectors/notion

Notion Phase-1 connector. Implements read (search/get page/blocks) and write
(append/create page). Uses the REST API via `httpx`.

## Status

- ✅ Client (`src/client.py`) — search, get_page, get_page_blocks, append_blocks, create_page
- ✅ OAuth flow — lives in `services/connector-manager/app/oauth/notion.py`
- ⏳ Sync task — poll-every-15-minutes job not yet implemented
- ⏳ Write diff preview — rendered in web via `DiffViewer` component (stubbed)

## Auth

Uses the standard OAuth 2.0 Authorization Code grant. Tokens are workspace-scoped
and long-lived (no refresh). Docs: https://developers.notion.com/docs/authorization

## Notion MCP (alt path — not yet wired)

Notion also hosts an official MCP server at `https://mcp.notion.com/mcp` which
speaks OAuth 2.1 + PKCE with refresh token rotation. The `mcp` Python SDK
(installed in `services/agent-orchestration/pyproject.toml`) can connect via
Streamable HTTP. This is the alternative transport for agent-orchestration to
query Notion without going through connector-manager — for future sessions we
may migrate reads to MCP to take advantage of Notion's richer tool surface.

## Usage inside agent-orchestration

```python
from connectors.notion.src.client import NotionClient, paragraph_block
from services.connector_manager.repositories.connectors import ConnectorsRepository
from services.connector_manager.security import decrypt_token

repo = ConnectorsRepository(db.raw)
row = await repo.get_token(user_id=uid, tool="notion")
client = NotionClient(access_token=decrypt_token(row["auth_token_encrypted"]))
results = await client.search("project axis")
```

## Rate limits

Notion allows ~3 requests/second per integration. We don't yet throttle — first
hit will bubble up a 429. Next session: token-bucket via Redis.
