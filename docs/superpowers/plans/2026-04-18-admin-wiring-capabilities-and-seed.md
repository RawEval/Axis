# Axis UI Plan 9 — Admin Wiring + Capabilities Panel + Demo Seed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Admin page to the existing api-gateway admin endpoints (`/v1/admin/stats`, `/v1/admin/connectors`, `/v1/admin/runs`), build the Settings "What Axis can do" capability tuner panel as a localStorage-backed UI, and extend the existing `scripts/seed.py` with demo data so first-run users land on a workspace that has something in it.

**Architecture:** Backend already has the admin endpoints we need (verified — `services/api-gateway/app/routes/admin.py` has 4 routes). This plan adds React Query hooks + page wiring on the frontend. The capability tuner is frontend-only with localStorage persistence — no backend tier registry refactor in this plan (deferred). Seed extension uses the same `psycopg` pattern as the existing `scripts/seed.py`.

**Tech Stack:** Existing — no new deps. React Query for data fetching, the admin API already returns the right shapes.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact §3i (Settings — Capabilities tab) + §3l (Admin) + §5g (Onboarding).

**Out of scope** (still deferred to Plan 10+):
- Capability tier registry refactor in `services/agent-orchestration` (Tier 0/1/2 metadata on every capability).
- `POST /v1/actions/{id}/undo` endpoint + per-capability undo handlers.
- Audience counter (sends >3 recipients → Tier 2).
- Real backend storage for trust mode (this plan uses localStorage).
- CI integration for Playwright (Linux baselines, GitHub Actions).
- Saga compensations for cross-connector cascades.

**Deviations:**
1. **Trust mode is localStorage-only.** The Settings "What Axis can do" panel reads/writes from `localStorage["axis.capabilities"]`. When the backend tier registry lands, the same UI will read from the API and persist to the grants table — the surface is forward-compatible.
2. **Demo seed inserts memory rows + a project but does NOT create OAuth tokens.** Real OAuth tokens require a sandbox app per connector, out of scope for a local demo. Connectors stay in `disconnected` state for demo accounts.

---

## File structure

**Create:**

```
apps/web/lib/queries/admin.ts                              # React Query hooks for admin endpoints
apps/web/app/(app)/admin/page.tsx                          # Rewritten — consumes admin hooks
apps/web/lib/capabilities.ts                               # Local capability registry + trust-mode store
apps/web/components/settings/capabilities-panel.tsx        # The "What Axis can do" UI
```

**Modify:**

```
apps/web/app/(app)/settings/page.tsx                       # Mount CapabilitiesPanel in Capabilities tab
scripts/seed.py                                            # Extend with demo project + memory rows
```

**Total:** 4 new files, 2 modified, 4 commits.

---

## Phase A — Admin wiring

### Task A1: Admin React Query hooks + page rewrite

**Files:**
- Create: `apps/web/lib/queries/admin.ts`
- Modify: `apps/web/app/(app)/admin/page.tsx` (replaces the Plan 7 stub)

- [ ] **Step 1: Inspect the existing admin endpoints**

```bash
cat /Users/mrinalraj/Documents/Axis/services/api-gateway/app/routes/admin.py | head -90
```

Note the response shapes for `/admin/stats`, `/admin/connectors`, `/admin/runs`, `/admin/eval`. These are the data sources.

- [ ] **Step 2: Create the hooks**

Create `apps/web/lib/queries/admin.ts`:
```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export interface AdminStats {
  total_users: number;
  total_runs: number;
  active_runs_24h: number;
  total_connectors_connected: number;
  error_rate_24h: number;
}

export interface AdminConnector {
  user_id: string;
  tool: string;
  status: string;
  health: string | null;
  last_sync: string | null;
}

export interface AdminRun {
  id: string;
  user_id: string;
  prompt: string;
  status: string;
  created_at: string;
  duration_ms: number | null;
}

export interface AdminEvalSummary {
  composite: number;
  flagged: number;
  recent_count: number;
}

export function useAdminStats() {
  return useQuery<AdminStats>({
    queryKey: ['admin', 'stats'],
    queryFn: () => api.get<AdminStats>('/admin/stats'),
  });
}

export function useAdminConnectors() {
  return useQuery<AdminConnector[]>({
    queryKey: ['admin', 'connectors'],
    queryFn: () => api.get<AdminConnector[]>('/admin/connectors'),
  });
}

export function useAdminRuns() {
  return useQuery<AdminRun[]>({
    queryKey: ['admin', 'runs'],
    queryFn: () => api.get<AdminRun[]>('/admin/runs?limit=10'),
  });
}

export function useAdminEval() {
  return useQuery<AdminEvalSummary>({
    queryKey: ['admin', 'eval'],
    queryFn: () => api.get<AdminEvalSummary>('/admin/eval'),
  });
}
```

