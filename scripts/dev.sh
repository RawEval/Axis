#!/usr/bin/env bash
# Start all services + web app for local development.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Starting local infra…"
docker compose -f infra/docker/docker-compose.yml up -d

echo "Starting web + services (parallel)…"
pnpm turbo run dev --parallel
