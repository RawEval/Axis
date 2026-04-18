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
