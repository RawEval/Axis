# Axis UI Foundation — Phase 0 + Login Slice

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the artifact's design tokens, theme system, and starter primitives (Button, Input, Card) end-to-end on the Login + Signup pages, proving the system works in light and dark modes.

**Architecture:** Tokens defined in `packages/design-system/src/tokens/` and exposed two ways — (1) JS constants for component code, (2) CSS custom properties on `:root` and `[data-theme="light"]` consumed by the web app's Tailwind config via `var(--…)`. Theme is stored in `localStorage["axis.theme"]` (`'system' | 'light' | 'dark'`) and applied to `document.documentElement` via a `data-theme` attribute. Inter Display + Inter + JetBrains Mono load via `next/font/google` (JetBrains Mono is V1's stand-in for Commit Mono — token swap later). Primitives live in `packages/design-system`; web's existing `components/ui/*` files become thin re-exports so callers don't churn.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5.5, Tailwind 3.4, Vitest 1.x + React Testing Library + jsdom, Zustand (existing), React Query (existing), `lucide-react`, `framer-motion`, pnpm 9, Turbo 2.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md`.

**Out of scope** for this plan (deferred to later plans): feature flags (no users yet — would be theater), Storybook, Playwright visual regression, the rest of the primitive set (Modal, Toast, Popover, etc.), every page besides Login + Signup, the shell rewrite, the operations-center Home, all Axis-native components, all backend changes for capability tiers.

**Deviations from the spec/artifact** worth surfacing:
1. **Commit Mono → JetBrains Mono for V1.** Reason: JetBrains Mono is on Google Fonts and loads with `next/font/google` in one line. Commit Mono needs a self-host workflow (download `.woff2` from `commitmono.com`, place in repo, configure `next/font/local`). Token swap later — single CSS variable change.
2. **No `VISUAL_V2` feature flag in this plan.** Reason: zero users today, repo has zero commits, no rollback safety net needed yet. Flag scaffolding ships in a later plan before beta users land.
3. **Vitest only — no Playwright in this plan.** Reason: visual regression has more value once 5+ pages exist. Plan 2 adds Playwright when there's surface to regress.

---

## File structure

**Create:**

```
packages/design-system/
  vitest.config.ts                              # Vitest with jsdom + RTL setup
  test-setup.ts                                 # @testing-library/jest-dom imports
  src/
    tokens/
      colors.ts                                 # Color token JS constants + CSS var names
      typography.ts                             # Font + scale + tracking constants
      spacing.ts                                # Spacing, radius, motion durations
      index.ts                                  # Re-exports (rewrite, currently has wrong tokens)
    components/
      button/
        button.tsx                              # Rewrite — current button uses dead tokens
        button.test.tsx                         # New
        index.ts                                # New
      input/
        input.tsx                               # New
        input.test.tsx                          # New
        index.ts                                # New
      card/
        card.tsx                                # Rewrite — current card uses dead tokens
        card.test.tsx                           # New
        index.ts                                # New
      index.ts                                  # New — barrel re-export

apps/web/
  lib/
    theme.tsx                                   # ThemeProvider + useTheme hook
    theme.test.tsx                              # Hook tests
  app/
    fonts.ts                                    # next/font declarations (Inter, Inter Display, JetBrains Mono)
  vitest.config.ts                              # Vitest config for web
  test-setup.ts                                 # RTL setup
```

**Modify:**

```
packages/design-system/
  package.json                                  # Add devDeps: vitest, @testing-library/*, jsdom, framer-motion peer
  src/index.ts                                  # Re-export new tokens + components
  tsconfig.json                                 # If needed: ensure jsx + dom lib

apps/web/
  package.json                                  # Add deps: lucide-react, framer-motion. devDeps: vitest, @testing-library/*, jsdom
  tailwind.config.ts                            # Replace token map with CSS-var-backed names
  app/globals.css                               # Replace with new CSS variables (both themes), keyframes, prefers-reduced-motion
  app/layout.tsx                                # Load fonts via next/font, set data-theme=system on html
  app/providers.tsx                             # Mount ThemeProvider
  app/(auth)/layout.tsx                         # Rewrite per artifact §3b — split-screen
  app/(auth)/login/page.tsx                     # Rewrite per artifact §3b
  app/(auth)/signup/page.tsx                    # Rewrite per artifact §3b
  components/ui/button.tsx                      # Re-export from @axis/design-system
  components/ui/form.tsx                        # Re-export Input from @axis/design-system; Field/Label/Textarea/Select stay local
  components/ui/card.tsx                        # Decision: keep `Panel`/`PanelHeader`/`PanelBody`/`PanelFooter` names but back them with the new Card primitive

apps/web/app/(app)/settings/page.tsx            # Fix &apos; lint error (unblocks build)
apps/web/components/team/invite-modal.tsx       # Fix &apos; lint error (unblocks build)
```

---

## Phase A — Preflight

### Task A1: Fix the two ESLint errors that block the build

**Files:**
- Modify: `apps/web/app/(app)/settings/page.tsx:61`
- Modify: `apps/web/components/team/invite-modal.tsx:118`

- [ ] **Step 1: Run the build to confirm the failures**

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -20
```
Expected: build fails with two `react/no-unescaped-entities` errors at the lines listed above.

- [ ] **Step 2: Read both files at the cited lines**

Read `apps/web/app/(app)/settings/page.tsx` lines 55–70 and `apps/web/components/team/invite-modal.tsx` lines 110–125 to find the literal `'` characters in JSX that need escaping.

- [ ] **Step 3: Replace each unescaped `'` with `&apos;`**

In each file, find the JSX text content (not inside a `{…}` expression) containing a single quote and replace it with `&apos;`. Example: `don't` → `don&apos;t`.

- [ ] **Step 4: Re-run the build to confirm green**

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -10
```
Expected: `Compiled successfully` (warnings are OK, errors are not).

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(app\)/settings/page.tsx apps/web/components/team/invite-modal.tsx && git commit -m "fix(web): escape single quotes blocking lint"
```

### Task A2: Install new runtime + dev dependencies

**Files:**
- Modify: `apps/web/package.json`
- Modify: `packages/design-system/package.json`

- [ ] **Step 1: Add runtime deps to web**

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web add lucide-react@^0.451.0 framer-motion@^11.11.0
```
Expected: pnpm reports two new dependencies added.

- [ ] **Step 2: Add Vitest + RTL devDeps to web**

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web add -D vitest@^1.6.0 @vitejs/plugin-react@^4.3.0 @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.5.0 @testing-library/user-event@^14.5.0 jsdom@^25.0.0
```
Expected: 6 devDeps added.

