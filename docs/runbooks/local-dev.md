# Local Development Runbook

## Prerequisites

- macOS or Linux
- Node 20+ (via nvm)
- Python 3.12+
- Docker Desktop
- Xcode 15+ (iOS dev only)
- Android Studio Hedgehog+ (Android dev only)

## First-time setup

```bash
git clone <repo>
cd Axis
./scripts/bootstrap.sh
```

This installs pnpm, uv, all JS workspaces, and every Python service.

## Daily dev

```bash
make infra-up      # start postgres/redis/qdrant/neo4j
make dev           # run web + backend in parallel
```

Web: http://localhost:3000
API docs: http://localhost:8000/docs
Qdrant UI: http://localhost:6333/dashboard
Neo4j browser: http://localhost:7474 (neo4j / axis-dev-password)
Mailhog: http://localhost:8025

## Useful commands

```bash
make test          # run everything
make lint          # ruff + eslint
make format        # auto-format
make clean         # nuke build artifacts
make fresh-install # nuke everything and reinstall
```

## Troubleshooting

- **Port already in use:** `lsof -i :3000` (or 8000/5432/6379/7687/6333)
- **Python import errors:** `cd services/<name> && uv sync`
- **Neo4j auth:** default password is `axis-dev-password`
- **Postgres connection refused:** check `make infra-up` has run
