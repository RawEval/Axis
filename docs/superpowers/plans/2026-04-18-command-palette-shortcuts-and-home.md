# Axis UI Plan 4 — ⌘K Palette + ? Overlay + Home Operations-Center

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the ⌘K command palette (cmdk-backed), the `?` shortcut overlay, the `BreathingPulse` primitive, and the Home operations-center page from artifact §3a — so users have a real landing page (instead of an instant redirect to `/chat`) and global keyboard navigation.

**Architecture:** `cmdk` provides the searchable palette primitive; we wrap it with our own categories (Navigation / Connectors / Theme / Recent). Global key handlers live in a single hook (`useGlobalShortcuts`) mounted once in `Shell`. The Home page is a server component that streams real connector data via React Query and renders empty states for the rest (running runs / approvals / recent runs are deferred to Plan 5+ when backend support exists). `BreathingPulse` is a tiny styled span that other components can compose — Home uses it on placeholder agent rows; future Plan 5 work will use it on real running rows.

**Tech Stack:** Adds `cmdk` (Paco Coursey's command palette). Existing — Next.js 14, React 18, TS 5.5, Tailwind 3.4, design-system primitives, lucide-react.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§3a Home + App Shell, §5j Keyboard model).

**Out of scope** (handed off):
- Plan 5: Chat page rebuild + remaining Axis-native components (`LiveTaskTree`, `DiffViewer`, `PermissionCard`, `WritePreviewCard`, `CitationChip`, `AgentStateDot`, `ConnectorTile`, `MemoryRow`, `PromptInput`).
- Plan 6: Per-page rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin) per artifact §3d-§3l.
- Plan 7: Backend support for capability tiers, undo handlers, audience counter, trust mode (ADR 006 + invariant #1 amendments).
- Plan 8: Onboarding / demo workspace seed + Playwright visual regression.

**Deviations from spec/artifact:**
1. **Home shows empty states for "Running now" and "Needs your approval".** Real data requires the backend to expose run/approval state (Plan 7). For now those sections render a friendly empty state with a "Start a chat" CTA that links to `/chat`.
2. **⌘K palette has only Navigation + Theme + Connectors categories.** Recent runs, pinned prompts, and capability-jump are deferred to Plan 5/6 when their data lives somewhere.
3. **? overlay is static.** It shows a hardcoded list of shortcuts from artifact §5j; per-page contextual shortcuts arrive in Plan 5.

---

## File structure

**Create:**

```
packages/design-system/src/components/breathing-pulse/
  breathing-pulse.tsx
  breathing-pulse.test.tsx
  index.ts

apps/web/components/shell/
  command-palette.tsx              # cmdk wrapper
  command-palette.test.tsx
  shortcut-overlay.tsx
  shortcut-overlay.test.tsx

apps/web/lib/
  global-shortcuts.ts              # useGlobalShortcuts hook + open/close stores
  global-shortcuts.test.ts

apps/web/app/(app)/
  page.tsx                         # The new Home (operations-center)
```

**Modify:**

```
packages/design-system/package.json          # add cmdk
packages/design-system/src/index.ts          # export BreathingPulse
apps/web/components/shell/shell.tsx          # mount CommandPalette + ShortcutOverlay + global-shortcut hook
```

**Delete:**

```
apps/web/app/page.tsx                        # was a redirect to /chat — replaced by app/(app)/page.tsx (Home)
```

**Total:** ~10 new files, ~3 modified, 1 deleted, ~7 commits.

---

## Phase A — Setup + primitive

### Task A1: Add `cmdk` dependency to apps/web

**Files:**
- Modify: `apps/web/package.json`

The consumer (`CommandPalette` wrapper) lives in `apps/web/components/shell/`, so cmdk goes in apps/web's deps.

- [ ] **Step 1: Install**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web add cmdk@^1.0.0
```

Expected: 1 package added.

- [ ] **Step 2: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/package.json pnpm-lock.yaml && git commit -m "build(web): add cmdk for command palette"
```

### Task A2: BreathingPulse primitive

A small dot or ring that loops the `breathe` keyframe — used on active / running rows in Home and (later) Chat task tree.

**Files:**
- Create: `packages/design-system/src/components/breathing-pulse/breathing-pulse.tsx`
- Create: `packages/design-system/src/components/breathing-pulse/breathing-pulse.test.tsx`
- Create: `packages/design-system/src/components/breathing-pulse/index.ts`
- Modify: `packages/design-system/src/index.ts`

- [ ] **Step 1: Failing test**

Create `packages/design-system/src/components/breathing-pulse/breathing-pulse.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BreathingPulse } from './breathing-pulse';

describe('BreathingPulse', () => {
  it('renders an aria-hidden span with the breathe animation', () => {
    render(<BreathingPulse data-testid="p" />);
    const el = screen.getByTestId('p');
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute('aria-hidden', 'true');
    expect(el).toHaveClass('animate-breathe');
  });

  it('uses the agent-running tone by default', () => {
    render(<BreathingPulse data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('bg-agent-running');
  });

  it('honors the tone prop', () => {
    render(<BreathingPulse tone="awaiting" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('bg-agent-awaiting');
  });

  it('honors the size prop', () => {
    const { rerender } = render(<BreathingPulse size="sm" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('h-1.5');
    rerender(<BreathingPulse size="lg" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('h-3');
  });

  it('forwards className', () => {
    render(<BreathingPulse className="my-class" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('my-class');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/breathing-pulse/breathing-pulse.tsx`:
```tsx
import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type BreathingTone =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background';

export type BreathingSize = 'sm' | 'md' | 'lg';

export interface BreathingPulseProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  tone?: BreathingTone;
  size?: BreathingSize;
}

const TONE: Record<BreathingTone, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
};

const SIZE: Record<BreathingSize, string> = {
  sm: 'h-1.5 w-1.5',
  md: 'h-2 w-2',
  lg: 'h-3 w-3',
};

export const BreathingPulse = forwardRef<HTMLSpanElement, BreathingPulseProps>(
  function BreathingPulse({ tone = 'running', size = 'md', className, ...rest }, ref) {
    return (
      <span
        ref={ref}
        aria-hidden="true"
        className={clsx('inline-block rounded-full animate-breathe', TONE[tone], SIZE[size], className)}
        {...rest}
      />
    );
  },
);
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/breathing-pulse/index.ts`:
```typescript
export { BreathingPulse } from './breathing-pulse';
export type { BreathingPulseProps, BreathingTone, BreathingSize } from './breathing-pulse';
```

- [ ] **Step 5: Re-export from package barrel**

Edit `packages/design-system/src/index.ts` — append:
```typescript
export {
  BreathingPulse,
  type BreathingPulseProps,
  type BreathingTone,
  type BreathingSize,
} from './components/breathing-pulse';
```

- [ ] **Step 6: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/breathing-pulse packages/design-system/src/index.ts && git commit -m "feat(design-system): build BreathingPulse primitive"
```

Expected: 67 + 5 = **72 design-system tests**.

---

## Phase B — Global shortcuts plumbing

### Task B1: Global shortcuts store + hook

A tiny external store mirroring the `right-panel` pattern from Plan 3. Two booleans (palette-open, overlay-open) + setters. A `useGlobalShortcuts` hook binds the keyboard listeners.

**Files:**
- Create: `apps/web/lib/global-shortcuts.ts`
- Create: `apps/web/lib/global-shortcuts.test.ts`

- [ ] **Step 1: Failing test**

Create `apps/web/lib/global-shortcuts.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { commandPalette, shortcutOverlay } from './global-shortcuts';

describe('global-shortcuts stores', () => {
  beforeEach(() => {
    commandPalette.close();
    shortcutOverlay.close();
  });

  it('command palette starts closed', () => {
    expect(commandPalette.getState().open).toBe(false);
  });

  it('command palette toggle flips state', () => {
    commandPalette.toggle();
    expect(commandPalette.getState().open).toBe(true);
    commandPalette.toggle();
    expect(commandPalette.getState().open).toBe(false);
  });

  it('shortcut overlay opens and closes', () => {
    shortcutOverlay.open();
    expect(shortcutOverlay.getState().open).toBe(true);
    shortcutOverlay.close();
    expect(shortcutOverlay.getState().open).toBe(false);
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement the stores + hook**

Create `apps/web/lib/global-shortcuts.ts`:
```typescript
import { useEffect } from 'react';
import { useSyncExternalStore } from 'react';

interface OpenState {
  open: boolean;
}

function makeStore() {
  let state: OpenState = { open: false };
  const listeners = new Set<() => void>();
  const emit = () => {
    for (const l of listeners) l();
  };
  return {
    getState: (): OpenState => state,
    open: () => {
      if (state.open) return;
      state = { open: true };
      emit();
    },
    close: () => {
      if (!state.open) return;
      state = { open: false };
      emit();
    },
    toggle: () => {
      state = { open: !state.open };
      emit();
    },
    subscribe: (l: () => void) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
  };
}

export const commandPalette = makeStore();
export const shortcutOverlay = makeStore();

export function useCommandPalette(): OpenState {
  return useSyncExternalStore(
    commandPalette.subscribe,
    commandPalette.getState,
    commandPalette.getState,
  );
}

export function useShortcutOverlay(): OpenState {
  return useSyncExternalStore(
    shortcutOverlay.subscribe,
    shortcutOverlay.getState,
    shortcutOverlay.getState,
  );
}

/**
 * Mounts the global key handlers. Call once from the app shell.
 *  - ⌘K / Ctrl+K toggles the command palette.
 *  - ?  opens the shortcut overlay (only when not focused inside an input).
 *  - Escape closes whichever is open.
 */
export function useGlobalShortcuts(): void {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const inField =
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        commandPalette.toggle();
        return;
      }

      if (e.key === '?' && !inField) {
        e.preventDefault();
        shortcutOverlay.open();
        return;
      }

      if (e.key === 'Escape') {
        if (commandPalette.getState().open) commandPalette.close();
        if (shortcutOverlay.getState().open) shortcutOverlay.close();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}
```

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/lib/global-shortcuts.ts apps/web/lib/global-shortcuts.test.ts && git commit -m "feat(web): add global-shortcuts stores + hook"
```

Expected: 21 + 3 = **24 web tests**.

---

## Phase C — Palette + Overlay components

### Task C1: CommandPalette component

cmdk-based searchable palette with three categories.

**Files:**
- Create: `apps/web/components/shell/command-palette.tsx`
- Create: `apps/web/components/shell/command-palette.test.tsx`

- [ ] **Step 1: Failing test**

Create `apps/web/components/shell/command-palette.test.tsx`:
```tsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/lib/theme';
import { commandPalette } from '@/lib/global-shortcuts';
import { CommandPalette } from './command-palette';

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
  usePathname: () => '/',
}));

beforeEach(() => {
  pushMock.mockReset();
  act(() => {
    commandPalette.close();
  });
});

function rendered() {
  return render(
    <ThemeProvider>
      <CommandPalette />
    </ThemeProvider>,
  );
}

describe('CommandPalette', () => {
  it('renders nothing when the store is closed', () => {
    rendered();
    expect(screen.queryByPlaceholderText(/search…/i)).not.toBeInTheDocument();
  });

  it('renders the search input + nav category when opened', () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    expect(screen.getByPlaceholderText(/search…/i)).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Activity')).toBeInTheDocument();
  });

  it('navigates and closes when a nav item is selected', async () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    await userEvent.click(screen.getByText('Chat'));
    expect(pushMock).toHaveBeenCalledWith('/chat');
    expect(commandPalette.getState().open).toBe(false);
  });

  it('exposes theme switching items', () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    expect(screen.getByText(/light theme/i)).toBeInTheDocument();
    expect(screen.getByText(/dark theme/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement**

Create `apps/web/components/shell/command-palette.tsx`:
```tsx
'use client';

import { Command } from 'cmdk';
import { useRouter } from 'next/navigation';
import {
  Activity,
  Brain,
  Clock,
  FolderOpen,
  Home,
  MessageSquare,
  Monitor,
  Moon,
  Plug,
  Settings,
  Sun,
  Users,
} from 'lucide-react';
import { commandPalette, useCommandPalette } from '@/lib/global-shortcuts';
import { useTheme, type Theme } from '@/lib/theme';

const NAV = [
  { href: '/',            label: 'Home',        icon: Home },
  { href: '/chat',        label: 'Chat',        icon: MessageSquare },
  { href: '/feed',        label: 'Activity',    icon: Activity },
  { href: '/history',     label: 'History',     icon: Clock },
  { href: '/memory',      label: 'Memory',      icon: Brain },
  { href: '/projects',    label: 'Projects',    icon: FolderOpen },
  { href: '/connections', label: 'Connections', icon: Plug },
  { href: '/team',        label: 'Team',        icon: Users },
  { href: '/settings',    label: 'Settings',    icon: Settings },
] as const;

const THEMES: ReadonlyArray<{ value: Theme; label: string; Icon: typeof Sun }> = [
  { value: 'system', label: 'Use system theme', Icon: Monitor },
  { value: 'light',  label: 'Light theme',      Icon: Sun },
  { value: 'dark',   label: 'Dark theme',       Icon: Moon },
];

export function CommandPalette() {
  const { open } = useCommandPalette();
  const router = useRouter();
  const { setTheme } = useTheme();

  if (!open) return null;

  const close = () => commandPalette.close();

  return (
    <div
      className="fixed inset-0 z-[80] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-[2px]"
      onClick={close}
    >
      <Command
        label="Command palette"
        className="w-full max-w-[520px] mx-4 bg-canvas-surface border border-edge rounded-lg shadow-e3 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command.Input
          placeholder="Search…"
          autoFocus
          className="w-full h-12 px-4 bg-transparent border-b border-edge-subtle text-body text-ink placeholder:text-ink-tertiary focus:outline-none"
        />
        <Command.List className="max-h-[60vh] overflow-y-auto p-2">
          <Command.Empty className="px-4 py-6 text-center text-body-s text-ink-tertiary">
            No results.
          </Command.Empty>

          <Command.Group
            heading="Navigation"
            className="text-ink-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em]"
          >
            {NAV.map((item) => {
              const Icon = item.icon;
              return (
                <Command.Item
                  key={item.href}
                  value={`nav-${item.label}`}
                  onSelect={() => {
                    router.push(item.href);
                    close();
                  }}
                  className="flex items-center gap-3 h-9 px-2 rounded-sm text-body-s text-ink-secondary cursor-pointer data-[selected=true]:bg-canvas-elevated data-[selected=true]:text-ink"
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{item.label}</span>
                </Command.Item>
              );
            })}
          </Command.Group>

          <Command.Group
            heading="Theme"
            className="text-ink-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em]"
          >
            {THEMES.map(({ value, label, Icon }) => (
              <Command.Item
                key={value}
                value={`theme-${value}`}
                onSelect={() => {
                  setTheme(value);
                  close();
                }}
                className="flex items-center gap-3 h-9 px-2 rounded-sm text-body-s text-ink-secondary cursor-pointer data-[selected=true]:bg-canvas-elevated data-[selected=true]:text-ink"
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/command-palette.tsx apps/web/components/shell/command-palette.test.tsx && git commit -m "feat(web): build CommandPalette (cmdk) with nav + theme categories"
```

Expected: 24 + 4 = **28 web tests**.

### Task C2: ShortcutOverlay component

Static, scrollable list of keyboard shortcuts grouped by category.

**Files:**
- Create: `apps/web/components/shell/shortcut-overlay.tsx`
- Create: `apps/web/components/shell/shortcut-overlay.test.tsx`

- [ ] **Step 1: Failing test**

Create `apps/web/components/shell/shortcut-overlay.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { shortcutOverlay } from '@/lib/global-shortcuts';
import { ShortcutOverlay } from './shortcut-overlay';

beforeEach(() => {
  act(() => {
    shortcutOverlay.close();
  });
});

describe('ShortcutOverlay', () => {
  it('renders nothing when closed', () => {
    render(<ShortcutOverlay />);
    expect(screen.queryByText(/keyboard shortcuts/i)).not.toBeInTheDocument();
  });

  it('renders shortcut categories when opened', () => {
    render(<ShortcutOverlay />);
    act(() => {
      shortcutOverlay.open();
    });
    expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
    expect(screen.getByText(/global/i)).toBeInTheDocument();
    expect(screen.getByText(/command palette/i)).toBeInTheDocument();
  });

  it('closes when Close button is clicked', async () => {
    render(<ShortcutOverlay />);
    act(() => {
      shortcutOverlay.open();
    });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(shortcutOverlay.getState().open).toBe(false);
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement**

Create `apps/web/components/shell/shortcut-overlay.tsx`:
```tsx
'use client';

import { X } from 'lucide-react';
import { Kbd } from '@axis/design-system';
import { shortcutOverlay, useShortcutOverlay } from '@/lib/global-shortcuts';

interface Shortcut {
  keys: ReadonlyArray<string>;
  label: string;
}

interface ShortcutGroup {
  title: string;
  items: ReadonlyArray<Shortcut>;
}

const GROUPS: ReadonlyArray<ShortcutGroup> = [
  {
    title: 'Global',
    items: [
      { keys: ['⌘', 'K'],          label: 'Command palette' },
      { keys: ['?'],                label: 'Show shortcuts' },
      { keys: ['Esc'],              label: 'Close palette / overlay' },
    ],
  },
  {
    title: 'Navigation',
    items: [
      { keys: ['G', 'H'],           label: 'Go to Home' },
      { keys: ['G', 'C'],           label: 'Go to Chat' },
      { keys: ['G', 'A'],           label: 'Go to Activity' },
      { keys: ['G', 'S'],           label: 'Go to Settings' },
    ],
  },
  {
    title: 'Chat (coming soon)',
    items: [
      { keys: ['⌘', '⏎'],          label: 'Send prompt' },
      { keys: ['⇧', '⏎'],          label: 'Newline' },
      { keys: ['⌘', '.'],           label: 'Stop current run' },
    ],
  },
];

export function ShortcutOverlay() {
  const { open } = useShortcutOverlay();
  if (!open) return null;

  const close = () => shortcutOverlay.close();

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 backdrop-blur-[2px]"
      onClick={close}
    >
      <div
        role="dialog"
        aria-label="Keyboard shortcuts"
        className="w-full max-w-[640px] mx-4 max-h-[80vh] bg-canvas-surface border border-edge rounded-lg shadow-e3 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between h-12 px-4 border-b border-edge-subtle">
          <h2 className="font-display text-heading-2 text-ink">Keyboard shortcuts</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={close}
            className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {GROUPS.map((group) => (
            <section key={group.title}>
              <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-3">
                {group.title}
              </h3>
              <ul className="space-y-2">
                {group.items.map((s) => (
                  <li key={s.label} className="flex items-center justify-between text-body-s">
                    <span className="text-ink">{s.label}</span>
                    <span className="flex items-center gap-1">
                      {s.keys.map((k) => (
                        <Kbd key={k}>{k}</Kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/shortcut-overlay.tsx apps/web/components/shell/shortcut-overlay.test.tsx && git commit -m "feat(web): build ShortcutOverlay with hardcoded shortcut groups"
```

Expected: 28 + 3 = **31 web tests**.

---

## Phase D — Wire palette + overlay into the shell

### Task D1: Mount in `Shell`

**Files:**
- Modify: `apps/web/components/shell/shell.tsx`

- [ ] **Step 1: Read the current shell**

```bash
cat /Users/mrinalraj/Documents/Axis/apps/web/components/shell/shell.tsx
```

- [ ] **Step 2: Edit to add CommandPalette + ShortcutOverlay + the global-shortcuts hook**

Modify `apps/web/components/shell/shell.tsx`:
```tsx
'use client';

import { type ReactNode } from 'react';
import { ToastViewport, TooltipProvider } from '@axis/design-system';
import { LeftNav } from './left-nav';
import { TopBar } from './top-bar';
import { RightPanel } from './right-panel';
import { CommandPalette } from './command-palette';
import { ShortcutOverlay } from './shortcut-overlay';
import { useGlobalShortcuts } from '@/lib/global-shortcuts';

export function Shell({ children }: { children: ReactNode }) {
  useGlobalShortcuts();
  return (
    <TooltipProvider delayDuration={500}>
      <div className="flex h-screen w-screen overflow-hidden bg-canvas">
        <LeftNav />
        <div className="flex flex-1 min-w-0 flex-col">
          <TopBar />
          <div className="flex flex-1 min-h-0">
            <main className="flex-1 overflow-y-auto">{children}</main>
            <RightPanel />
          </div>
        </div>
      </div>
      <CommandPalette />
      <ShortcutOverlay />
      <ToastViewport />
    </TooltipProvider>
  );
}
```

- [ ] **Step 3: Type-check + tests**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5 && pnpm --filter @axis/web test 2>&1 | tail -5
```

Expected: clean type-check, 31 tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/shell/shell.tsx && git commit -m "feat(web): mount CommandPalette + ShortcutOverlay + global shortcuts in Shell"
```

### Task D2: Make TopBar's ⌘K chip wire the open action

The chip currently is `aria-disabled` and does nothing. Now it should open the palette on click.

**Files:**
- Modify: `apps/web/components/shell/top-bar.tsx`

- [ ] **Step 1: Read current top-bar**

```bash
cat /Users/mrinalraj/Documents/Axis/apps/web/components/shell/top-bar.tsx
```

- [ ] **Step 2: Replace the disabled chip with an interactive button**

In `apps/web/components/shell/top-bar.tsx`, find the `⌘K` button. Currently it has `aria-disabled="true"` and `cursor-not-allowed` classes. Replace that single button block with:

```tsx
<button
  type="button"
  aria-label="Open command palette"
  onClick={() => commandPalette.open()}
  className="inline-flex items-center gap-2 h-8 px-3 rounded-md border border-edge text-ink-secondary hover:text-ink hover:bg-canvas-elevated text-body-s transition-colors"
>
  <span>Search…</span>
  <Kbd>⌘K</Kbd>
</button>
```

Add the import at the top of the file:
```typescript
import { commandPalette } from '@/lib/global-shortcuts';
```

- [ ] **Step 3: Update top-bar.test.tsx** to reflect the chip is now interactive

Edit the `top-bar.test.tsx` file's first `it(…)` test. Replace the existing assertion about the ⌘K chip with:
```tsx
it('renders the ⌘K chip and opens the palette when clicked', async () => {
  rendered();
  const btn = screen.getByRole('button', { name: /open command palette/i });
  expect(btn).toBeInTheDocument();
  expect(btn).not.toHaveAttribute('aria-disabled', 'true');
});
```

(The actual click→open behavior is covered by the command-palette tests; the top-bar test only asserts wiring + label.)

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/top-bar.tsx apps/web/components/shell/top-bar.test.tsx && git commit -m "feat(web): wire TopBar ⌘K chip to open command palette"
```

Expected: 31 web tests still pass (one test rewritten, no count change).

---

## Phase E — Home operations-center

### Task E1: Build Home page at `app/(app)/page.tsx`

The new landing surface (artifact §3a). Replaces the old `app/page.tsx` redirect.

**Files:**
- Create: `apps/web/app/(app)/page.tsx`
- Delete: `apps/web/app/page.tsx`

- [ ] **Step 1: Investigate the deletion safety**

```bash
cd /Users/mrinalraj/Documents/Axis && grep -rn "app/page.tsx" apps/web/ docs/ 2>&1 | head -5
```

Confirm `apps/web/app/page.tsx` is not referenced by any test or code other than Next.js routing.

- [ ] **Step 2: Delete the old redirect file**

```bash
rm /Users/mrinalraj/Documents/Axis/apps/web/app/page.tsx
```

- [ ] **Step 3: Create the new Home page**

Create `apps/web/app/(app)/page.tsx`:
```tsx
'use client';

import Link from 'next/link';
import { ArrowRight, MessageSquare, Plug } from 'lucide-react';
import {
  BreathingPulse,
  Button,
  Card,
  CardBody,
} from '@axis/design-system';
import { useConnectors } from '@/lib/queries/connectors';

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

const SUGGESTED_PROMPTS: ReadonlyArray<string> = [
  'Summarize what happened in #product on Slack today',
  'Draft a Q3 retro in Notion',
  'Triage my Gmail inbox',
];

export default function HomePage() {
  const { data: connectors } = useConnectors();

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header>
        <h1 className="font-display text-display-l text-ink">{greeting()}</h1>
      </header>

      <section aria-labelledby="running-now">
        <SectionHeader id="running-now" title="Running now" count={0} />
        <Card>
          <CardBody className="flex items-center justify-between py-6">
            <div className="flex items-center gap-3 text-ink-secondary">
              <BreathingPulse tone="background" size="sm" />
              <span className="text-body-s">Nothing running yet.</span>
            </div>
            <Button variant="ghost" size="sm" trailingIcon={<ArrowRight size={14} />} asChild>
              <Link href="/chat" className="inline-flex items-center gap-2">
                <MessageSquare size={14} aria-hidden="true" />
                Start a chat
              </Link>
            </Button>
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="needs-approval">
        <SectionHeader id="needs-approval" title="Needs your approval" count={0} />
        <Card>
          <CardBody className="py-6 text-body-s text-ink-secondary">
            No actions waiting on you.
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="connectors">
        <SectionHeader id="connectors" title="Connectors" count={connectors?.length ?? 0} />
        <Card>
          <CardBody className="flex items-center justify-between py-5">
            <div className="flex items-center gap-3">
              {(connectors ?? []).slice(0, 6).map((c) => (
                <span
                  key={c.tool}
                  title={c.tool}
                  className={`inline-block h-2 w-2 rounded-full ${
                    c.status === 'connected' ? 'bg-success' :
                    c.status === 'error' ? 'bg-danger' :
                    'bg-canvas-elevated border border-edge'
                  }`}
                />
              ))}
              {(!connectors || connectors.length === 0) && (
                <span className="text-body-s text-ink-tertiary">No connectors yet.</span>
              )}
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/connections" className="inline-flex items-center gap-2">
                <Plug size={14} aria-hidden="true" />
                Manage
              </Link>
            </Button>
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="suggested">
        <SectionHeader id="suggested" title="Suggested prompts" count={SUGGESTED_PROMPTS.length} />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <Link
              key={prompt}
              href={`/chat?prompt=${encodeURIComponent(prompt)}`}
              className="block p-4 rounded-md border border-edge-subtle bg-canvas-surface hover:border-edge hover:bg-canvas-elevated transition-colors"
            >
              <span className="text-body-s text-ink">{prompt}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function SectionHeader({
  id,
  title,
  count,
}: {
  id: string;
  title: string;
  count: number;
}) {
  return (
    <h2
      id={id}
      className="mb-3 flex items-baseline gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
    >
      <span>{title}</span>
      <span className="text-ink-secondary tabular-nums">({count})</span>
    </h2>
  );
}
```

- [ ] **Step 4: Drop the `asChild` prop fix**

The design-system `Button` component (Plan 1, Task D1) does NOT support `asChild`. The Home page above uses `asChild` to get a `<Link>` with Button styling. Verify by running:

```bash
cd /Users/mrinalraj/Documents/Axis && grep -n "asChild" packages/design-system/src/components/button/button.tsx
```

If no match, the `asChild` prop is unsupported. The Home page in Step 3 wraps `<Link>` *inside* `<Button>` instead — which is fine because the Button just renders its children. Edit the Home page if needed: remove the `asChild` from the Buttons. The cleaner pattern is:

```tsx
<Button variant="ghost" size="sm" trailingIcon={<ArrowRight size={14} />}>
  <Link href="/chat" className="inline-flex items-center gap-2">
    <MessageSquare size={14} aria-hidden="true" />
    Start a chat
  </Link>
</Button>
```

— wait, that produces nested `<button><a>`, invalid HTML. The right fix: replace `<Button>` with a styled `<Link>` directly for those slots. Update the Home page so the two `<Button asChild>` usages become:

```tsx
<Link
  href="/chat"
  className="inline-flex items-center gap-2 h-8 px-3 rounded-md text-body-s text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
>
  <MessageSquare size={14} aria-hidden="true" />
  Start a chat
  <ArrowRight size={14} aria-hidden="true" />
</Link>
```

```tsx
<Link
  href="/connections"
  className="inline-flex items-center gap-2 h-8 px-3 rounded-md text-body-s text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
>
  <Plug size={14} aria-hidden="true" />
  Manage
</Link>
```

Apply these substitutions to the Home page before running the build.

- [ ] **Step 5: Build and confirm `/` resolves to the new Home**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -15
```

Expected: build passes, the route table shows `/` as a static page (no longer a redirect).

- [ ] **Step 6: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/page.tsx apps/web/app/\(app\)/page.tsx && git commit -m "feat(web): build Home operations-center page (artifact §3a)"
```

---

## Phase F — Verify

### Task F1: Workspace verify

- [ ] **Step 1: Tests**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10
```

Expected: design-system **72** (added BreathingPulse 5), web **31** (added 3 store + 4 palette + 3 overlay = 10).

- [ ] **Step 2: Type-check + lint**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && pnpm lint 2>&1 | tail -5
```

Expected: clean.

- [ ] **Step 3: Build + route check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | grep -E "Route|^\s*[├└]\s*[○◯ƒ]\s*/" | head -20
```

Expected: `/` is a static page; the inner-app routes are present; no failures.

- [ ] **Step 4: Manual dev smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && rm -rf apps/web/.next && pnpm --filter @axis/web dev
```

Open `http://localhost:3001/` (you'll auth-redirect to `/login` if no session — sign in or set the cookie manually):
- After auth, `/` shows the Home operations-center: greeting, four sections, connector dots if `/api/backend/connectors` is reachable.
- Press `⌘K` → palette opens, type "chat" → only the Chat row shows. Click → navigates to `/chat`, palette closes.
- Press `⌘K` → palette opens, type "light" → "Light theme" row shows. Click → background flips to warm white.
- Press `?` → shortcut overlay opens. Press `Esc` → it closes.
- Click the topbar `Search… ⌘K` chip → palette opens.
- Click the topbar theme toggle → menu still works.

Stop the dev server.

(No commit for verify — it's a checkpoint.)

---

## What we have at the end of this plan

- ⌘K command palette with Navigation + Theme categories, fuzzy-searchable.
- ? shortcut overlay with three groups (Global, Navigation, Chat-coming-soon).
- BreathingPulse primitive available everywhere via `@axis/design-system`.
- Home operations-center page at `/`: greeting + four sections (Running now empty, Approvals empty, Connectors live data, Suggested prompts).
- Old `app/page.tsx` redirect deleted; `/` resolves to the new Home inside the (app) shell.
- Design-system tests: **72** (was 67). Web tests: **31** (was 21).

## What we explicitly did NOT do (handed off)

- Plan 5: Chat page rebuild + remaining Axis-native components (LiveTaskTree, DiffViewer, PermissionCard, WritePreviewCard, CitationChip, AgentStateDot, ConnectorTile, MemoryRow, PromptInput).
- Plan 6: Per-page rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin).
- Plan 7: Backend support for capability tiers, undo handlers, audience counter, trust mode.
- Plan 8: Onboarding / demo workspace seed + Playwright visual regression.
- Real "Running now" / "Needs approval" content on Home — needs backend run/approval state (Plan 7).

## Self-Review

- **Spec coverage:** Plan 4 covers artifact §3a App Shell ⌘K + ?, the operations-center Home structure, and the BreathingPulse primitive used on Home + later Chat. The Home's empty-state treatment for Running/Approvals matches artifact §6 empty-state guidance.
- **Placeholder scan:** No "TBD"; no "implement later". Step 4 in Task E1 explicitly resolves the `asChild` ambiguity inline rather than deferring it.
- **Type consistency:** `BreathingTone` consistent across breathing-pulse.tsx, the test, the index, and the barrel. `OpenState` (palette + overlay store) consistent across global-shortcuts.ts, the test, and consumers. The palette uses `Theme` (`'system' | 'light' | 'dark'`) imported from `@/lib/theme` — same type as ThemeToggle (Plan 3).
- **Commands:** Every `pnpm --filter` targets an existing package. The cmdk dep gets installed in the design-system package even though the consumer is the web app — that matches how Radix is installed (cmdk is a primitive the web shell uses through a wrapper, but the wrapper file lives in apps/web). If install conflicts surface, move cmdk to apps/web instead.
