# Axis UI Plan 8 — Playwright Visual Regression + Onboarding Banner

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a Playwright visual-regression suite that locks in the design language across the most-used pages (Login, Signup, Home, Chat empty state) in both light + dark themes, and add an onboarding hint banner on Home for first-time users.

**Architecture:** Playwright tests live in `apps/web/e2e/`. The webServer config starts `pnpm dev` if not already running. Auth-gated routes are reached by setting an `axis.token` cookie before navigation (the middleware only checks for cookie presence, not validity). A shared `prepareForSnapshot` helper disables animations, waits for fonts, and hides the cursor. Snapshots live in `apps/web/e2e/__snapshots__/<test>-snapshots/<name>-<platform>.png`. The onboarding banner is a dismissable React component on Home that hides itself once `localStorage["axis.onboarded"]` is set.

**Tech Stack:** Adds `@playwright/test ^1.48.0`. Chromium browser via `npx playwright install chromium`.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and the canonical artifact §8 risk #4 (visual regression must be in place before more design churn).

**Out of scope** (Plan 9):
- Backend tier registry (`services/agent-orchestration`)
- Undo handlers (`services/api-gateway`)
- Audience counter, trust mode UI
- Real metrics endpoints for the Admin dashboard
- Demo workspace seed (synthetic data for first-run)
- CI integration (running the suite on every PR)

**Deviations:**
1. **Local-only.** No CI integration — Playwright runs locally only. Engineers run `pnpm e2e` before merging to update snapshots intentionally. CI integration is a Plan 9 follow-up that needs a CI provider config.
2. **Chromium only.** Multi-browser snapshot diffing is overkill for V1; chromium captures 95% of regression cases for a Tailwind-based app.
3. **Snapshot updates are manual.** First run creates baselines (`--update-snapshots`); subsequent runs compare. No auto-approval.

---

## File structure

**Create:**

```
apps/web/playwright.config.ts                  # Playwright config
apps/web/e2e/helpers.ts                        # Shared helpers (theme cookie, prepareForSnapshot)
apps/web/e2e/auth.spec.ts                      # Login + Signup snapshots × 2 themes
apps/web/e2e/home.spec.ts                      # Home snapshots × 2 themes
apps/web/e2e/chat.spec.ts                      # Chat empty-state snapshots × 2 themes
apps/web/e2e/__snapshots__/                    # baselines (created on first --update-snapshots)
apps/web/components/home/onboarding-banner.tsx # The banner component
```

**Modify:**

```
apps/web/package.json                          # add e2e script + @playwright/test devDep
apps/web/.gitignore                            # don't ignore __snapshots__ (we want them tracked)
apps/web/app/(app)/page.tsx                    # mount OnboardingBanner above existing sections
```

**Total:** 6 new files, 3 modified, 5 commits + initial snapshot baseline commit.

---

## Phase A — Playwright setup

### Task A1: Install Playwright + config + helpers

**Files:**
- Modify: `apps/web/package.json`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/e2e/helpers.ts`

- [ ] **Step 1: Install Playwright**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web add -D @playwright/test@^1.48.0
```

- [ ] **Step 2: Install chromium browser**

```bash
cd /Users/mrinalraj/Documents/Axis/apps/web && npx playwright install chromium
```

This downloads ~100MB. Expected output: `chromium … installed`.

- [ ] **Step 3: Add scripts to `apps/web/package.json`**

In the `scripts` block, add:
```json
"e2e": "playwright test",
"e2e:update": "playwright test --update-snapshots",
"e2e:ui": "playwright test --ui"
```

- [ ] **Step 4: Create `apps/web/playwright.config.ts`**

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  // Run tests in files in parallel
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    // Lock viewport for consistent snapshots
    viewport: { width: 1280, height: 800 },
    // Disable animations / transitions in screenshots
    screenshot: { mode: 'off', fullPage: true },
  },
  // Tighter snapshot diff threshold than the default
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      animations: 'disabled',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3001',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
```

- [ ] **Step 5: Create `apps/web/e2e/helpers.ts`**

```typescript
import { type Page, type BrowserContext, expect } from '@playwright/test';

export type Theme = 'light' | 'dark';

/**
 * Prepares a page for a deterministic visual snapshot:
 *  - Sets the theme via localStorage + data-theme attribute
 *  - Disables animations (defense-in-depth even though Playwright's expect.animations: 'disabled' covers most)
 *  - Hides the caret/cursor
 *  - Waits for fonts to load
 *  - Waits for the network to idle
 */