If the actual backend response shapes differ from these interfaces, adapt the interfaces to match (read `admin.py` carefully). The route paths under `api.get()` are the path AFTER the gateway prefix — check `lib/api.ts` to see what prefix it adds (likely `/v1`).

- [ ] **Step 3: Rewrite the Admin page**

Replace `apps/web/app/(app)/admin/page.tsx` with:
```tsx
'use client';

import { Card, CardBody, Skeleton } from '@axis/design-system';
import { useAdminStats, useAdminConnectors, useAdminRuns, useAdminEval } from '@/lib/queries/admin';

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toLocaleString();
}

function formatPercent(n: number | null | undefined): string {
  if (n == null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

export default function AdminPage() {
  const stats = useAdminStats();
  const connectors = useAdminConnectors();
  const runs = useAdminRuns();
  const evalSummary = useAdminEval();

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Admin</h1>
        <p className="text-body text-ink-secondary">
          System health, connector matrix, eval trends.
        </p>
      </header>

      <section aria-labelledby="system-health">
        <h2 id="system-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          System health
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <KPI label="Total users"      value={formatNumber(stats.data?.total_users)}              loading={stats.isLoading} />
          <KPI label="Total runs"       value={formatNumber(stats.data?.total_runs)}                loading={stats.isLoading} />
          <KPI label="Active 24h"       value={formatNumber(stats.data?.active_runs_24h)}           loading={stats.isLoading} />
          <KPI label="Connected"        value={formatNumber(stats.data?.total_connectors_connected)} loading={stats.isLoading} />
          <KPI label="Error rate 24h"   value={formatPercent(stats.data?.error_rate_24h)}           loading={stats.isLoading} />
        </div>
      </section>

      <section aria-labelledby="connector-health">
        <h2 id="connector-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Connector health
        </h2>
        <Card>
          {connectors.isLoading ? (
            <CardBody><Skeleton height={120} rounded="md" /></CardBody>
          ) : connectors.data && connectors.data.length > 0 ? (
            <ul className="divide-y divide-edge-subtle">
              {connectors.data.slice(0, 10).map((c, i) => (
                <li key={`${c.user_id}-${c.tool}-${i}`} className="flex items-center gap-3 px-5 py-3">
                  <span className="font-mono text-mono-s text-ink uppercase">{c.tool}</span>
                  <span className="font-mono text-mono-s text-ink-tertiary">{c.user_id.slice(0, 8)}…</span>
                  <span className="ml-auto font-mono text-[11px] uppercase tracking-[0.06em] text-ink-secondary">{c.status}</span>
                </li>
              ))}
            </ul>
          ) : (
            <CardBody className="py-10 text-center text-body-s text-ink-tertiary">No connector data.</CardBody>
          )}
        </Card>
      </section>

      <section aria-labelledby="eval-trends">
        <h2 id="eval-trends" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Eval summary
        </h2>
        <Card>
          {evalSummary.isLoading ? (
            <CardBody><Skeleton height={80} rounded="md" /></CardBody>
          ) : (
            <CardBody className="grid grid-cols-3 gap-6">
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">{formatPercent(evalSummary.data?.composite)}</div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">Composite score</div>
              </div>
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">{formatNumber(evalSummary.data?.flagged)}</div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">Flagged runs</div>
              </div>
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">{formatNumber(evalSummary.data?.recent_count)}</div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">Recent (50)</div>
              </div>
            </CardBody>
          )}
        </Card>
      </section>
    </div>
  );
}

function KPI({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <Card>
      <CardBody className="space-y-1">
        {loading ? (
          <Skeleton height={36} rounded="sm" />
        ) : (
          <div className="font-display text-display-m text-ink tabular-nums">{value}</div>
        )}
        <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
          {label}
        </div>
      </CardBody>
    </Card>
  );
}
```

