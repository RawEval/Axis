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
    // Playwright e2e specs use a different runner — exclude them from Vitest.
    exclude: ['node_modules', 'dist', '.next', 'e2e/**'],
  },
});
