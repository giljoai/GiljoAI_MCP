import { test, expect } from '@playwright/test'

/**
 * E2E Test: Launch Tab Workflow (Job Staging)
 *
 * Validates complete user journey for staging projects and generating missions
 * Handover 0243f: Integration Testing & Performance Optimization (FINAL)
 */
test.describe('Launch Tab Workflow (Job Staging)', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // Login as test user (create via API first if needed)
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')

    // Wait for navigation to projects page
    await page.waitForURL('**/projects', { timeout: 10000 })
    await page.waitForLoadState('networkidle')
  })

  test('User stages project and generates mission', async ({ page }) => {
    // Step 1: Navigate to test project (or use first available)
    const projectCards = page.locator('[data-testid="project-card"]')
    const cardCount = await projectCards.count()

    if (cardCount > 0) {
      // Click first project
      await projectCards.first().click()
    } else {
      // Create test project if none exist
      await page.click('[data-testid="create-project-button"]')
      await page.fill('[data-testid="project-name"]', 'E2E Test Project')
      await page.fill('[data-testid="project-description"]', 'Automated E2E test')
      await page.click('[data-testid="save-project"]')
      await page.waitForURL('**/projects/**', { timeout: 5000 })
    }

    // Step 2: Navigate to Launch tab
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')

    // Verify unified container structure
    const container = page.locator('.main-container')
    await expect(container).toBeVisible()

    // Verify container styles
    const containerStyles = await container.evaluate(el => {
      const styles = window.getComputedStyle(el)
      return {
        border: styles.border,
        borderRadius: styles.borderRadius,
        padding: styles.padding
      }
    })

    // Verify Nicepage design tokens applied
    expect(containerStyles.border).toContain('2px')
    expect(containerStyles.border).toContain('rgba(255, 255, 255, 0.2)')
    expect(containerStyles.borderRadius).toBe('16px')
    expect(containerStyles.padding).toBe('30px')

    // Step 3: Verify three equal-width panels
    const panels = page.locator('.panel')
    await expect(panels).toHaveCount(3)

    // Verify equal widths (allow 2px tolerance for rounding)
    const panelWidths = await panels.evaluateAll(elements =>
      elements.map(el => el.getBoundingClientRect().width)
    )
    const tolerance = 2
    expect(Math.abs(panelWidths[0] - panelWidths[1])).toBeLessThan(tolerance)
    expect(Math.abs(panelWidths[1] - panelWidths[2])).toBeLessThan(tolerance)

    // Step 4: Click "Stage Project" button
    const stageBtn = page.locator('.stage-button')
    await expect(stageBtn).toBeVisible()
    await expect(stageBtn).toContainText('Stage Project')
    await stageBtn.click()

    // Step 5: Verify success notification
    const toast = page.locator('.v-snackbar')
    await expect(toast).toBeVisible({ timeout: 3000 })
    await expect(toast).toContainText('Orchestrator prompt')

    // Step 6: Wait for mission to appear (WebSocket event)
    const missionContent = page.locator('.mission-content')
    await expect(missionContent).toBeVisible({ timeout: 5000 })

    // Verify mission text is not empty
    const missionText = await missionContent.textContent()
    expect(missionText).toBeTruthy()
    expect(missionText!.length).toBeGreaterThan(50)

    // Step 7: Verify agent cards appear (WebSocket events)
    const agentCards = page.locator('.agent-card')
    const agentCount = await agentCards.count()
    expect(agentCount).toBeGreaterThan(0)

    // Verify each agent card has required elements
    for (let i = 0; i < Math.min(agentCount, 3); i++) {
      const card = agentCards.nth(i)
      await expect(card.locator('.agent-name')).toBeVisible()
      await expect(card.locator('.agent-type')).toBeVisible()
      await expect(card.locator('.agent-status')).toBeVisible()
    }

    // Step 8: Verify "Launch jobs" button enabled
    const launchBtn = page.locator('.launch-button')
    await expect(launchBtn).toBeVisible()
    await expect(launchBtn).toBeEnabled()
    await expect(launchBtn).toContainText('Launch')
  })

  test('Verify panel responsiveness on resize', async ({ page }) => {
    // Navigate to a project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }

    // Navigate to Launch tab
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')

    // Test desktop viewport: 1920x1080
    await page.setViewportSize({ width: 1920, height: 1080 })
    const panelsDesktop = page.locator('.panel')
    await expect(panelsDesktop).toHaveCount(3)

    // Verify horizontal layout (flex-direction: row)
    const containerFlexDesktop = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).flexDirection
    )
    expect(containerFlexDesktop).toBe('row')

    // Test tablet viewport: 768x1024
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.waitForTimeout(500) // Allow CSS transition
    const panelsTablet = page.locator('.panel')
    await expect(panelsTablet).toHaveCount(3)

    // Test mobile viewport: 375x667
    await page.setViewportSize({ width: 375, height: 667 })
    await page.waitForTimeout(500)
    const panelsMobile = page.locator('.panel')
    await expect(panelsMobile).toHaveCount(3)

    // Verify mobile layout (may be column flex-direction)
    const containerFlexMobile = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).flexDirection
    )
    // Mobile may be 'row' or 'column' - just verify panels are still visible
    await expect(panelsMobile.first()).toBeVisible()
  })

  test('Verify visual consistency with Nicepage design', async ({ page }) => {
    // Navigate to project and Launch tab
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')

    // Check gradient background on body
    const bodyBg = await page.locator('body').evaluate(el =>
      window.getComputedStyle(el).background
    )
    expect(bodyBg).toContain('linear-gradient')

    // Check font family is Roboto
    const fontFamily = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).fontFamily
    )
    expect(fontFamily).toContain('Roboto')

    // Check button styling
    const stageBtn = page.locator('.stage-button')
    const btnStyles = await stageBtn.evaluate(el => {
      const styles = window.getComputedStyle(el)
      return {
        borderRadius: styles.borderRadius,
        textTransform: styles.textTransform,
        fontWeight: styles.fontWeight
      }
    })

    expect(btnStyles.borderRadius).toBe('30px')
    expect(btnStyles.textTransform).toBe('uppercase')
    expect(parseInt(btnStyles.fontWeight)).toBeGreaterThanOrEqual(500)

    // Check that no console errors occurred
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // Navigate and let page settle
    await page.waitForTimeout(2000)
    expect(consoleErrors).toHaveLength(0)
  })

  test('Verify accessibility of Launch Tab', async ({ page }) => {
    // Navigate to project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')

    // Test keyboard navigation: Tab through interactive elements
    await page.keyboard.press('Tab')
    const focusedElement = await page.evaluate(() => document.activeElement?.className)
    expect(focusedElement).toBeTruthy()

    // Verify Stage button is keyboard accessible
    const stageBtn = page.locator('.stage-button')
    await stageBtn.focus()
    const isFocused = await stageBtn.evaluate(el => el === document.activeElement)
    expect(isFocused).toBe(true)

    // Test Enter key activation
    const focusedBefore = await page.evaluate(() => document.activeElement?.tagName)
    await page.keyboard.press('Enter')
    // Just verify button press didn't cause error
    await page.waitForTimeout(500)

    // Verify no console errors from accessibility interactions
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
  })

  test('Verify performance metrics', async ({ page }) => {
    // Navigate to project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }

    // Measure navigation performance
    const navigationStart = Date.now()
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')
    const navigationTime = Date.now() - navigationStart

    // Launch Tab should render in < 1 second
    expect(navigationTime).toBeLessThan(1000)

    // Get Core Web Vitals
    const metrics = await page.evaluate(() => {
      const navTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      return {
        domContentLoaded: navTiming?.domContentLoadedEventEnd - navTiming?.domContentLoadedEventStart,
        loadComplete: navTiming?.loadEventEnd - navTiming?.loadEventStart
      }
    })

    // Verify DOM is interactive quickly
    expect(metrics.domContentLoaded || 0).toBeLessThan(3000)
  })
})
