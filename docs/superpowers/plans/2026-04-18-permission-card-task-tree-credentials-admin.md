# Axis UI Plan 7 — PermissionCard + LiveTaskTree v2 + Credentials Migration + Admin Stub

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two remaining Axis-native primitives (`PermissionCard` per A1 amendment, `LiveTaskTree` v2 per artifact §4), migrate the existing chat wrappers to consume them, fold Credentials into the Connections RightPanel per artifact §3g, and add the Admin dashboard route stub per artifact §3l. Frontend only — backend tier-registry, undo handlers, audience counter, and trust mode all stay deferred to Plan 8.

**Architecture:** PermissionCard and LiveTaskTree v2 land in `packages/design-system` as data-agnostic presentation primitives. The existing web-side wrappers (`apps/web/components/chat/permission-modal.tsx`, `apps/web/components/chat/live-task-tree.tsx`) become thin adapters: same exported names + same prop contracts so `chat/page.tsx` doesn't need rewiring; internally they translate live events / mutations into the new primitive's props. Credentials migration adds an inline "Manage credentials" button to each ConnectorTile that opens RightPanel via `rightPanel.open(...)`; the standalone `/credentials` route stays as a fallback. Admin stub renders the §3l three-section structure with placeholder cards (no backend metric endpoints yet).

**Tech Stack:** Existing — no new deps.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§3g Credentials, §3l Admin, §4 LiveTaskTree, §5b Permission model A1 amendment).

**Out of scope** (Plan 8):
- Backend support: capability tier registry (services/agent-orchestration), undo handlers (services/api-gateway), audience counter, per-capability trust mode.
- The "single Allow / Just once" UX deviation only matters once tier registry exists; for V1 the primitive surfaces the same axes the existing modal exposes (lifetime grid + Deny) but presents them inline-in-card per artifact §5b's Option-C container instead of as a modal.
- Onboarding / demo workspace seed.
- Playwright visual regression.

**Deviations:**
1. **PermissionCard initially keeps the four-lifetime axes** (`session/24h/project/forever`) because the backend mutation (`useResolvePermission`) requires them. The visual treatment is the new card pattern; the data axes will collapse to single-Allow + popover when tier-registry lands (Plan 8). The artifact §5b notes this is the right migration order.
2. **Admin route is a structural stub.** Without backend metric endpoints, KPI cards render placeholder zeros + sparkline skeletons. Plan 8 wires real data.
3. **Credentials migration preserves the standalone route** rather than deleting it. The new inline path is the primary affordance; the route is a fallback so any deep-link to `/credentials` continues to work.

---

## File structure

**Create:**

```
packages/design-system/src/components/permission-card/
  permission-card.tsx
  permission-card.test.tsx
  index.ts

packages/design-system/src/components/live-task-tree/
  live-task-tree.tsx
  live-task-tree.test.tsx
  index.ts

apps/web/components/connections/credentials-panel.tsx   # New — RightPanel body for credentials
apps/web/app/(app)/admin/page.tsx                       # New — Admin dashboard stub route
```

**Modify:**

```
packages/design-system/src/index.ts                              # add 2 new exports
apps/web/components/chat/permission-modal.tsx                    # adapter wrapping new PermissionCard
apps/web/components/chat/live-task-tree.tsx                      # adapter wrapping new LiveTaskTree v2
apps/web/components/connections-content.tsx                      # add "Manage credentials" affordance per tile
```

**Total:** 8 new files, 4 modified, 7 commits.

---

## Phase A — Primitives

### Task A1: PermissionCard primitive

Inline-in-chat card per artifact §5b. Renders capability + description + optional inputs preview + a 2×2 grid of Allow lifetime options + a separate Deny button. Per-button busy state.

**Files:**
- Create: `packages/design-system/src/components/permission-card/permission-card.tsx`
- Create: `packages/design-system/src/components/permission-card/permission-card.test.tsx`
- Create: `packages/design-system/src/components/permission-card/index.ts`

