# CLAUDE.md — services/connector-manager

Owns the OAuth lifecycle, token encryption, sync scheduling, and connector health for every tool. Spec §6.1, §07. Read `services/CLAUDE.md` first.

## Responsibilities

- OAuth 2.0 consent URL generation per tool
- OAuth callback: exchange code → encrypted token in Postgres
- Token refresh on 24h cycle + red/yellow/green health status
- Sync scheduling: Celery jobs per tool (Slack events, Notion 15m poll, etc.)
- Connector health API: `/health/<user_id>` returns status per connected tool
- Tool call proxy: agent-orchestration asks "read N most recent slack messages for user X" and we dispatch to the connector module

## Not responsibilities

- Do not understand the *content* of tool data. Just fetch and index it.
- Do not run LLMs. This is dumb infrastructure.
- Do not decide what to show the user. That's agent-orchestration + proactive-monitor.

## Encryption

Every OAuth token is encrypted with AES-256-GCM before writing to Postgres, using a key from `TOKEN_ENCRYPTION_KEY` (32 bytes, base64). Decryption happens *only* in memory at call time. Never log decrypted tokens.

## Sync schedule (spec §6.1)

| Tool | Mechanism | Frequency |
|---|---|---|
| Slack | Events API webhook | real-time |
| Gmail | Pub/Sub push | real-time |
| Drive | Drive push notifications | real-time |
| GitHub | Webhooks | real-time |
| Notion | Celery poll | 15 min |
| Linear | Webhooks | real-time |
| Jira | Webhooks | real-time |
| Airtable | Celery poll | 15 min |

## Health status

- **Green** — last sync successful, token valid
- **Yellow** — token expires within 7 days, or last sync > 2× expected interval
- **Red** — auth failure, revoked, or last sync failed 3× in a row

Users see this as a dot on the Connections page.

## Layout

```
app/
├── main.py
├── config.py
├── db.py
├── security.py        encrypt_token / decrypt_token (AES-256-GCM)
├── oauth/
│   ├── slack.py       per-tool OAuth URL + code exchange
│   ├── notion.py
│   ├── gmail.py
│   ├── gdrive.py
│   └── github.py
├── sync/
│   ├── scheduler.py   Celery beat config
│   └── tasks.py       poll_notion, refresh_tokens, ...
├── repositories/
│   └── connectors.py
└── routes/
    ├── health.py
    ├── oauth.py       /oauth/{tool}/start, /oauth/{tool}/callback
    └── connectors.py  GET /connectors, DELETE /connectors/{tool}
```

## Dev

```bash
cd services/connector-manager
uv run uvicorn app.main:app --reload --port 8002

# Start Celery worker in another terminal
uv run celery -A app.sync.scheduler worker -B -l info
```

## Don't

- Don't store raw tokens. Ever.
- Don't log tokens, even encrypted.
- Don't add a connector without copying the existing pattern and implementing all four capabilities (index, listen, query, write).
- Don't skip health status updates — the user sees them on the Connections page.
