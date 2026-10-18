import { defineConfig } from '@playwright/test';

const port = process.env.FRONTEND_PORT || '5173';
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL,
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `bun run dev -- --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
  },
});