- [ ] **Step 1: Failing test**

```tsx
// packages/design-system/src/components/permission-card/permission-card.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PermissionCard } from './permission-card';

describe('PermissionCard', () => {
  const baseProps = {
    capability: 'connector.notion.read',
    description: 'Axis wants to read your Notion workspace.',
    onAllow: vi.fn(),
    onDeny: vi.fn(),
  };

  it('renders capability and description', () => {
    render(<PermissionCard {...baseProps} />);
    expect(screen.getByText('connector.notion.read')).toBeInTheDocument();
    expect(screen.getByText(/wants to read/)).toBeInTheDocument();
  });

  it('renders four allow buttons + one deny button', () => {
    render(<PermissionCard {...baseProps} />);
    expect(screen.getByRole('button', { name: /allow once/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow for project/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow 24h/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow forever/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^deny$/i })).toBeInTheDocument();
  });

  it('fires onAllow with the chosen lifetime', async () => {
    const onAllow = vi.fn();
    render(<PermissionCard {...baseProps} onAllow={onAllow} />);
    await userEvent.click(screen.getByRole('button', { name: /allow for project/i }));
    expect(onAllow).toHaveBeenCalledWith('project');
  });

  it('fires onDeny when Deny is clicked', async () => {
    const onDeny = vi.fn();
    render(<PermissionCard {...baseProps} onDeny={onDeny} />);
    await userEvent.click(screen.getByRole('button', { name: /^deny$/i }));
    expect(onDeny).toHaveBeenCalled();
  });

  it('renders inputs preview when provided', () => {
    render(
      <PermissionCard {...baseProps} inputs={{ workspace: 'engineering' }} />,
    );
    expect(screen.getByText(/workspace/)).toBeInTheDocument();
    expect(screen.getByText(/engineering/)).toBeInTheDocument();
  });

  it('disables all buttons when busy is set', () => {
    render(<PermissionCard {...baseProps} busy="project" />);
    expect(screen.getByRole('button', { name: /allow once/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /allow for project/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^deny$/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

```tsx
// packages/design-system/src/components/permission-card/permission-card.tsx
'use client';

import clsx from 'clsx';
import { type ReactNode } from 'react';
import { Card, CardHeader, CardBody, CardFooter } from '../card';
import { Button } from '../button';

export type PermissionLifetime = 'session' | 'project' | '24h' | 'forever';
export type PermissionDecision = PermissionLifetime | 'deny';

export interface PermissionCardProps {
  capability: string;
  description: ReactNode;
  inputs?: Record<string, unknown>;
  busy?: PermissionDecision | null;
  onAllow: (lifetime: PermissionLifetime) => void;
  onDeny: () => void;
  className?: string;
}

const LIFETIME_LABELS: Record<PermissionLifetime, { label: string; hint: string }> = {
  session: { label: 'Allow once',         hint: 'just this call' },
  project: { label: 'Allow for project',  hint: 'remember for this workspace' },
  '24h':   { label: 'Allow 24h',          hint: 're-ask tomorrow' },
  forever: { label: 'Allow forever',      hint: 'across all sessions' },
};

const ORDER: PermissionLifetime[] = ['session', 'project', '24h', 'forever'];

