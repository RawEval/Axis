# CLAUDE.md — apps/web

Next.js 14 App Router. TypeScript. Tailwind. Zustand for UI state. React Query for server state. Runs on **port 3001** in local dev.

## Purpose

The web app is Phase 1's primary surface. Five views from spec §8.1:
- `/feed` — proactive surfaces + recent actions (default landing)
- `/chat` — the single prompt box; core reactive interface
- `/connections` — OAuth connect/disconnect tools
- `/history` — past agent actions with source traces and rollback
- `/memory` — three-tier memory inspector
- `/settings` — trust level, notifications, data export, billing

Auth-gated routes under `/(app)/*`; public routes under `/(auth)/*` (login, signup).

## Layout

```
app/
├── (app)/             route group for authenticated routes
│   ├── layout.tsx     Sidebar + main
│   ├── feed/page.tsx
│   ├── chat/page.tsx
│   ├── connections/page.tsx
│   ├── history/page.tsx
│   ├── memory/page.tsx
│   └── settings/page.tsx
├── (auth)/            route group for public auth
│   ├── login/page.tsx
│   └── signup/page.tsx
├── layout.tsx         root layout — ONLY <html>, <body>, Providers
├── providers.tsx      React Query + Theme
├── globals.css        Tailwind entry
└── page.tsx           redirects to /feed
middleware.ts          Edge middleware — redirects unauth → /login
components/
├── sidebar.tsx        left nav
├── diff-viewer.tsx    write-back diff (spec §8.1 "Key component")
└── task-tree.tsx      multi-agent execution tree (spec §8.1)
lib/
├── api.ts             typed fetch wrapper w/ Authorization header
├── auth.ts            client-side token storage (httpOnly cookie)
├── ws.ts              WebSocket client for live agent updates
├── store.ts           Zustand UI store
└── queries/           React Query hooks, one file per resource
```

## Rules

- **Server components by default.** Add `'use client'` only when you need state, effects, or browser APIs. Fetching in server components is fine and preferred.
- **Never read `process.env.ANTHROPIC_API_KEY` or any secret in the browser.** Secrets live in the backend. If you need to call a privileged endpoint, do it via a Next.js Route Handler (`app/api/*`).
- **Imports use `@/*`** for apps/web, `@axis/design-system` and `@axis/shared-types` for shared packages. Never reach across into another app or service.
- **React Query is the only server-state store.** Don't duplicate server data in Zustand. Zustand is for pure UI state (active prompt text, modal open state, optimistic trust level).
- **Tailwind, no inline styles.** Use the custom tokens in `tailwind.config.ts` (`bg`, `fg`, `accent`, `success`, `warning`, `danger`). The `.glass` utility is for elevated surfaces.
- **New routes go through the sidebar.** Update `components/sidebar.tsx` whenever you add one.
- **Auth header attached centrally.** Every `fetch` to the backend goes through `lib/api.ts` — it reads the token and adds `Authorization: Bearer <token>`. Never hand-roll fetch.
- **All writes show a diff preview.** When the user is about to confirm a write action, render the `DiffViewer` component first. This is non-negotiable per spec §6.5.

## Dev

```bash
# from repo root
pnpm --filter @axis/web dev      # starts on http://localhost:3001

# type-check
pnpm --filter @axis/web type-check

# lint
pnpm --filter @axis/web lint
```

## Don't

- Don't add a new state library. React Query + Zustand is the answer.
- Don't add a new styling system. Tailwind is the answer.
- Don't inline fetch in components — use a React Query hook from `lib/queries/`.
- Don't create a new API wrapper — use `lib/api.ts`.
- Don't write translations/i18n yet. English only in Phase 1.
- Don't add analytics SDKs without approval. PostHog is planned, nothing else.