export async function prepareForSnapshot(page: Page, theme: Theme): Promise<void> {
  // Set theme BEFORE first paint
  await page.addInitScript((t) => {
    window.localStorage.setItem('axis.theme', t);
  }, theme);

  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0ms !important;
        animation-delay: 0ms !important;
        transition-duration: 0ms !important;
        caret-color: transparent !important;
      }
    `,
  });

  await page.evaluateHandle('document.fonts.ready');
  await page.waitForLoadState('networkidle').catch(() => {});
}

/**
 * Sets a fake auth cookie so middleware-protected routes load.
 * The middleware only checks for cookie *presence*, not validity.
 */
export async function fakeAuthCookie(context: BrowserContext): Promise<void> {
  await context.addCookies([
    {
      name: 'axis.token',
      value: 'e2e-test-token',
      domain: 'localhost',
      path: '/',
      expires: Math.floor(Date.now() / 1000) + 3600,
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
    },
  ]);
}

/**
 * Marks the onboarding banner as dismissed so it doesn't show in snapshots
 * of pages that aren't testing the banner itself.
 */
export async function dismissOnboarding(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('axis.onboarded', 'true');
  });
}

/**
 * Re-export expect so test files have a single import.
 */
export { expect };
```

- [ ] **Step 6: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/package.json apps/web/playwright.config.ts apps/web/e2e/helpers.ts pnpm-lock.yaml && git commit -m "build(web): add Playwright + visual-regression helpers"
```

### Task A2: Snapshot auth pages (Login + Signup × 2 themes)

**Files:**
- Create: `apps/web/e2e/auth.spec.ts`

- [ ] **Step 1: Create the spec**

```typescript
// apps/web/e2e/auth.spec.ts
import { test } from '@playwright/test';
import { expect, prepareForSnapshot } from './helpers';

const themes = ['light', 'dark'] as const;

for (const theme of themes) {
  test.describe(`auth pages — ${theme}`, () => {
    test(`login page snapshot (${theme})`, async ({ page }) => {
      await prepareForSnapshot(page, theme);
      await page.goto('/login');
      await page.waitForSelector('h1:has-text("Sign in")');
      await expect(page).toHaveScreenshot(`login-${theme}.png`);
    });

    test(`signup page snapshot (${theme})`, async ({ page }) => {
      await prepareForSnapshot(page, theme);
      await page.goto('/signup');
      await page.waitForSelector('h1');
      await expect(page).toHaveScreenshot(`signup-${theme}.png`);
    });
  });
}
```

- [ ] **Step 2: Generate baselines**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e:update auth.spec.ts 2>&1 | tail -20
```

Expected: 4 tests pass, 4 baselines created in `apps/web/e2e/__snapshots__/auth.spec.ts-snapshots/`.

If anything fails: read the error carefully. Common: dev server didn't start in time → bump `webServer.timeout` in config. Or the routes aren't loading → manually `pnpm --filter @axis/web dev` and visit `/login` in a browser to confirm it works first.

- [ ] **Step 3: Re-run without --update to confirm stability**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e auth.spec.ts 2>&1 | tail -5
```

Expected: 4 passed, no diffs.

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/e2e/auth.spec.ts apps/web/e2e/__snapshots__ && git commit -m "test(web): add Playwright snapshots for auth pages (light + dark)"
```

### Task A3: Snapshot Home page (× 2 themes) + onboarding-dismissed state

**Files:**
- Create: `apps/web/e2e/home.spec.ts`

- [ ] **Step 1: Create the spec**

```typescript
// apps/web/e2e/home.spec.ts
import { test } from '@playwright/test';
import { expect, prepareForSnapshot, fakeAuthCookie, dismissOnboarding } from './helpers';

const themes = ['light', 'dark'] as const;

for (const theme of themes) {
  test.describe(`home — ${theme}`, () => {
    test(`home page snapshot (${theme})`, async ({ page, context }) => {
      await fakeAuthCookie(context);
      await dismissOnboarding(page);
      await prepareForSnapshot(page, theme);
      await page.goto('/');
      await page.waitForSelector('h1');
      await expect(page).toHaveScreenshot(`home-${theme}.png`);
    });
  });
}
```

