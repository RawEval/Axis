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
 *
 * Uses `url` instead of `domain` because chromium drops cookies with
 * `domain: 'localhost'` on outbound requests (a known Chromium quirk
 * around localhost cookie scoping). The `url` form lets the browser
 * derive the right scope from the request URL.
 */
export async function fakeAuthCookie(context: BrowserContext): Promise<void> {
  await context.addCookies([
    {
      name: 'axis.token',
      value: 'e2e-test-token',
      url: 'http://127.0.0.1:3001',
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
