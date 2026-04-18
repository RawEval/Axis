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
    baseURL: 'http://127.0.0.1:3001',
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
    url: 'http://127.0.0.1:3001',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