- [ ] **Step 2: Generate baselines**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e:update home.spec.ts 2>&1 | tail -10
```

Expected: 2 tests pass, 2 baselines.

- [ ] **Step 3: Re-run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e home.spec.ts 2>&1 | tail -5
git add apps/web/e2e/home.spec.ts apps/web/e2e/__snapshots__ && git commit -m "test(web): add Playwright snapshots for Home (light + dark)"
```

### Task A4: Snapshot Chat empty state (× 2 themes)

**Files:**
- Create: `apps/web/e2e/chat.spec.ts`

- [ ] **Step 1: Create the spec**

```typescript
// apps/web/e2e/chat.spec.ts
import { test } from '@playwright/test';
import { expect, prepareForSnapshot, fakeAuthCookie } from './helpers';

const themes = ['light', 'dark'] as const;

for (const theme of themes) {
  test.describe(`chat — ${theme}`, () => {
    test(`chat empty state snapshot (${theme})`, async ({ page, context }) => {
      await fakeAuthCookie(context);
      await prepareForSnapshot(page, theme);
      await page.goto('/chat');
      // Wait for the display heading "What should Axis do?" to render
      await page.waitForSelector('h1:has-text("What should Axis do?")');
      await expect(page).toHaveScreenshot(`chat-empty-${theme}.png`);
    });
  });
}
```

- [ ] **Step 2: Generate baselines + run + commit**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e:update chat.spec.ts 2>&1 | tail -10
pnpm --filter @axis/web e2e chat.spec.ts 2>&1 | tail -5
git add apps/web/e2e/chat.spec.ts apps/web/e2e/__snapshots__ && git commit -m "test(web): add Playwright snapshots for Chat empty state"
```

---

## Phase B — Onboarding banner

### Task B1: OnboardingBanner component + mount on Home

**Files:**
- Create: `apps/web/components/home/onboarding-banner.tsx`
- Modify: `apps/web/app/(app)/page.tsx` (mount it above the existing sections)

- [ ] **Step 1: Create the banner**

```tsx
// apps/web/components/home/onboarding-banner.tsx
'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Plug, X, MessageSquare } from 'lucide-react';

const STORAGE_KEY = 'axis.onboarded';

export function OnboardingBanner() {
  const [visible, setVisible] = useState<boolean | null>(null);

  useEffect(() => {
    setVisible(window.localStorage.getItem(STORAGE_KEY) !== 'true');
  }, []);

  const dismiss = () => {
    window.localStorage.setItem(STORAGE_KEY, 'true');
    setVisible(false);
  };

  // SSR + first paint: render nothing until we know the localStorage state
  if (!visible) return null;

  return (
    <aside
      role="region"
      aria-label="Welcome to Axis"
      className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-lg border border-accent/30 bg-accent-subtle px-5 py-4"
    >
      <div className="space-y-1">
        <h2 className="font-display text-heading-2 text-ink">Welcome to Axis</h2>
        <p className="text-body-s text-ink-secondary">
          Connect a tool, then ask Axis to do something across your work.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Link
          href="/connections"
          className="inline-flex items-center gap-2 h-8 px-3 rounded-md bg-accent text-accent-on text-body-s font-medium hover:bg-accent-hover transition-colors"
        >
          <Plug size={14} aria-hidden="true" />
          Connect a tool
        </Link>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 h-8 px-3 rounded-md text-body-s text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
        >
          <MessageSquare size={14} aria-hidden="true" />
          Start a chat
        </Link>
      </div>
      <button
        type="button"
        aria-label="Dismiss welcome banner"
        onClick={dismiss}
        className="absolute top-2 right-2 inline-flex items-center justify-center h-7 w-7 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated transition-colors"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </aside>
  );
}
```

- [ ] **Step 2: Mount on Home**

Read `apps/web/app/(app)/page.tsx`. Add the import:
```tsx
import { OnboardingBanner } from '@/components/home/onboarding-banner';
```

Inside the page's outer wrapper `<div>`, add `<OnboardingBanner />` as the first child after `<header>`. Pattern:
```tsx
<header>…</header>
<OnboardingBanner />
<section …>…</section>
```

- [ ] **Step 3: Type-check + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -3 && pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mrinalraj/Documents/Axis && git add apps/web/components/home apps/web/app/\(app\)/page.tsx && git commit -m "feat(web): add OnboardingBanner on Home for first-time users"
```

- [ ] **Step 5: Update Home snapshot baseline (the banner now appears unless dismissed)**

