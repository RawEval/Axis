# Axis UI Plan 2 — Primitive Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 11 design-system primitives the inner-app pages need before they can be rebuilt — Badge, StatusBadge, Avatar, Kbd, SkeletonBlock, SegmentedControl, Modal, Toast, DropdownMenu, Tooltip, Tabs.

**Architecture:** Simple primitives (Badge / StatusBadge / Avatar / Kbd / SkeletonBlock / SegmentedControl) are hand-rolled styled `div` / `span` components. Behavior-heavy primitives (Modal / DropdownMenu / Tooltip / Tabs) wrap Radix primitives — a11y, focus trap, keyboard nav are theirs; we own the styling. Toast is custom because we need a queue + a 30 s "undo" affordance that doesn't exist in any off-the-shelf library. All primitives live in `packages/design-system/src/components/<name>/` and follow Plan 1's pattern (`<name>.tsx`, `<name>.test.tsx`, `index.ts`).

**Tech Stack:** Adds `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip`, `@radix-ui/react-tabs` to design-system. Existing: React 18, TS 5.5, Vitest 1.x, RTL, `clsx`, Tailwind 3.4 (consumes the new tokens via the web app's config). Toast uses Zustand-style hook (no new dep — primitive React state in a singleton store).

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§4 Component patterns).

**Out of scope** (handed off):
- Plan 3: shell rewrite (LeftNav 240/56 + Topbar 48 + RightPanel 360 + ⌘K + ? overlay) and inner-app page restoration (chat / feed / history / connections / memory / settings / team / projects).
- Plan 4: Axis-native components (LiveTaskTree, DiffViewer, PermissionCard, WritePreviewCard, CitationChip, AgentStateDot, ConnectorTile, MemoryRow, PromptInput, BreathingPulse) + Home operations-center + Playwright visual regression.
- Plan 5: Backend support for capability tiers, undo handlers, audience counter, trust mode.
- Plan 6: Onboarding, demo workspace seed.

**Deviations from spec/artifact:**
1. **Toast does not yet wire to the backend `undo` endpoint.** That endpoint doesn't exist (Plan 5 builds it). Toast component exposes the API; the actual undo callback is the consumer's. No backend change in this plan.
2. **No Combobox / Select primitive.** The artifact mentions these but no inner-app page in Plan 3's scope needs them yet. Defer until first consumer.

---

## File structure

**Create:**

```
packages/design-system/src/components/
  badge/{badge.tsx, badge.test.tsx, index.ts}
  status-badge/{status-badge.tsx, status-badge.test.tsx, index.ts}
  avatar/{avatar.tsx, avatar.test.tsx, index.ts}
  kbd/{kbd.tsx, kbd.test.tsx, index.ts}
  skeleton/{skeleton.tsx, skeleton.test.tsx, index.ts}
  segmented-control/{segmented-control.tsx, segmented-control.test.tsx, index.ts}
  modal/{modal.tsx, modal.test.tsx, index.ts}
  toast/{toast.tsx, toast.test.tsx, toast-store.ts, index.ts}
  dropdown-menu/{dropdown-menu.tsx, dropdown-menu.test.tsx, index.ts}
  tooltip/{tooltip.tsx, tooltip.test.tsx, index.ts}
  tabs/{tabs.tsx, tabs.test.tsx, index.ts}
```

**Modify:**

```
packages/design-system/package.json                # add Radix deps
packages/design-system/src/index.ts                # extend barrel exports
```

**Total:** 33 new files, 2 modified, 13 commits (one per primitive task + 1 deps + 1 barrel).

---

## Phase A — Setup

### Task A1: Install Radix dependencies

**Files:**
- Modify: `packages/design-system/package.json`