⚠️ If the field shapes from the backend don't match what's typed above (e.g. snake_case mismatches), the React Query call will succeed but `value={formatNumber(stats.data?.total_users)}` will show `—` for unknown fields. Read the actual response in `admin.py` and update both the interface AND the field accesses to match.

- [ ] **Step 4: Type-check + build + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|/admin|Failed)" | head -3
```

```bash
git add apps/web/lib/queries/admin.ts apps/web/app/\(app\)/admin/page.tsx && git commit -m "feat(web): wire Admin page to backend stats/connectors/runs/eval endpoints"
```

---

## Phase B — Capabilities tuner

### Task B1: Local capability registry + trust-mode store

**Files:**
- Create: `apps/web/lib/capabilities.ts`

- [ ] **Step 1: Create the registry + store**

```typescript
'use client';

import { useSyncExternalStore } from 'react';

export type CapabilityId =
  | 'connector.slack.read'
  | 'connector.slack.write'
  | 'connector.notion.read'
  | 'connector.notion.write'
  | 'connector.gmail.read'
  | 'connector.gmail.send'
  | 'connector.gdrive.read'
  | 'connector.github.read'
  | 'connector.github.write';

export type TrustMode = 'ask' | 'auto-reversible' | 'auto';

export interface CapabilityMeta {
  id: CapabilityId;
  label: string;
  tier: 0 | 1 | 2;
  description: string;
}

export const CAPABILITIES: ReadonlyArray<CapabilityMeta> = [
  { id: 'connector.slack.read',    tier: 0, label: 'Read Slack',          description: 'Channels, threads, search.' },
  { id: 'connector.slack.write',   tier: 1, label: 'Post to Slack',       description: 'Send messages to channels and DMs.' },
  { id: 'connector.notion.read',   tier: 0, label: 'Read Notion',         description: 'Pages, databases, search.' },
  { id: 'connector.notion.write',  tier: 1, label: 'Edit Notion',         description: 'Create + update pages.' },
  { id: 'connector.gmail.read',    tier: 0, label: 'Read Gmail',          description: 'Inbox, labels, search.' },
  { id: 'connector.gmail.send',    tier: 2, label: 'Send Gmail',          description: 'Send email on your behalf — irreversible.' },
  { id: 'connector.gdrive.read',   tier: 0, label: 'Read Google Drive',   description: 'Files, folders, content.' },
  { id: 'connector.github.read',   tier: 0, label: 'Read GitHub',         description: 'Issues, PRs, code.' },
  { id: 'connector.github.write',  tier: 1, label: 'Comment on GitHub',   description: 'Comment on issues + PRs.' },
];

const STORAGE_KEY = 'axis.capabilities';

type State = Record<CapabilityId, TrustMode>;

function defaultMode(meta: CapabilityMeta): TrustMode {
  return meta.tier === 0 ? 'auto' : meta.tier === 1 ? 'ask' : 'ask';
}

function readStored(): State {
  if (typeof window === 'undefined') {
    return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
    }
    const parsed = JSON.parse(raw) as Partial<State>;
    return Object.fromEntries(
      CAPABILITIES.map((c) => [c.id, parsed[c.id] ?? defaultMode(c)]),
    ) as State;
  } catch {
    return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
  }
}

let state: State = readStored();
const listeners = new Set<() => void>();

function emit(): void {
  for (const l of listeners) l();
}

