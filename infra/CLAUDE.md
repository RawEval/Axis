# CLAUDE.md — infra/

Everything that isn't application code.

## Layout

- `docker/` — local dev infrastructure via Docker Compose
- `railway/` — Phase 1 deploy target
- `terraform/` — Phase 2 AWS multi-region (stub)
- `k8s/` — Phase 3 (stub)

## Local docker stack

`docker/docker-compose.yml` defines:

| Container | Purpose | Port |
|---|---|---|
| axis-postgres | primary DB | 5432 |
| axis-redis | cache, Celery broker | 6379 |
| axis-qdrant | vector store | 6333 (REST) / 6334 (gRPC) |
| axis-neo4j | memory graph | 7474 (UI) / 7687 (bolt) |
| axis-mailhog | local email | 1025 (SMTP) / 8025 (UI) |

`docker/init/postgres/001_init.sql` is the canonical schema. Every new table and migration goes here with a numbered prefix (002_, 003_, ...). **Do not edit 001 — append new files.**

## Commands

```bash
make infra-up        # start everything
make infra-down      # stop everything (volumes persist)
make infra-logs      # tail
```

To wipe local data: `docker compose -f infra/docker/docker-compose.yml down -v` (removes volumes).

## Railway (Phase 1)

Each service deploys from its own Dockerfile. Plan: one Railway project, services link via internal hostnames. Managed Postgres and Redis via Railway plugins. Qdrant and Neo4j as custom services. Secrets via Railway env vars synced from local `.env` (never committed).

## Terraform (Phase 2)

Planned stack:
- ECS Fargate per service (one task def each)
- RDS Postgres (ap-south-1 primary, eu-west-1 replica for EU residency)
- ElastiCache Redis
- Qdrant Cloud or self-hosted on EKS
- Neo4j Aura Enterprise
- R2 for snapshots (not S3 — egress matters)
- CloudFront + Route53 + ACM

Not touched until Phase 1 validates PMF.

## Rules

- **Infra changes must be reversible.** Migrations are append-only. No destructive SQL without a backup plan.
- **Never commit credentials.** Not in compose, not in .env.example, not in terraform. Use `${VAR}` substitution.
- **Test schema changes locally first.** `make infra-down -v && make infra-up` — confirm init runs clean.
- **Phase alignment.** Railway is P1. AWS is P2+. Don't skip ahead.

## Don't

- Don't add a new service to the compose file without also wiring it into CI + the CLAUDE.md service registry.
- Don't use `:latest` image tags in anything beyond local dev.
- Don't put secrets in init SQL.
