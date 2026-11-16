import { expect, test } from '@playwright/test';

test('demo review, workflow inspection, and export', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page).toHaveTitle('Beleg: German Tax Document Review');
  await expect(page.getByRole('link', { name: /Beleg: German Tax Document Review/ })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  const focusTop = await page
    .locator('.skip-link')
    .evaluate((el) => el.getBoundingClientRect().top);
  expect(focusTop).toBeGreaterThanOrEqual(0);
  expect(focusTop).toBeLessThan(68);
  await page.keyboard.press('Enter');
  await expect(page.locator('#workspace')).toBeFocused();
  await expect(page.getByRole('heading', { name: 'Document inbox' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'northstar-dividend-2025.txt' })).toBeVisible();
  await expect(page.getByText('€1,101.50', { exact: true })).toBeVisible();
  await expect(page.getByText('18 Apr 2025', { exact: true })).toBeVisible();
  await page.getByRole('heading', { name: 'Document inbox' }).click();
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Workflow', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Every step, accounted for.' })).toBeVisible();
  await expect(page.getByText('NS-2025-0418', { exact: false }).last()).toBeVisible();
  await expect(page.getByText(/5\s*\/ 7 steps complete/)).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('workflow.png'), fullPage: true });
  await page.getByRole('button', { name: 'Document inbox' }).click();
  const approve = page.getByRole('button', { name: 'Approve document' });
  if (await approve.isVisible()) {
    await page.getByLabel('Review note').fill('Verified fictional example in browser test.');
    await approve.click();
  }
  await expect(page.getByRole('link', { name: 'Export CSV' })).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export CSV' }).click();
  expect((await downloadPromise).suggestedFilename()).toBe('belegflow-record.csv');
  expect(errors).toEqual([]);
});

test('mobile document selection, validation, and setup', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Document inbox' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true });
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: width < 650 ? 844 : 900 });
    const dimensions = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      deviceWidth: document.documentElement.getBoundingClientRect().width,
      viewport: document.querySelector('meta[name="viewport"]')?.getAttribute('content'),
      largestRight: Math.max(
        ...[...document.querySelectorAll('body *')]
          .filter((element) => getComputedStyle(element).position !== 'fixed')
          .map((element) => element.getBoundingClientRect().right),
      ),
    }));
    expect(
      dimensions.documentWidth <= dimensions.innerWidth &&
        dimensions.bodyWidth <= dimensions.innerWidth &&
        dimensions.clientWidth === dimensions.innerWidth &&
        dimensions.deviceWidth === dimensions.innerWidth &&
        dimensions.largestRight <= dimensions.innerWidth,
      `No horizontal overflow at ${width}px: ${JSON.stringify(dimensions)}`,
    ).toBe(true);
    if (width === 320) {
      await page.screenshot({ path: testInfo.outputPath('mobile-320.png'), fullPage: true });
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Try a sample' }).click();
  await page.getByRole('button', { name: /Missing data, not invented data/ }).click();
  await expect(page.getByRole('heading', { name: 'travel-receipt-incomplete.txt' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve document' })).toBeDisabled();
  await page.getByRole('button', { name: 'Edit fields' }).click();
  await expect(page.getByLabel('Currency (ISO code)')).toBeVisible();
  await page.getByRole('button', { name: 'Connections & setup' }).click();
  await expect(
    page.getByRole('heading', { name: 'Your machine. Your credentials.' }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
