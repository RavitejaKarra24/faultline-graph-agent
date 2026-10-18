import { expect, test } from '@playwright/test';

// Frontend smoke coverage only. Requires the contract API and FalkorDB for live
// topology checks; the main project owns mutation and end-to-end coverage.
for (const width of [375, 768, 1440]) {
  test(`live topology stays contained at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Clarity when it breaks.',
    );
    await expect(
      page.getByRole('button', { name: 'Investigate', exact: true }),
    ).toBeEnabled();
    await expect(page.locator('.graph-node')).toHaveCount(11);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    const redis = page.getByRole('button', { name: /^Redis, degraded/ });
    await redis.scrollIntoViewIfNeeded();
    await redis.click();
    await expect(page.locator('.node-inspector')).toContainText('svc-redis');
    await page.getByRole('button', { name: 'Close node details' }).click();
    await page
      .getByRole('button', { name: 'Workspace memory', exact: true })
      .click();
    await expect(
      page.getByRole('heading', { name: 'Leave context for next time' }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Switch to dark theme' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    expect(errors).toEqual([]);
  });
}

test('connection failure offers recovery and never substitutes a graph', async ({
  page,
}) => {
  await page.route('**/api/**', (route) => route.abort('connectionfailed'));
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Graph connection needs attention' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Retry connection' }),
  ).toBeEnabled();
  await expect(
    page.getByRole('button', { name: 'Investigate', exact: true }),
  ).toBeDisabled();
  await expect(page.locator('.graph-node')).toHaveCount(0);
  await expect(
    page.getByText('No offline graph is substituted.', { exact: false }),
  ).toBeVisible();
});