- [ ] **Step 3: Add the same Vitest + RTL devDeps to design-system**

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system add -D vitest@^1.6.0 @vitejs/plugin-react@^4.3.0 @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.5.0 @testing-library/user-event@^14.5.0 jsdom@^25.0.0
```
Expected: 6 devDeps added.

- [ ] **Step 4: Add `framer-motion` as a peer dep on design-system**

Edit `packages/design-system/package.json` so `peerDependencies` becomes:
```json
"peerDependencies": {
  "react": ">=18",
  "framer-motion": ">=11"
}
```

- [ ] **Step 5: Add a `test` script to both packages**

Edit `apps/web/package.json` `scripts` to add: `"test": "vitest run", "test:watch": "vitest"`.
Edit `packages/design-system/package.json` `scripts` to add: `"test": "vitest run", "test:watch": "vitest"`.

- [ ] **Step 6: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/package.json packages/design-system/package.json pnpm-lock.yaml && git commit -m "build: add lucide-react, framer-motion, vitest stack"
```

### Task A3: Set up Vitest config in design-system

**Files:**
- Create: `packages/design-system/vitest.config.ts`
- Create: `packages/design-system/test-setup.ts`

- [ ] **Step 1: Write `vitest.config.ts`**

Create `packages/design-system/vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./test-setup.ts'],
    globals: true,
    css: false,
  },
});
```

- [ ] **Step 2: Write `test-setup.ts`**

Create `packages/design-system/test-setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 3: Add a smoke test to confirm Vitest runs**

Create `packages/design-system/src/smoke.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';

describe('vitest', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2);
  });
});
```

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```
Expected: `1 passed`.

- [ ] **Step 4: Delete the smoke test** (no longer needed)

```bash
rm /Users/mrinalraj/Documents/Axis/packages/design-system/src/smoke.test.ts
```

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/vitest.config.ts packages/design-system/test-setup.ts && git commit -m "test(design-system): set up vitest + jsdom + RTL"
```

### Task A4: Set up Vitest config in web

**Files:**
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/test-setup.ts`

- [ ] **Step 1: Write `vitest.config.ts`**

Create `apps/web/vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./test-setup.ts'],
    globals: true,
    css: false,
  },
});
```

- [ ] **Step 2: Write `test-setup.ts`**

Create `apps/web/test-setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 3: Smoke-test it**

Create `apps/web/lib/smoke.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
describe('vitest in web', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2);
  });
});
```

Run:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```
Expected: `1 passed`.

- [ ] **Step 4: Delete the smoke test**

```bash
rm /Users/mrinalraj/Documents/Axis/apps/web/lib/smoke.test.ts
```

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/vitest.config.ts apps/web/test-setup.ts && git commit -m "test(web): set up vitest + jsdom + RTL"
```

---

## Phase B — Tokens

### Task B1: Define the color token map (JS + CSS variable names)

**Files:**
- Create: `packages/design-system/src/tokens/colors.ts`

- [ ] **Step 1: Write `colors.ts` with the artifact §2a tables**

Create `packages/design-system/src/tokens/colors.ts`:
```typescript
/**
 * Color tokens — see docs/compass_artifact §2a.
 * Values are exposed as CSS custom properties in apps/web/app/globals.css.
 * Component code should reference the CSS-var name (e.g. `var(--color-bg-canvas)`)
 * via Tailwind utility classes (`bg-canvas`, `text-ink`, etc.) wired in tailwind.config.ts.
 */

export type ColorToken =
  | 'bg.canvas' | 'bg.surface' | 'bg.elevated' | 'bg.sunken'
  | 'border.subtle' | 'border.default' | 'border.strong'
  | 'text.primary' | 'text.secondary' | 'text.tertiary' | 'text.inverse'
  | 'accent.primary' | 'accent.hover' | 'accent.subtle' | 'accent.on'
  | 'success' | 'warning' | 'danger' | 'info'
  | 'agent.thinking' | 'agent.running' | 'agent.awaiting'
  | 'agent.recovered' | 'agent.blocked' | 'agent.background';

export const COLORS_DARK: Record<ColorToken, string> = {
  'bg.canvas': '#09090B',
  'bg.surface': '#111113',
  'bg.elevated': '#1A1A1D',
  'bg.sunken': '#060608',
  'border.subtle': '#27272A',
  'border.default': '#3F3F46',
  'border.strong': '#52525B',
  'text.primary': '#FAFAFA',
  'text.secondary': '#A1A1AA',
  'text.tertiary': '#71717A',
  'text.inverse': '#09090B',
  'accent.primary': '#4F5AF0',
  'accent.hover': '#6B74F3',
  'accent.subtle': '#1C1E3D',
  'accent.on': '#FFFFFF',
  'success': '#34D399',
  'warning': '#F5A524',
  'danger': '#F87171',
  'info': '#60A5FA',
  'agent.thinking': '#9CA3F7',
  'agent.running': '#4F5AF0',
  'agent.awaiting': '#F5A524',
  'agent.recovered': '#34D399',
  'agent.blocked': '#F87171',
  'agent.background': '#71717A',
};

export const COLORS_LIGHT: Record<ColorToken, string> = {
  'bg.canvas': '#F7F6F3',
  'bg.surface': '#FFFFFF',
  'bg.elevated': '#FAFAF8',
  'bg.sunken': '#EFEDE8',
  'border.subtle': '#E7E5E0',
  'border.default': '#D4D1CA',
  'border.strong': '#A8A49A',
  'text.primary': '#0E0E10',
  'text.secondary': '#55545A',
  'text.tertiary': '#89878F',
  'text.inverse': '#FAFAFA',
  'accent.primary': '#3340E6',
  'accent.hover': '#202CD4',
  'accent.subtle': '#E8EAFE',
  'accent.on': '#FFFFFF',
  'success': '#059669',
  'warning': '#B45309',
  'danger': '#DC2626',
  'info': '#2563EB',
  'agent.thinking': '#6366F1',
  'agent.running': '#3340E6',
  'agent.awaiting': '#B45309',
  'agent.recovered': '#059669',
  'agent.blocked': '#DC2626',
  'agent.background': '#89878F',
};

/** CSS custom-property name for a token (e.g. 'bg.canvas' → '--color-bg-canvas'). */
export const cssVar = (token: ColorToken): string =>
  `--color-${token.replace(/\./g, '-')}`;
```

- [ ] **Step 2: Write a sanity test that confirms both maps have identical keys**

Create `packages/design-system/src/tokens/colors.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { COLORS_DARK, COLORS_LIGHT, cssVar } from './colors';

