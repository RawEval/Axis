# CLAUDE.md — connectors/

Each connector is a thin async client around a vendor API. **No `Connector` base class** — that pattern was tried and removed because nothing actually inherited from it correctly. The real agent-facing dispatch lives in `services/connector-manager/app/routes/tools.py`.

## What's in here

```
connectors/<tool>/
  src/client.py         # Imported by services. The only file that matters.
  pyproject.toml        # Python deps for the client.
```

That's it. Keep it minimal. If you find yourself adding a `connector.py` or a base protocol — stop, you're recreating the dead architecture.

## Where things actually live

| Thing                                   | Location                                                       |
|-----------------------------------------|----------------------------------------------------------------|
| Vendor API client                       | `connectors/<tool>/src/client.py`                              |
| OAuth flow                              | `services/connector-manager/app/oauth/<tool>.py`               |
| Tool HTTP endpoints (`/tools/<tool>/*`) | `services/connector-manager/app/routes/tools.py`               |
| Webhook receiver                        | `services/connector-manager/app/routes/webhooks.py`            |
| Background sync (poll/backfill)         | `services/connector-manager/app/sync/<tool>_sync.py`           |
| Agent capability classes                | `services/agent-orchestration/app/capabilities/<tool>.py`      |
| Frontend tool union + capability list   | `apps/web/lib/queries/connectors.ts`, `apps/web/lib/capabilities.ts` |

## Adding a new connector

See the steps in `connectors/README.md`. Order matters — `client.py` first, then OAuth, then routes, then capabilities, then the frontend.

## Don't

- Don't reintroduce a `Connector` base class. The deleted one is in git history if you really need to look.
- Don't put service code (DB calls, repository imports) in `client.py`. Clients only know about the vendor API.
- Don't leave dead stubs around. If you scaffold a connector and don't get to the real implementation, delete the directory.
- Don't call Claude from a connector. Connectors are pure I/O.
- Don't silently retry indefinitely on 4xx — bubble it up as a health-yellow signal.
