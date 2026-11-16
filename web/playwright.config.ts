import { defineConfig } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const testDataDir = join(tmpdir(), `belegflow-e2e-${randomUUID()}`);

export default defineConfig({
  testDir: './tests',
  workers: 1,
  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:8019',
    reducedMotion: 'reduce',
    screenshot: 'only-on-failure',
    viewport: { width: 1440, height: 1000 },
  },
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: 'uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8019',
        cwd: '..',
        url: 'http://127.0.0.1:8019/api/health',
        env: { DATA_DIR: testDataDir, OPENAI_API_KEY: '', SEED_DEMO: 'true' },
        reuseExistingServer: !process.env.CI,
        timeout: 60000,
      },
});
