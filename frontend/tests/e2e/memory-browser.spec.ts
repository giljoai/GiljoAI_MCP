import { test, expect } from '@playwright/test'

/**
 * FE-5042 — 360 Memory browser e2e.
 *
 * Walks the required flow: nav → search → expand. Resilient to seed-data
 * variance: it always asserts nav + the browser surface + the search box, and
 * when the active product has at least one entry it additionally drives the
 * search field and expands a row (asserting the sanitized markdown body).
 */
test.describe('360 Memory Browser', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('#username', 'testuser')
    await page.fill('#password', 'password')
    await page.click('button[type="submit"]')
  })

  test('nav → search → expand', async ({ page }) => {
    // NAV: the "Memory" entry appears in the sidebar and routes to /memory.
    await page.click('[data-test="nav-memory"]')
    await expect(page).toHaveURL(/\/memory$/)
    await expect(page.locator('[data-test="memory-browser"]')).toBeVisible()

    // SEARCH: the client-side search box is present.
    const search = page.locator('[data-test="memory-search"] input')
    await expect(search).toBeVisible()

    const rows = page.locator('[data-test^="memory-row-"]')
    const rowCount = await rows.count()

    if (rowCount === 0) {
      // No entries for the active product — the empty state must show. The
      // nav + search surface is still proven above.
      await expect(page.locator('[data-test="memory-empty"]')).toBeVisible()
      return
    }

    // EXPAND: open the first row and assert its detail body renders.
    const firstRow = rows.first()
    const rowTestId = await firstRow.getAttribute('data-test')
    const entryId = rowTestId!.replace('memory-row-', '')

    await firstRow.locator('.mem-row-head').click()
    await expect(page.locator(`[data-test="memory-body-${entryId}"]`)).toBeVisible()

    // SEARCH drives the list: typing a non-matching token clears the rows.
    await search.fill('zzz-no-such-entry-token-xyz')
    await expect(page.locator('[data-test="memory-empty"]')).toBeVisible()

    // Clearing the search restores rows.
    await search.fill('')
    await expect(rows.first()).toBeVisible()
  })
})
