import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: '.venv/bin/python -m backend.tests.e2e_server',
      cwd: fileURLToPath(new URL('..', import.meta.url)),
      url: 'http://127.0.0.1:8001/api/listings',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
})