describe('color tokens', () => {
  it('dark and light palettes share identical token keys', () => {
    expect(Object.keys(COLORS_DARK).sort()).toEqual(Object.keys(COLORS_LIGHT).sort());
  });

  it('cssVar generates kebab-cased CSS custom property names', () => {
    expect(cssVar('bg.canvas')).toBe('--color-bg-canvas');
    expect(cssVar('agent.thinking')).toBe('--color-agent-thinking');
  });

  it('every token has a non-empty hex string in both palettes', () => {
    for (const token of Object.keys(COLORS_DARK) as Array<keyof typeof COLORS_DARK>) {
      expect(COLORS_DARK[token]).toMatch(/^#[0-9A-F]{6}$/i);
      expect(COLORS_LIGHT[token]).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });
});
```

- [ ] **Step 3: Run the test**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```
Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/tokens/colors.ts packages/design-system/src/tokens/colors.test.ts && git commit -m "feat(design-system): add color tokens for dark + light themes"
```

### Task B2: Define typography tokens

**Files:**
- Create: `packages/design-system/src/tokens/typography.ts`

- [ ] **Step 1: Write `typography.ts`**

Create `packages/design-system/src/tokens/typography.ts`:
```typescript
/** Typography tokens — see docs/compass_artifact §2b. */

export const FONT_FAMILY = {
  display: 'var(--font-display), "Inter Display", -apple-system, BlinkMacSystemFont, sans-serif',
  sans: 'var(--font-sans), "Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  mono: 'var(--font-mono), "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace',
} as const;

/** [size in px, line-height multiplier, letter-spacing em] */
export const TYPE_SCALE = {
  'display.xl':  [48, 1.05, -0.03],
  'display.l':   [36, 1.10, -0.025],
  'display.m':   [28, 1.15, -0.02],
  'heading.1':   [22, 1.25, -0.015],
  'heading.2':   [18, 1.30, -0.01],
  'heading.3':   [15, 1.35, -0.005],
  'body.l':      [16, 1.55, 0],
  'body':        [14, 1.50, 0],
  'body.s':      [13, 1.45, 0.005],
  'caption':     [12, 1.40, 0.01],
  'micro':       [11, 1.35, 0.04],
  'mono.l':      [14, 1.50, 0],
  'mono':        [13, 1.50, 0],
  'mono.s':      [12, 1.45, 0],
  'kbd':         [11, 1.00, 0.02],
} as const satisfies Record<string, readonly [number, number, number]>;

export type TypeScaleKey = keyof typeof TYPE_SCALE;
```

- [ ] **Step 2: Test it**

Create `packages/design-system/src/tokens/typography.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { FONT_FAMILY, TYPE_SCALE } from './typography';

describe('typography tokens', () => {
  it('exposes display/sans/mono families', () => {
    expect(FONT_FAMILY.display).toContain('Inter Display');
    expect(FONT_FAMILY.sans).toContain('Inter');
    expect(FONT_FAMILY.mono).toContain('JetBrains Mono');
  });

  it('every scale entry has [size, lineHeight, tracking]', () => {
    for (const [, value] of Object.entries(TYPE_SCALE)) {
      expect(value).toHaveLength(3);
      expect(typeof value[0]).toBe('number');
    }
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/tokens/typography.ts packages/design-system/src/tokens/typography.test.ts && git commit -m "feat(design-system): add typography tokens"
```

### Task B3: Define spacing, radius, and motion tokens

**Files:**
- Create: `packages/design-system/src/tokens/spacing.ts`

- [ ] **Step 1: Write `spacing.ts`**

Create `packages/design-system/src/tokens/spacing.ts`:
```typescript
/** Spacing, radius, motion tokens — see docs/compass_artifact §2c. */

export const SPACING = [0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 80] as const;

export const RADIUS = {
  none: 0,
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 999,
} as const;

export const DURATION = {
  micro: 120,
  short: 200,
  medium: 280,
  long: 400,
  ambient: 2400,
  shimmer: 1400,
} as const;

export const EASING = {
  spring: { stiffness: 300, damping: 30 },
  easeOut: 'cubic-bezier(0.2, 0, 0, 1)',
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  linear: 'linear',
} as const;
```

- [ ] **Step 2: Test it**

Create `packages/design-system/src/tokens/spacing.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { SPACING, RADIUS, DURATION, EASING } from './spacing';

describe('spacing/radius/motion tokens', () => {
  it('SPACING is the artifact 4px-base scale', () => {
    expect(SPACING).toEqual([0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 80]);
  });

  it('RADIUS includes md (default) and full (pill)', () => {
    expect(RADIUS.md).toBe(8);
    expect(RADIUS.full).toBe(999);
  });

  it('DURATION includes ambient breathing cycle (2400ms)', () => {
    expect(DURATION.ambient).toBe(2400);
  });

  it('EASING.spring is the artifact-prescribed stiffness/damping pair', () => {
    expect(EASING.spring).toEqual({ stiffness: 300, damping: 30 });
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/tokens/spacing.ts packages/design-system/src/tokens/spacing.test.ts && git commit -m "feat(design-system): add spacing, radius, motion tokens"
```

### Task B4: Wire token barrel + replace `src/index.ts`

**Files:**
- Create: `packages/design-system/src/tokens/index.ts`
- Modify: `packages/design-system/src/index.ts`

- [ ] **Step 1: Write `tokens/index.ts`**

Create `packages/design-system/src/tokens/index.ts`:
```typescript
export * from './colors';
export * from './typography';
export * from './spacing';
```

- [ ] **Step 2: Replace the current `src/index.ts`**

Read `packages/design-system/src/index.ts`. Then overwrite it:
```typescript
export * from './tokens';
// Components are re-exported below as they land.
export { Button, type ButtonProps } from './components/button';
export { Input, type InputProps } from './components/input';
export { Card, type CardProps } from './components/card';
```

(The component re-exports will resolve once Tasks D1–D3 land. Confirm the test runner doesn't try to compile `src/index.ts` standalone — Vitest only loads files referenced by tests.)

- [ ] **Step 3: Delete the old (currently broken) tokens file**

The current `packages/design-system/src/tokens/index.ts` exports JS constants `colors`, `spacing`, `radius` with values that don't match the new system. Overwriting it in Step 1 already replaced it. Confirm by running:
```bash
cat /Users/mrinalraj/Documents/Axis/packages/design-system/src/tokens/index.ts
```
Expected: only the three `export *` lines.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/tokens/index.ts packages/design-system/src/index.ts && git commit -m "refactor(design-system): replace token barrel with new system"
```

### Task B5: Replace web's `tailwind.config.ts`

**Files:**
- Modify: `apps/web/tailwind.config.ts`

- [ ] **Step 1: Read the current file**

Read `apps/web/tailwind.config.ts` to confirm structure.

- [ ] **Step 2: Overwrite with the CSS-variable-backed version**

Write `apps/web/tailwind.config.ts`:
```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    '../../packages/design-system/src/**/*.{ts,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: 'var(--color-bg-canvas)',
          surface: 'var(--color-bg-surface)',
          elevated: 'var(--color-bg-elevated)',
          sunken: 'var(--color-bg-sunken)',
        },
        edge: {
          DEFAULT: 'var(--color-border-default)',
          subtle: 'var(--color-border-subtle)',
          strong: 'var(--color-border-strong)',
        },
        ink: {
          DEFAULT: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          inverse: 'var(--color-text-inverse)',
        },
        accent: {
          DEFAULT: 'var(--color-accent-primary)',
          hover: 'var(--color-accent-hover)',
          subtle: 'var(--color-accent-subtle)',
          on: 'var(--color-accent-on)',
        },
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
        info: 'var(--color-info)',
        agent: {
          thinking: 'var(--color-agent-thinking)',
          running: 'var(--color-agent-running)',
          awaiting: 'var(--color-agent-awaiting)',
          recovered: 'var(--color-agent-recovered)',
          blocked: 'var(--color-agent-blocked)',
          background: 'var(--color-agent-background)',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'Inter Display', '-apple-system', 'sans-serif'],
        sans: ['var(--font-sans)', 'Inter', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['48px', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '500' }],
        'display-l':  ['36px', { lineHeight: '1.10', letterSpacing: '-0.025em', fontWeight: '500' }],
        'display-m':  ['28px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '500' }],
        'heading-1':  ['22px', { lineHeight: '1.25', letterSpacing: '-0.015em', fontWeight: '600' }],
        'heading-2':  ['18px', { lineHeight: '1.30', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-3':  ['15px', { lineHeight: '1.35', letterSpacing: '-0.005em', fontWeight: '600' }],
        'body-l':     ['16px', { lineHeight: '1.55' }],
        'body':       ['14px', { lineHeight: '1.50' }],
        'body-s':     ['13px', { lineHeight: '1.45' }],
        'caption':    ['12px', { lineHeight: '1.40' }],
        'micro':      ['11px', { lineHeight: '1.35', letterSpacing: '0.04em', fontWeight: '500' }],
        'mono-l':     ['14px', { lineHeight: '1.50' }],
        'mono':       ['13px', { lineHeight: '1.50' }],
        'mono-s':     ['12px', { lineHeight: '1.45' }],
        'kbd':        ['11px', { lineHeight: '1.00', letterSpacing: '0.02em', fontWeight: '500' }],
      },
      spacing: {
        '0.5': '2px',
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '14': '56px',
        '20': '80px',
      },
      borderRadius: {
        none: '0',
        xs: '4px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        full: '999px',
      },
      boxShadow: {
        // Light-mode only — dark uses luminance layers, no shadows.
        'e1': '0 1px 2px rgba(14,14,16,0.05)',
        'e2': '0 1px 2px rgba(14,14,16,0.05), 0 2px 4px rgba(14,14,16,0.04)',
        'e3': '0 20px 40px rgba(14,14,16,0.12)',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.92' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        breathe: 'breathe 2400ms ease-in-out infinite',
        shimmer: 'shimmer 1400ms linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 3: Verify Tailwind compiles**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -10
```
Expected: build will likely fail because existing pages reference old token names (`bg-canvas-raised`, `bg-brand-500`, `text-ink-tertiary`, `bg-nav`, etc.). **This is expected** — Tasks B6 and beyond replace those references. For this step, you only need Tailwind itself to parse the config without error. Look at the output: if there's a Tailwind config-parse error, fix it. If it's compile errors about unknown classes in `app/(app)/...`, that is fine for now.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/tailwind.config.ts && git commit -m "feat(web): replace tailwind theme with CSS-var-backed token map"
```

### Task B6: Replace `apps/web/app/globals.css`

**Files:**
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Overwrite the file**

Write `apps/web/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ========================================================================
   Color tokens — kept in sync with packages/design-system/src/tokens/colors.ts.
   Dark is the canonical theme; light is a faithful mirror.
   See docs/compass_artifact §2a.
   ======================================================================== */

:root,
[data-theme='dark'] {
  --color-bg-canvas: #09090B;
  --color-bg-surface: #111113;
  --color-bg-elevated: #1A1A1D;
  --color-bg-sunken: #060608;
  --color-border-subtle: #27272A;
  --color-border-default: #3F3F46;
  --color-border-strong: #52525B;
  --color-text-primary: #FAFAFA;
  --color-text-secondary: #A1A1AA;
  --color-text-tertiary: #71717A;
  --color-text-inverse: #09090B;
  --color-accent-primary: #4F5AF0;
  --color-accent-hover: #6B74F3;
  --color-accent-subtle: #1C1E3D;
  --color-accent-on: #FFFFFF;
  --color-success: #34D399;
  --color-warning: #F5A524;
  --color-danger: #F87171;
  --color-info: #60A5FA;
  --color-agent-thinking: #9CA3F7;
  --color-agent-running: #4F5AF0;
  --color-agent-awaiting: #F5A524;
  --color-agent-recovered: #34D399;
  --color-agent-blocked: #F87171;
  --color-agent-background: #71717A;
}

[data-theme='light'] {
  --color-bg-canvas: #F7F6F3;
  --color-bg-surface: #FFFFFF;
  --color-bg-elevated: #FAFAF8;
  --color-bg-sunken: #EFEDE8;
  --color-border-subtle: #E7E5E0;
  --color-border-default: #D4D1CA;
  --color-border-strong: #A8A49A;
  --color-text-primary: #0E0E10;
  --color-text-secondary: #55545A;
  --color-text-tertiary: #89878F;
  --color-text-inverse: #FAFAFA;
  --color-accent-primary: #3340E6;
  --color-accent-hover: #202CD4;
  --color-accent-subtle: #E8EAFE;
  --color-accent-on: #FFFFFF;
  --color-success: #059669;
  --color-warning: #B45309;
  --color-danger: #DC2626;
  --color-info: #2563EB;
  --color-agent-thinking: #6366F1;
  --color-agent-running: #3340E6;
  --color-agent-awaiting: #B45309;
  --color-agent-recovered: #059669;
  --color-agent-blocked: #DC2626;
  --color-agent-background: #89878F;
}

/* Font CSS variables are set by next/font in app/layout.tsx via the className.
   The fallbacks here let the page render before fonts hydrate. */
:root {
  --font-display: 'Inter Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
}

@layer base {
  html {
    font-family: var(--font-sans);
    background: var(--color-bg-canvas);
    color: var(--color-text-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }

  body {
    background: var(--color-bg-canvas);
    color: var(--color-text-primary);
    min-height: 100vh;
  }

  *:focus-visible {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 2px;
    border-radius: 2px;
  }

  ::selection {
    background: var(--color-accent-subtle);
    color: var(--color-text-primary);
  }

  .num,
  table,
  pre,
  code {
    font-variant-numeric: tabular-nums;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 2: Note that any old utility classes in `globals.css` are gone on purpose**

The current `globals.css` had `.panel`, `.label-caps`, `.row-hover` utilities. Those are deleted; their styling lives on the new components in `packages/design-system`. Existing usages will stop working until Tasks E1–E3 migrate components.

- [ ] **Step 3: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/globals.css && git commit -m "feat(web): rewrite globals.css with new token CSS variables"
```

### Task B7: Load fonts via next/font

**Files:**
- Create: `apps/web/app/fonts.ts`
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: Write `fonts.ts`**

Create `apps/web/app/fonts.ts`:
```typescript
import { Inter, Inter_Tight, JetBrains_Mono } from 'next/font/google';

/** Body font — covers ~85% of the UI. */
export const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-sans',
  display: 'swap',
});

/**
 * Display cut for Display M/L/XL sizes only.
 * (Inter Display is not on Google Fonts as a separate family;
 * Inter Tight is the closest published cut and reads similarly at large sizes.
 * See spec deviation note in plan header.)
 */
export const interDisplay = Inter_Tight({
  subsets: ['latin'],
  weight: ['500', '600'],
  variable: '--font-display',
  display: 'swap',
});

/** Mono — used selectively (~15% of text per artifact §2b). */
export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'optional',
});
```

- [ ] **Step 2: Modify `app/layout.tsx`** to apply the font variable classNames

Read `apps/web/app/layout.tsx` first. Then modify the `<html>` tag's `className` to include the three font variables and set `data-theme="dark"` as the default:

```tsx
import { inter, interDisplay, jetbrainsMono } from './fonts';
// ...existing imports
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      className={`${inter.variable} ${interDisplay.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

(Adapt the surrounding code to match what's already in the file. Keep any existing `<head>` content, metadata, etc.)

- [ ] **Step 3: Run dev to confirm fonts load**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```
Open `http://localhost:3000` (or 3001 if 3000 is taken — see CLAUDE.md), open DevTools → Network → Font, confirm three font files load. Stop the dev server.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/fonts.ts apps/web/app/layout.tsx && git commit -m "feat(web): load Inter + Inter Tight + JetBrains Mono via next/font"
```

---

## Phase C — Theme system

### Task C1: Build the `useTheme` hook + ThemeProvider

**Files:**
- Create: `apps/web/lib/theme.tsx`
- Create: `apps/web/lib/theme.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/web/lib/theme.test.tsx`:
```tsx
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme } from './theme';

function ThemeProbe() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button onClick={() => setTheme('light')}>light</button>
      <button onClick={() => setTheme('dark')}>dark</button>
      <button onClick={() => setTheme('system')}>system</button>
    </div>
  );
}

describe('ThemeProvider + useTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('defaults to system when no localStorage value is set', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    expect(screen.getByTestId('theme').textContent).toBe('system');
  });

  it('applies the resolved theme to document.documentElement', async () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByText('light'));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(screen.getByTestId('resolved').textContent).toBe('light');

    await userEvent.click(screen.getByText('dark'));
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('persists the user choice to localStorage', async () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByText('light'));
    expect(localStorage.getItem('axis.theme')).toBe('light');
  });

  it('reads an existing localStorage value on mount', () => {
    localStorage.setItem('axis.theme', 'light');
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    expect(screen.getByTestId('theme').textContent).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```
Expected: 4 failures — `theme` module not found.

- [ ] **Step 3: Write the implementation**

Create `apps/web/lib/theme.tsx`:
```tsx
'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

const STORAGE_KEY = 'axis.theme';

function readSystemPreference(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function readStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'system';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  return 'system';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => readStoredTheme());
  const [systemPreference, setSystemPreference] = useState<ResolvedTheme>(() =>
    readSystemPreference(),
  );

  useEffect(() => {
    const mql = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => setSystemPreference(mql.matches ? 'light' : 'dark');
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme: ResolvedTheme = theme === 'system' ? systemPreference : theme;

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    if (next === 'system') {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web test
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/lib/theme.tsx apps/web/lib/theme.test.tsx && git commit -m "feat(web): add ThemeProvider + useTheme hook"
```

### Task C2: Mount ThemeProvider in `providers.tsx`

**Files:**
- Modify: `apps/web/app/providers.tsx`

- [ ] **Step 1: Read the current providers**

Read `apps/web/app/providers.tsx`.

- [ ] **Step 2: Wrap children with `ThemeProvider`**

Modify the file so the component returns:
```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ThemeProvider } from '@/lib/theme';

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}
```

(Preserve any existing imports or non-trivial logic — only add the ThemeProvider wrap and import.)

- [ ] **Step 3: Run dev, switch theme via DevTools to confirm**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```
Open the app, in the browser console run `localStorage.setItem('axis.theme', 'light'); location.reload()`. The page background should switch to the warm-white. Then `localStorage.removeItem('axis.theme'); location.reload()` to fall back to system.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/providers.tsx && git commit -m "feat(web): mount ThemeProvider"
```

---

## Phase D — Primitives

### Task D1: Build the new `Button` primitive

**Files:**
- Create: `packages/design-system/src/components/button/button.tsx`
- Create: `packages/design-system/src/components/button/button.test.tsx`
- Create: `packages/design-system/src/components/button/index.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/design-system/src/components/button/button.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('fires onClick', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies the variant class for primary by default', () => {
    render(<Button>Primary</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-accent');
  });

  it('renders the danger variant with a danger background', () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-danger');
  });

  it('renders the secondary variant with a border', () => {
    render(<Button variant="secondary">More</Button>);
    expect(screen.getByRole('button')).toHaveClass('border');
  });

  it('disables interaction when `disabled`', async () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Off</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders the loading state with aria-busy', () => {
    render(<Button loading>Submit</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toHaveAttribute('aria-busy', 'true');
    expect(btn).toBeDisabled();
  });

  it('respects `size` prop', () => {
    const { rerender } = render(<Button size="sm">sm</Button>);
    expect(screen.getByRole('button')).toHaveClass('h-8');
    rerender(<Button size="lg">lg</Button>);
    expect(screen.getByRole('button')).toHaveClass('h-12');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```
Expected: failures — `button` module not found.

- [ ] **Step 3: Write the implementation**

Create `packages/design-system/src/components/button/button.tsx`:
```tsx
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  children?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:   'bg-accent text-accent-on hover:bg-accent-hover border-transparent',
  secondary: 'bg-canvas-elevated text-ink border border-edge hover:border-edge-strong hover:bg-canvas-elevated',
  ghost:     'bg-transparent text-ink-secondary hover:text-ink hover:bg-canvas-elevated border-transparent',
  danger:    'bg-danger text-white border-transparent hover:opacity-90',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-body-s gap-1',
  md: 'h-10 px-4 text-body gap-2',
  lg: 'h-12 px-6 text-body-l gap-2',
};

const BASE_CLASSES =
  'inline-flex items-center justify-center rounded-md font-medium transition-colors duration-[120ms] ease-out disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 select-none';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled,
    leadingIcon,
    trailingIcon,
    className,
    children,
    type = 'button',
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={clsx(BASE_CLASSES, VARIANT_CLASSES[variant], SIZE_CLASSES[size], className)}
      {...rest}
    >
      {leadingIcon}
      {loading ? (
        <span className="inline-block h-3 w-3 rounded-full border-2 border-current border-r-transparent animate-spin" />
      ) : (
        children
      )}
      {trailingIcon}
    </button>
  );
});
```

- [ ] **Step 4: Write the index file**

Create `packages/design-system/src/components/button/index.ts`:
```typescript
export { Button } from './button';
export type { ButtonProps, ButtonVariant, ButtonSize } from './button';
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```
Expected: 8 button tests pass + 8 token tests still pass = 16 total.

- [ ] **Step 6: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add packages/design-system/src/components/button && git commit -m "feat(design-system): build new Button primitive"
```

### Task D2: Build the new `Input` primitive

**Files:**
- Create: `packages/design-system/src/components/input/input.tsx`
- Create: `packages/design-system/src/components/input/input.test.tsx`
- Create: `packages/design-system/src/components/input/index.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/design-system/src/components/input/input.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from './input';

describe('Input', () => {
  it('renders with placeholder', () => {
    render(<Input placeholder="you@company.com" />);
    expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument();
  });

  it('accepts user input', async () => {
    render(<Input aria-label="email" />);
    await userEvent.type(screen.getByLabelText('email'), 'a@b.com');
    expect(screen.getByLabelText('email')).toHaveValue('a@b.com');
  });

  it('forwards ref', () => {
    let captured: HTMLInputElement | null = null;
    render(<Input ref={(el) => (captured = el)} aria-label="x" />);
    expect(captured).toBeInstanceOf(HTMLInputElement);
  });

  it('renders an error state with aria-invalid', () => {
    render(<Input invalid aria-label="email" />);
    expect(screen.getByLabelText('email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('honors `disabled`', async () => {
    render(<Input disabled aria-label="off" />);
    expect(screen.getByLabelText('off')).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/input/input.tsx`:
```tsx
import { forwardRef, type InputHTMLAttributes } from 'react';
import clsx from 'clsx';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  invalid?: boolean;
}

const BASE_CLASSES =
  'block w-full h-10 px-3 py-2 rounded-md text-body bg-canvas-surface text-ink placeholder:text-ink-tertiary border border-edge transition-colors duration-[120ms] ease-out focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-50 disabled:cursor-not-allowed';

const ERROR_CLASSES = 'border-danger focus:border-danger focus:ring-danger/20';

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={clsx(BASE_CLASSES, invalid && ERROR_CLASSES, className)}
      {...rest}
    />
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/input/index.ts`:
```typescript
export { Input } from './input';
export type { InputProps } from './input';
```

- [ ] **Step 5: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/input && git commit -m "feat(design-system): build new Input primitive"
```

### Task D3: Build the new `Card` primitive

**Files:**
- Create: `packages/design-system/src/components/card/card.tsx`
- Create: `packages/design-system/src/components/card/card.test.tsx`
- Create: `packages/design-system/src/components/card/index.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/design-system/src/components/card/card.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardBody, CardFooter } from './card';

describe('Card', () => {
  it('renders children inside a surface container', () => {
    render(<Card data-testid="c">hello</Card>);
    const el = screen.getByTestId('c');
    expect(el).toHaveTextContent('hello');
    expect(el).toHaveClass('bg-canvas-surface');
    expect(el).toHaveClass('border');
  });

  it('renders header / body / footer slots', () => {
    render(
      <Card>
        <CardHeader data-testid="h">title</CardHeader>
        <CardBody data-testid="b">body</CardBody>
        <CardFooter data-testid="f">footer</CardFooter>
      </Card>,
    );
    expect(screen.getByTestId('h')).toHaveTextContent('title');
    expect(screen.getByTestId('b')).toHaveTextContent('body');
    expect(screen.getByTestId('f')).toHaveTextContent('footer');
  });

  it('forwards className', () => {
    render(<Card className="custom-class" data-testid="c">x</Card>);
    expect(screen.getByTestId('c')).toHaveClass('custom-class');
  });
});
```

- [ ] **Step 2: Run to fail**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test
```

- [ ] **Step 3: Implement**

Create `packages/design-system/src/components/card/card.tsx`:
```tsx
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

const CARD_BASE = 'bg-canvas-surface border border-edge-subtle rounded-lg overflow-hidden';

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx(CARD_BASE, className)} {...rest}>
      {children}
    </div>
  );
});

export const CardHeader = forwardRef<HTMLDivElement, CardProps>(function CardHeader(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4 border-b border-edge-subtle', className)} {...rest}>
      {children}
    </div>
  );
});

export const CardBody = forwardRef<HTMLDivElement, CardProps>(function CardBody(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4', className)} {...rest}>
      {children}
    </div>
  );
});

export const CardFooter = forwardRef<HTMLDivElement, CardProps>(function CardFooter(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4 border-t border-edge-subtle', className)} {...rest}>
      {children}
    </div>
  );
});
```

- [ ] **Step 4: Index**

Create `packages/design-system/src/components/card/index.ts`:
```typescript
export { Card, CardHeader, CardBody, CardFooter } from './card';
export type { CardProps } from './card';
```

- [ ] **Step 5: Update the component barrel and the package's main `src/index.ts`** to also re-export `CardHeader`/`CardBody`/`CardFooter`

Edit `packages/design-system/src/index.ts` so the Card line becomes:
```typescript
export { Card, CardHeader, CardBody, CardFooter, type CardProps } from './components/card';
```

- [ ] **Step 6: Run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/design-system test && git add packages/design-system/src/components/card packages/design-system/src/index.ts && git commit -m "feat(design-system): build new Card primitive with slots"
```

---

## Phase E — Migrate web's existing wrappers

### Task E1: Make `apps/web/components/ui/button.tsx` a thin re-export

**Files:**
- Modify: `apps/web/components/ui/button.tsx`

- [ ] **Step 1: Read the current file** to inventory what it exports.

- [ ] **Step 2: Replace with a re-export**

Write `apps/web/components/ui/button.tsx`:
```tsx
export { Button, type ButtonProps, type ButtonVariant, type ButtonSize } from '@axis/design-system';
```

- [ ] **Step 3: Type-check the web app to find any callers using removed props**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -30
```
Expected: any callers passing variants like `xs` size or props the new Button doesn't accept will error. Fix each caller to use the new prop set: variants `primary | secondary | ghost | danger`, sizes `sm | md | lg`. The set of caller files comes from the type-check output — change them in this task and they're part of this commit.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/ui/button.tsx apps/web/app apps/web/components && git commit -m "refactor(web): re-export Button from design-system"
```

### Task E2: Migrate `Input` re-export from `apps/web/components/ui/form.tsx`

**Files:**
- Modify: `apps/web/components/ui/form.tsx`

- [ ] **Step 1: Read the current form.tsx** to inventory exports (it bundles Input, Textarea, Select, Label, Field).

- [ ] **Step 2: Replace `Input` export with a re-export from design-system**

In `apps/web/components/ui/form.tsx`, remove the local `Input` implementation and add at the top:
```typescript
export { Input, type InputProps } from '@axis/design-system';
```
Keep `Textarea`, `Select`, `Label`, `Field` local for now — they'll move to design-system in a later plan.

- [ ] **Step 3: Type-check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -30
```
Fix any caller that used a removed Input prop.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/ui/form.tsx apps/web/app apps/web/components && git commit -m "refactor(web): re-export Input from design-system"
```

### Task E3: Migrate `Panel` to back onto `Card`

**Files:**
- Modify: `apps/web/components/ui/card.tsx` (or whichever file currently exports `Panel`)

- [ ] **Step 1: Find the Panel exports**

```bash
cd /Users/mrinalraj/Documents/Axis && rg "export.*Panel" apps/web/components/ui/ 2>&1
```

- [ ] **Step 2: Replace Panel with re-aliased Card**

Edit the file that exports `Panel`/`PanelHeader`/`PanelBody`/`PanelFooter` so it becomes:
```typescript
export {
  Card as Panel,
  CardHeader as PanelHeader,
  CardBody as PanelBody,
  CardFooter as PanelFooter,
  type CardProps as PanelProps,
} from '@axis/design-system';
```

- [ ] **Step 3: Type-check**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -30
```
Fix any caller passing Card-incompatible props.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/ui && git commit -m "refactor(web): alias Panel to design-system Card"
```

---

## Phase F — Login + Signup vertical slice

### Task F1: Rebuild the auth shell layout per artifact §3b

**Files:**
- Modify: `apps/web/app/(auth)/layout.tsx`

- [ ] **Step 1: Read current layout** to preserve any logic.

- [ ] **Step 2: Rewrite per the artifact**

Per artifact §3b: split-screen, light-mode default in this surface (enterprise context), 420 px form on the left, ambient preview canvas on the right (a static placeholder for now — the real "muted preview canvas with breathing pulse" lands in Plan 3 once `BreathingPulse` and the streaming primitives exist).

Write `apps/web/app/(auth)/layout.tsx`:
```tsx
import type { ReactNode } from 'react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[420px_1fr] bg-canvas">
      <section className="flex flex-col px-8 py-10 lg:px-10 lg:py-14 bg-canvas">
        <header className="mb-12 flex items-center gap-2">
          <span aria-hidden className="block h-3 w-3 rounded-sm bg-accent" />
          <span className="font-display text-heading-1 text-ink">Axis</span>
        </header>
        <main className="flex-1 flex flex-col justify-center max-w-[360px]">
          {children}
        </main>
        <footer className="mt-12 text-caption text-ink-tertiary">
          Axis · v0.1 · © 2026 RawEval Inc
        </footer>
      </section>

      <aside
        aria-hidden
        className="hidden lg:block bg-canvas-surface border-l border-edge-subtle relative overflow-hidden"
      >
        <div className="absolute inset-0 flex items-center justify-center text-ink-tertiary">
          <span className="font-mono text-caption uppercase tracking-[0.12em]">
            preview canvas — coming soon
          </span>
        </div>
      </aside>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(auth\)/layout.tsx && git commit -m "feat(web): rebuild auth shell as split-screen per artifact §3b"
```

### Task F2: Rebuild the Login page per artifact §3b

**Files:**
- Modify: `apps/web/app/(auth)/login/page.tsx`

- [ ] **Step 1: Read the current login page** to preserve `useLogin`, `ApiError` handling, the `from` redirect logic.

- [ ] **Step 2: Rewrite the JSX**

Write `apps/web/app/(auth)/login/page.tsx`:
```tsx
'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@axis/design-system';
import { Field, Input } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { useLogin } from '@/lib/queries/auth';

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get('from') ?? '/feed';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const login = useLogin();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push(from);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'Login failed.'
          : 'Login failed.',
      );
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-display-m text-ink">Sign in</h1>
        <p className="text-body text-ink-secondary">Welcome back.</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label="Email" required>
          <Input
            type="email"
            required
            autoFocus
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
        </Field>

        <Field label="Password" required>
          <Input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-body-s text-danger"
          >
            {error}
          </div>
        )}

        <Button type="submit" size="md" className="w-full" loading={login.isPending}>
          Sign in
        </Button>
      </form>

      <p className="text-body-s text-ink-tertiary">
        No account?{' '}
        <Link
          href="/signup"
          className="text-accent hover:text-accent-hover underline-offset-4 hover:underline"
        >
          Create one
        </Link>
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Run dev, smoke-test the page**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```
Open `http://localhost:3000/login` (or 3001). Confirm:
- Page renders without console errors.
- Layout is split-screen on desktop, single-column on small screens.
- Inputs accept text. Tab order works.
- Toggle theme via DevTools (`document.documentElement.setAttribute('data-theme','light')`) — colors flip cleanly.
- Submit with empty form is blocked (HTML5 `required`); submit with invalid creds shows the error block (assuming the auth backend is running, otherwise expect a network error).

