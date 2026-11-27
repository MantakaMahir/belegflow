import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const root = fileURLToPath(new URL('../../', import.meta.url));
const preview = 'http://beleg-preview.test/';
const contentTypes = {
  'index.html': 'text/html; charset=utf-8',
  'styles.css': 'text/css',
  'demo.js': 'text/javascript',
  'assets/beleg.svg': 'image/svg+xml',
  'assets/archivo-latin.woff2': 'font/woff2',
};
let output: string;

test.beforeAll(() => {
  output = mkdtempSync(join(tmpdir(), 'beleg-static-'));
  execFileSync('uv', ['run', '--no-sync', 'python', '-m', 'deploy.build_demo', '--output', output], {
    cwd: root,
  });
});

test.afterAll(() => {
  if (output) rmSync(output, { recursive: true, force: true });
});

test('the static demo works without an API, including keyboard navigation and evidence links', async ({
  context,
  page,
}) => {
  const unexpectedRequests: string[] = [];
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await context.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    const asset = url.pathname.slice(1) || 'index.html';
    if (url.origin !== new URL(preview).origin || !Object.hasOwn(contentTypes, asset)) {
      unexpectedRequests.push(url.href);
      await route.abort();
      return;
    }
    await route.fulfill({
      body: readFileSync(join(output, asset)),
      contentType: contentTypes[asset as keyof typeof contentTypes],
    });
  });

  await page.goto(preview);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('main')).toBeFocused();
  await expect(page.getByText('€1,101.50', { exact: true })).toBeVisible();
  await expect(page.getByText('Simulation with fictional data')).toBeVisible();

  await page.getByRole('button', { name: 'German translation' }).click();
  await expect(page.getByText('Bruttodividende: 1.250,00 USD')).toBeVisible();
  await page.getByRole('link', { name: 'Gross dividend: USD 1,250.00', exact: true }).click();
  await expect(page.locator('#us-dividend-line-5')).toBeFocused();
  await expect(page.locator('#us-dividend-line-5')).toHaveText('Gross dividend: USD 1,250.00');

  await page.getByRole('button', { name: /German invoice/ }).click();
  await expect(page.getByText('€2,400.00', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'German translation' })).toHaveCount(0);

  await page.getByRole('button', { name: /Incomplete receipt/ }).click();
  await expect(page.getByText('Missing information', { exact: true })).toBeVisible();
  await expect(page.getByText('Unavailable', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: /Incomplete receipt/, pressed: true })).toBeVisible();

  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 850 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    );
    await expect(page.getByText('Unavailable', { exact: true })).toBeVisible();
  }

  expect(unexpectedRequests).toEqual([]);
  expect(errors).toEqual([]);
});