The Home snapshot from A3 was taken with `dismissOnboarding(page)` so the banner is hidden. We don't need to re-baseline. But add a NEW snapshot test for the banner's visible state:

Add to `apps/web/e2e/home.spec.ts` (append to the existing for-loop):
```typescript
for (const theme of themes) {
  test.describe(`home onboarding — ${theme}`, () => {
    test(`home with onboarding banner (${theme})`, async ({ page, context }) => {
      await fakeAuthCookie(context);
      // intentionally skip dismissOnboarding so the banner shows
      await prepareForSnapshot(page, theme);
      await page.goto('/');
      await page.waitForSelector('h1');
      await page.waitForSelector('aside[aria-label="Welcome to Axis"]');
      await expect(page).toHaveScreenshot(`home-with-onboarding-${theme}.png`);
    });
  });
}
```

Then:
```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e:update home.spec.ts 2>&1 | tail -10
git add apps/web/e2e/home.spec.ts apps/web/e2e/__snapshots__ && git commit -m "test(web): snapshot Home with OnboardingBanner visible"
```

---

## Phase C — Verify

### Task C1: Workspace verify

- [ ] **Step 1: Vitest tests + type-check + lint + build**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10
pnpm --filter @axis/web type-check 2>&1 | tail -3
pnpm --filter @axis/design-system type-check 2>&1 | tail -3
pnpm lint 2>&1 | tail -5
pnpm --filter @axis/web build 2>&1 | tail -10
```

Expected: design-system **113** (unchanged); web **31** (Vitest unit tests unchanged; Playwright tests run separately); type-checks clean; lint clean; build green.

- [ ] **Step 2: Run the full Playwright suite**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web e2e 2>&1 | tail -15
```

Expected: **8 tests pass** (4 auth + 2 home + 2 home-with-banner — chat snapshots from A4 = 2, total **10 tests**). All snapshots match baselines.

- [ ] **Step 3: Manual smoke**

```bash
cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web dev
```

Visit `http://localhost:3001/login` → sign in → land on `/` → onboarding banner is visible. Click X → it disappears + persists (refresh confirms it stays dismissed). Toggle theme via topbar → banner re-renders with new accent color.

(No commit for smoke.)

---

## What we have at the end of this plan

- Playwright installed + configured + chromium browser available.
- 10 visual-regression baselines locked in for: Login (light, dark), Signup (light, dark), Home with onboarding (light, dark), Home dismissed (light, dark), Chat empty (light, dark).
- `pnpm e2e` runs the suite; `pnpm e2e:update` regenerates baselines on intentional UI changes.
- OnboardingBanner shows on Home for first-time users; persists dismissal in localStorage.

## What we explicitly did NOT do (handed off to Plan 9+)

- CI integration (running Playwright on every PR)
- Multi-browser snapshots (Firefox, Safari)
- Visual snapshots for the inner pages built in Plan 6 (Activity, History, Memory, Settings, Team, Connections, Projects, Admin) — easy to extend, just more tests
- Visual snapshots for interactive states (PermissionCard open, WritePreviewCard, RightPanel slides)
- Backend tier registry, undo handlers, audience counter, trust mode, Admin metrics — all Plan 9.
- Demo workspace seed (synthetic Slack/Notion/Gmail data for first-run beyond the banner).

## Self-Review

- **Spec coverage:** Plan 8 lands the artifact §8 risk #4 visual-regression suite (deferred since Phase 0) and gives first-time users the welcome surface that artifact §3a's "operations center" implies. Onboarding flow (full demo workspace per artifact §5g) is appropriately deferred to Plan 9.
- **Placeholder scan:** No "TBD" / "implement later". The "Awaiting backend" stubs in the Admin page (Plan 7) and the "Coming soon" Capabilities tab in Settings (Plan 6) are not touched here — they're explicit Plan 9 backend dependencies.
- **Type consistency:** `Theme` type imported from `@/lib/theme` is `'system' | 'light' | 'dark'`; the helpers' local `Theme = 'light' | 'dark'` is intentional (Playwright tests don't snapshot `system` since it depends on OS preference). Naming kept distinct mentally; there's no cross-file confusion since the helpers are scoped to e2e/.
- **Commands:** `pnpm --filter @axis/web e2e <spec>` only runs the named file. `pnpm --filter @axis/web e2e` (no arg) runs the whole suite. Each `git add` matches its task's file list.