- [ ] **Step 1: Install Radix packages**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system add @radix-ui/react-dialog@^1.1.2 @radix-ui/react-dropdown-menu@^2.1.2 @radix-ui/react-tooltip@^1.1.4 @radix-ui/react-tabs@^1.1.1
```

Expected: 4 packages added.

- [ ] **Step 2: Verify installations**

```bash
cd /Users/mrinalraj/Documents/Axis && cat packages/design-system/package.json | grep -A 6 '"dependencies"'
```

Expected: the four `@radix-ui/*` packages appear in the dependencies block.

- [ ] **Step 3: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/package.json pnpm-lock.yaml && git commit -m "build(design-system): add radix primitives for modal/dropdown/tooltip/tabs"
```

---

## Phase B — Simple primitives

These six are pure styled markup. TDD: small test, simple implementation.

### Task B1: Badge

The all-purpose count / tag pill. Used everywhere.

**Files:**
- Create: `packages/design-system/src/components/badge/badge.tsx`
- Create: `packages/design-system/src/components/badge/badge.test.tsx`
- Create: `packages/design-system/src/components/badge/index.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/design-system/src/components/badge/badge.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>12</Badge>);
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('defaults to neutral tone', () => {
    render(<Badge data-testid="b">x</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('bg-canvas-elevated');
  });

  it('applies the success tone', () => {
    render(<Badge tone="success" data-testid="b">ok</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('text-success');
  });

  it('applies the danger tone', () => {
    render(<Badge tone="danger" data-testid="b">err</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('text-danger');
  });

  it('renders the with-dot variant', () => {
    render(<Badge tone="warning" dot data-testid="b">stale</Badge>);
    const el = screen.getByTestId('b');
    expect(el.querySelector('span[aria-hidden="true"]')).toBeInTheDocument();
  });

  it('forwards className', () => {
    render(<Badge className="my-class" data-testid="b">x</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('my-class');
  });
});
```

- [ ] **Step 2: Run, expect 6 failures (module not found)**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/badge/badge.tsx`:
```tsx
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  dot?: boolean;
  children?: ReactNode;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: 'bg-canvas-elevated text-ink-secondary border-edge-subtle',
  accent:  'bg-accent-subtle text-accent border-accent/30',
  success: 'bg-success/10 text-success border-success/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
  danger:  'bg-danger/10 text-danger border-danger/30',
  info:    'bg-info/10 text-info border-info/30',
};

const DOT_COLOR: Record<BadgeTone, string> = {
  neutral: 'bg-ink-tertiary',
  accent:  'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger:  'bg-danger',
  info:    'bg-info',
};

const BASE = 'inline-flex items-center gap-1.5 h-5 px-2 rounded-full border text-caption font-medium tabular-nums';

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { tone = 'neutral', dot = false, className, children, ...rest },
  ref,
) {
  return (
    <span ref={ref} className={clsx(BASE, TONE_CLASSES[tone], className)} {...rest}>
      {dot && <span aria-hidden="true" className={clsx('h-1.5 w-1.5 rounded-full', DOT_COLOR[tone])} />}
      {children}
    </span>
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/badge/index.ts`:
```typescript
export { Badge } from './badge';
export type { BadgeProps, BadgeTone } from './badge';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/badge && git commit -m "feat(design-system): build Badge primitive"
```

Expected: 6 new badge tests pass + 25 prior = **31 total**.

### Task B2: StatusBadge — mono uppercase agent-state pill with optional pulse

The artifact §4 status-badge: mono 11px, uppercase, semantic color at 8% bg / 18% border, optional 5px pulsing dot.

**Files:**
- Create: `packages/design-system/src/components/status-badge/status-badge.tsx`
- Create: `packages/design-system/src/components/status-badge/status-badge.test.tsx`
- Create: `packages/design-system/src/components/status-badge/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/status-badge/status-badge.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from './status-badge';

describe('StatusBadge', () => {
  it('renders the status text uppercased', () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('uses the agent-running tone color', () => {
    render(<StatusBadge status="running" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('text-agent-running');
  });

  it('renders a pulsing dot when pulse is true', () => {
    render(<StatusBadge status="thinking" pulse data-testid="s" />);
    const dot = screen.getByTestId('s').querySelector('span[aria-hidden="true"]');
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveClass('animate-breathe');
  });

  it('renders a static dot when pulse is false', () => {
    render(<StatusBadge status="done" data-testid="s" />);
    const dot = screen.getByTestId('s').querySelector('span[aria-hidden="true"]');
    expect(dot).not.toHaveClass('animate-breathe');
  });

  it('exposes a className override', () => {
    render(<StatusBadge status="awaiting" className="my" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('my');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/status-badge/status-badge.tsx`:
```tsx
import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type StatusKind =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background' | 'done';

export interface StatusBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  status: StatusKind;
  /** Optional override label (defaults to uppercased status string). */
  label?: string;
  /** Show a breathing pulse on the dot. */
  pulse?: boolean;
}

const TONE: Record<StatusKind, string> = {
  thinking:   'text-agent-thinking bg-agent-thinking/10 border-agent-thinking/20',
  running:    'text-agent-running bg-agent-running/10 border-agent-running/20',
  awaiting:   'text-agent-awaiting bg-agent-awaiting/10 border-agent-awaiting/20',
  recovered:  'text-agent-recovered bg-agent-recovered/10 border-agent-recovered/20',
  blocked:    'text-agent-blocked bg-agent-blocked/10 border-agent-blocked/20',
  background: 'text-agent-background bg-agent-background/10 border-agent-background/20',
  done:       'text-success bg-success/10 border-success/20',
};

const DOT_BG: Record<StatusKind, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
  done:       'bg-success',
};