export function PermissionCard({
  capability,
  description,
  inputs,
  busy,
  onAllow,
  onDeny,
  className,
}: PermissionCardProps) {
  return (
    <Card className={clsx('shadow-e1', className)}>
      <CardHeader className="flex items-start gap-2">
        <span aria-hidden className="mt-1 inline-block h-2 w-2 rounded-full bg-agent-awaiting animate-breathe" />
        <div>
          <div className="text-body-s text-ink">
            Axis wants to use <span className="font-mono text-mono-s">{capability}</span>
          </div>
          <p className="mt-1 text-body-s text-ink-secondary">{description}</p>
        </div>
      </CardHeader>

      {inputs && Object.keys(inputs).length > 0 && (
        <div className="px-5 pb-3">
          <pre className="max-h-36 overflow-auto rounded-md border border-edge-subtle bg-canvas-elevated px-3 py-2 font-mono text-mono-s text-ink-secondary">
            {JSON.stringify(inputs, null, 2)}
          </pre>
        </div>
      )}

      <CardBody className="grid grid-cols-2 gap-2 pt-0">
        {ORDER.map((lt) => {
          const meta = LIFETIME_LABELS[lt];
          const isBusy = busy === lt;
          return (
            <Button
              key={lt}
              variant={lt === 'session' ? 'primary' : 'secondary'}
              size="sm"
              disabled={busy != null}
              onClick={() => onAllow(lt)}
              className="flex-col items-start h-auto py-2"
            >
              <span>{isBusy ? 'Granting…' : meta.label}</span>
              <span className="text-[10px] font-normal opacity-70">{meta.hint}</span>
            </Button>
          );
        })}
      </CardBody>

      <CardFooter className="pt-0">
        <Button
          variant="danger"
          size="sm"
          className="w-full"
          disabled={busy != null}
          onClick={onDeny}
        >
          {busy === 'deny' ? 'Denying…' : 'Deny'}
        </Button>
      </CardFooter>
    </Card>
  );
}
```

- [ ] **Step 4: Index**

```typescript
// packages/design-system/src/components/permission-card/index.ts
export { PermissionCard } from './permission-card';
export type {
  PermissionCardProps,
  PermissionLifetime,
  PermissionDecision,
} from './permission-card';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/permission-card && git commit -m "feat(design-system): build PermissionCard primitive (artifact §5b)"
```

Expected: 101 + 6 = **107 design-system tests**.

### Task A2: LiveTaskTree v2 primitive

Data-agnostic step-tree renderer per artifact §4. Takes `steps: StepData[]`, renders each as a row with state dot + label + duration + optional expand for tool I/O. Recursive children.

**Files:**
- Create: `packages/design-system/src/components/live-task-tree/live-task-tree.tsx`
- Create: `packages/design-system/src/components/live-task-tree/live-task-tree.test.tsx`
- Create: `packages/design-system/src/components/live-task-tree/index.ts`

- [ ] **Step 1: Failing test**

```tsx
// packages/design-system/src/components/live-task-tree/live-task-tree.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LiveTaskTree, type StepData } from './live-task-tree';

const steps: StepData[] = [
  { id: '1', label: 'Read #product Slack', state: 'done', durationMs: 3200 },
  { id: '2', label: 'Read Notion: Q3 roadmap', state: 'done', durationMs: 5800 },
  {
    id: '3',
    label: 'Draft recap',
    state: 'running',
    toolCall: { name: 'notion.create_draft', args: { title: 'Q3 Engineering Recap' } },
  },
  { id: '4', label: 'Post to #leadership', state: 'pending' },
];

