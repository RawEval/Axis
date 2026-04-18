# Axis — top-level dev commands
.PHONY: help bootstrap infra-up infra-down infra-logs dev web api \
        test lint format clean fresh-install

help:
	@echo "Axis make targets:"
	@echo "  bootstrap      Install all toolchains and dependencies"
	@echo "  infra-up       Start local Postgres, Redis, Qdrant, Neo4j"
	@echo "  infra-down     Stop local infra"
	@echo "  infra-logs     Tail infra container logs"
	@echo "  dev            Run web + all backend services in parallel"
	@echo "  web            Run web app only"
	@echo "  api            Run api-gateway only"
	@echo "  test           Run all tests"
	@echo "  lint           Run all linters"
	@echo "  format         Auto-format all code"
	@echo "  clean          Remove all build artifacts"
	@echo "  fresh-install  Nuke node_modules + .venvs and reinstall"

bootstrap:
	./scripts/bootstrap.sh

infra-up:
	docker compose -f infra/docker/docker-compose.yml up -d
	@echo "waiting for services..."
	@sleep 3
	@docker compose -f infra/docker/docker-compose.yml ps

infra-down:
	docker compose -f infra/docker/docker-compose.yml down

infra-logs:
	docker compose -f infra/docker/docker-compose.yml logs -f

dev:
	pnpm turbo run dev --parallel

web:
	pnpm --filter @axis/web dev

api:
	cd services/api-gateway && uv run uvicorn app.main:app --reload --port 8000

test:
	pnpm turbo run test
	@for svc in services/*/; do \
		if [ -f "$$svc/pyproject.toml" ]; then \
			echo "Testing $$svc"; \
			(cd $$svc && uv run pytest) || exit 1; \
		fi \
	done

lint:
	pnpm turbo run lint
	@for svc in services/*/; do \
		if [ -f "$$svc/pyproject.toml" ]; then \
			(cd $$svc && uv run ruff check .) || exit 1; \
		fi \
	done

format:
	pnpm format
	@for svc in services/*/; do \
		if [ -f "$$svc/pyproject.toml" ]; then \
			(cd $$svc && uv run ruff format .) || exit 1; \
		fi \
	done

clean:
	pnpm turbo run clean
	find . -type d -name ".venv" -prune -exec rm -rf {} +
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +

fresh-install:
	rm -rf node_modules .turbo
	find . -type d -name ".venv" -prune -exec rm -rf {} +
	pnpm install
	./scripts/bootstrap.sh
