# Axis UI Plan 5 — Axis-Native Primitives + Chat Shell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Axis-native primitives that the Chat surface needs (`AgentStateDot`, `CitationChip`, `PromptInput`, `DiffViewer`, `WritePreviewCard`) and rebuild the Chat page shell per artifact §3c — sticky bottom-anchored prompt + empty-state with display heading + suggestion chips.

**Architecture:** Each primitive lives in `packages/design-system/src/components/<name>/` and follows the established pattern (`<name>.tsx` + `.test.tsx` + `index.ts`, exported from the package barrel). The new `DiffViewer` replaces the existing thin one in `apps/web/components/diff-viewer.tsx` — that file becomes a re-export. The Chat page rebuild keeps the existing live-task-tree and permission-modal components in place (they get rebuilt in Plan 6 once backend event-protocol coordination is decided) and focuses purely on the prompt input + empty state — the hero affordances of the surface.

**Tech Stack:** Existing — no new deps. React 18 + TS 5.5 + Tailwind + Vitest + RTL + design-system primitives.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§3c Chat + §4 component patterns).

**Out of scope** (handed off):
- Plan 6: PermissionCard rebuild (per A1 amendment), LiveTaskTree v2 with the new event protocol — both depend on backend wiring decisions.
- Plan 7: Per-page rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin) per artifact §3d-§3l.
- Plan 8: Backend support for capability tiers, undo handlers, audience counter, trust mode (ADR 006 + invariant #1).
- Plan 9: Onboarding / demo workspace seed + Playwright visual regression.
- Real chat-streaming wiring — the Chat page shell will keep its existing live-progress / cited-response / permission-modal components, which work but visually predate the new tokens (the Plan 3 sweep already restored their styling).

**Deviations from spec/artifact:**
1. **Chat page is not a wholesale rewrite.** This plan reshapes the empty state + the sticky prompt. The existing live-progress card / preview card / cited-response / permission-modal subtrees remain in place inside the new layout — they get rebuilt in Plan 6 alongside the backend tier-registry work that the artifact's §5b/§5c models require.
2. **`PromptInput` does not yet wire `@connector` chips, slash commands, voice, or file drop.** Those affordances are described in artifact §4 but their data sources (connector list, slash registry, file pipeline) live behind backend / future-plan work. PromptInput exposes the primitive shape; consumer wiring is incremental.
3. **`AgentStateDot` is intentionally close to `BreathingPulse` (Plan 4).** They differ: `BreathingPulse` is a single small dot with the `breathe` keyframe always on; `AgentStateDot` is the more compact "agent state semaphore" used in lists, carrying state + optional pulse + screen-reader label. Both ship.

---

## File structure

**Create:**

```
packages/design-system/src/components/
  agent-state-dot/{agent-state-dot.tsx, agent-state-dot.test.tsx, index.ts}
  citation-chip/{citation-chip.tsx, citation-chip.test.tsx, index.ts}
  prompt-input/{prompt-input.tsx, prompt-input.test.tsx, index.ts}
  diff-viewer/{diff-viewer.tsx, diff-viewer.test.tsx, index.ts}
  write-preview-card/{write-preview-card.tsx, write-preview-card.test.tsx, index.ts}
```

**Modify:**

```
packages/design-system/src/index.ts             # add 5 new exports
apps/web/components/diff-viewer.tsx             # convert to re-export
apps/web/app/(app)/chat/page.tsx                # rebuild empty-state + sticky prompt
```

**Total:** 15 new files, 3 modified, 7 commits (one per primitive + 1 barrel + 1 chat page).

---

## Phase A — Primitives

### Task A1: AgentStateDot primitive

A small accessible state indicator. Used in lists (Home "Running now", future LiveTaskTree, history rows). Distinct from `BreathingPulse` because it carries semantic state + optional label.

**Files:**
- Create: `packages/design-system/src/components/agent-state-dot/agent-state-dot.tsx`
- Create: `packages/design-system/src/components/agent-state-dot/agent-state-dot.test.tsx`
- Create: `packages/design-system/src/components/agent-state-dot/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/agent-state-dot/agent-state-dot.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentStateDot } from './agent-state-dot';

describe('AgentStateDot', () => {
  it('renders with the agent-running tone for the running state', () => {
    render(<AgentStateDot state="running" data-testid="d" />);
    const el = screen.getByTestId('d');
    const dot = el.querySelector('span[aria-hidden="true"]');
    expect(dot).toHaveClass('bg-agent-running');
  });

  it('uses the awaiting tone with pulse for the awaiting state', () => {
    render(<AgentStateDot state="awaiting" data-testid="d" />);
    const dot = screen.getByTestId('d').querySelector('span[aria-hidden="true"]');
    expect(dot).toHaveClass('bg-agent-awaiting');
    expect(dot).toHaveClass('animate-breathe');
  });

  it('does not pulse for the recovered state', () => {
    render(<AgentStateDot state="recovered" data-testid="d" />);
    const dot = screen.getByTestId('d').querySelector('span[aria-hidden="true"]');
    expect(dot).not.toHaveClass('animate-breathe');
  });

  it('renders an sr-only label describing the state', () => {
    render(<AgentStateDot state="blocked" />);
    expect(screen.getByText('Blocked', { selector: '.sr-only' })).toBeInTheDocument();
  });

  it('honors a custom label', () => {
    render(<AgentStateDot state="running" label="Drafting reply" />);
    expect(screen.getByText('Drafting reply', { selector: '.sr-only' })).toBeInTheDocument();
  });

  it('forwards className', () => {
    render(<AgentStateDot state="running" className="my-class" data-testid="d" />);
    expect(screen.getByTestId('d')).toHaveClass('my-class');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/agent-state-dot/agent-state-dot.tsx`:
```tsx
import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type AgentState =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background' | 'done';

export interface AgentStateDotProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  state: AgentState;
  /** Override the screen-reader label (defaults to the state title-cased). */
  label?: string;
}

const TONE: Record<AgentState, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
  done:       'bg-success',
};

const PULSING: ReadonlySet<AgentState> = new Set(['thinking', 'running', 'awaiting']);

const DEFAULT_LABEL: Record<AgentState, string> = {
  thinking:   'Thinking',
  running:    'Running',
  awaiting:   'Awaiting permission',
  recovered:  'Recovered',
  blocked:    'Blocked',
  background: 'Backgrounded',
  done:       'Done',
};

export const AgentStateDot = forwardRef<HTMLSpanElement, AgentStateDotProps>(
  function AgentStateDot({ state, label, className, ...rest }, ref) {
    const text = label ?? DEFAULT_LABEL[state];
    return (
      <span ref={ref} className={clsx('inline-flex items-center', className)} {...rest}>
        <span
          aria-hidden="true"
          className={clsx(
            'inline-block h-2 w-2 rounded-full',
            TONE[state],
            PULSING.has(state) && 'animate-breathe',
          )}
        />
        <span className="sr-only">{text}</span>
      </span>
    );
  },
);
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/agent-state-dot/index.ts`:
```typescript
export { AgentStateDot } from './agent-state-dot';
export type { AgentStateDotProps, AgentState } from './agent-state-dot';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/agent-state-dot && git commit -m "feat(design-system): build AgentStateDot primitive"
```

Expected: 72 + 6 = **78 design-system tests**.

### Task A2: CitationChip primitive

Inline superscript citation pill (`<sup>` button). Click fires a callback the consumer wires (typically opens the RightPanel).

**Files:**
- Create: `packages/design-system/src/components/citation-chip/citation-chip.tsx`
- Create: `packages/design-system/src/components/citation-chip/citation-chip.test.tsx`
- Create: `packages/design-system/src/components/citation-chip/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/citation-chip/citation-chip.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CitationChip } from './citation-chip';

describe('CitationChip', () => {
  it('renders the index inside square brackets', () => {
    render(<CitationChip index={3} sourceId="s_3" />);
    expect(screen.getByText('[3]')).toBeInTheDocument();
  });

  it('exposes the source title via aria-label when provided', () => {
    render(<CitationChip index={1} sourceId="s_1" sourceTitle="Q3 Roadmap" />);
    expect(screen.getByRole('button')).toHaveAccessibleName('Source 1: Q3 Roadmap');
  });

  it('falls back to a generic aria-label', () => {
    render(<CitationChip index={1} sourceId="s_1" />);
    expect(screen.getByRole('button')).toHaveAccessibleName('Source 1');
  });

  it('fires onClick with the sourceId', async () => {
    const onClick = vi.fn();
    render(<CitationChip index={2} sourceId="s_42" onClick={onClick} />);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledWith('s_42');
  });

  it('renders inside a sup element', () => {
    render(<CitationChip index={1} sourceId="s_1" data-testid="c" />);
    expect(screen.getByTestId('c').tagName).toBe('SUP');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/citation-chip/citation-chip.tsx`:
```tsx
import { forwardRef, type HTMLAttributes, type MouseEvent } from 'react';
import clsx from 'clsx';

export interface CitationChipProps extends Omit<HTMLAttributes<HTMLElement>, 'onClick'> {
  index: number;
  sourceId: string;
  sourceTitle?: string;
  onClick?: (sourceId: string) => void;
}

const CHIP =
  'mx-0.5 inline-flex items-center justify-center min-w-[18px] h-4 px-1 rounded-sm bg-accent-subtle text-accent border border-accent/30 font-mono text-[10px] tabular-nums hover:bg-accent hover:text-accent-on transition-colors cursor-pointer';

export const CitationChip = forwardRef<HTMLElement, CitationChipProps>(
  function CitationChip(
    { index, sourceId, sourceTitle, onClick, className, ...rest },
    ref,
  ) {
    const label = sourceTitle ? `Source ${index}: ${sourceTitle}` : `Source ${index}`;
    return (
      <sup ref={ref} className={clsx('citation-chip', className)} {...rest}>
        <button
          type="button"
          aria-label={label}
          onClick={(e: MouseEvent<HTMLButtonElement>) => {
            e.preventDefault();
            onClick?.(sourceId);
          }}
          className={CHIP}
        >
          [{index}]
        </button>
      </sup>
    );
  },
);
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/citation-chip/index.ts`:
```typescript
export { CitationChip } from './citation-chip';
export type { CitationChipProps } from './citation-chip';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/citation-chip && git commit -m "feat(design-system): build CitationChip primitive"
```

Expected: 78 + 5 = **83 design-system tests**.

### Task A3: PromptInput primitive

Multi-line auto-resize textarea (80 → 240 px). `⌘+⏎` / `Ctrl+⏎` submits. `⇧+⏎` newlines. Disabled while in flight. Send button on the right turns primary when there's content.

**Files:**
- Create: `packages/design-system/src/components/prompt-input/prompt-input.tsx`
- Create: `packages/design-system/src/components/prompt-input/prompt-input.test.tsx`
- Create: `packages/design-system/src/components/prompt-input/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/prompt-input/prompt-input.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PromptInput } from './prompt-input';

describe('PromptInput', () => {
  it('renders the placeholder', () => {
    render(<PromptInput value="" onChange={() => {}} onSubmit={() => {}} placeholder="Ask Axis…" />);
    expect(screen.getByPlaceholderText('Ask Axis…')).toBeInTheDocument();
  });

  it('calls onChange while typing', async () => {
    const onChange = vi.fn();
    render(<PromptInput value="" onChange={onChange} onSubmit={() => {}} aria-label="prompt" />);
    await userEvent.type(screen.getByLabelText('prompt'), 'hi');
    // Two characters typed → onChange called twice
    expect(onChange).toHaveBeenCalledTimes(2);
  });

  it('calls onSubmit on ⌘+Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hello" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Meta>}{Enter}{/Meta}');
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('calls onSubmit on Ctrl+Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hello" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Control>}{Enter}{/Control}');
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('does NOT submit on plain Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hi" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Enter}');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit when the send button is clicked', async () => {
    const onSubmit = vi.fn();
    render(<PromptInput value="text" onChange={() => {}} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(onSubmit).toHaveBeenCalledWith('text');
  });

  it('disables the send button when the value is empty', () => {
    render(<PromptInput value="" onChange={() => {}} onSubmit={() => {}} />);
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });

  it('disables both textarea and send when busy', () => {
    render(<PromptInput value="x" onChange={() => {}} onSubmit={() => {}} busy aria-label="prompt" />);
    expect(screen.getByLabelText('prompt')).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/prompt-input/prompt-input.tsx`:
```tsx
'use client';

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  type KeyboardEvent,
  type TextareaHTMLAttributes,
} from 'react';
import clsx from 'clsx';

export interface PromptInputProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  busy?: boolean;
  /** min height in px (default 80). */
  minHeight?: number;
  /** max height in px before scroll (default 240). */
  maxHeight?: number;
}

const WRAPPER =
  'relative flex items-end gap-2 rounded-md border border-edge bg-canvas-surface px-3 py-2 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20 transition-colors';

const TEXTAREA_BASE =
  'flex-1 resize-none bg-transparent text-body text-ink placeholder:text-ink-tertiary focus:outline-none disabled:opacity-50';

const SEND_BASE =
  'inline-flex items-center justify-center h-8 px-4 rounded-sm font-mono text-[11px] uppercase tracking-[0.06em] transition-colors disabled:opacity-40 disabled:cursor-not-allowed';

const SEND_ACTIVE = 'bg-accent text-accent-on hover:bg-accent-hover';
const SEND_INACTIVE = 'bg-canvas-elevated text-ink-tertiary';

export const PromptInput = forwardRef<HTMLTextAreaElement, PromptInputProps>(
  function PromptInput(
    {
      value,
      onChange,
      onSubmit,
      busy = false,
      minHeight = 80,
      maxHeight = 240,
      placeholder = 'Type a message, or /command',
      className,
      style,
      ...rest
    },
    ref,
  ) {
    const innerRef = useRef<HTMLTextAreaElement | null>(null);
    useImperativeHandle(ref, () => innerRef.current as HTMLTextAreaElement);

    const resize = useCallback(() => {
      const el = innerRef.current;
      if (!el) return;
      el.style.height = 'auto';
      const next = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
      el.style.height = `${next}px`;
      el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
    }, [minHeight, maxHeight]);

    useEffect(() => {
      resize();
    }, [value, resize]);

    const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!busy && value.trim().length > 0) onSubmit(value);
        return;
      }
    };

    const canSend = !busy && value.trim().length > 0;

    return (
      <div className={clsx(WRAPPER, className)} style={style}>
        <textarea
          ref={innerRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={busy}
          rows={3}
          className={TEXTAREA_BASE}
          style={{ minHeight }}
          {...rest}
        />
        <button
          type="button"
          aria-label="Send"
          disabled={!canSend}
          onClick={() => onSubmit(value)}
          className={clsx(SEND_BASE, canSend ? SEND_ACTIVE : SEND_INACTIVE)}
        >
          Send
        </button>
      </div>
    );
  },
);
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/prompt-input/index.ts`:
```typescript
export { PromptInput } from './prompt-input';
export type { PromptInputProps } from './prompt-input';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/prompt-input && git commit -m "feat(design-system): build PromptInput primitive"
```

Expected: 83 + 8 = **91 design-system tests**.

### Task A4: DiffViewer primitive (in design-system)

Replaces the 27-line `apps/web/components/diff-viewer.tsx` with a properly tokenized version that lives in design-system. The web file becomes a re-export.

**Files:**
- Create: `packages/design-system/src/components/diff-viewer/diff-viewer.tsx`
- Create: `packages/design-system/src/components/diff-viewer/diff-viewer.test.tsx`
- Create: `packages/design-system/src/components/diff-viewer/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/diff-viewer/diff-viewer.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiffViewer } from './diff-viewer';

describe('DiffViewer', () => {
  it('renders one row per line with a + / − /   prefix', () => {
    render(
      <DiffViewer
        lines={[
          { type: 'add', text: 'hello' },
          { type: 'del', text: 'gone' },
          { type: 'eq', text: 'same' },
        ]}
      />,
    );
    expect(screen.getByText('hello')).toBeInTheDocument();
    expect(screen.getByText('gone')).toBeInTheDocument();
    expect(screen.getByText('same')).toBeInTheDocument();
  });

  it('marks added lines with the success tone', () => {
    render(<DiffViewer lines={[{ type: 'add', text: 'x' }]} />);
    const row = screen.getByText('x').closest('div');
    expect(row).toHaveClass('text-success');
    expect(row).toHaveClass('bg-success/10');
  });

  it('marks removed lines with the danger tone and strikethrough', () => {
    render(<DiffViewer lines={[{ type: 'del', text: 'x' }]} />);
    const row = screen.getByText('x').closest('div');
    expect(row).toHaveClass('text-danger');
    expect(row).toHaveClass('bg-danger/10');
    expect(row).toHaveClass('line-through');
  });

  it('renders an optional header above the diff', () => {
    render(
      <DiffViewer
        header="notion://pages/q3"
        lines={[{ type: 'eq', text: 'x' }]}
      />,
    );
    expect(screen.getByText('notion://pages/q3')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/diff-viewer/diff-viewer.tsx`:
```tsx
import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type DiffLineType = 'add' | 'del' | 'eq';

export interface DiffLine {
  type: DiffLineType;
  text: string;
}

export interface DiffViewerProps extends HTMLAttributes<HTMLDivElement> {
  lines: ReadonlyArray<DiffLine>;
  /** Optional header (e.g. file path) above the diff. */
  header?: ReactNode;
}

const ROW_BASE =
  'flex items-baseline gap-3 px-3 py-0.5 font-mono text-[13px] leading-relaxed whitespace-pre-wrap';

const ROW_CLASSES: Record<DiffLineType, string> = {
  add: 'bg-success/10 text-success',
  del: 'bg-danger/10 text-danger line-through',
  eq:  'text-ink-secondary',
};

const PREFIX: Record<DiffLineType, string> = {
  add: '+',
  del: '−',
  eq:  ' ',
};

export function DiffViewer({ lines, header, className, ...rest }: DiffViewerProps) {
  return (
    <div
      className={clsx('overflow-hidden rounded-md border border-edge bg-canvas-surface', className)}
      {...rest}
    >
      {header && (
        <div className="px-3 py-2 border-b border-edge-subtle font-mono text-mono-s text-ink-tertiary">
          {header}
        </div>
      )}
      <div className="overflow-x-auto py-1">
        {lines.map((line, i) => (
          <div key={i} className={clsx(ROW_BASE, ROW_CLASSES[line.type])}>
            <span aria-hidden="true" className="select-none w-3 text-center text-ink-tertiary">
              {PREFIX[line.type]}
            </span>
            <span>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/diff-viewer/index.ts`:
```typescript
export { DiffViewer } from './diff-viewer';
export type { DiffViewerProps, DiffLine, DiffLineType } from './diff-viewer';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/diff-viewer && git commit -m "feat(design-system): build DiffViewer primitive"
```

Expected: 91 + 4 = **95 design-system tests**.

### Task A5: WritePreviewCard primitive

Composes Card + DiffViewer + Confirm/Edit/Refine/Cancel buttons per artifact §5c.

**Files:**
- Create: `packages/design-system/src/components/write-preview-card/write-preview-card.tsx`
- Create: `packages/design-system/src/components/write-preview-card/write-preview-card.test.tsx`
- Create: `packages/design-system/src/components/write-preview-card/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/write-preview-card/write-preview-card.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WritePreviewCard } from './write-preview-card';

describe('WritePreviewCard', () => {
  it('renders the title', () => {
    render(
      <WritePreviewCard
        title="Gmail · Send draft"
        onConfirm={() => {}}
        onCancel={() => {}}
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByText('Gmail · Send draft')).toBeInTheDocument();
  });

  it('renders meta rows when provided', () => {
    render(
      <WritePreviewCard
        title="Gmail · Send"
        meta={[
          { label: 'To', value: 'a@b.com, c@d.com' },
          { label: 'Subj', value: 'Q3' },
        ]}
        onConfirm={() => {}}
        onCancel={() => {}}
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByText('To')).toBeInTheDocument();
    expect(screen.getByText('a@b.com, c@d.com')).toBeInTheDocument();
    expect(screen.getByText('Subj')).toBeInTheDocument();
  });

  it('fires onConfirm when Confirm is clicked', async () => {
    const onConfirm = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={onConfirm} onCancel={() => {}}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('fires onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={() => {}} onCancel={onCancel}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('renders an Edit button when onEdit is provided', async () => {
    const onEdit = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={() => {}} onCancel={() => {}} onEdit={onEdit}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalled();
  });

  it('disables Confirm and shows the loading label when busy', () => {
    render(
      <WritePreviewCard
        title="x"
        onConfirm={() => {}}
        onCancel={() => {}}
        busy
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByRole('button', { name: /sending/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/write-preview-card/write-preview-card.tsx`:
```tsx
'use client';

import { type ReactNode } from 'react';
import clsx from 'clsx';
import { Card, CardHeader, CardBody, CardFooter } from '../card';
import { Button } from '../button';

export interface WritePreviewMeta {
  label: string;
  value: ReactNode;
}

export interface WritePreviewCardProps {
  title: string;
  meta?: ReadonlyArray<WritePreviewMeta>;
  children?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
  onEdit?: () => void;
  onRefine?: () => void;
  busy?: boolean;
  className?: string;
}

export function WritePreviewCard({
  title,
  meta,
  children,
  onConfirm,
  onCancel,
  onEdit,
  onRefine,
  busy = false,
  className,
}: WritePreviewCardProps) {
  return (
    <Card className={clsx('shadow-e1', className)}>
      <CardHeader className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Write preview
        </span>
        <span className="text-body-s font-medium text-ink">{title}</span>
      </CardHeader>

      {meta && meta.length > 0 && (
        <div className="px-5 py-3 border-b border-edge-subtle space-y-1">
          {meta.map((m, i) => (
            <div key={i} className="flex items-baseline gap-3 text-body-s">
              <span className="w-12 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                {m.label}
              </span>
              <span className="text-ink">{m.value}</span>
            </div>
          ))}
        </div>
      )}

      <CardBody>{children}</CardBody>

      <CardFooter className="flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        {onEdit && (
          <Button variant="secondary" size="sm" onClick={onEdit} disabled={busy}>
            Edit
          </Button>
        )}
        {onRefine && (
          <Button variant="secondary" size="sm" onClick={onRefine} disabled={busy}>
            Refine
          </Button>
        )}
        <Button variant="primary" size="sm" onClick={onConfirm} disabled={busy} loading={busy}>
          {busy ? 'Sending…' : 'Confirm'}
        </Button>
      </CardFooter>
    </Card>
  );
}
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/write-preview-card/index.ts`:
```typescript
export { WritePreviewCard } from './write-preview-card';
export type { WritePreviewCardProps, WritePreviewMeta } from './write-preview-card';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/write-preview-card && git commit -m "feat(design-system): build WritePreviewCard primitive"
```

Expected: 95 + 6 = **101 design-system tests**.

---

## Phase B — Wire-up + Chat page

### Task B1: Extend the design-system barrel + re-export DiffViewer in web

**Files:**
- Modify: `packages/design-system/src/index.ts`
- Modify: `apps/web/components/diff-viewer.tsx` (becomes re-export)

- [ ] **Step 1: Append the new exports to the barrel**

Edit `packages/design-system/src/index.ts` — append:
```typescript
// Plan 5 — Axis-native primitives.
export { AgentStateDot, type AgentStateDotProps, type AgentState } from './components/agent-state-dot';
export { CitationChip, type CitationChipProps } from './components/citation-chip';
export { PromptInput, type PromptInputProps } from './components/prompt-input';
export { DiffViewer, type DiffViewerProps, type DiffLine, type DiffLineType } from './components/diff-viewer';
export { WritePreviewCard, type WritePreviewCardProps, type WritePreviewMeta } from './components/write-preview-card';
```

- [ ] **Step 2: Replace `apps/web/components/diff-viewer.tsx` with a re-export**

Overwrite the file:
```typescript
export { DiffViewer, type DiffViewerProps, type DiffLine, type DiffLineType } from '@axis/design-system';
```

- [ ] **Step 3: Type-check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && pnpm --filter @axis/web type-check 2>&1 | tail -10
```

If any caller of the OLD `DiffLine` type was using `'eq'` only (matches), nothing changes; the new type uses the same union (`'add' | 'del' | 'eq'`) so callers continue to compile. If a caller surfaces any type error, fix it inline.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/index.ts apps/web/components/diff-viewer.tsx && git commit -m "refactor(web): re-export Plan 5 primitives + DiffViewer from design-system"
```

### Task B2: Rebuild the Chat page shell per artifact §3c

**Files:**
- Modify: `apps/web/app/(app)/chat/page.tsx`

- [ ] **Step 1: Read the current page** to inventory what's there (live progress, write preview card, last result, meta row, correction form, sticky command bar — per the audit).

```bash
cat /Users/mrinalraj/Documents/Axis/apps/web/app/\(app\)/chat/page.tsx | head -80
```

- [ ] **Step 2: Identify the parts to PRESERVE** (existing functioning logic):
   - The query / mutation hooks (`useRunChat`, `usePermissionDecide`, etc.)
   - The existing components used inside the page (`PermissionModal`, `LiveTaskTree`, `CitedResponse`, `DiffViewer`)
   - State: `prompt`, `running`, `result`, `error`, `permission`, `events`, `correction`

The redesign affects the OUTER LAYOUT and the EMPTY-STATE UX. The interactive run logic stays as-is; we wrap it in the new chrome.

- [ ] **Step 3: Rewrite the layout, replacing the existing command bar with `<PromptInput>` and replacing the existing empty-state with the artifact-spec one**

The general pattern (adapt to whatever exact state/handlers the existing file uses — preserve every existing handler, just move where it lives):

```tsx
'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  PromptInput,
} from '@axis/design-system';
// keep existing imports for query hooks, PermissionModal, LiveTaskTree, CitedResponse, DiffViewer, etc.

const SUGGESTED_PROMPTS: ReadonlyArray<string> = [
  'Summarize what happened in #product on Slack today',
  'Draft a Q3 retro in Notion',
  'Triage my Gmail inbox',
];

export default function ChatPage() {
  const router = useRouter();
  const params = useSearchParams();
  const initialPrompt = params.get('prompt') ?? '';

  const [prompt, setPrompt] = useState(initialPrompt);
  // keep all the other useState / hook calls from the existing file
  // (running, result, error, permission, events, correction, etc.)

  const onSubmit = (text: string) => {
    // call into the existing run / mutation handler that the previous file used
    // (e.g. runChat.mutateAsync({ prompt: text }) or whatever it was named)
    setPrompt(text);
    // ...existing run kickoff logic ...
  };

  const isEmpty = !prompt && !/* whatever signal "no run yet" used to be */ false;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-6 py-10">
          {isEmpty ? (
            <EmptyState onPick={(p) => setPrompt(p)} />
          ) : (
            // Existing live progress / preview card / cited-response / correction form
            // — keep ALL the existing JSX here, just remove the old sticky command bar at the bottom
            <>
              {/* preserve existing children: live task tree, write-preview card, results */}
            </>
          )}
        </div>
      </div>

      {/* Sticky bottom prompt — replaces the prior bar */}
      <div className="border-t border-edge-subtle bg-canvas-surface">
        <div className="mx-auto w-full max-w-[860px] px-6 py-4">
          <PromptInput
            value={prompt}
            onChange={setPrompt}
            onSubmit={onSubmit}
            busy={false /* hook this to the existing "running" boolean */}
            placeholder="Type a message, or /command"
            aria-label="Prompt"
          />
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-20 text-center">
      <h1 className="font-display text-display-l text-ink">What should Axis do?</h1>
      <p className="text-body text-ink-secondary max-w-prose">
        Pick a starter or write your own. Axis can read and write across your connected tools.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-[640px] w-full">
        {SUGGESTED_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick(p)}
            className="block p-4 rounded-md border border-edge-subtle bg-canvas-surface text-left hover:border-edge hover:bg-canvas-elevated transition-colors"
          >
            <span className="text-body-s text-ink">{p}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

**The implementer of this task must:**
1. Read the entire existing `apps/web/app/(app)/chat/page.tsx` (~265 lines) first.
2. Preserve every single existing query hook, mutation, event listener, and child component (PermissionModal, LiveTaskTree, CitedResponse, DiffViewer).
3. Move the OUTER layout to the new pattern shown above.
4. Replace ONLY the bottom command bar with `<PromptInput>`.
5. Replace ONLY the empty state with the new EmptyState component.
6. Keep everything else inside `<>` in the active branch — preserve JSX structure of the live-progress block and result block.
7. Pass the existing "running" boolean to PromptInput's `busy` prop.

If the existing handler signature for "submit prompt" is different (e.g. takes form event, takes object), adapt the `onSubmit` callback to call it correctly.

- [ ] **Step 4: Smoke test in dev**

```bash
cd /Users/mrinalraj/Documents/Axis && rm -rf apps/web/.next && pnpm --filter @axis/web build 2>&1 | tail -10
```

If it builds, the file structure is sound. Visit `/chat?prompt=summarize` in dev to confirm the prompt arrives and the new bottom bar renders.

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(app\)/chat/page.tsx && git commit -m "feat(web): rebuild Chat page shell per artifact §3c"
```

### Task B3: Final verify

- [ ] **Step 1: Tests**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10
```

Expected: design-system **101** (was 72, added 29 across A1-A5: 6 + 5 + 8 + 4 + 6); web **31** (no new tests in this plan).

- [ ] **Step 2: Type-check + lint + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && pnpm lint 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | tail -10
```

Expected: clean, clean, clean, green.

- [ ] **Step 3: Manual dev smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```

Visit `http://localhost:3001/chat`:
- Bottom is the new `<PromptInput>` — click in, type, press ⌘+Enter or click Send.
- Empty state above shows the display heading + 3 suggested prompt cards. Clicking a card fills the prompt.
- Existing live task tree / preview card / cited response continue to render once a run starts (preserved from the old code).

(No commit — this is verification.)

---

## What we have at the end of this plan

- 5 new Axis-native primitives in `@axis/design-system`: `AgentStateDot`, `CitationChip`, `PromptInput`, `DiffViewer`, `WritePreviewCard`.
- Web's old `apps/web/components/diff-viewer.tsx` is now a thin re-export.
- Chat page reshaped: sticky bottom `<PromptInput>` + display-font empty state with three suggestion chips that pre-fill the prompt. Existing run logic preserved.
- Design-system tests: **101** (was 72). Web tests unchanged at 31.

## What we explicitly did NOT do (handed off)

- Plan 6: PermissionCard rebuild (per A1 amendment), LiveTaskTree v2 (per artifact §4), per-page rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin) per artifact §3d-§3l.
- Plan 7: Backend support for capability tiers, undo handlers, audience counter, trust mode (ADR 006 + invariant #1).
- Plan 8: Onboarding / demo workspace seed + Playwright visual regression.
- Live wiring of `WritePreviewCard` to backend write-confirm flow — the primitive ships; the consumer that calls it lands when the backend `undo` endpoint exists.
- Live wiring of `CitationChip` to a citation-fetch action in chat — the primitive fires `onClick(sourceId)`; what the consumer does with it is incremental.

## Self-Review

- **Spec coverage:** Covers artifact §3c (Chat shell, prompt input pinned at bottom, empty state with suggestions) and §4 (DiffViewer, AgentStateDot, CitationChip, PromptInput, WritePreviewCard component patterns). The deferred items (LiveTaskTree v2, PermissionCard) are explicit and tied to backend coordination.
- **Placeholder scan:** No "TBD"; no "implement later". Task B2 step 3 documents the OUTER-vs-INNER preservation contract explicitly so the implementer doesn't accidentally rewrite working code.
- **Type consistency:** `AgentState` consistent across `agent-state-dot.tsx`, the test, the index, and the barrel. `DiffLine` / `DiffLineType` shared between `diff-viewer.tsx` and the legacy file's re-export. `WritePreviewMeta` declared once in `write-preview-card.tsx`. `PromptInputProps` exposes `value/onChange/onSubmit/busy` consistently across implementation and tests.
- **Commands:** Every `pnpm --filter` targets an existing package. Each `git add` path matches the file the task created/modified.
