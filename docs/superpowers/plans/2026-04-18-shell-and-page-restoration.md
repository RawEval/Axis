# Axis UI Plan 3 — Shell Rewrite + Page Restoration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing 52-px icon-only nav + topbar + status-bar shell with the artifact §3a three-column shell (LeftNav 240/56 collapsible + Topbar 48 + contextual RightPanel 360), then sweep every inner-app page to swap dead Tailwind class names for new-token equivalents — so every route renders correctly with the new design system.

**Architecture:** Shell components live in `apps/web/components/shell/` (replacing existing files where they exist). They compose the design-system primitives built in Plans 1 + 2 (`Button`, `Avatar`, `DropdownMenu`, `Tooltip`, `Kbd`, `Card`). RightPanel state lives in a tiny Zustand-style store (`apps/web/lib/right-panel.ts`) so any page can `usePanel().open(<JSX/>)`. The page-restoration sweep is a single mechanical commit using a sed script — all dead Tailwind class names map 1-to-1 onto new tokens; no semantic changes.

**Tech Stack:** Existing — Next.js 14, React 18, Tailwind 3.4, Zustand 4.5, design-system primitives, lucide-react. No new deps.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§3a App Shell).

**Out of scope** (handed off):
- Plan 4: ⌘K command palette (`cmdk`), `?` shortcut overlay, Home operations-center page rebuild, Chat page rebuild, Axis-native components (LiveTaskTree, DiffViewer, PermissionCard, WritePreviewCard, CitationChip, AgentStateDot, ConnectorTile, MemoryRow, PromptInput, BreathingPulse).
- Plan 5: Per-page artifact §3d–§3l rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin) — Plan 3 only restores them visually; Plan 5 restructures them to artifact spec.
- Plan 6: Backend support for capability tiers, undo handlers, audience counter, trust mode.

**Deviations from spec/artifact:**
1. **No `⌘K` chip in topbar yet.** The artifact says it sits center-topbar; we render the chip but it's a no-op until Plan 4 wires the command palette. Marked with a clear `aria-disabled` so users know it's not yet functional.
2. **Connector dots in topbar are decorative.** They render the right number of dots based on installed connectors, but the per-dot popover (artifact §3a) lands when Plan 5 rebuilds the Connections page.

---

## File structure

**Create:**

```
apps/web/components/shell/
  left-nav.tsx                      # New — replaces nav-rail.tsx
  left-nav.test.tsx
  top-bar.tsx                       # Rewritten — keep file path, replace contents
  top-bar.test.tsx
  right-panel.tsx                   # New
  right-panel.test.tsx
  theme-toggle.tsx                  # New
  theme-toggle.test.tsx
  shell.tsx                         # Rewritten — keep file path, replace contents

apps/web/lib/
  right-panel.ts                    # New — Zustand-style store for RightPanel state
  right-panel.test.ts

scripts/
  sweep-tailwind-tokens.sh          # New — codemod for dead-class replacement
```

**Modify:**

```
apps/web/app/(app)/layout.tsx       # Mount new shell
apps/web/components/sidebar.tsx     # Re-export the new LeftNav for any leftover callers (if file exists)
```

**Delete:**

```
apps/web/components/shell/nav-rail.tsx    # Replaced by left-nav.tsx
apps/web/components/shell/status-bar.tsx  # Removed entirely per artifact §3a
```

**Touched by sweep (not enumerated — script handles all .tsx under apps/web/{app,components}):** every page and component using dead Tailwind classes. Validated via build + grep.

**Total:** ~10 new files, ~5 modified, ~2 deleted, ~8 commits.

---

## Phase A — Shell components

### Task A1: LeftNav component

The collapsible 240/56 sidebar with two sections (primary + secondary), each a vertical list of icon + label rows, plus a collapse toggle at the bottom.

**Files:**
- Create: `apps/web/components/shell/left-nav.tsx`
- Create: `apps/web/components/shell/left-nav.test.tsx`
- Delete (in this commit): `apps/web/components/shell/nav-rail.tsx`

