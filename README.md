# Axis

> One app. Connect everything. Just tell it what to do.

Axis is an AI agent platform that connects every tool a startup uses — Slack, Notion, Gmail, Drive, GitHub, Linear, Calendar, and more — and lets teams interact with their entire workspace through a single intelligent agent interface.

**Status:** Phase 1 scaffold · Pre-seed · RawEval Inc, Bengaluru

See `docs/axis_full_spec.docx` for the full product spec.

## Repository Layout

```
axis/
├── apps/                  # User-facing applications
│   ├── web/               # Next.js 14 web app (Phase 1)
│   ├── mobile-ios/        # Swift + SwiftUI (Phase 2)
│   ├── mobile-android/    # Kotlin + Jetpack Compose (Phase 2)
│   └── desktop/           # Electron / Tauri (Phase 3)
│
├── services/              # Backend microservices
│   ├── api-gateway/       # FastAPI — auth, routing, WebSocket
│   ├── agent-orchestration/ # LangGraph — planning + execution
│   ├── connector-manager/ # OAuth, sync scheduling, health
│   ├── proactive-monitor/ # Celery — background signal processing
│   ├── eval-engine/       # LLM-as-judge scoring + correction loop
│   ├── memory-service/    # Neo4j + Qdrant memory graph
│   ├── notification-service/ # Node.js — APNs/FCM/Resend
│   └── auth-service/      # Supabase + JWT
│
├── packages/              # Shared libraries
│   ├── design-system/     # Tailwind tokens + React components
│   ├── shared-types/      # TS types mirrored from Pydantic
│   └── kmm-shared/        # Kotlin Multiplatform business logic
│
├── connectors/            # Per-tool connector modules
│   ├── slack/ notion/ gmail/ gdrive/ github/   # Phase 1
│   └── _phase2/           # Linear, Calendar, Jira, Airtable, LocalFS
│
├── infra/                 # Infrastructure as code
│   ├── docker/            # docker-compose for local dev
│   ├── railway/           # Phase 1 deploy configs
│   ├── terraform/         # Phase 2 AWS multi-region
│   └── k8s/               # Phase 3 manifests
│
├── docs/                  # Architecture, API, runbooks
├── scripts/               # Bootstrap, dev, seed
└── .github/workflows/     # CI/CD
```

## Quickstart

```bash
# 1. Install toolchains (once)
./scripts/bootstrap.sh

# 2. Start local infra (Postgres, Redis, Qdrant, Neo4j)
make infra-up

# 3. Start all services + web app
make dev

# 4. Open
open http://localhost:3000
```

## Tech Stack

| Layer | Stack |
|---|---|
| Web | Next.js 14 · TypeScript · Tailwind · Zustand · React Query |
| iOS | Swift · SwiftUI · iOS 16+ |
| Android | Kotlin · Jetpack Compose · Android 12+ |
| Shared mobile logic | Kotlin Multiplatform (KMM) |
| Backend | Python 3.12 · FastAPI · LangGraph · CrewAI · Celery |
| Databases | PostgreSQL (Supabase) · Qdrant · Neo4j · Redis |
| Storage | Cloudflare R2 |
| LLMs | Claude Sonnet 4.5 (planning/writes) · Haiku 4.5 (summarise/eval) |
| Hosting | Railway (P1) → AWS multi-region (P2+) |
| Package managers | pnpm + Turborepo (JS) · uv (Python) |

## Build Phases

- **Phase 1 · Months 1–3 — MVP.** Web only. 5 connectors (Slack, Notion, Gmail, Drive, GitHub). 10 beta users. Target: 5+ actions/user/week.
- **Phase 2 · Months 3–6 — Scale & Mobile.** iOS + Android. 12 connectors. Proactive layer v1. 100 paying users.
- **Phase 3 · Months 6–12 — Moat.** Full correction loop. Fine-tune pipeline. Multi-agent. 500 users. ₹1.5Cr ARR.

## Licensing

Proprietary · © 2025 RawEval Inc
