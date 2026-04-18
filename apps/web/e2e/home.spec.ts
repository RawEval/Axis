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
