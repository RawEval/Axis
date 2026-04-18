# CLAUDE.md — packages/

Shared libraries consumed by apps and services. **Nothing here runs — these are pure modules.**

## What's in here

| Package | Lang | Consumers |
|---|---|---|
| `design-system` | TS/React | `apps/web`, eventually `apps/desktop` |
| `shared-types` | TS | `apps/web`, `apps/desktop` |
| `kmm-shared` | Kotlin Multiplatform | `apps/mobile-ios`, `apps/mobile-android` |

## design-system

Tailwind tokens + primitive React components. Imports via `@axis/design-system`. Theme tokens are the source of truth for colors, spacing, radius. If you need a new token, add it here first, then extend the Tailwind config in `apps/web/tailwind.config.ts` to reference it.

## shared-types

Pure TypeScript types that mirror the Pydantic models in services. One file per domain (users, connectors, actions, surfaces, memory). When a Pydantic model changes in a service that crosses the API boundary, update this package in the same PR.

Phase 2 goal: auto-generate from `/openapi.json` via `openapi-typescript`. For now, hand-written but kept 1:1 with the backend.

## kmm-shared

Kotlin Multiplatform business logic shared between iOS and Android. Connector auth, memory retrieval, response parsing, canonical data types. Does *not* include UI — that's native per platform. Phase 2 deliverable.

## Rules

- **No runtime.** These packages must be pure. No server, no env reads, no side effects at import time.
- **No circular deps.** `design-system` does not import from `shared-types` and vice versa.
- **Stable API.** Every exported symbol is public contract. Breaking changes require updating all consumers in the same PR.
- **Tree-shakeable.** ES modules, named exports only.

## Don't

- Don't add state libraries here (no Zustand, no Redux).
- Don't depend on Next.js — these should work in any React runtime.
- Don't depend on a specific database client.
- Don't add a package just because it feels shared. Two consumers minimum.
