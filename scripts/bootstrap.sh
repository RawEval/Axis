#!/usr/bin/env bash
# Axis — one-shot bootstrap. Installs every toolchain and dependency
# needed for local development.
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say() { printf "${BLUE}▶ %s${NC}\n" "$*"; }
ok()  { printf "${GREEN}✓ %s${NC}\n" "$*"; }
warn(){ printf "${YELLOW}⚠ %s${NC}\n" "$*"; }
err() { printf "${RED}✗ %s${NC}\n" "$*" >&2; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---- Required toolchains -----------------------------------------------
say "Checking toolchains…"

need() { command -v "$1" >/dev/null 2>&1; }

if ! need node; then
  err "node not found. Install Node 20+ (recommended: nvm install 20)"; exit 1
fi
NODE_MAJOR=$(node -v | sed 's/v\([0-9]*\).*/\1/')
if [ "$NODE_MAJOR" -lt 20 ]; then
  err "Node $NODE_MAJOR is too old — need >= 20"; exit 1
fi
ok "node $(node -v)"

if ! need pnpm; then
  warn "pnpm not found — installing via corepack"
  corepack enable && corepack prepare pnpm@9.12.0 --activate
fi
ok "pnpm $(pnpm -v)"

if ! need python3; then
  err "python3 not found. Install Python 3.12+"; exit 1
fi
ok "python $(python3 --version)"

if ! need uv; then
  warn "uv not found — installing"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
ok "uv $(uv --version)"

if ! need docker; then
  warn "docker not found — install Docker Desktop to use local infra"
else
  ok "docker $(docker --version | cut -d, -f1)"
fi

# ---- JS workspace ------------------------------------------------------
say "Installing JS workspace (pnpm)…"
pnpm install
ok "pnpm workspace installed"

# ---- Python services ---------------------------------------------------
say "Installing Python services (uv)…"
for svc in services/*/; do
  if [ -f "$svc/pyproject.toml" ]; then
    say "  → $svc"
    (cd "$svc" && uv sync) || warn "failed: $svc"
  fi
done
ok "Python services ready"

# ---- Env file ----------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  warn ".env created from template — fill in credentials before running services"
fi

say "Done."
printf "\n${GREEN}Next:${NC}\n"
echo "  make infra-up   # start Postgres/Redis/Qdrant/Neo4j"
echo "  make dev        # run web + backend"