Stop the dev server.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(auth\)/login/page.tsx && git commit -m "feat(web): rebuild login page per artifact §3b"
```

### Task F3: Rebuild the Signup page (mirror of Login)

**Files:**
- Modify: `apps/web/app/(auth)/signup/page.tsx`

- [ ] **Step 1: Read the current signup page**.

- [ ] **Step 2: Apply the same visual treatment** — same heading rhythm, same input/button stack, plus a "Work email recommended" hint per artifact §3b.

Pattern (adapt to the actual signup mutation, fields, and API in the existing file):
```tsx
<div className="space-y-8">
  <div className="space-y-2">
    <h1 className="font-display text-display-m text-ink">Create your account</h1>
    <p className="text-body text-ink-secondary">Work email recommended.</p>
  </div>

  <form onSubmit={onSubmit} className="space-y-5" noValidate>
    {/* fields, error block, Button — exactly as in login */}
  </form>

  <p className="text-body-s text-ink-tertiary">
    Already have an account?{' '}
    <Link href="/login" className="text-accent hover:text-accent-hover">
      Sign in
    </Link>
  </p>
</div>
```

- [ ] **Step 3: Smoke-test in dev** (same as Task F2 step 3, but at `/signup`).

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/app/\(auth\)/signup/page.tsx && git commit -m "feat(web): rebuild signup page per artifact §3b"
```

