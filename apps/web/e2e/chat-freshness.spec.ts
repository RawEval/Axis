// apps/web/e2e/chat-freshness.spec.ts
//
// Phase 4 dispatch C — visual snapshot for the freshness chip + footer
// rendered in the chat answer block.
//
// Mocks the /agent/run endpoint with a synthesized RunResponse that has
// freshness_by_source populated for Notion. The chip should render green
// (synced ≤2min ago) and the answer text should appear above it.
//
// This does NOT exercise the planner/LLM — that's covered by the Phase 1
// regression test at the capability layer.

import { test } from '@playwright/test';
import { expect, prepareForSnapshot, fakeAuthCookie, dismissOnboarding } from './helpers';

const themes = ['light', 'dark'] as const;

function fakeRunResponse() {
  const now = Date.now();
  return {
    action_id: 'e2e-action-id',
    task_id: 'e2e-task-id',
    message_id: 'e2e-msg-id',
    project_id: null,
    project_scope: 'inferred',
    status: 'completed',
    output:
      "Here's what changed in your Notion today:\n\n• My recent edit (2 minutes ago)\n• Q3 Planning doc — header tweaks (12 minutes ago)",
    plan: [
      {
        step: 1,
        kind: 'tool_use',
        name: 'connector.notion.recent_activity',
        status: 'done',
        summary: 'found 2 notion events since today',
      },
    ],
    citations: [
      {
        source_type: 'notion_page_edited',
        provider: 'notion',
        ref_id: 'page-test-1',
        title: 'My recent edit',
        actor: null,
        excerpt: null,
        occurred_at: new Date(now - 2 * 60_000).toISOString(),
      },
    ],
    freshness_by_source: {
      notion: {
        source: 'notion',
        last_synced_at: new Date(now - 30_000).toISOString(),
        sync_status: 'ok',
        error_message: null,
      },
    },
    tokens_used: 142,
    latency_ms: 1830,
  };
}

for (const theme of themes) {
  test.describe(`chat freshness chip — ${theme}`, () => {
    test(`notion freshness chip renders green after answer (${theme})`, async ({ page, context }) => {
      await fakeAuthCookie(context);
      await dismissOnboarding(page);
      await prepareForSnapshot(page, theme);

      // Intercept the /agent/run POST and return the synthesized response.
      // The api wrapper calls http://localhost:8000/agent/run directly
      // (BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').
      // The wildcard prefix covers the full host+path.
      await page.route('**/agent/run', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(fakeRunResponse()),
        });
      });

      await page.goto('/chat');
      await page.waitForSelector('h1:has-text("What should Axis do?")');

      // The PromptInput component renders a <textarea>. Submit is triggered
      // by clicking the "Send" button (Cmd/Ctrl+Enter also works but clicking
      // is more reliable in headless environments with no modifier-key state).
      const promptInput = page.locator('textarea').first();
      await promptInput.fill('what happened in my Notion today?');
      await page.getByRole('button', { name: /send/i }).click();

      // Wait for the freshness chip to appear — proves the answer rendered
      // AND freshness propagated through FreshnessFooter to the chip.
      await page.waitForSelector('[data-testid="freshness-chip-notion"]', { timeout: 10_000 });

      const chip = page.getByTestId('freshness-chip-notion');
      await expect(chip).toBeVisible();
      await expect(chip).toContainText(/synced/i);

      // Snapshot the full page (matches the existing chat.spec.ts pattern).
      await expect(page).toHaveScreenshot(`chat-freshness-${theme}.png`);
    });
  });
}