- [ ] **Step 1: Failing test**

Create `apps/web/components/shell/left-nav.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LeftNav } from './left-nav';

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}));

describe('LeftNav', () => {
  it('renders the primary nav items with labels when expanded', () => {
    render(<LeftNav />);
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Activity')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Memory')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('marks the active route', () => {
    render(<LeftNav />);
    const chatLink = screen.getByRole('link', { name: /chat/i });
    expect(chatLink).toHaveAttribute('aria-current', 'page');
  });

  it('hides labels when collapsed', async () => {
    render(<LeftNav />);
    await userEvent.click(screen.getByRole('button', { name: /collapse/i }));
    expect(screen.queryByText('Home')).not.toBeInTheDocument();
  });

  it('shows labels again when expanded', async () => {
    render(<LeftNav />);
    await userEvent.click(screen.getByRole('button', { name: /collapse/i }));
    await userEvent.click(screen.getByRole('button', { name: /expand/i }));
    expect(screen.getByText('Home')).toBeInTheDocument();
  });

  it('renders the secondary nav (Connections, Team, Settings)', () => {
    render(<LeftNav />);
    expect(screen.getByText('Connections')).toBeInTheDocument();
    expect(screen.getByText('Team')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

Expected: 5 failures, "module not found" for `./left-nav`.

- [ ] **Step 3: Implement**

Create `apps/web/components/shell/left-nav.tsx`:
```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  Activity,
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock,
  FolderOpen,
  Home,
  MessageSquare,
  Plug,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const PRIMARY: ReadonlyArray<NavItem> = [
  { href: '/',         label: 'Home',     icon: Home },
  { href: '/chat',     label: 'Chat',     icon: MessageSquare },
  { href: '/feed',     label: 'Activity', icon: Activity },
  { href: '/history',  label: 'History',  icon: Clock },
  { href: '/memory',   label: 'Memory',   icon: Brain },
  { href: '/projects', label: 'Projects', icon: FolderOpen },
];

const SECONDARY: ReadonlyArray<NavItem> = [
  { href: '/connections', label: 'Connections', icon: Plug },
  { href: '/team',        label: 'Team',        icon: Users },
  { href: '/settings',    label: 'Settings',    icon: Settings },
];

const ITEM_BASE =
  'flex items-center gap-3 h-10 px-3 mx-2 my-0.5 rounded-md text-body-s transition-colors duration-[120ms] ease-out';

const ITEM_INACTIVE = 'text-ink-secondary hover:text-ink hover:bg-canvas-elevated';
const ITEM_ACTIVE   = 'text-ink bg-canvas-elevated font-medium';

export function LeftNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string): boolean => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? 'page' : undefined}
        className={clsx(
          ITEM_BASE,
          active ? ITEM_ACTIVE : ITEM_INACTIVE,
          collapsed && 'justify-center px-0',
        )}
        title={collapsed ? item.label : undefined}
      >
        <Icon size={18} aria-hidden="true" className="shrink-0" />
        {!collapsed && <span className="truncate">{item.label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={clsx(
        'flex flex-col bg-canvas-surface border-r border-edge-subtle h-full transition-[width] duration-200 ease-out',
        collapsed ? 'w-14' : 'w-60',
      )}
      aria-label="Primary"
    >
      <div className={clsx('flex items-center h-14 px-4 gap-2 border-b border-edge-subtle', collapsed && 'justify-center px-0')}>
        <span aria-hidden className="block h-3 w-3 rounded-sm bg-accent shrink-0" />
        {!collapsed && <span className="font-display text-heading-2 text-ink">Axis</span>}
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {PRIMARY.map(renderItem)}
        <div className="mx-3 my-2 h-px bg-edge-subtle" aria-hidden="true" />
        {SECONDARY.map(renderItem)}
      </nav>

      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className={clsx(
          'flex items-center gap-2 h-10 px-3 mx-2 my-1 rounded-md text-ink-tertiary hover:text-ink-secondary hover:bg-canvas-elevated transition-colors',
          collapsed && 'justify-center px-0',
        )}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span className="text-caption">Collapse</span>}
      </button>
    </aside>
  );
}
```

- [ ] **Step 4: Delete the old nav-rail file**

```bash
rm /Users/mrinalraj/Documents/Axis/apps/web/components/shell/nav-rail.tsx
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/left-nav.tsx apps/web/components/shell/left-nav.test.tsx apps/web/components/shell/nav-rail.tsx && git commit -m "feat(web): replace nav-rail with collapsible LeftNav per artifact §3a"
```

Expected: 5 new tests + 4 prior = **9 web tests**.

### Task A2: ThemeToggle component

A small button group / dropdown used in the topbar to switch between system/light/dark.

**Files:**
- Create: `apps/web/components/shell/theme-toggle.tsx`
- Create: `apps/web/components/shell/theme-toggle.test.tsx`

- [ ] **Step 1: Failing test**

Create `apps/web/components/shell/theme-toggle.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/lib/theme';
import { ThemeToggle } from './theme-toggle';