### Task F4: Verify everything together

- [ ] **Step 1: Run all tests**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test
```
Expected: every test in `packages/design-system` and `apps/web` passes. Count and report numbers — should be at least: 3 colors + 2 typography + 4 spacing + 8 button + 5 input + 3 card + 4 theme = **29 tests**.

- [ ] **Step 2: Run lint across the workspace**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm lint 2>&1 | tail -20
```
Expected: zero errors. Warnings are acceptable but log them.

- [ ] **Step 3: Run type-check across the workspace**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm type-check 2>&1 | tail -20
```
Expected: zero errors. If errors remain in pages we did NOT touch (Home, Chat, etc.), that means those pages reference dead Tailwind classes from the old token map. **Two options:** (1) leave them broken in this plan and fix in Plan 2 when we redesign them, OR (2) do a quick "compile-clean" pass replacing dead class names with the closest new equivalent. Recommend option 1; surface the broken pages in the wrap-up message.

- [ ] **Step 4: Run the build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web build 2>&1 | tail -20
```
Expected: build succeeds. If it fails on pages outside the auth slice, decide per Step 3 above. The build MUST succeed for the auth pages — that's the slice this plan delivers.

- [ ] **Step 5: Manual smoke test in dev (light + dark)**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```
- Open `/login` → confirm dark theme by default, ink-cobalt primary button, Inter text.
- In DevTools, set `localStorage.setItem('axis.theme','light'); location.reload()` → confirm warm-white background, ink-cobalt deepens to `#3340E6`, layout intact.
- Resize window to <1024px → preview canvas hides, form goes single-column.
- Tab through the form → focus rings show 2 px ink-cobalt outline.
- Visit `/signup` → same treatment.
- Stop dev server.

