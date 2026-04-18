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

const themesAgain = ['light', 'dark'] as const;

for (const theme of themesAgain) {
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
