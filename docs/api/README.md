# API Reference

Each FastAPI service exposes `/docs` (Swagger UI) and `/openapi.json` when running.

| Service | Port | Docs |
|---|---|---|
| api-gateway | 8000 | http://localhost:8000/docs |
| agent-orchestration | 8001 | http://localhost:8001/docs |
| connector-manager | 8002 | http://localhost:8002/docs |
| eval-engine | 8003 | http://localhost:8003/docs |
| memory-service | 8004 | http://localhost:8004/docs |
| notification-service | 8005 | (no Swagger — Fastify) |
| auth-service | 8006 | http://localhost:8006/docs |

## Generating client stubs

```bash
# after services run:
curl http://localhost:8000/openapi.json > docs/api/api-gateway.openapi.json
```

TS clients generated via `openapi-typescript` into `packages/shared-types/src/generated/`.