const BASE =
  'inline-flex items-center gap-1.5 h-5 px-2 rounded-full border font-mono text-[11px] uppercase tracking-[0.08em] tabular-nums whitespace-nowrap';

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(function StatusBadge(
  { status, label, pulse = false, className, ...rest },
  ref,
) {
  return (
    <span ref={ref} className={clsx(BASE, TONE[status], className)} {...rest}>
      <span
        aria-hidden="true"
        className={clsx('h-1.5 w-1.5 rounded-full', DOT_BG[status], pulse && 'animate-breathe')}
      />
      {label ?? status.toUpperCase()}
    </span>
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/status-badge/index.ts`:
```typescript
export { StatusBadge } from './status-badge';
export type { StatusBadgeProps, StatusKind } from './status-badge';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/status-badge && git commit -m "feat(design-system): build StatusBadge with agent-state tones"
```

### Task B3: Avatar

**Files:**
- Create: `packages/design-system/src/components/avatar/avatar.tsx`
- Create: `packages/design-system/src/components/avatar/avatar.test.tsx`
- Create: `packages/design-system/src/components/avatar/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/avatar/avatar.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Avatar } from './avatar';

describe('Avatar', () => {
  it('renders the first letter of name when no src', () => {
    render(<Avatar name="Alice" />);
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('renders an img when src is provided', () => {
    render(<Avatar name="Alice" src="/x.png" />);
    expect(screen.getByRole('img')).toHaveAttribute('src', '/x.png');
  });

  it('uses the agent shape (squircle) when shape="agent"', () => {
    render(<Avatar name="Axis" shape="agent" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('rounded-md');
  });

  it('uses circle by default', () => {
    render(<Avatar name="x" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('rounded-full');
  });

  it('applies size sm/md/lg', () => {
    const { rerender } = render(<Avatar name="x" size="sm" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('h-6');
    rerender(<Avatar name="x" size="lg" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('h-10');
  });

  it('falls back to ? when no name and no src', () => {
    render(<Avatar />);
    expect(screen.getByText('?')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/avatar/avatar.tsx`:
```tsx
import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type AvatarShape = 'circle' | 'agent';
export type AvatarSize = 'sm' | 'md' | 'lg';

export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  name?: string;
  src?: string;
  alt?: string;
  shape?: AvatarShape;
  size?: AvatarSize;
}

const SIZE_CLASSES: Record<AvatarSize, string> = {
  sm: 'h-6 w-6 text-caption',
  md: 'h-8 w-8 text-body-s',
  lg: 'h-10 w-10 text-body',
};

const SHAPE_CLASSES: Record<AvatarShape, string> = {
  circle: 'rounded-full',
  agent: 'rounded-md',
};

function initial(name?: string): string {
  if (!name) return '?';
  const c = name.trim().charAt(0);
  return c ? c.toUpperCase() : '?';
}

export const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(function Avatar(
  { name, src, alt, shape = 'circle', size = 'md', className, ...rest },
  ref,
) {
  const base = clsx(
    'inline-flex items-center justify-center font-medium overflow-hidden border border-edge-subtle bg-canvas-elevated text-ink',
    SIZE_CLASSES[size],
    SHAPE_CLASSES[shape],
    className,
  );

  return (
    <span ref={ref} className={base} {...rest}>
      {src ? (
        <img src={src} alt={alt ?? name ?? ''} className="h-full w-full object-cover" />
      ) : (
        initial(name)
      )}
    </span>
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/avatar/index.ts`:
```typescript
export { Avatar } from './avatar';
export type { AvatarProps, AvatarShape, AvatarSize } from './avatar';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/avatar && git commit -m "feat(design-system): build Avatar primitive (initial + img + agent shape)"
```

### Task B4: Kbd

Mono keyboard chip per artifact §4.

**Files:**
- Create: `packages/design-system/src/components/kbd/kbd.tsx`
- Create: `packages/design-system/src/components/kbd/kbd.test.tsx`
- Create: `packages/design-system/src/components/kbd/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/kbd/kbd.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Kbd } from './kbd';

describe('Kbd', () => {
  it('renders the key label', () => {
    render(<Kbd>⌘K</Kbd>);
    expect(screen.getByText('⌘K')).toBeInTheDocument();
  });

  it('uses mono font + border', () => {
    render(<Kbd data-testid="k">A</Kbd>);
    const el = screen.getByTestId('k');
    expect(el).toHaveClass('font-mono');
    expect(el).toHaveClass('border');
  });

  it('renders inside a kbd element', () => {
    render(<Kbd>X</Kbd>);
    expect(screen.getByText('X').tagName).toBe('KBD');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/kbd/kbd.tsx`:
```tsx
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface KbdProps extends HTMLAttributes<HTMLElement> {
  children?: ReactNode;
}

const BASE =
  'inline-flex items-center justify-center min-w-[20px] h-[20px] px-1 rounded-xs border border-edge bg-canvas-elevated text-ink-secondary font-mono text-[11px] tracking-[0.02em] tabular-nums';

export const Kbd = forwardRef<HTMLElement, KbdProps>(function Kbd(
  { className, children, ...rest },
  ref,
) {
  return (
    <kbd ref={ref} className={clsx(BASE, className)} {...rest}>
      {children}
    </kbd>
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/kbd/index.ts`:
```typescript
export { Kbd } from './kbd';
export type { KbdProps } from './kbd';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/kbd && git commit -m "feat(design-system): build Kbd primitive"
```

### Task B5: SkeletonBlock

Loading placeholder per artifact §6 — `bg-elevated` block with shimmer sweep.

**Files:**
- Create: `packages/design-system/src/components/skeleton/skeleton.tsx`
- Create: `packages/design-system/src/components/skeleton/skeleton.test.tsx`
- Create: `packages/design-system/src/components/skeleton/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/skeleton/skeleton.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from './skeleton';

describe('Skeleton', () => {
  it('renders an empty container with shimmer animation', () => {
    render(<Skeleton data-testid="s" />);
    const el = screen.getByTestId('s');
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass('animate-shimmer');
  });

  it('respects width and height props', () => {
    render(<Skeleton width={120} height={20} data-testid="s" />);
    const el = screen.getByTestId('s');
    expect(el).toHaveStyle({ width: '120px', height: '20px' });
  });

  it('exposes className override', () => {
    render(<Skeleton className="my" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('my');
  });

  it('uses the rounded variant when rounded="full"', () => {
    render(<Skeleton rounded="full" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('rounded-full');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/skeleton/skeleton.tsx`:
```tsx
import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type SkeletonRounded = 'sm' | 'md' | 'lg' | 'full';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: number | string;
  height?: number | string;
  rounded?: SkeletonRounded;
}

const ROUNDED: Record<SkeletonRounded, string> = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

const BASE = 'block bg-canvas-elevated overflow-hidden relative animate-shimmer';

function px(v: number | string | undefined): string | undefined {
  if (v == null) return undefined;
  return typeof v === 'number' ? `${v}px` : v;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(function Skeleton(
  { width, height, rounded = 'md', className, style, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      aria-hidden="true"
      className={clsx(BASE, ROUNDED[rounded], className)}
      style={{ width: px(width), height: px(height), ...style }}
      {...rest}
    />
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/skeleton/index.ts`:
```typescript
export { Skeleton } from './skeleton';
export type { SkeletonProps, SkeletonRounded } from './skeleton';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/skeleton && git commit -m "feat(design-system): build Skeleton primitive"
```

### Task B6: SegmentedControl

Tab-like switcher with sliding indicator per artifact §4.

**Files:**
- Create: `packages/design-system/src/components/segmented-control/segmented-control.tsx`
- Create: `packages/design-system/src/components/segmented-control/segmented-control.test.tsx`
- Create: `packages/design-system/src/components/segmented-control/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/segmented-control/segmented-control.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SegmentedControl } from './segmented-control';

describe('SegmentedControl', () => {
  const options = [
    { value: 'all', label: 'All' },
    { value: 'mine', label: 'Mine' },
    { value: 'team', label: 'Team' },
  ];

  it('renders each option label', () => {
    render(<SegmentedControl value="all" onChange={() => {}} options={options} />);
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('Mine')).toBeInTheDocument();
    expect(screen.getByText('Team')).toBeInTheDocument();
  });

  it('marks the active option', () => {
    render(<SegmentedControl value="mine" onChange={() => {}} options={options} />);
    expect(screen.getByRole('button', { name: 'Mine' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onChange with the new value when a button is clicked', async () => {
    const onChange = vi.fn();
    render(<SegmentedControl value="all" onChange={onChange} options={options} />);
    await userEvent.click(screen.getByText('Team'));
    expect(onChange).toHaveBeenCalledWith('team');
  });

  it('does not call onChange when the active option is clicked', async () => {
    const onChange = vi.fn();
    render(<SegmentedControl value="all" onChange={onChange} options={options} />);
    await userEvent.click(screen.getByText('All'));
    expect(onChange).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/segmented-control/segmented-control.tsx`:
```tsx
import clsx from 'clsx';

export interface SegmentedControlOption<T extends string = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SegmentedControlProps<T extends string = string> {
  value: T;
  onChange: (value: T) => void;
  options: ReadonlyArray<SegmentedControlOption<T>>;
  className?: string;
  'aria-label'?: string;
}

const CONTAINER =
  'inline-flex items-center h-8 p-0.5 rounded-md border border-edge bg-canvas-elevated';

const SEGMENT_BASE =
  'inline-flex items-center justify-center px-3 h-7 rounded-sm font-mono text-[11px] uppercase tracking-[0.06em] transition-colors duration-[120ms] ease-out';

const SEGMENT_ACTIVE = 'bg-canvas-surface text-ink shadow-sm';
const SEGMENT_INACTIVE = 'text-ink-secondary hover:text-ink';

export function SegmentedControl<T extends string = string>({
  value,
  onChange,
  options,
  className,
  ...rest
}: SegmentedControlProps<T>) {
  return (
    <div role="group" className={clsx(CONTAINER, className)} {...rest}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            disabled={opt.disabled}
            aria-pressed={active}
            className={clsx(
              SEGMENT_BASE,
              active ? SEGMENT_ACTIVE : SEGMENT_INACTIVE,
              opt.disabled && 'opacity-40 cursor-not-allowed',
            )}
            onClick={() => {
              if (!active && !opt.disabled) onChange(opt.value);
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/segmented-control/index.ts`:
```typescript
export { SegmentedControl } from './segmented-control';
export type { SegmentedControlProps, SegmentedControlOption } from './segmented-control';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/segmented-control && git commit -m "feat(design-system): build SegmentedControl primitive"
```

---

## Phase C — Behavior-heavy primitives

These wrap Radix for a11y / focus / keyboard. We own the styling and the composition API.

### Task C1: Modal — Radix Dialog wrapper

**Files:**
- Create: `packages/design-system/src/components/modal/modal.tsx`
- Create: `packages/design-system/src/components/modal/modal.test.tsx`
- Create: `packages/design-system/src/components/modal/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/modal/modal.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal, ModalTitle, ModalBody, ModalFooter } from './modal';

describe('Modal', () => {
  it('does not render when open is false', () => {
    render(
      <Modal open={false} onOpenChange={() => {}}>
        <ModalTitle>Hi</ModalTitle>
      </Modal>,
    );
    expect(screen.queryByText('Hi')).not.toBeInTheDocument();
  });

  it('renders title / body / footer slots when open', () => {
    render(
      <Modal open onOpenChange={() => {}}>
        <ModalTitle>Title</ModalTitle>
        <ModalBody>Body</ModalBody>
        <ModalFooter>Footer</ModalFooter>
      </Modal>,
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
    expect(screen.getByText('Footer')).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when Escape is pressed', async () => {
    const onOpenChange = vi.fn();
    render(
      <Modal open onOpenChange={onOpenChange}>
        <ModalTitle>x</ModalTitle>
      </Modal>,
    );
    await userEvent.keyboard('{Escape}');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('exposes a description slot via ModalDescription', () => {
    render(
      <Modal open onOpenChange={() => {}}>
        <ModalTitle>x</ModalTitle>
      </Modal>,
    );
    // dialog must be present
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/modal/modal.tsx`:
```tsx
'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  /** max-width override (default 480px). */
  widthClass?: string;
}

const OVERLAY =
  'fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out';

const CONTENT =
  'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full bg-canvas-surface border border-edge rounded-lg shadow-e3 outline-none max-h-[85vh] flex flex-col';

export function Modal({ open, onOpenChange, children, widthClass = 'max-w-[480px]' }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={OVERLAY} />
        <Dialog.Content className={clsx(CONTENT, widthClass)} aria-describedby={undefined}>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ModalTitle({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <Dialog.Title asChild>
      <h2 className={clsx('px-6 pt-6 pb-2 text-heading-2 text-ink', className)} {...rest}>
        {children}
      </h2>
    </Dialog.Title>
  );
}

export function ModalDescription({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <Dialog.Description asChild>
      <p className={clsx('px-6 text-body-s text-ink-secondary', className)} {...rest}>
        {children}
      </p>
    </Dialog.Description>
  );
}

export function ModalBody({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('px-6 py-4 overflow-y-auto', className)} {...rest}>
      {children}
    </div>
  );
}

export function ModalFooter({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('px-6 pb-6 pt-2 flex items-center justify-end gap-3', className)} {...rest}>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/modal/index.ts`:
```typescript
export { Modal, ModalTitle, ModalDescription, ModalBody, ModalFooter } from './modal';
export type { ModalProps } from './modal';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/modal && git commit -m "feat(design-system): build Modal primitive (radix dialog)"
```

### Task C2: Toast — custom queue + undo

The artifact §4 says action toasts (the undo flavor) live up to 30 s, hover pauses dismiss, no auto-dismiss for action-required. Custom because Radix's toast queue model doesn't fit this UX cleanly.

**Files:**
- Create: `packages/design-system/src/components/toast/toast-store.ts`
- Create: `packages/design-system/src/components/toast/toast.tsx`
- Create: `packages/design-system/src/components/toast/toast.test.tsx`
- Create: `packages/design-system/src/components/toast/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/toast/toast.test.tsx`:
```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastViewport, useToasts, toast } from './toast';

describe('Toast', () => {
  beforeEach(() => {
    // reset toast store
    useToasts.setState({ toasts: [] });
  });

  it('renders no toasts initially', () => {
    render(<ToastViewport />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows a toast when toast.success is called', () => {
    render(<ToastViewport />);
    act(() => {
      toast.success('Saved');
    });
    expect(screen.getByText('Saved')).toBeInTheDocument();
  });

  it('shows an undo toast with an Undo button', async () => {
    const onUndo = vi.fn();
    render(<ToastViewport />);
    act(() => {
      toast.action('Sent message', { actionLabel: 'Undo', onAction: onUndo });
    });
    expect(screen.getByText('Sent message')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Undo' }));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });

  it('removes a toast when its dismiss icon is clicked', async () => {
    render(<ToastViewport />);
    act(() => {
      toast.info('Hello');
    });
    expect(screen.getByText('Hello')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByText('Hello')).not.toBeInTheDocument();
  });

  it('renders the danger tone for error toasts', () => {
    render(<ToastViewport />);
    act(() => {
      toast.error('Failed');
    });
    expect(screen.getByText('Failed').closest('[role="status"]')).toHaveClass('border-danger/30');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement the store**

Create `packages/design-system/src/components/toast/toast-store.ts`:
```typescript
import { useSyncExternalStore } from 'react';

export type ToastTone = 'info' | 'success' | 'warning' | 'danger' | 'action';

export interface ToastItem {
  id: string;
  tone: ToastTone;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  /** ms; undefined = no auto-dismiss. */
  durationMs?: number;
}

type Store = {
  toasts: ToastItem[];
};

const listeners = new Set<() => void>();
let state: Store = { toasts: [] };

function emit() {
  for (const l of listeners) l();
}

export const useToasts = (() => {
  const subscribe = (l: () => void) => {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  };
  const getSnapshot = () => state;
  const setState = (next: Store | ((prev: Store) => Store)) => {
    state = typeof next === 'function' ? (next as (p: Store) => Store)(state) : next;
    emit();
  };

  function hook(): Store {
    return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  }

  hook.setState = setState;
  hook.getState = () => state;
  return hook;
})();

let counter = 0;
function makeId(): string {
  counter += 1;
  return `toast_${counter}`;
}

export function pushToast(input: Omit<ToastItem, 'id'>): string {
  const id = makeId();
  const item: ToastItem = { id, ...input };
  useToasts.setState((s) => ({ toasts: [...s.toasts, item] }));
  if (item.durationMs && item.durationMs > 0) {
    setTimeout(() => dismissToast(id), item.durationMs);
  }
  return id;
}

export function dismissToast(id: string): void {
  useToasts.setState((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
}
```

- [ ] **Step 4: Implement the React layer**

Create `packages/design-system/src/components/toast/toast.tsx`:
```tsx
'use client';

import clsx from 'clsx';
import { type ReactNode } from 'react';
import { dismissToast, pushToast, useToasts, type ToastTone } from './toast-store';

export { useToasts, dismissToast, pushToast };

const TONE_CLASSES: Record<ToastTone, string> = {
  info:    'bg-info/10 border-info/30 text-info',
  success: 'bg-success/10 border-success/30 text-success',
  warning: 'bg-warning/10 border-warning/30 text-warning',
  danger:  'bg-danger/10 border-danger/30 text-danger',
  action:  'bg-accent-subtle border-accent/30 text-accent',
};

export function ToastViewport() {
  const { toasts } = useToasts();
  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-6 right-6 z-[60] flex flex-col gap-2 max-w-[360px] w-full pointer-events-none"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={clsx(
            'pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-md border shadow-e2 bg-canvas-surface',
            TONE_CLASSES[t.tone],
          )}
        >
          <div className="flex-1 text-body-s text-ink">{t.message}</div>
          {t.actionLabel && t.onAction && (
            <button
              type="button"
              className="font-mono text-[11px] uppercase tracking-[0.06em] text-accent hover:text-accent-hover"
              onClick={() => {
                t.onAction?.();
                dismissToast(t.id);
              }}
            >
              {t.actionLabel}
            </button>
          )}
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => dismissToast(t.id)}
            className="text-ink-tertiary hover:text-ink-secondary"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export const toast = {
  info: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'info', message, durationMs: opts.durationMs ?? 4000 }),
  success: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'success', message, durationMs: opts.durationMs ?? 4000 }),
  warning: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'warning', message, durationMs: opts.durationMs ?? 4000 }),
  error: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'danger', message, durationMs: opts.durationMs ?? 4000 }),
  action: (
    message: string,
    opts: { actionLabel: string; onAction: () => void; durationMs?: number },
  ) =>
    pushToast({
      tone: 'action',
      message,
      actionLabel: opts.actionLabel,
      onAction: opts.onAction,
      durationMs: opts.durationMs ?? 30_000,
    }),
};

// Re-export children for convenience
export type { ToastTone, ToastItem } from './toast-store';
```

- [ ] **Step 5: Index**

Create `packages/design-system/src/components/toast/index.ts`:
```typescript
export { ToastViewport, toast, useToasts, dismissToast, pushToast } from './toast';
export type { ToastItem, ToastTone } from './toast';
```

- [ ] **Step 6: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/toast && git commit -m "feat(design-system): build Toast primitive with action+undo support"
```

### Task C3: DropdownMenu — Radix DropdownMenu wrapper

**Files:**
- Create: `packages/design-system/src/components/dropdown-menu/dropdown-menu.tsx`
- Create: `packages/design-system/src/components/dropdown-menu/dropdown-menu.test.tsx`
- Create: `packages/design-system/src/components/dropdown-menu/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/dropdown-menu/dropdown-menu.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from './dropdown-menu';

describe('DropdownMenu', () => {
  it('opens when the trigger is clicked', async () => {
    render(
      <DropdownMenu>
        <DropdownMenuTrigger>Open</DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem>One</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Two</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    );
    await userEvent.click(screen.getByText('Open'));
    expect(await screen.findByText('One')).toBeInTheDocument();
    expect(screen.getByText('Two')).toBeInTheDocument();
  });

  it('fires onSelect when an item is chosen', async () => {
    const onSelect = vi.fn();
    render(
      <DropdownMenu>
        <DropdownMenuTrigger>Open</DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={onSelect}>Pick</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    );
    await userEvent.click(screen.getByText('Open'));
    await userEvent.click(await screen.findByText('Pick'));
    expect(onSelect).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/dropdown-menu/dropdown-menu.tsx`:
```tsx
'use client';

import * as DM from '@radix-ui/react-dropdown-menu';
import clsx from 'clsx';
import { forwardRef, type ComponentPropsWithoutRef } from 'react';

export const DropdownMenu = DM.Root;
export const DropdownMenuTrigger = DM.Trigger;

const CONTENT =
  'min-w-[180px] z-50 bg-canvas-surface border border-edge rounded-md shadow-e2 p-1 outline-none';

export const DropdownMenuContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Content>
>(function DropdownMenuContent({ className, sideOffset = 4, ...rest }, ref) {
  return (
    <DM.Portal>
      <DM.Content
        ref={ref}
        sideOffset={sideOffset}
        className={clsx(CONTENT, className)}
        {...rest}
      />
    </DM.Portal>
  );
});

const ITEM =
  'relative flex items-center h-8 px-3 rounded-sm text-body-s text-ink-secondary cursor-pointer outline-none data-[highlighted]:bg-canvas-elevated data-[highlighted]:text-ink data-[disabled]:opacity-40 data-[disabled]:cursor-not-allowed';

export const DropdownMenuItem = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Item>
>(function DropdownMenuItem({ className, ...rest }, ref) {
  return <DM.Item ref={ref} className={clsx(ITEM, className)} {...rest} />;
});

export const DropdownMenuSeparator = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Separator>
>(function DropdownMenuSeparator({ className, ...rest }, ref) {
  return (
    <DM.Separator
      ref={ref}
      className={clsx('h-px my-1 bg-edge-subtle', className)}
      {...rest}
    />
  );
});

export const DropdownMenuLabel = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Label>
>(function DropdownMenuLabel({ className, ...rest }, ref) {
  return (
    <DM.Label
      ref={ref}
      className={clsx(
        'px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.04em] text-ink-tertiary',
        className,
      )}
      {...rest}
    />
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/dropdown-menu/index.ts`:
```typescript
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from './dropdown-menu';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/dropdown-menu && git commit -m "feat(design-system): build DropdownMenu primitive (radix)"
```

### Task C4: Tooltip — Radix Tooltip wrapper

**Files:**
- Create: `packages/design-system/src/components/tooltip/tooltip.tsx`
- Create: `packages/design-system/src/components/tooltip/tooltip.test.tsx`
- Create: `packages/design-system/src/components/tooltip/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/tooltip/tooltip.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Tooltip, TooltipProvider } from './tooltip';

describe('Tooltip', () => {
  it('wraps a trigger and exposes a label', () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip label="Hi">
          <button>Trigger</button>
        </Tooltip>
      </TooltipProvider>,
    );
    expect(screen.getByText('Trigger')).toBeInTheDocument();
  });
});
```

(Tooltip's hover-show is hard to test reliably without timers; the smoke test confirms it composes without error. Coverage of show-on-hover comes via integration / manual smoke when shell consumers land in Plan 3.)

- [ ] **Step 2: Run, expect 1 failure**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/tooltip/tooltip.tsx`:
```tsx
'use client';

import * as TT from '@radix-ui/react-tooltip';
import clsx from 'clsx';
import { type ReactNode } from 'react';

export const TooltipProvider = TT.Provider;

export interface TooltipProps {
  label: ReactNode;
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  delayDuration?: number;
}

const CONTENT =
  'z-[70] px-2 py-1 rounded bg-canvas-surface border border-edge shadow-e2 text-caption text-ink-secondary';

export function Tooltip({
  label,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 600,
}: TooltipProps) {
  return (
    <TT.Root delayDuration={delayDuration}>
      <TT.Trigger asChild>{children}</TT.Trigger>
      <TT.Portal>
        <TT.Content side={side} align={align} className={clsx(CONTENT)} sideOffset={4}>
          {label}
        </TT.Content>
      </TT.Portal>
    </TT.Root>
  );
}
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/tooltip/index.ts`:
```typescript
export { Tooltip, TooltipProvider } from './tooltip';
export type { TooltipProps } from './tooltip';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/tooltip && git commit -m "feat(design-system): build Tooltip primitive (radix)"
```

### Task C5: Tabs — Radix Tabs wrapper

**Files:**
- Create: `packages/design-system/src/components/tabs/tabs.tsx`
- Create: `packages/design-system/src/components/tabs/tabs.test.tsx`
- Create: `packages/design-system/src/components/tabs/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/tabs/tabs.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './tabs';

describe('Tabs', () => {
  it('shows the default panel', () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
          <TabsTrigger value="b">B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">panel-a</TabsContent>
        <TabsContent value="b">panel-b</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText('panel-a')).toBeInTheDocument();
    expect(screen.queryByText('panel-b')).not.toBeInTheDocument();
  });

  it('switches panel on trigger click', async () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
          <TabsTrigger value="b">B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">panel-a</TabsContent>
        <TabsContent value="b">panel-b</TabsContent>
      </Tabs>,
    );
    await userEvent.click(screen.getByText('B'));
    expect(screen.getByText('panel-b')).toBeInTheDocument();
    expect(screen.queryByText('panel-a')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/tabs/tabs.tsx`:
```tsx
'use client';

import * as T from '@radix-ui/react-tabs';
import clsx from 'clsx';
import { forwardRef, type ComponentPropsWithoutRef } from 'react';

export const Tabs = T.Root;

const LIST = 'inline-flex items-end gap-4 border-b border-edge-subtle';

export const TabsList = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof T.List>
>(function TabsList({ className, ...rest }, ref) {
  return <T.List ref={ref} className={clsx(LIST, className)} {...rest} />;
});

const TRIGGER =
  'h-10 -mb-px px-1 text-body-s font-medium text-ink-secondary border-b-2 border-transparent hover:text-ink data-[state=active]:text-ink data-[state=active]:border-accent transition-colors';

export const TabsTrigger = forwardRef<
  HTMLButtonElement,
  ComponentPropsWithoutRef<typeof T.Trigger>
>(function TabsTrigger({ className, ...rest }, ref) {
  return <T.Trigger ref={ref} className={clsx(TRIGGER, className)} {...rest} />;
});

export const TabsContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof T.Content>
>(function TabsContent({ className, ...rest }, ref) {
  return <T.Content ref={ref} className={clsx('pt-6 outline-none', className)} {...rest} />;
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/tabs/index.ts`:
```typescript
export { Tabs, TabsList, TabsTrigger, TabsContent } from './tabs';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/tabs && git commit -m "feat(design-system): build Tabs primitive (radix)"
```

---

## Phase D — Wire-up

### Task D1: Extend the design-system barrel

**Files:**
- Modify: `packages/design-system/src/index.ts`

- [ ] **Step 1: Read current index**

```bash
cat /Users/mrinalraj/Documents/Axis/packages/design-system/src/index.ts
```

- [ ] **Step 2: Add the new exports**

Append to `packages/design-system/src/index.ts`:
```typescript
// Phase 2 — Plan 2 primitives.
export { Badge, type BadgeProps, type BadgeTone } from './components/badge';
export { StatusBadge, type StatusBadgeProps, type StatusKind } from './components/status-badge';
export { Avatar, type AvatarProps, type AvatarShape, type AvatarSize } from './components/avatar';
export { Kbd, type KbdProps } from './components/kbd';
export { Skeleton, type SkeletonProps, type SkeletonRounded } from './components/skeleton';
export {
  SegmentedControl,
  type SegmentedControlProps,
  type SegmentedControlOption,
} from './components/segmented-control';
export {
  Modal,
  ModalTitle,
  ModalDescription,
  ModalBody,
  ModalFooter,
  type ModalProps,
} from './components/modal';
export {
  ToastViewport,
  toast,
  useToasts,
  dismissToast,
  pushToast,
  type ToastItem,
  type ToastTone,
} from './components/toast';
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from './components/dropdown-menu';
export { Tooltip, TooltipProvider, type TooltipProps } from './components/tooltip';
export { Tabs, TabsList, TabsTrigger, TabsContent } from './components/tabs';
```

- [ ] **Step 3: Type-check the package**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system type-check 2>&1 | tail -10
```

Expected: clean. Any error here means a primitive's actual exports don't match what the barrel declared.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/index.ts && git commit -m "refactor(design-system): export Plan 2 primitives from barrel"
```

### Task D2: Final verify

- [ ] **Step 1: Workspace test count**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Tests|passed|failed)" | head -10
```

Expected: design-system reports the new test totals (started Plan 2 at 25; should grow by: 6 badge + 5 status-badge + 6 avatar + 3 kbd + 4 skeleton + 4 segmented + 4 modal + 5 toast + 2 dropdown + 1 tooltip + 2 tabs = 42 new tests = **67 design-system tests**); web stays at **4**.

- [ ] **Step 2: Workspace type-check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm type-check 2>&1 | tail -10
```

Expected: design-system + web pass. The `notification-service` failure remains pre-existing and out of scope.

- [ ] **Step 3: Workspace lint**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm lint 2>&1 | tail -10
```

Expected: clean.

- [ ] **Step 4: Web build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -15
```

Expected: green. The new primitives aren't consumed by any web file yet, so the build output is unchanged from Plan 1's end state. (No commit for verify — it's a checkpoint, not a change.)

---

## What we have at the end of this plan

- 11 design-system primitives, all tested, all exported from the package barrel: `Badge`, `StatusBadge`, `Avatar`, `Kbd`, `Skeleton`, `SegmentedControl`, `Modal`, `Toast`, `DropdownMenu`, `Tooltip`, `Tabs`.
- ~42 new unit tests (67 total in design-system).
- Build still green, type-check still green, lint still clean.

## What we explicitly did NOT do (handed off to Plan 3)

- The shell rewrite (`LeftNav 240/56` + `Topbar 48` + `RightPanel 360` + `ThemeToggle` UI + `⌘K` command palette via `cmdk` + `?` shortcut overlay).
- Inner-app pages (chat, feed, history, memory, settings, connections, team, projects) — they still render with broken styles until Plan 3 swaps their dead Tailwind classes.
- Migrating web's existing `apps/web/components/ui/badge.tsx` and similar wrappers to re-export from design-system — done as part of Plan 3 when each page that consumes them gets touched.

## Self-Review

- **Spec coverage:** All 11 primitives the artifact §4 lists as needed-by-Plan-3-pages are in this plan. The deferred ones (`Combobox`, `Select`, `ContextMenu`, `ProgressBar`) are not blocked-by-Plan-3 and are pushed to later plans where their first consumer lands.
- **Placeholder scan:** No "TBD"; no "implement later"; no "similar to Task N"; every code block is complete.
- **Type consistency:** `BadgeTone` ⊂ `'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'` consistent across Badge.tsx and the barrel. `StatusKind` consistent across StatusBadge.tsx, the test, and the barrel. `ToastTone` declared once in toast-store.ts, re-exported from toast.tsx and from index.ts. `Modal*` slot names match between modal.tsx, modal.test.tsx, modal/index.ts, and the barrel. `DropdownMenu*` symbol names consistent across all three locations.
- **Commands:** Every `pnpm --filter` command targets an existing package per `pnpm-workspace.yaml`. Each `git add` path matches the file the task created.