describe('LiveTaskTree', () => {
  it('renders one row per step', () => {
    render(<LiveTaskTree steps={steps} />);
    expect(screen.getByText('Read #product Slack')).toBeInTheDocument();
    expect(screen.getByText('Read Notion: Q3 roadmap')).toBeInTheDocument();
    expect(screen.getByText('Draft recap')).toBeInTheDocument();
    expect(screen.getByText('Post to #leadership')).toBeInTheDocument();
  });

  it('shows duration for completed steps', () => {
    render(<LiveTaskTree steps={steps} />);
    expect(screen.getByText('3.2s')).toBeInTheDocument();
    expect(screen.getByText('5.8s')).toBeInTheDocument();
  });

  it('renders nested children when provided', () => {
    const tree: StepData[] = [
      {
        id: 'p',
        label: 'Plan',
        state: 'running',
        children: [
          { id: 'p-1', label: 'Substep one', state: 'done', durationMs: 100 },
          { id: 'p-2', label: 'Substep two', state: 'pending' },
        ],
      },
    ];
    render(<LiveTaskTree steps={tree} />);
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Substep one')).toBeInTheDocument();
    expect(screen.getByText('Substep two')).toBeInTheDocument();
  });

  it('renders nothing when steps is empty', () => {
    const { container } = render(<LiveTaskTree steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('expands tool I/O on click when toolCall is present', async () => {
    render(<LiveTaskTree steps={steps} />);
    const expandButton = screen.getByRole('button', { name: /expand notion\.create_draft/i });
    await userEvent.click(expandButton);
    expect(screen.getByText(/Q3 Engineering Recap/)).toBeInTheDocument();
  });

  it('marks running steps with the running animation class', () => {
    render(<LiveTaskTree steps={steps} />);
    const runningRow = screen.getByText('Draft recap').closest('div');
    expect(runningRow?.querySelector('span.animate-breathe')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

```tsx
// packages/design-system/src/components/live-task-tree/live-task-tree.tsx
'use client';

import clsx from 'clsx';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState, type ReactNode } from 'react';

export type StepState = 'pending' | 'running' | 'done' | 'failed' | 'denied' | 'awaiting';

export interface StepToolCall {
  name: string;
  args?: unknown;
  result?: unknown;
}

export interface StepData {
  id: string;
  label: string;
  state: StepState;
  durationMs?: number;
  toolCall?: StepToolCall;
  children?: ReadonlyArray<StepData>;
}

const STATE_DOT: Record<StepState, string> = {
  pending:  'bg-agent-background',
  running:  'bg-agent-running animate-breathe',
  done:     'bg-success',
  failed:   'bg-danger',
  denied:   'bg-warning',
  awaiting: 'bg-agent-awaiting animate-breathe',
};

const STATE_LABEL: Record<StepState, string> = {
  pending:  'pending',
  running:  'running',
  done:     'done',
  failed:   'failed',
  denied:   'denied',
  awaiting: 'awaiting',
};

function formatDuration(ms?: number): string | null {
  if (ms == null) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StepRow({ step, depth }: { step: StepData; depth: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasTool = step.toolCall != null;
  const duration = formatDuration(step.durationMs);

  return (
    <div className="flex flex-col">
      <div
        className="flex items-center gap-3 px-2 py-1 font-mono text-mono-s text-ink-secondary"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        <span aria-hidden="true" className={clsx('inline-block h-2 w-2 rounded-full shrink-0', STATE_DOT[step.state])} />
        <span className={clsx('flex-1 truncate', step.state === 'running' && 'text-ink')}>
          {step.label}
        </span>
        <span className="sr-only">{STATE_LABEL[step.state]}</span>
        {duration && (
          <span className="text-ink-tertiary tabular-nums">{duration}</span>
        )}
        {hasTool && (
          <button
            type="button"
            aria-label={`Expand ${step.toolCall?.name}`}
            onClick={() => setExpanded((v) => !v)}
            className="text-ink-tertiary hover:text-ink-secondary"
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
      </div>

      {hasTool && expanded && (
        <div
          className="mb-1 rounded-sm border border-edge-subtle bg-canvas-elevated px-3 py-2 font-mono text-mono-s text-ink-secondary"
          style={{ marginLeft: `${depth * 16 + 24}px` }}
        >
          <div className="text-ink-tertiary">tool_call: {step.toolCall?.name}</div>
          {step.toolCall?.args !== undefined && (
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap">
              args: {JSON.stringify(step.toolCall.args, null, 2)}
            </pre>
          )}
          {step.toolCall?.result !== undefined && (
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap">
              → {JSON.stringify(step.toolCall.result, null, 2)}
            </pre>
          )}
        </div>
      )}

      {step.children && step.children.length > 0 && (
        <div className="flex flex-col">
          {step.children.map((child) => (
            <StepRow key={child.id} step={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export interface LiveTaskTreeProps {
  steps: ReadonlyArray<StepData>;
  /** Optional content rendered at the bottom (e.g. "Thinking…" pulse). */
  trailing?: ReactNode;
}

export function LiveTaskTree({ steps, trailing }: LiveTaskTreeProps) {
  if (steps.length === 0 && !trailing) return null;
  return (
    <div className="flex flex-col gap-0">
      {steps.map((s) => (
        <StepRow key={s.id} step={s} depth={0} />
      ))}
      {trailing}
    </div>
  );
}
```

- [ ] **Step 4: Index**

```typescript
// packages/design-system/src/components/live-task-tree/index.ts
export { LiveTaskTree } from './live-task-tree';
export type {
  LiveTaskTreeProps,
  StepData,
  StepState,
  StepToolCall,
} from './live-task-tree';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/live-task-tree && git commit -m "feat(design-system): build LiveTaskTree v2 primitive (artifact §4)"
```

Expected: 107 + 6 = **113 design-system tests**.

### Task A3: Wire barrel + adapt the chat permission-modal wrapper

**Files:**
- Modify: `packages/design-system/src/index.ts` (add 2 new exports)
- Modify: `apps/web/components/chat/permission-modal.tsx` (becomes adapter)

- [ ] **Step 1: Append to barrel**

Add to `packages/design-system/src/index.ts`:
```typescript
// Plan 7 — Axis-native primitives.
export {
  PermissionCard,
  type PermissionCardProps,
  type PermissionLifetime,
  type PermissionDecision,
} from './components/permission-card';
export {
  LiveTaskTree,
  type LiveTaskTreeProps,
  type StepData,
  type StepState,
  type StepToolCall,
} from './components/live-task-tree';
```

- [ ] **Step 2: Replace `apps/web/components/chat/permission-modal.tsx`**

```tsx
'use client';

import { useState } from 'react';
import {
  PermissionCard,
  type PermissionDecision,
  type PermissionLifetime,
} from '@axis/design-system';
import {
  useResolvePermission,
} from '@/lib/queries/live';

export type PermissionRequest = {
  pending_id: string;
  capability: string;
  description: string;
  inputs: Record<string, unknown>;
};

export function PermissionModal({
  request,
  onResolved,
}: {
  request: PermissionRequest;
  onResolved: () => void;
}) {
  const resolve = useResolvePermission();
  const [busy, setBusy] = useState<PermissionDecision | null>(null);

  const decide = async (decision: PermissionDecision) => {
    if (resolve.isPending) return;
    setBusy(decision);
    try {
      await resolve.mutateAsync({
        pending_id: request.pending_id,
        granted: decision !== 'deny',
        lifetime: decision === 'deny' ? 'session' : decision,
      });
      onResolved();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md">
        <PermissionCard
          capability={request.capability}
          description={request.description}
          inputs={request.inputs}
          busy={busy}
          onAllow={(lt: PermissionLifetime) => decide(lt)}
          onDeny={() => decide('deny')}
        />
      </div>
    </div>
  );
}
```

The exported `PermissionModal` symbol + `PermissionRequest` type stay identical — `chat/page.tsx` doesn't change.

- [ ] **Step 3: Type-check + tests**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test 2>&1 | tail -3 && pnpm --filter @axis/web type-check 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head -3
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/index.ts apps/web/components/chat/permission-modal.tsx && git commit -m "refactor(web): adapt PermissionModal wrapper to design-system PermissionCard"
```

### Task A4: Adapt the chat live-task-tree wrapper

**Files:**
- Modify: `apps/web/components/chat/live-task-tree.tsx` (becomes adapter)

- [ ] **Step 1: Read the existing file** to understand the `accumulateSteps(events)` function — it's the data layer that converts streaming `LiveEvent[]` into a flat list of `StepCard` objects keyed by `step + name`. Preserve that function; the new wrapper feeds its output into the design-system `LiveTaskTree`.

- [ ] **Step 2: Rewrite the wrapper**

```tsx
'use client';

import { useMemo } from 'react';
import { LiveTaskTree as LiveTaskTreeUI, type StepData, type StepState } from '@axis/design-system';
import type { LiveEvent } from '@/lib/queries/live';

type StepCardStatus = 'running' | 'done' | 'error' | 'denied' | 'awaiting_permission';

type StepCard = {
  step: number;
  kind: string;
  name: string;
  status: StepCardStatus;
  summary: string | null;
};

const STATUS_TO_STATE: Record<StepCardStatus, StepState> = {
  running: 'running',
  done: 'done',
  error: 'failed',
  denied: 'denied',
  awaiting_permission: 'awaiting',
};

// PRESERVE this function from the previous file verbatim — it's the data layer.
function accumulateSteps(events: LiveEvent[]): StepCard[] {
  const byKey = new Map<string, StepCard>();

  for (const ev of events) {
    if (ev.type === 'task.started') continue;
    if (ev.type === 'task.completed' || ev.type === 'task.failed') continue;

    const payload = (ev as { payload?: Record<string, unknown> }).payload;
    if (!payload) continue;

    const stepNum = typeof payload.step === 'number' ? payload.step : 0;
    const name = typeof payload.name === 'string' ? payload.name : 'unknown';
    const kind = typeof payload.kind === 'string' ? payload.kind : 'tool';
    const key = `${stepNum}::${name}`;

    const existing = byKey.get(key);
    let status: StepCardStatus = existing?.status ?? 'running';
    let summary: string | null = existing?.summary ?? null;

    if (ev.type === 'step.started') {
      status = 'running';
    } else if (ev.type === 'step.completed') {
      const evStatus = typeof payload.status === 'string' ? payload.status : 'done';
      status = (
        evStatus === 'error' ? 'error' :
        evStatus === 'denied' ? 'denied' :
        'done'
      ) as StepCardStatus;
      if (typeof payload.summary === 'string') summary = payload.summary;
    } else if (ev.type === 'permission.request') {
      status = 'awaiting_permission';
    }

    byKey.set(key, { step: stepNum, kind, name, status, summary });
  }

  return Array.from(byKey.values()).sort((a, b) => a.step - b.step);
}

export function LiveTaskTree({ events }: { events: LiveEvent[] }) {
  const cards = useMemo(() => accumulateSteps(events), [events]);
  const completed = events.some(
    (e) => e.type === 'task.completed' || e.type === 'task.failed',
  );
  const isRunning = events.length > 0 && !completed;
  const allIdle = cards.every((c) => c.status !== 'running');

  const steps: StepData[] = cards.map((c) => ({
    id: `${c.step}::${c.name}`,
    label: c.summary ? `${c.name} — ${c.summary}` : c.name,
    state: STATUS_TO_STATE[c.status],
  }));

  const trailing = isRunning && allIdle ? (
    <div className="flex items-center gap-2 px-2 py-1 font-mono text-mono-s text-ink-tertiary">
      <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full bg-accent animate-breathe" />
      Thinking…
    </div>
  ) : undefined;

  return <LiveTaskTreeUI steps={steps} trailing={trailing} />;
}
```

- [ ] **Step 3: Type-check + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head -3
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/chat/live-task-tree.tsx && git commit -m "refactor(web): adapt LiveTaskTree wrapper to design-system LiveTaskTree v2"
```

---

## Phase B — Credentials migration + Admin stub

### Task B1: Credentials → Connections RightPanel migration

Add a "Manage credentials" button per connector tile that opens RightPanel with the credentials form. The standalone `/credentials` route stays as fallback.

**Files:**
- Create: `apps/web/components/connections/credentials-panel.tsx`
- Modify: `apps/web/components/connections-content.tsx` (add the button + open handler)

- [ ] **Step 1: Build the credentials panel**

The RightPanel body shows a per-tool credentials form. For V1 it surfaces the same three sections the existing `/credentials` page exposes (App credentials, Scopes, Usage) but in a single panel scoped to one tool. Use the existing query hooks if they exist; otherwise this is a simple form scaffold.

```tsx
// apps/web/components/connections/credentials-panel.tsx
'use client';

import Link from 'next/link';
import { Button, Field, Input } from '@/components/ui';
import { ExternalLink } from 'lucide-react';

export interface CredentialsPanelProps {
  tool: string;
  toolLabel: string;
}

export function CredentialsPanel({ tool, toolLabel }: CredentialsPanelProps) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-3">
          App credentials
        </h3>
        <p className="text-body-s text-ink-secondary mb-3">
          Using Axis&apos;s default OAuth app. Bring your own to keep your team&apos;s data
          inside your own Workspace app.
        </p>
        <div className="space-y-3">
          <Field label="Client ID">
            <Input placeholder={`${tool}-client-id`} disabled />
          </Field>
          <Field label="Client Secret">
            <Input type="password" placeholder="••••••••" disabled />
          </Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button variant="primary" size="sm" disabled>Use my own app</Button>
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-2">
          Scopes
        </h3>
        <p className="text-body-s text-ink-secondary">
          Granted scopes for {toolLabel}. Detailed scope picker coming soon.
        </p>
      </section>

      <Link
        href="/credentials"
        className="inline-flex items-center gap-2 text-body-s text-accent hover:text-accent-hover"
      >
        Open full credentials page
        <ExternalLink size={12} aria-hidden="true" />
      </Link>
    </div>
  );
}
```

- [ ] **Step 2: Add the inline trigger to ConnectorTile**

In `apps/web/components/connections-content.tsx`, add an import:
```tsx
import { rightPanel } from '@/lib/right-panel';
import { CredentialsPanel } from './connections/credentials-panel';
```

In the `ToolCard` component's footer area (next to Connect/Disconnect), add a ghost button:
```tsx
<Button
  variant="ghost"
  size="sm"
  onClick={() =>
    rightPanel.open({
      title: `${tool.label} credentials`,
      body: <CredentialsPanel tool={tool.tool} toolLabel={tool.label} />,
    })
  }
>
  Manage credentials
</Button>
```

Place it next to the existing Connect/Disconnect button cluster.

- [ ] **Step 3: Type-check + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head -3
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/connections apps/web/components/connections-content.tsx && git commit -m "feat(web): inline credentials panel in Connections RightPanel (artifact §3g)"
```

### Task B2: Admin dashboard stub route

Per artifact §3l: System health (5 KPI cards), Connector health matrix, Eval trends. Stub with placeholders since backend metrics endpoints don't exist yet.

**Files:**
- Create: `apps/web/app/(app)/admin/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
'use client';

import { Card, CardBody } from '@axis/design-system';

const KPIS: ReadonlyArray<{ label: string; value: string; delta?: string }> = [
  { label: 'Indexing backlog',     value: '—' },
  { label: 'Avg run latency',      value: '—' },
  { label: 'Error rate',           value: '—' },
  { label: 'Connector uptime',     value: '—' },
  { label: 'Active runs',          value: '—' },
];

export default function AdminPage() {
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Admin</h1>
        <p className="text-body text-ink-secondary">
          System health, connector matrix, eval trends. Backend metrics land in Plan 8.
        </p>
      </header>

      <section aria-labelledby="system-health">
        <h2 id="system-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          System health
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {KPIS.map((k) => (
            <Card key={k.label}>
              <CardBody className="space-y-1">
                <div className="font-display text-display-m text-ink tabular-nums">{k.value}</div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                  {k.label}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="connector-health">
        <h2 id="connector-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Connector health matrix
        </h2>
        <Card>
          <CardBody className="py-10 text-center text-body-s text-ink-tertiary">
            Awaiting backend metrics endpoint.
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="eval-trends">
        <h2 id="eval-trends" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Eval trends
        </h2>
        <Card>
          <CardBody className="py-10 text-center text-body-s text-ink-tertiary">
            Awaiting backend metrics endpoint.
          </CardBody>
        </Card>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Build to confirm `/admin` becomes a route**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | grep -E "/admin" | head
```

Expected: `○ /admin` row appears.

- [ ] **Step 3: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(app\)/admin && git commit -m "feat(web): add Admin dashboard stub route (artifact §3l)"
```

---

## Phase C — Verify

### Task C1: Workspace verify

- [ ] **Step 1: Tests + type-check + lint + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10 && \
  pnpm --filter @axis/web type-check 2>&1 | tail -3 && \
  pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && \
  pnpm lint 2>&1 | tail -5 && \
  pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|/admin)" | head -3
```

Expected: design-system **113** (was 101, added 6 + 6); web **31** (no new tests in this plan); type-checks clean; lint clean; build green; `/admin` listed.

- [ ] **Step 2: Manual dev smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && rm -rf apps/web/.next && pnpm --filter @axis/web dev
```

- Visit `/admin` → renders five "—" KPI cards + two empty matrix sections.
- Visit `/connections` → each tile has a "Manage credentials" ghost button. Click → RightPanel slides in with the tool's credentials form (disabled inputs + scope blurb + link to full page).
- Visit `/chat` → run a prompt that triggers a permission request. The PermissionModal renders the new card layout (mono capability, awaiting-pulse dot, 2×2 lifetime grid, full-width Deny).
- Visit `/chat` → during a streaming run, the LiveTaskTree v2 renders mono rows with state dots + duration; a tool-call step has a chevron that expands the args/result pane.

(No commit.)

---

## What we have at the end of this plan

- `PermissionCard` + `LiveTaskTree v2` in `@axis/design-system` with full type exports.
- The chat page's PermissionModal + LiveTaskTree adapters delegate to the new primitives. No callers of those wrappers had to change.
- Connections page has an inline "Manage credentials" affordance that opens RightPanel — `/credentials` standalone route still works as a fallback.
- `/admin` is a static route with stub content — visible structure waiting for backend metrics.
- Design-system tests: **113** (was 101). Web tests unchanged at 31.

## What we explicitly did NOT do (handed off to Plan 8)

- Backend tier registry in `services/agent-orchestration` (would let PermissionCard collapse to single-Allow + popover per artifact §5b).
- Backend `undo` handlers + audience counter in `services/api-gateway` (so WritePreviewCard's optimistic-with-undo path can ship per artifact §5c + ADR 006 amendment).
- Per-capability trust mode store + UI (the artifact's "What Axis can do" panel in Settings that today shows a "Coming soon" stub).
- Real metrics endpoints for the Admin dashboard.
- Onboarding / demo workspace seed.
- Playwright visual regression.

## Self-Review

- **Spec coverage:** Plan 7 covers artifact §3g (Credentials inline panel), §3l (Admin route), §4 (LiveTaskTree component pattern), §5b (PermissionCard inline-in-card pattern). Backend amendments (A1 + A2 wiring) explicitly deferred to Plan 8 with the rationale that the data axes need backend tier registry to match the artifact's single-Allow UX.
- **Placeholder scan:** No "TBD" / "implement later" inside any task step. Stub copy on the Admin page is intentional and labelled clearly as awaiting backend.
- **Type consistency:** `PermissionDecision` = `PermissionLifetime | 'deny'` consistent across `permission-card.tsx`, the test, the index, the barrel, and the web wrapper. `StepState` enum identical between `live-task-tree.tsx`, the test, the index, the web wrapper's `STATUS_TO_STATE` map. `StepData.id` used as key in both nested children and top-level steps.
- **Commands:** Every `pnpm --filter` and `git add` path is correct. The escaped `(app)` paths in zsh are `\(app\)`.
