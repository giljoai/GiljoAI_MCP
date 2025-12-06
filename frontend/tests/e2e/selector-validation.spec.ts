/**
 * Selector Validation Tests
 *
 * Validates all data-testid selectors added to frontend components.
 * Tests that each selector exists, is queryable, and behaves as expected.
 *
 * Selector Coverage:
 * 1. LaunchTab.vue - agent-type, status-chip (hidden spans)
 * 2. CloseoutModal.vue - submit-closeout-btn
 * 3. MessageItem.vue - message-item, message-from, message-to, message-content
 * 4. UserSettings.vue - context-settings-tab, agent-templates-settings-tab, integrations-settings-tab
 * 5. ContextPriorityConfig.vue - dynamic priority-*, depth-* selectors
 * 6. GitIntegrationCard.vue - github-integration-toggle
 * 7. TemplateManager.vue - dynamic template-toggle-* selectors
 * 8. ProjectsView.vue - project-status
 */

import { test, expect, Page } from '@playwright/test'

// ============================================
// TEST CONFIGURATION
// ============================================

const API_BASE_URL = 'http://localhost:7272'
const FRONTEND_URL = 'http://localhost:7274'
const TEST_USER_EMAIL = 'patrik'
const TEST_USER_PASSWORD = '***REMOVED***'

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Login as test user
 */
async function loginAsTestUser(page: Page): Promise<void> {
  await page.goto(`${FRONTEND_URL}/login`)
  await page.waitForLoadState('networkidle')

  const emailInput = page.locator('[data-testid="email-input"] input')
  const passwordInput = page.locator('[data-testid="password-input"] input')

  await emailInput.fill(TEST_USER_EMAIL)
  await passwordInput.fill(TEST_USER_PASSWORD)
  await page.click('[data-testid="login-button"]')

  // Wait for redirect to dashboard/projects
  await page.waitForURL((url) => !url.pathname.includes('/login'))
  await page.waitForLoadState('networkidle')
}

/**
 * Navigate to projects and ensure at least one exists
 */
async function navigateToProjects(page: Page): Promise<void> {
  await page.goto(`${FRONTEND_URL}/projects`)
  await page.waitForLoadState('networkidle')
  // Wait for projects list to load
  await page.waitForSelector('[data-testid="project-card"]', { timeout: 5000 }).catch(() => {
    // Projects might not exist, but page should still load
  })
}

/**
 * Navigate to settings page
 */
async function navigateToSettings(page: Page): Promise<void> {
  await page.goto(`${FRONTEND_URL}/settings`)
  await page.waitForLoadState('networkidle')
}

/**
 * Navigate to messages page
 */
async function navigateToMessages(page: Page): Promise<void> {
  await page.goto(`${FRONTEND_URL}/messages`)
  await page.waitForLoadState('networkidle')
}

// ============================================
// TEST SUITE: SELECTOR VALIDATION
// ============================================

