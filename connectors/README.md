# Connectors

Each connector implements four capabilities per spec §07:

| Capability | What it does |
|---|---|
| `index`  | Read all relevant content into the user's Qdrant namespace |
| `listen` | Receive real-time updates (webhooks / Pub/Sub / polling) |
| `query`  | Answer specific questions via structured API calls |
| `write`  | Push actions back to the tool (with confirmation) |

## Phase 1 (launch)

| Tool   | Auth    | Listen     | Write notes |
|--------|---------|------------|-------------|
| Slack  | OAuth 2 | Events API | Post, DM, react |
| Notion | OAuth 2 | Poll 15m   | Create, update, append (MCP-compat) |
| Gmail  | OAuth 2 | Pub/Sub    | Draft, send, label — send requires confirmation |
| Gdrive | OAuth 2 | Push       | Create + edit Docs |
| GitHub | OAuth 2 | Webhooks   | Commit file, comment PR |

## Phase 2 (90 days) — in `_phase2/`

Linear · Google Calendar · Jira · Airtable · Local Filesystem

## Phase 3 (180 days)

Confluence · HubSpot · Figma · Zoom / Meet · Obsidian