export const capabilities = {
  getState: (): State => state,
  setMode: (id: CapabilityId, mode: TrustMode): void => {
    state = { ...state, [id]: mode };
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
    emit();
  },
  subscribe: (l: () => void) => {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
};

export function useCapabilities(): State {
  return useSyncExternalStore(capabilities.subscribe, capabilities.getState, capabilities.getState);
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/lib/capabilities.ts && git commit -m "feat(web): add capabilities registry + trust-mode store (localStorage)"
```

### Task B2: CapabilitiesPanel + mount in Settings

**Files:**
- Create: `apps/web/components/settings/capabilities-panel.tsx`
- Modify: `apps/web/app/(app)/settings/page.tsx` (replace the "Coming soon" stub)

- [ ] **Step 1: Build the panel**

Create `apps/web/components/settings/capabilities-panel.tsx`:
```tsx
'use client';

import { Badge, SegmentedControl } from '@axis/design-system';
import {
  CAPABILITIES,
  capabilities,
  useCapabilities,
  type CapabilityId,
  type TrustMode,
} from '@/lib/capabilities';

const TIER_LABEL: Record<0 | 1 | 2, string> = {
  0: 'Read',
  1: 'Reversible',
  2: 'Irreversible',
};

const TIER_TONE: Record<0 | 1 | 2, 'success' | 'info' | 'warning'> = {
  0: 'success',
  1: 'info',
  2: 'warning',
};

const TRUST_OPTIONS: ReadonlyArray<{ value: TrustMode; label: string }> = [
  { value: 'ask',             label: 'Ask' },
  { value: 'auto-reversible', label: 'Auto if reversible' },
  { value: 'auto',            label: 'Auto' },
];

export function CapabilitiesPanel() {
  const modes = useCapabilities();

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-heading-1 text-ink">What Axis can do</h2>
        <p className="text-body-s text-ink-secondary">
          Tier-2 (irreversible) capabilities always ask, regardless of trust mode.
        </p>
      </header>

      <ul className="divide-y divide-edge-subtle border-y border-edge-subtle">
        {CAPABILITIES.map((cap) => {
          const mode = modes[cap.id];
          const isIrreversible = cap.tier === 2;
          return (
            <li key={cap.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:gap-6">
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-body-s font-medium text-ink">{cap.label}</span>
                  <Badge tone={TIER_TONE[cap.tier]}>{TIER_LABEL[cap.tier]}</Badge>
                </div>
                <div className="font-mono text-mono-s text-ink-tertiary">{cap.id}</div>
                <p className="text-caption text-ink-secondary">{cap.description}</p>
              </div>
              <SegmentedControl
                value={isIrreversible ? 'ask' : mode}
                onChange={(next: TrustMode) => {
                  if (!isIrreversible) capabilities.setMode(cap.id as CapabilityId, next);
                }}
                options={TRUST_OPTIONS}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Mount in Settings**

In `apps/web/app/(app)/settings/page.tsx`, find the Capabilities tab content (currently a "Coming soon" `<p>`). Replace with `<CapabilitiesPanel />`.

Add the import at the top:
```tsx
import { CapabilitiesPanel } from '@/components/settings/capabilities-panel';
```

The `<TabsContent value="capabilities">` block becomes:
```tsx
<TabsContent value="capabilities">
  <CapabilitiesPanel />
</TabsContent>
```

- [ ] **Step 3: Type-check + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && git add apps/web/components/settings apps/web/app/\(app\)/settings/page.tsx && git commit -m "feat(web): add CapabilitiesPanel to Settings (artifact §3i)"
```

---

## Phase C — Demo seed

### Task C1: Extend `scripts/seed.py` with demo project + memory

**Files:**
- Modify: `scripts/seed.py`

- [ ] **Step 1: Read current seed**

```bash
cat /Users/mrinalraj/Documents/Axis/scripts/seed.py
```

- [ ] **Step 2: Extend it**

Append these blocks INSIDE the existing `with psycopg.connect(...)` block (before the existing `print(...)` statement at the end). The existing seed creates a user; this extension adds a project and 3 memory rows for that user.

The exact additions:
```python
        # Plan 9 — demo project + memory rows for first-run UX.
        project_id = uuid.uuid4()
        cur.execute(
            """
            INSERT INTO projects (id, owner_id, name, description, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (id) DO NOTHING;
            """,
            (project_id, user_id, "Demo project", "Synthetic data for first-run."),
        )

        for tier, content in [
            ("episodic",  "User asked Axis to summarise yesterday's #product channel"),
            ("semantic",  "User prefers TL;DRs under 80 words"),
            ("procedural", "Always skip the #random channel in recaps"),
        ]:
            cur.execute(
                """
                INSERT INTO memory_rows (id, owner_id, project_id, tier, content, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (id) DO NOTHING;
                """,
                (
                    uuid.uuid4(),
                    user_id,
                    project_id,
                    tier,
                    content,
                    '{"source": "demo-seed", "pinned": true}' if tier == "semantic" else '{"source": "demo-seed"}',
                ),
            )

        print(f"+ project {project_id} for user {user_id}")
        print("+ 3 memory rows (1 episodic, 1 semantic pinned, 1 procedural)")
```

The schema column names (`owner_id`, `project_id`, `tier`, `content`, `metadata`) are based on Plan 6 audit references. **Verify against the actual schema** before running:
```bash
cat /Users/mrinalraj/Documents/Axis/infra/docker/init/postgres/001_init.sql 2>&1 | grep -A 12 "CREATE TABLE memory_rows\|CREATE TABLE projects" | head -40
```

If column names differ, adapt the INSERT statements before running.

- [ ] **Step 3: Test the seed**

If Postgres is running locally (`make infra-up` started it), run:
```bash
cd /Users/mrinalraj/Documents/Axis && python scripts/seed.py
```

Expected output: lines about user, project, memory rows. If it errors on schema mismatch, adapt the script.

If Postgres is NOT running locally, the seed will fail to connect — that's fine for this task; the script still gets committed and runs when infra is up.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add scripts/seed.py && git commit -m "feat(scripts): extend seed with demo project + memory rows for first-run UX"
```

---

## Phase D — Verify

### Task D1: Workspace verify

- [ ] **Step 1: Tests + type-check + lint + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10 && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && pnpm lint 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|/admin|/settings|Failed)" | head -5
```

Expected: design-system 113, web 31. Type-check + lint clean. Build green; `/admin` and `/settings` listed.

- [ ] **Step 2: Run Playwright suite**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e 2>&1 | tail -3
```

Expected: 10 tests pass. The Settings/Admin changes shouldn't affect the Login/Home/Chat snapshots.

- [ ] **Step 3: Manual dev smoke**

Visit `/admin` → KPIs render with real numbers (or zeros if backend has no data) instead of em-dashes. Connector matrix lists real connectors. Eval summary shows real composite + flagged + recent counts.

Visit `/settings` → Capabilities tab shows the 9 capability rows with tier badges and per-row SegmentedControl. Toggle one → refresh → persists. Tier-2 rows are visibly locked to "Ask".

(No commit.)

---

## What we have at the end of this plan

- Admin page reads real data from `services/api-gateway/admin/*` endpoints.
- Settings → Capabilities tab is the localStorage-backed trust mode tuner with all 9 capabilities surfaced + tier badges.
- `scripts/seed.py` extended with demo project + 3 memory rows (1 episodic, 1 semantic pinned, 1 procedural) so a first-run user lands in a non-empty workspace.

## What we explicitly did NOT do (deferred to future plans)

- Backend tier registry refactor (`services/agent-orchestration` — Tier 0/1/2 metadata propagated to capability decisions).
- Server-side undo handlers per Tier-1 capability (`POST /v1/actions/{id}/undo`).
- Audience counter + recipient escalation to Tier 2 for Slack post / Gmail send.
- Real backend storage for trust mode (this plan uses localStorage; future plan persists to a `capability_trust` table).
- Admin metrics: real time-series charts for eval trends (this plan shows snapshot KPIs only).
- CI integration for Playwright (Linux baselines + GitHub Actions).
- Saga compensations for cross-connector cascades.
- Real OAuth tokens in the demo seed (would need sandbox apps per connector).

## Self-Review

- **Spec coverage:** Plan 9 covers artifact §3i Capabilities tab + §3l Admin (data wiring) + §5g first-run state (demo data). The remaining backend amendments (A1 + A2 wiring full tier registry + undo) are explicitly out of scope and will be a Plan 10 backend lift.
- **Placeholder scan:** No "TBD" / "implement later". The "Sending…" busy state on WritePreviewCard from Plan 5 + the "Coming soon" copy on Notifications/Capabilities tabs are intentional Plan 10 dependencies.
- **Type consistency:** `CapabilityId` union shared across `capabilities.ts` and `CapabilitiesPanel`. `TrustMode` shared. `AdminStats` shape declared once in `admin.ts` queries hook.
- **Commands:** Every `pnpm --filter` and `git add` path is correct.