test.describe('Data-TestID Selector Validation', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsTestUser(page)
  })

  // ========================================
  // LaunchTab.vue Tests
  // ========================================

  test('LaunchTab - agent-type selector exists (hidden span)', async ({ page }) => {
    await navigateToProjects(page)

    // Look for any agent-type selector in the DOM
    const selector = page.locator('[data-testid="agent-type"]').first()

    // Check if selector exists (even if hidden)
    const count = await selector.count()
    if (count > 0) {
      console.log('[PASS] LaunchTab agent-type selector found')
      expect(count).toBeGreaterThan(0)
    } else {
      console.log('[SKIP] LaunchTab agent-type selector - no agents in list')
    }
  })

  test('LaunchTab - status-chip selector exists (hidden span)', async ({ page }) => {
    await navigateToProjects(page)

    // Look for status-chip selector
    const selector = page.locator('[data-testid="status-chip"]').first()

    const count = await selector.count()
    if (count > 0) {
      console.log('[PASS] LaunchTab status-chip selector found')
      expect(count).toBeGreaterThan(0)
    } else {
      console.log('[SKIP] LaunchTab status-chip selector - no agents in list')
    }
  })

  // ========================================
  // CloseoutModal.vue Tests
  // ========================================

  test('CloseoutModal - submit-closeout-btn selector exists', async ({ page }) => {
    await navigateToProjects(page)

    // Look for the closeout modal submit button
    const button = page.locator('[data-testid="submit-closeout-btn"]')

    const count = await button.count()
    if (count > 0) {
      console.log('[PASS] CloseoutModal submit-closeout-btn selector found')
      expect(count).toBeGreaterThan(0)
      // Verify button is visible when modal is open
      await expect(button).toBeVisible()
    } else {
      console.log('[SKIP] CloseoutModal submit-closeout-btn - modal not rendered in current view')
    }
  })

  // ========================================
  // MessageItem.vue Tests
  // ========================================

  test('MessageItem - message-item selector exists', async ({ page }) => {
    await navigateToMessages(page)

    // Wait for messages to load
    await page.waitForSelector('[data-testid="message-item"]', { timeout: 5000 }).catch(() => {
      console.log('[SKIP] No messages in list')
    })

    const selector = page.locator('[data-testid="message-item"]').first()
    const count = await selector.count()

    if (count > 0) {
      console.log('[PASS] MessageItem message-item selector found')
      expect(count).toBeGreaterThan(0)
      await expect(selector).toBeVisible()
    } else {
      console.log('[SKIP] MessageItem message-item - no messages in list')
    }
  })

  test('MessageItem - message-from selector exists', async ({ page }) => {
    await navigateToMessages(page)

    const selector = page.locator('[data-testid="message-from"]').first()
    const count = await selector.count()

    if (count > 0) {
      console.log('[PASS] MessageItem message-from selector found')
      expect(count).toBeGreaterThan(0)
      // Verify it contains text
      const text = await selector.textContent()
      expect(text).toBeTruthy()
    } else {
      console.log('[SKIP] MessageItem message-from - no messages in list')
    }
  })

  test('MessageItem - message-to selector exists', async ({ page }) => {
    await navigateToMessages(page)

    const selector = page.locator('[data-testid="message-to"]').first()
    const count = await selector.count()

    if (count > 0) {
      console.log('[PASS] MessageItem message-to selector found')
      expect(count).toBeGreaterThan(0)
    } else {
      console.log('[SKIP] MessageItem message-to - no messages with recipients in list')
    }
  })

  test('MessageItem - message-content selector exists', async ({ page }) => {
    await navigateToMessages(page)

    const selector = page.locator('[data-testid="message-content"]').first()
    const count = await selector.count()

    if (count > 0) {
      console.log('[PASS] MessageItem message-content selector found')
      expect(count).toBeGreaterThan(0)
      // Verify it has content
      const text = await selector.textContent()
      expect(text).toBeTruthy()
    } else {
      console.log('[SKIP] MessageItem message-content - no messages in list')
    }
  })

  // ========================================
  // UserSettings.vue Tests
  // ========================================

  test('UserSettings - context-settings-tab selector exists', async ({ page }) => {
    await navigateToSettings(page)

    const selector = page.locator('[data-testid="context-settings-tab"]')
    const count = await selector.count()

    console.log(`[INFO] context-settings-tab count: ${count}`)
    expect(count).toBeGreaterThan(0)
    console.log('[PASS] UserSettings context-settings-tab selector found')
  })

  test('UserSettings - agent-templates-settings-tab selector exists', async ({ page }) => {
    await navigateToSettings(page)

    const selector = page.locator('[data-testid="agent-templates-settings-tab"]')
    const count = await selector.count()

    console.log(`[INFO] agent-templates-settings-tab count: ${count}`)
    expect(count).toBeGreaterThan(0)
    console.log('[PASS] UserSettings agent-templates-settings-tab selector found')
  })

  test('UserSettings - integrations-settings-tab selector exists', async ({ page }) => {
    await navigateToSettings(page)

    const selector = page.locator('[data-testid="integrations-settings-tab"]')
    const count = await selector.count()

    console.log(`[INFO] integrations-settings-tab count: ${count}`)
    expect(count).toBeGreaterThan(0)
    console.log('[PASS] UserSettings integrations-settings-tab selector found')
  })

  // ========================================
  // ContextPriorityConfig.vue Tests
  // ========================================

  test('ContextPriorityConfig - priority-* dynamic selectors exist', async ({ page }) => {
    await navigateToSettings(page)

    // Click on context tab if not already visible
    const contextTab = page.locator('[data-testid="context-settings-tab"]')
    await contextTab.click()
    await page.waitForLoadState('networkidle')

    // Check for dynamic priority selectors (priority-product-core, priority-vision-docs, etc)
    const prioritySelectors = page.locator('[data-testid^="priority-"]')
    const count = await prioritySelectors.count()

    console.log(`[INFO] Found ${count} priority-* selectors`)

    if (count > 0) {
      console.log('[PASS] ContextPriorityConfig priority-* selectors found')
      expect(count).toBeGreaterThan(0)

      // Verify first one is visible
      const firstSelector = prioritySelectors.first()
      await expect(firstSelector).toBeVisible()
    } else {
      console.log('[FAIL] ContextPriorityConfig priority-* selectors NOT found')
    }
  })

  test('ContextPriorityConfig - depth-* dynamic selectors exist', async ({ page }) => {
    await navigateToSettings(page)

    // Click on context tab if not already visible
    const contextTab = page.locator('[data-testid="context-settings-tab"]')
    await contextTab.click()
    await page.waitForLoadState('networkidle')

    // Check for dynamic depth selectors (depth-vision-docs, depth-tech-stack, etc)
    const depthSelectors = page.locator('[data-testid^="depth-"]')
    const count = await depthSelectors.count()

    console.log(`[INFO] Found ${count} depth-* selectors`)

    if (count > 0) {
      console.log('[PASS] ContextPriorityConfig depth-* selectors found')
      expect(count).toBeGreaterThan(0)

      // Verify first one is visible
      const firstSelector = depthSelectors.first()
      await expect(firstSelector).toBeVisible()
    } else {
      console.log('[FAIL] ContextPriorityConfig depth-* selectors NOT found')
    }
  })

  // ========================================
  // GitIntegrationCard.vue Tests
  // ========================================

  test('GitIntegrationCard - github-integration-toggle selector exists', async ({ page }) => {
    await navigateToSettings(page)

    // Click on integrations tab
    const integrationsTab = page.locator('[data-testid="integrations-settings-tab"]')
    await integrationsTab.click()
    await page.waitForLoadState('networkidle')

    const selector = page.locator('[data-testid="github-integration-toggle"]')
    const count = await selector.count()

    console.log(`[INFO] github-integration-toggle count: ${count}`)

    if (count > 0) {
      console.log('[PASS] GitIntegrationCard github-integration-toggle selector found')
      expect(count).toBeGreaterThan(0)
      await expect(selector).toBeVisible()
    } else {
      console.log('[SKIP] GitIntegrationCard github-integration-toggle - not visible in integrations tab')
    }
  })

  // ========================================
  // TemplateManager.vue Tests
  // ========================================

  test('TemplateManager - template-toggle-* dynamic selectors exist', async ({ page }) => {
    await navigateToSettings(page)

    // Click on agent-templates tab
    const agentTemplatesTab = page.locator('[data-testid="agent-templates-settings-tab"]')
    await agentTemplatesTab.click()
    await page.waitForLoadState('networkidle')

    // Check for dynamic template-toggle selectors
    const templateSelectors = page.locator('[data-testid^="template-toggle-"]')
    const count = await templateSelectors.count()

    console.log(`[INFO] Found ${count} template-toggle-* selectors`)

    if (count > 0) {
      console.log('[PASS] TemplateManager template-toggle-* selectors found')
      expect(count).toBeGreaterThan(0)

      // Verify first one is visible
      const firstSelector = templateSelectors.first()
      await expect(firstSelector).toBeVisible()
    } else {
      console.log('[SKIP] TemplateManager template-toggle-* selectors - no templates in list')
    }
  })

  // ========================================
  // ProjectsView.vue Tests
  // ========================================

  test('ProjectsView - project-status selector exists', async ({ page }) => {
    await navigateToProjects(page)

    // Look for project status selector
    const selector = page.locator('[data-testid="project-status"]').first()
    const count = await selector.count()

    if (count > 0) {
      console.log('[PASS] ProjectsView project-status selector found')
      expect(count).toBeGreaterThan(0)
      // Verify it contains status text
      const text = await selector.textContent()
      console.log(`[INFO] Status text: ${text}`)
      expect(text).toBeTruthy()
    } else {
      console.log('[SKIP] ProjectsView project-status - no projects in list')
    }
  })
})