- [ ] **Step 6: Final commit if any small fixes were needed during smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && git status
# If clean, no commit. Otherwise:
git add -A && git commit -m "chore(web): smoke-test fixes after auth slice landing"
```

---

## What we have at the end of this plan

- Design tokens (colors, typography, spacing, motion) defined in `packages/design-system/src/tokens` and exposed as CSS variables in `apps/web/app/globals.css`.
- Both dark and light themes wired, with a `ThemeProvider` + `useTheme` hook persisting choice to `localStorage`.
- Three primitives (`Button`, `Input`, `Card`) live in `packages/design-system`, fully tested with Vitest + RTL.
- Web app's `components/ui/{button,form,card}` are thin re-exports of the design-system primitives.
- `(auth)/login` and `(auth)/signup` rebuilt per artifact §3b — split-screen, ink-cobalt, Inter, the new visual register.
- Build is green for the auth slice. Lint, type-check, tests all pass.
- Approximately 29 unit tests in place — the seed of a real test suite for the redesign.

## What we explicitly did NOT do (handed off to Plan 2)

- Inner-app pages (Home, Chat, Activity, History, Connections, Memory, Settings, Team) — these will likely break when their old Tailwind class names lose their tokens. Plan 2 starts with deciding whether to do a one-shot "compile-clean" sweep on those routes or rebuild them per artifact section in order.
- Shell rewrite (LeftNav 240/56, Topbar 48, RightPanel 360, ⌘K command palette, `?` shortcut overlay).
- The rest of the primitives (`Modal`, `Toast`, `Tooltip`, `Popover`, `DropdownMenu`, `ContextMenu`, `Tabs`, `SegmentedControl`, `ProgressBar`, `SkeletonBlock`, `Avatar`, `Kbd`).
- All Axis-native components (`LiveTaskTree`, `DiffViewer`, `PermissionCard`, `WritePreviewCard`, `CitationChip`, `AgentStateDot`, `ConnectorTile`, `MemoryRow`, `PromptInput`, `BreathingPulse`).
- Theme toggle UI (the hook is wired; the toggle control comes with the user menu in Plan 3).
- The "operations-center" Home page (artifact §3a).
- Backend support for capability tiers, undo handlers, audience counter, trust mode (Plan 5+).
- Feature flag system (`VISUAL_V2`).
- Self-hosting Commit Mono (token swap from JetBrains Mono).
- Söhne (token swap from Inter once licensed).
- Visual regression suite (Playwright).
- Storybook.
- Onboarding / demo workspace seed (Plan 4+).

## Self-review — completed inline before commit

- **Spec coverage:** Plan covers spec sections "Tokens & globals", "Component library" (initial 3 primitives only — rest deferred), "Pages" (Login + Signup only — rest deferred), "Feature flags" (deferred with clear note), "Tech-stack additions" (lucide-react, framer-motion, Vitest, RTL added; cmdk, react-virtual, Radix deferred to plans that need them).
- **Placeholder scan:** No "TBD" / "TODO" / "implement later" inside any task step. The "What we did NOT do" section is intentional scope marking, not placeholder.
- **Type consistency:** `Button` props match across button.tsx, button.test.tsx, and button index. `ButtonVariant` `'primary'|'secondary'|'ghost'|'danger'` and `ButtonSize` `'sm'|'md'|'lg'` are consistent everywhere. `Input` `invalid` prop is consistent. `Card` slot names (`CardHeader`/`CardBody`/`CardFooter`) match the Panel aliases.
- **Commands:** Every `pnpm` command uses the `--filter` form that matches the workspace package names from `pnpm-workspace.yaml`. Build / test / type-check / lint commands all match the scripts already in the package.json files (with the `test` script we add in A2).
