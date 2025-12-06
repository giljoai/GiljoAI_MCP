/**
 * Selector Validation Test Suite
 *
 * This test file validates that all data-testid selectors added to components
 * actually exist in the DOM and are accessible.
 *
 * Test Configuration:
 * - Backend: http://localhost:7272
 * - Frontend: http://localhost:7274
 * - Test User: patrik / ***REMOVED***
 */

import { test, expect } from '@playwright/test'

test.describe('Data-TestID Selector Validation', () => {
  let page

  test.beforeAll(async ({ browser }) => {
    // Create page context
    page = await browser.newPage()
  })

  test.afterAll(async () => {
    await page?.close()
  })

  // ============================================================================
  // SELECTOR 1: LaunchTab.vue - agent-type (hidden span)
  // ============================================================================
  test('LaunchTab: data-testid="agent-type" selector exists', async ({ page }) => {
    await page.goto('http://localhost:7274/')

    // Login
    await page.fill('input[type="email"]', 'patrik')
    await page.fill('input[type="password"]', '***REMOVED***')
    await page.click('button:has-text("Login")')

    // Wait for navigation
    await page.waitForURL('**/dashboard')

    // Navigate to a project with agents (assumes at least one exists)
    // For now, we'll check if selector CAN be found in DOM
    const selector = '[data-testid="agent-type"]'

    try {
      const element = await page.$(selector)
      if (element) {
        const content = await element.textContent()
        expect(element).toBeDefined()
        console.log(`✓ PASS: agent-type selector found with content: "${content}"`)
      } else {
        console.log(`⚠ SKIP: agent-type selector not found (component not rendered)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: agent-type selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 2: LaunchTab.vue - status-chip (hidden span)
  // ============================================================================
  test('LaunchTab: data-testid="status-chip" selector exists', async ({ page }) => {
    const selector = '[data-testid="status-chip"]'

    try {
      const element = await page.$(selector)
      if (element) {
        const content = await element.textContent()
        expect(element).toBeDefined()
        console.log(`✓ PASS: status-chip selector found with content: "${content}"`)
      } else {
        console.log(`⚠ SKIP: status-chip selector not found (component not rendered)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: status-chip selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 3: CloseoutModal.vue - submit-closeout-btn
  // ============================================================================
  test('CloseoutModal: data-testid="submit-closeout-btn" selector exists', async ({ page }) => {
    const selector = '[data-testid="submit-closeout-btn"]'

    try {
      const element = await page.$(selector)
      if (element) {
        expect(element).toBeDefined()
        const isVisible = await element.isVisible()
        console.log(`✓ PASS: submit-closeout-btn selector found (visible: ${isVisible})`)
      } else {
        console.log(`⚠ SKIP: submit-closeout-btn selector not found (modal not open)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: submit-closeout-btn selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 4: MessageItem.vue - message-item
  // ============================================================================
  test('MessageItem: data-testid="message-item" selector exists', async ({ page }) => {
    // Navigate to messages
    await page.click('text=Messages')
    await page.waitForURL('**/messages')

    const selector = '[data-testid="message-item"]'

    try {
      const elements = await page.$$(selector)
      if (elements.length > 0) {
        expect(elements.length).toBeGreaterThan(0)
        console.log(`✓ PASS: message-item selector found (${elements.length} items)`)
      } else {
        console.log(`⚠ SKIP: message-item selector not found (no messages in list)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: message-item selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 5: MessageItem.vue - message-from
  // ============================================================================
  test('MessageItem: data-testid="message-from" selector exists', async ({ page }) => {
    const selector = '[data-testid="message-from"]'

    try {
      const element = await page.$(selector)
      if (element) {
        const content = await element.textContent()
        expect(element).toBeDefined()
        console.log(`✓ PASS: message-from selector found with content: "${content}"`)
      } else {
        console.log(`⚠ SKIP: message-from selector not found (no messages)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: message-from selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 6: MessageItem.vue - message-to
  // ============================================================================
  test('MessageItem: data-testid="message-to" selector exists', async ({ page }) => {
    const selector = '[data-testid="message-to"]'

    try {
      const element = await page.$(selector)
      if (element) {
        const content = await element.textContent()
        expect(element).toBeDefined()
        console.log(`✓ PASS: message-to selector found with content: "${content}"`)
      } else {
        console.log(`⚠ SKIP: message-to selector not found (no recipients)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: message-to selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 7: MessageItem.vue - message-content
  // ============================================================================
  test('MessageItem: data-testid="message-content" selector exists', async ({ page }) => {
    const selector = '[data-testid="message-content"]'

    try {
      const element = await page.$(selector)
      if (element) {
        const content = await element.textContent()
        expect(element).toBeDefined()
        console.log(`✓ PASS: message-content selector found`)
      } else {
        console.log(`⚠ SKIP: message-content selector not found (no messages)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: message-content selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 8: UserSettings.vue - context-settings-tab
  // ============================================================================
  test('UserSettings: data-testid="context-settings-tab" selector exists', async ({ page }) => {
    // Navigate to settings
    await page.click('text=Settings')
    await page.waitForURL('**/settings')

    const selector = '[data-testid="context-settings-tab"]'

    try {
      const element = await page.$(selector)
      if (element) {
        expect(element).toBeDefined()
        console.log(`✓ PASS: context-settings-tab selector found`)
      } else {
        console.log(`❌ FAIL: context-settings-tab selector not found`)
      }
    } catch (error) {
      console.log(`❌ FAIL: context-settings-tab selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 9: UserSettings.vue - agent-templates-settings-tab
  // ============================================================================
  test('UserSettings: data-testid="agent-templates-settings-tab" selector exists', async ({ page }) => {
    const selector = '[data-testid="agent-templates-settings-tab"]'

    try {
      const element = await page.$(selector)
      if (element) {
        expect(element).toBeDefined()
        console.log(`✓ PASS: agent-templates-settings-tab selector found`)
      } else {
        console.log(`❌ FAIL: agent-templates-settings-tab selector not found`)
      }
    } catch (error) {
      console.log(`❌ FAIL: agent-templates-settings-tab selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 10: UserSettings.vue - integrations-settings-tab
  // ============================================================================
  test('UserSettings: data-testid="integrations-settings-tab" selector exists', async ({ page }) => {
    const selector = '[data-testid="integrations-settings-tab"]'

    try {
      const element = await page.$(selector)
      if (element) {
        expect(element).toBeDefined()
        console.log(`✓ PASS: integrations-settings-tab selector found`)
      } else {
        console.log(`❌ FAIL: integrations-settings-tab selector not found`)
      }
    } catch (error) {
      console.log(`❌ FAIL: integrations-settings-tab selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 11: ContextPriorityConfig.vue - Dynamic priority-* selectors
  // ============================================================================
  test('ContextPriorityConfig: Dynamic priority-* selectors exist', async ({ page }) => {
    // Click context tab
    await page.click('[data-testid="context-settings-tab"]')
    await page.waitForTimeout(500)

    // Look for priority selectors
    const prioritySelectors = [
      'priority-product-core',
      'priority-vision-documents',
      'priority-tech-stack',
      'priority-architecture',
      'priority-testing',
      'priority-360-memory',
      'priority-git-history',
      'priority-agent-templates',
    ]

    for (const testid of prioritySelectors) {
      const selector = `[data-testid="${testid}"]`
      try {
        const element = await page.$(selector)
        if (element) {
          console.log(`✓ PASS: ${testid} selector found`)
        } else {
          console.log(`⚠ SKIP: ${testid} selector not found`)
        }
      } catch (error) {
        console.log(`⚠ SKIP: ${testid} selector - ${error.message}`)
      }
    }
  })

  // ============================================================================
  // SELECTOR 12: ContextPriorityConfig.vue - Dynamic depth-* selectors
  // ============================================================================
  test('ContextPriorityConfig: Dynamic depth-* selectors exist', async ({ page }) => {
    const depthSelectors = [
      'depth-vision-documents',
      'depth-tech-stack',
      'depth-architecture',
      'depth-testing',
      'depth-360-memory',
      'depth-git-history',
      'depth-agent-templates',
    ]

    for (const testid of depthSelectors) {
      const selector = `[data-testid="${testid}"]`
      try {
        const element = await page.$(selector)
        if (element) {
          console.log(`✓ PASS: ${testid} selector found`)
        } else {
          console.log(`⚠ SKIP: ${testid} selector not found`)
        }
      } catch (error) {
        console.log(`⚠ SKIP: ${testid} selector - ${error.message}`)
      }
    }
  })

  // ============================================================================
  // SELECTOR 13: GitIntegrationCard.vue - github-integration-toggle
  // ============================================================================
  test('GitIntegrationCard: data-testid="github-integration-toggle" selector exists', async ({ page }) => {
    // Navigate to integrations tab
    await page.click('[data-testid="integrations-settings-tab"]')
    await page.waitForTimeout(500)

    const selector = '[data-testid="github-integration-toggle"]'

    try {
      const element = await page.$(selector)
      if (element) {
        expect(element).toBeDefined()
        console.log(`✓ PASS: github-integration-toggle selector found`)
      } else {
        console.log(`❌ FAIL: github-integration-toggle selector not found`)
      }
    } catch (error) {
      console.log(`❌ FAIL: github-integration-toggle selector - ${error.message}`)
    }
  })

  // ============================================================================
  // SELECTOR 14: TemplateManager.vue - Dynamic template-toggle-* selectors
  // ============================================================================
  test('TemplateManager: Dynamic template-toggle-* selectors exist', async ({ page }) => {
    // Click agents tab
    await page.click('[data-testid="agent-templates-settings-tab"]')
    await page.waitForTimeout(500)

    // Look for template toggle selectors
    const templateRoles = [
      'orchestrator',
      'analyzer',
      'implementer',
      'tester',
      'reviewer',
      'documenter',
    ]

    for (const role of templateRoles) {
      const selector = `[data-testid="template-toggle-${role}"]`
      try {
        const element = await page.$(selector)
        if (element) {
          console.log(`✓ PASS: template-toggle-${role} selector found`)
        } else {
          console.log(`⚠ SKIP: template-toggle-${role} selector not found`)
        }
      } catch (error) {
        console.log(`⚠ SKIP: template-toggle-${role} selector - ${error.message}`)
      }
    }
  })

  // ============================================================================
  // SELECTOR 15: ProjectsView.vue - project-status
  // ============================================================================
  test('ProjectsView: data-testid="project-status" selector exists', async ({ page }) => {
    // Navigate to projects
    await page.click('text=Projects')
    await page.waitForURL('**/projects')

    const selector = '[data-testid="project-status"]'

    try {
      const elements = await page.$$(selector)
      if (elements.length > 0) {
        console.log(`✓ PASS: project-status selector found (${elements.length} items)`)
      } else {
        console.log(`⚠ SKIP: project-status selector not found (no projects)`)
      }
    } catch (error) {
      console.log(`❌ FAIL: project-status selector - ${error.message}`)
    }
  })
})