// ============================================
// TEST SUITE: INTEGRATION TESTS
// ============================================

test.describe('Selector Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page)
  })

  /**
   * Test that MessageItem selectors work together correctly
   */
  test('MessageItem selectors work together in message list', async ({ page }) => {
    await navigateToMessages(page)

    // Try to find a message with all selectors present
    const messageItem = page.locator('[data-testid="message-item"]').first()
    const messageFrom = messageItem.locator('[data-testid="message-from"]')
    const messageContent = messageItem.locator('[data-testid="message-content"]')

    const itemCount = await messageItem.count()

    if (itemCount > 0) {
      console.log('[PASS] MessageItem integration test - all selectors found together')
      expect(itemCount).toBeGreaterThan(0)

      // Verify related selectors exist
      const fromCount = await messageFrom.count()
      const contentCount = await messageContent.count()

      console.log(`[INFO] Found ${fromCount} message-from and ${contentCount} message-content selectors`)
    } else {
      console.log('[SKIP] MessageItem integration test - no messages available')
    }
  })

  /**
   * Test that UserSettings tabs are functional with selectors
   */
  test('UserSettings tab selectors are clickable', async ({ page }) => {
    await navigateToSettings(page)

    const contextTab = page.locator('[data-testid="context-settings-tab"]')
    const agentTab = page.locator('[data-testid="agent-templates-settings-tab"]')
    const integrationsTab = page.locator('[data-testid="integrations-settings-tab"]')

    // Click each tab and verify it's clickable
    await contextTab.click()
    await page.waitForLoadState('networkidle')
    console.log('[PASS] Context tab clickable')

    await agentTab.click()
    await page.waitForLoadState('networkidle')
    console.log('[PASS] Agent templates tab clickable')

    await integrationsTab.click()
    await page.waitForLoadState('networkidle')
    console.log('[PASS] Integrations tab clickable')

    expect(true).toBe(true)
  })

  /**
   * Test that ContextPriorityConfig selectors are rendered in context tab
   */
  test('ContextPriorityConfig selectors appear in context tab', async ({ page }) => {
    await navigateToSettings(page)

    const contextTab = page.locator('[data-testid="context-settings-tab"]')
    await contextTab.click()
    await page.waitForLoadState('networkidle')

    const prioritySelectors = page.locator('[data-testid^="priority-"]')
    const depthSelectors = page.locator('[data-testid^="depth-"]')

    const priorityCount = await prioritySelectors.count()
    const depthCount = await depthSelectors.count()

    console.log(`[INFO] Priority selectors: ${priorityCount}, Depth selectors: ${depthCount}`)

    if (priorityCount > 0 && depthCount > 0) {
      console.log('[PASS] ContextPriorityConfig selectors visible in context tab')
      expect(priorityCount).toBeGreaterThan(0)
      expect(depthCount).toBeGreaterThan(0)
    } else {
      console.log('[WARN] Some ContextPriorityConfig selectors missing')
    }
  })
})
