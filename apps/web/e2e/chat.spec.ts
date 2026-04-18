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