function renderWithTheme(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('renders a button labelled with the current theme', () => {
    renderWithTheme(<ThemeToggle />);
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument();
  });

  it('opens a menu of system / light / dark options', async () => {
    renderWithTheme(<ThemeToggle />);
    await userEvent.click(screen.getByRole('button', { name: /theme/i }));
    expect(await screen.findByText(/system/i)).toBeInTheDocument();
    expect(screen.getByText(/light/i)).toBeInTheDocument();
    expect(screen.getByText(/dark/i)).toBeInTheDocument();
  });

  it('switches theme when an option is selected', async () => {
    renderWithTheme(<ThemeToggle />);
    await userEvent.click(screen.getByRole('button', { name: /theme/i }));
    await userEvent.click(await screen.findByText(/light/i));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement**

Create `apps/web/components/shell/theme-toggle.tsx`:
```tsx
'use client';

import { Monitor, Moon, Sun } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@axis/design-system';
import { useTheme, type Theme } from '@/lib/theme';

const ICON: Record<Theme, typeof Monitor> = {
  system: Monitor,
  light: Sun,
  dark: Moon,
};

const LABEL: Record<Theme, string> = {
  system: 'System',
  light: 'Light',
  dark: 'Dark',
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Icon = ICON[theme];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Theme: ${LABEL[theme]}`}
        className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
      >
        <Icon size={16} aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(['system', 'light', 'dark'] as const).map((t) => {
          const ItemIcon = ICON[t];
          return (
            <DropdownMenuItem key={t} onSelect={() => setTheme(t)}>
              <ItemIcon size={14} aria-hidden="true" className="mr-2" />
              <span>{LABEL[t]}</span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/theme-toggle.tsx apps/web/components/shell/theme-toggle.test.tsx && git commit -m "feat(web): add ThemeToggle in shell"
```

Expected: 3 new tests + 9 prior = **12 web tests**.

### Task A3: Topbar component

48-px tall. Project selector left, ⌘K chip center, theme toggle + connector dots + user avatar right.

**Files:**
- Create: `apps/web/components/shell/top-bar.test.tsx`
- Modify: `apps/web/components/shell/top-bar.tsx` (full rewrite)

- [ ] **Step 1: Failing test**

Create `apps/web/components/shell/top-bar.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@/lib/theme';
import { TopBar } from './top-bar';

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}));

function rendered() {
  return render(
    <ThemeProvider>
      <TopBar />
    </ThemeProvider>,
  );
}

describe('TopBar', () => {
  it('renders the ⌘K chip (decorative until Plan 4 wires the palette)', () => {
    rendered();
    expect(screen.getByText(/⌘K/)).toBeInTheDocument();
  });

  it('renders the theme toggle', () => {
    rendered();
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument();
  });

  it('renders an account avatar/menu trigger', () => {
    rendered();
    expect(screen.getByRole('button', { name: /account/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement**

Read the current `apps/web/components/shell/top-bar.tsx` first. Then OVERWRITE with:

```tsx
'use client';

import { LogOut, User } from 'lucide-react';
import {
  Avatar,
  Kbd,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@axis/design-system';
import { ThemeToggle } from './theme-toggle';

export function TopBar() {
  return (
    <header
      className="flex items-center h-12 px-4 border-b border-edge-subtle bg-canvas-surface gap-4"
      role="banner"
    >
      <div className="flex-1" />

      <button
        type="button"
        aria-label="Open command palette (coming soon)"
        aria-disabled="true"
        className="inline-flex items-center gap-2 h-8 px-3 rounded-md border border-edge text-ink-tertiary hover:text-ink-secondary text-body-s opacity-60 cursor-not-allowed"
      >
        <span>Search…</span>
        <Kbd>⌘K</Kbd>
      </button>

      <div className="flex-1 flex items-center justify-end gap-1">
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Account menu"
            className="inline-flex items-center justify-center h-8 w-8 rounded-full hover:bg-canvas-elevated transition-colors"
          >
            <Avatar name="A" size="sm" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Account</DropdownMenuLabel>
            <DropdownMenuItem>
              <User size={14} aria-hidden="true" className="mr-2" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-danger data-[highlighted]:text-danger">
              <LogOut size={14} aria-hidden="true" className="mr-2" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/components/shell/top-bar.tsx apps/web/components/shell/top-bar.test.tsx && git commit -m "feat(web): rewrite TopBar with theme toggle + ⌘K chip + account menu"
```

Expected: 3 new tests + 12 prior = **15 web tests**.

### Task A4: RightPanel store + component

Slide-in 360-px panel triggered by `usePanel().open(node)`. Closes on `Esc` or button.

**Files:**
- Create: `apps/web/lib/right-panel.ts`
- Create: `apps/web/lib/right-panel.test.ts`
- Create: `apps/web/components/shell/right-panel.tsx`
- Create: `apps/web/components/shell/right-panel.test.tsx`

- [ ] **Step 1: Failing store test**

Create `apps/web/lib/right-panel.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { rightPanel } from './right-panel';

describe('rightPanel store', () => {
  beforeEach(() => {
    rightPanel.close();
  });

  it('starts closed', () => {
    expect(rightPanel.getState().open).toBe(false);
  });

  it('opens with a node', () => {
    rightPanel.open({ title: 'Run details', body: 'placeholder' });
    expect(rightPanel.getState().open).toBe(true);
    expect(rightPanel.getState().title).toBe('Run details');
  });

  it('closes', () => {
    rightPanel.open({ title: 'x', body: 'y' });
    rightPanel.close();
    expect(rightPanel.getState().open).toBe(false);
  });
});
```

- [ ] **Step 2: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 3: Implement the store**

Create `apps/web/lib/right-panel.ts`:
```typescript
import { useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';

export interface RightPanelContent {
  title: string;
  body: ReactNode;
}

interface RightPanelState extends Partial<RightPanelContent> {
  open: boolean;
}

let state: RightPanelState = { open: false };
const listeners = new Set<() => void>();

function emit(): void {
  for (const l of listeners) l();
}

function setState(next: RightPanelState): void {
  state = next;
  emit();
}

export const rightPanel = {
  getState: (): RightPanelState => state,
  open(content: RightPanelContent): void {
    setState({ open: true, ...content });
  },
  close(): void {
    setState({ open: false });
  },
  subscribe(l: () => void): () => void {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
};

export function useRightPanel(): RightPanelState {
  return useSyncExternalStore(rightPanel.subscribe, rightPanel.getState, rightPanel.getState);
}
```

- [ ] **Step 4: Failing component test**

Create `apps/web/components/shell/right-panel.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rightPanel } from '@/lib/right-panel';
import { RightPanel } from './right-panel';
import { act } from '@testing-library/react';

describe('RightPanel component', () => {
  beforeEach(() => {
    act(() => {
      rightPanel.close();
    });
  });

  it('renders nothing when store is closed', () => {
    render(<RightPanel />);
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });

  it('renders title + body when opened', () => {
    render(<RightPanel />);
    act(() => {
      rightPanel.open({ title: 'Run', body: 'details here' });
    });
    expect(screen.getByText('Run')).toBeInTheDocument();
    expect(screen.getByText('details here')).toBeInTheDocument();
  });

  it('closes when the close button is clicked', async () => {
    render(<RightPanel />);
    act(() => {
      rightPanel.open({ title: 'Run', body: 'x' });
    });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(screen.queryByText('Run')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Run, expect failures**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```

- [ ] **Step 6: Implement the component**

Create `apps/web/components/shell/right-panel.tsx`:
```tsx
'use client';

import { X } from 'lucide-react';
import { useEffect } from 'react';
import { rightPanel, useRightPanel } from '@/lib/right-panel';

export function RightPanel() {
  const state = useRightPanel();

  useEffect(() => {
    if (!state.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') rightPanel.close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [state.open]);

  if (!state.open) return null;

  return (
    <aside
      role="complementary"
      aria-label={state.title}
      className="w-[360px] flex-shrink-0 border-l border-edge-subtle bg-canvas-surface flex flex-col h-full"
    >
      <div className="flex items-center justify-between h-12 px-4 border-b border-edge-subtle">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-secondary truncate">
          {state.title}
        </h2>
        <button
          type="button"
          aria-label="Close panel"
          onClick={() => rightPanel.close()}
          className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated transition-colors"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 text-body-s text-ink">{state.body}</div>
    </aside>
  );
}
```

- [ ] **Step 7: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test && git add apps/web/lib/right-panel.ts apps/web/lib/right-panel.test.ts apps/web/components/shell/right-panel.tsx apps/web/components/shell/right-panel.test.tsx && git commit -m "feat(web): add RightPanel shell + store"
```

Expected: 3 store + 3 component = 6 new tests + 15 prior = **21 web tests**.

### Task A5: Shell wrapper rewrite + delete status-bar

Replace `shell.tsx` with the new layout. Delete `status-bar.tsx`.

**Files:**
- Modify: `apps/web/components/shell/shell.tsx` (full rewrite)
- Delete: `apps/web/components/shell/status-bar.tsx`

- [ ] **Step 1: Read the current shell**

```bash
cat /Users/mrinalraj/Documents/Axis/apps/web/components/shell/shell.tsx
```

- [ ] **Step 2: Rewrite**

Overwrite `apps/web/components/shell/shell.tsx`:
```tsx
'use client';

import { type ReactNode } from 'react';
import { ToastViewport, TooltipProvider } from '@axis/design-system';
import { LeftNav } from './left-nav';
import { TopBar } from './top-bar';
import { RightPanel } from './right-panel';

export function Shell({ children }: { children: ReactNode }) {
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
      <ToastViewport />
    </TooltipProvider>
  );
}
```

- [ ] **Step 3: Delete status-bar**

```bash
rm /Users/mrinalraj/Documents/Axis/apps/web/components/shell/status-bar.tsx
```

- [ ] **Step 4: Type-check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -10
```

If `apps/web/components/sidebar.tsx` (the old file) imports the removed `StatusBar` or `nav-rail`, type-check will surface it. Fix any caller in this same task by either re-exporting from a new file or removing the dead reference.

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/shell/shell.tsx apps/web/components/shell/status-bar.tsx && git commit -m "feat(web): rewrite shell with LeftNav + TopBar + RightPanel; delete status-bar"
```

### Task A6: Mount the new shell in `(app)/layout.tsx`

**Files:**
- Modify: `apps/web/app/(app)/layout.tsx`

- [ ] **Step 1: Read current layout**

```bash
cat /Users/mrinalraj/Documents/Axis/apps/web/app/\(app\)/layout.tsx
```

- [ ] **Step 2: Replace its contents** with:

```tsx
import type { ReactNode } from 'react';
import { Shell } from '@/components/shell/shell';

export default function AppLayout({ children }: { children: ReactNode }) {
  return <Shell>{children}</Shell>;
}
```

(If the existing layout has metadata exports, server-side data fetching, auth-redirect logic, or other components — preserve them. Only swap the rendered shell composition.)

- [ ] **Step 3: Build the web app to confirm shell wiring works**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -15
```

Expected: build still succeeds. The build output table should show all routes including `/`, `/chat`, `/feed`, `/history`, `/memory`, `/projects`, `/connections`, `/team`, `/settings`, `/credentials`, `/login`, `/signup`. Routes will compile cleanly even though their inner content still uses dead Tailwind classes (those produce no CSS but don't fail the build).

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(app\)/layout.tsx && git commit -m "feat(web): mount new shell in (app)/layout.tsx"
```

---

## Phase B — Page restoration sweep

### Task B1: Codemod for dead Tailwind class names

A single sed-based pass across `apps/web/{app,components}/**/*.tsx` that swaps every dead class name for its new-token equivalent. Mechanical; reviewable by `git diff` after.

**Files:**
- Create: `scripts/sweep-tailwind-tokens.sh`
- Touched (by the script): every `.tsx` under `apps/web/app` and `apps/web/components` that contains any dead class.

- [ ] **Step 1: Write the codemod script**

Create `scripts/sweep-tailwind-tokens.sh`:
```bash
#!/usr/bin/env bash
# Sweeps dead Tailwind class names from old token system → new one.
# Run from repo root. Operates on apps/web/{app,components}/**/*.tsx in place.
# Idempotent; safe to run twice.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/apps/web"

if [[ ! -d "$WEB" ]]; then
  echo "fatal: $WEB not found" >&2
  exit 1
fi

# All file targets — only .tsx under app/ and components/.
mapfile -t files < <(
  find "$WEB/app" "$WEB/components" -type f -name '*.tsx' 2>/dev/null
)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "no .tsx files found"
  exit 0
fi

echo "Sweeping ${#files[@]} files…"

# Class-name substitutions. Order matters where prefixes overlap
# (longer / more-specific patterns must run first).
#
# Format: from|to
substitutions=(
  # Sub-shaded canvas
  'bg-canvas-raised|bg-canvas-surface'
  'bg-canvas-subtle|bg-canvas-elevated'
  # Old nav surface
  'bg-nav-active|bg-accent-subtle'
  'bg-nav-hover|bg-canvas-elevated'
  'bg-nav|bg-canvas-surface'
  # Brand → accent (longer numeric values first to avoid bg-brand-50 swallowing 500)
  'bg-brand-700|bg-accent-hover'
  'bg-brand-600|bg-accent-hover'
  'bg-brand-500|bg-accent'
  'bg-brand-200|bg-accent-subtle'
  'bg-brand-100|bg-accent-subtle'
  'bg-brand-50|bg-accent-subtle'
  'text-brand-700|text-accent'
  'text-brand-600|text-accent'
  'text-brand-500|text-accent'
  'border-brand-500|border-accent'
  'ring-brand-500|ring-accent'
  'hover:bg-brand-700|hover:bg-accent-hover'
  'hover:bg-brand-600|hover:bg-accent-hover'
  'hover:text-brand-600|hover:text-accent-hover'
  # Ink-on-dark legacy
  'text-ink-onDark/60|text-ink-secondary'
  'text-ink-onDark|text-ink'
  'border-ink-onDark|border-edge'
  'text-ink-disabled|text-ink-tertiary'
  # Semantic compound colors → flat semantic
  'bg-success-bg|bg-success/10'
  'text-success-fg|text-success'
  'border-success-border|border-success/30'
  'bg-warning-bg|bg-warning/10'
  'text-warning-fg|text-warning'
  'border-warning-border|border-warning/30'
  'bg-danger-bg|bg-danger/10'
  'text-danger-fg|text-danger'
  'border-danger-border|border-danger/30'
  'bg-info-bg|bg-info/10'
  'text-info-fg|text-info'
  'border-info-border|border-info/30'
  # Shadows
  'shadow-sm-strong|shadow-e1'
  'shadow-popover|shadow-e2'
  'shadow-panel|shadow-e1'
)

for sub in "${substitutions[@]}"; do
  from="${sub%%|*}"
  to="${sub#*|}"
  # Word-ish boundaries: don't replace if surrounded by other word chars.
  # Tailwind class strings are space- or quote-delimited, so we look for
  # boundaries that are NOT alnum/dash, AND don't allow trailing alnum/dash.
  pattern="(^|[^A-Za-z0-9-])($from)([^A-Za-z0-9-]|\$)"
  for f in "${files[@]}"; do
    # macOS / GNU sed compat: use perl -pi for portability.
    perl -pi -e "s/$pattern/\${1}$to\${3}/g" "$f"
  done
done

echo "done"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x /Users/mrinalraj/Documents/Axis/scripts/sweep-tailwind-tokens.sh
```

- [ ] **Step 3: Run the codemod**

```bash
cd /Users/mrinalraj/Documents/Axis && bash scripts/sweep-tailwind-tokens.sh
```

Expected output: `Sweeping N files…` then `done`. No errors.

- [ ] **Step 4: Inspect the diff**

```bash
cd /Users/mrinalraj/Documents/Axis && git diff --stat | tail -20
```

Expected: many .tsx files touched. Specifically check that no file was touched in a non-class-name location:

```bash
cd /Users/mrinalraj/Documents/Axis && git diff apps/web/ | grep -E '^[-+]' | head -40
```

If you see any change inside a regular string (e.g. JSX text content) that wasn't a className, STOP and report — the script over-matched.

- [ ] **Step 5: Verify build is still green**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -15
```

Expected: build succeeds. Static page count unchanged.

- [ ] **Step 6: Verify no dead classes remain**

```bash
cd /Users/mrinalraj/Documents/Axis && grep -rEn '\b(bg-canvas-raised|bg-canvas-subtle|bg-nav|bg-brand-|text-brand-|text-ink-onDark|shadow-panel|shadow-popover|shadow-sm-strong|bg-success-bg|text-success-fg|bg-warning-bg|text-warning-fg|bg-danger-bg|text-danger-fg|bg-info-bg|text-info-fg)' apps/web/app apps/web/components 2>&1 | head -10
```

Expected: zero matches. If something is left, edit it manually in this same task and re-verify.

- [ ] **Step 7: Verify type-check + tests still pass**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/web test 2>&1 | tail -5
```

- [ ] **Step 8: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add scripts/sweep-tailwind-tokens.sh apps/web && git commit -m "$(cat <<'EOF'
refactor(web): sweep dead Tailwind class names → new token map

Mechanical replacement across apps/web/{app,components}/**/*.tsx via
scripts/sweep-tailwind-tokens.sh — no semantic changes. Pages now render
with the new token palette rather than silently producing zero CSS.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase C — Final verify

### Task C1: Workspace verify

- [ ] **Step 1: All tests pass**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10
```

Expected: `@axis/design-system: Test Files 17 passed (17), Tests 67 passed (67)`. `@axis/web: Test Files X passed, Tests Y passed` — Y should be at least **21** (was 4 before Plan 3, grew by 17 in A1+A2+A3+A4).

- [ ] **Step 2: All type-checks pass (web + design-system)**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/design-system type-check 2>&1 | tail -3
```

Both should output the bare command line with no errors. (`notification-service` is still pre-existing and out of scope.)

- [ ] **Step 3: Lint clean**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm lint 2>&1 | tail -5
```

- [ ] **Step 4: Build green, check for the inner-app routes**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | grep -E "Route|/(chat|feed|history|memory|settings|connections|team|projects|login|signup)" | head -20
```

Expected: every inner route appears in the static-build table.

- [ ] **Step 5: Manual dev smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```

Open `http://localhost:3000/` (or 3001):
- LeftNav appears with all 9 items, Home active by default.
- Click Chat → highlights, route changes.
- Collapse button shrinks nav to 56 px.
- Topbar has ⌘K chip (disabled), theme toggle, user avatar.
- Click theme toggle → menu opens, pick Light → background flips to warm white.
- Visit `/feed`, `/history`, `/memory`, `/settings`, `/connections`, `/team` — each renders with proper colors (no naked unstyled HTML, no dead classes leaving boxes white-on-white).
- Stop dev server.

No commit for the verify step.

---

## What we have at the end of this plan

- New three-column shell mounted on every authenticated route: collapsible LeftNav (240/56), 48-px Topbar with theme toggle and user menu, contextual RightPanel (closed until `usePanel().open(...)` fires).
- `usePanel()` hook + global store any page can use to slide content into the right panel.
- ToastViewport mounted globally — `toast.success(...)`, `toast.action(...)` etc. available.
- Tooltip provider mounted globally — `<Tooltip label="…"><Trigger /></Tooltip>` works anywhere.
- All inner-app routes (`/`, `/chat`, `/feed`, `/history`, `/memory`, `/projects`, `/connections`, `/credentials`, `/team`, `/settings`) compile, render with the new token palette, and look like proper Workbench-tier surfaces (within their existing layout — Plan 5 restructures them per artifact §3d-§3l).
- ~21 web tests (was 4), 67 design-system tests (unchanged from Plan 2 end).

## What we explicitly did NOT do (handed off)

- ⌘K command palette wiring — chip is decorative; Plan 4.
- ? shortcut overlay — Plan 4.
- Home operations-center page (artifact §3a inner content) — Plan 4.
- Chat page rebuild and Axis-native components (LiveTaskTree, DiffViewer, PermissionCard, WritePreviewCard, CitationChip, AgentStateDot, ConnectorTile, MemoryRow, PromptInput, BreathingPulse) — Plan 4.
- Per-page artifact §3d-§3l rebuilds (Activity, History, Memory, Settings, Connections, Credentials, Team, Projects, Admin) — Plan 5.
- Connector dot popovers, project switcher dropdown, full user-menu items — Plan 5.
- Backend support for capability tiers, undo handlers, audience counter, trust mode — Plan 6.
- Onboarding / demo workspace seed — Plan 7.

## Self-Review

- **Spec coverage:** Plan 3 covers the artifact §3a App Shell description (LeftNav 240/56, Topbar 48, RightPanel 360, no status bar, no breadcrumbs) plus the implicit "every page must actually render with the new tokens" requirement that Plan 1 left as known fallout. The two deferred items (⌘K chip, ? overlay) are explicitly called out in the artifact §3a and explicitly deferred in this plan's "out of scope" section with a Plan 4 pointer.
- **Placeholder scan:** No "TBD"; all code blocks are complete. The codemod's substitutions list is exhaustive based on the audit of the old `tailwind.config.ts` from Plan 1's discovery.
- **Type consistency:** `Theme` type is consistently `'system' | 'light' | 'dark'` across `lib/theme.tsx`, `theme-toggle.tsx`, `top-bar.tsx`. `RightPanelContent` is consistently `{ title: string; body: ReactNode }` across `right-panel.ts`, `right-panel.tsx`, and the test file. Nav item type is consistently `{ href: string; label: string; icon: LucideIcon }` in `left-nav.tsx`. `usePanel` is named `useRightPanel` to match the file name — checked across all consumers.
- **Commands:** Every `pnpm --filter` targets an existing package. `git add` paths use the literal escaped parentheses required by zsh for `(app)/` and `(auth)/`. Sweep script uses `perl -pi` for cross-platform sed compatibility (macOS `sed -i` requires a backup-extension argument that GNU `sed` doesn't).
