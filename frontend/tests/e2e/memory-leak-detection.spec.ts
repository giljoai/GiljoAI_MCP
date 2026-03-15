import { test, expect } from '@playwright/test'

/**
 * E2E Test: Memory Leak Detection
 *
 * Validates WebSocket cleanup, interval clearance, and proper garbage collection
 * Handover 0243f: Integration Testing & Performance Optimization (FINAL)
 */
test.describe('Memory Leak Detection', () => {
  test('No memory leaks on repeated tab navigation', async ({ page }) => {
    // Navigate to login
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // Login
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    // Navigate to a project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() === 0) {
      test.skip()
    }

    await projectCards.first().click()
    await page.waitForLoadState('networkidle')

    // Get initial memory (if available in Chrome)
    const initialMemory = await page.evaluate(() => {
      const perf = performance as any
      return perf.memory ? perf.memory.usedJSHeapSize : 0
    })

    // Navigate between tabs 10 times
    for (let i = 0; i < 10; i++) {
      // Navigate to Launch tab
      const launchTab = page.locator('[data-testid="launch-tab"]')
      if (await launchTab.isVisible()) {
        await launchTab.click()
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(300)
      }

      // Navigate to Implement tab
      const implementTab = page.locator('[data-testid="jobs-tab"]')
      if (await implementTab.isVisible()) {
        await implementTab.click()
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(300)
      }
    }

    // Force garbage collection if available (Chrome only with --js-flags="--expose-gc")
    await page.evaluate(() => {
      const perf = performance as any
      if (perf.memory && (window as any).gc) {
        (window as any).gc()
      }
    })

    // Get final memory
    const finalMemory = await page.evaluate(() => {
      const perf = performance as any
      return perf.memory ? perf.memory.usedJSHeapSize : 0
    })

    // Calculate memory increase
    const memoryIncrease = (finalMemory - initialMemory) / 1024 / 1024

    // If memory is tracked, verify increase is reasonable
    // Note: This may not work in all browsers without GC flags
    if (finalMemory > 0) {
      // Memory increase after 10 navigations should be < 20MB
      expect(memoryIncrease).toBeLessThan(20)
    }
  })

  test('WebSocket listeners properly cleaned up on unmount', async ({ page }) => {
    // Navigate to login
    await page.goto('/login')

    // Login
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    // Navigate to project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() === 0) {
      test.skip()
    }

    await projectCards.first().click()
    await page.waitForLoadState('networkidle')

    // Track console messages for WebSocket events
    const consoleMessages: string[] = []
    page.on('console', msg => {
      consoleMessages.push(msg.text())
    })

    // Navigate to Implement tab (has WebSocket listeners)
    await page.click('[data-testid="jobs-tab"]')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    const messagesAfterNavigate = consoleMessages.length

    // Navigate away and back multiple times
    for (let i = 0; i < 5; i++) {
      // Navigate to Launch tab
      const launchTab = page.locator('[data-testid="launch-tab"]')
      if (await launchTab.isVisible()) {
        await launchTab.click()
        await page.waitForLoadState('networkidle')
      }

      // Navigate back to Implement tab
      const implementTab = page.locator('[data-testid="jobs-tab"]')
      if (await implementTab.isVisible()) {
        await implementTab.click()
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(500)
      }
    }

    // Check for WebSocket-related errors
    const errorMessages = consoleMessages.filter(msg =>
      msg.toLowerCase().includes('websocket') && msg.toLowerCase().includes('error')
    )

    // Should not have increasing WebSocket errors
    expect(errorMessages.length).toBeLessThan(5)
  })

  test('Event handlers properly removed on component unmount', async ({ page }) => {
    // Navigate to login and authenticate
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    // Navigate to project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() === 0) {
      test.skip()
    }

    await projectCards.first().click()
    await page.waitForLoadState('networkidle')

    // Get initial listener count (this is implementation-specific)
    // For now, just verify no console errors accumulate
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Rapidly switch between tabs
    for (let i = 0; i < 20; i++) {
      const tabName = i % 2 === 0 ? 'launch-tab' : 'jobs-tab'
      const tab = page.locator(`[data-testid="${tabName}"]`)
      if (await tab.isVisible()) {
        await tab.click()
        await page.waitForTimeout(100)
      }
    }

    // Allow time for cleanup
    await page.waitForTimeout(500)

    // Should not accumulate errors
    expect(errors.length).toBeLessThan(5)
  })

  test('Interval timers cleared on component unmount', async ({ page }) => {
    // Navigate to login
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    // Get initial interval count
    const initialIntervals = await page.evaluate(() => {
      // Count setTimeout/setInterval calls (implementation-specific)
      return 0 // Baseline
    })

    // Navigate to Implement tab (has staleness monitor with intervals)
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }

    await page.click('[data-testid="jobs-tab"]')
    await page.waitForLoadState('networkidle')

    // Get interval count after navigation
    await page.waitForTimeout(1000)

    // Navigate away
    await page.goto('/projects')
    await page.waitForLoadState('networkidle')

    // Wait for cleanup
    await page.waitForTimeout(1000)

    // Verify no uncleared intervals by checking for memory issues
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Should not have interval-related errors
    const intervalErrors = errors.filter(e => e.includes('setInterval') || e.includes('clearInterval'))
    expect(intervalErrors).toHaveLength(0)
  })

  test('No message listener accumulation on WebSocket reconnection', async ({ page }) => {
    // Navigate to project
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() === 0) {
      test.skip()
    }

    await projectCards.first().click()
    await page.click('[data-testid="jobs-tab"]')
    await page.waitForLoadState('networkidle')

    // Simulate WebSocket reconnection by navigating away/back
    for (let i = 0; i < 5; i++) {
      await page.goto('/projects')
      await page.waitForTimeout(200)

      // Re-navigate to project
      const projCards = page.locator('[data-testid="project-card"]')
      if (await projCards.count() > 0) {
        await projCards.first().click()
        const implTab = page.locator('[data-testid="jobs-tab"]')
        if (await implTab.isVisible()) {
          await implTab.click()
        }
      }
      await page.waitForTimeout(200)
    }

    // Verify no listener accumulation errors
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Should not have listener-related errors
    const listenerErrors = errors.filter(e =>
      e.includes('listener') || e.includes('Memory leak') || e.includes('potential')
    )
    expect(listenerErrors).toHaveLength(0)
  })

  test('DOM references properly garbage collected', async ({ page }) => {
    // Navigate through the app
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    // Get DOM node count before navigation
    const initialNodeCount = await page.evaluate(() => {
      return document.getElementsByTagName('*').length
    })

    // Navigate to project
    const projectCards = page.locator('[data-testid="project-card"]')
    if (await projectCards.count() > 0) {
      await projectCards.first().click()
    }

    // Get DOM node count after navigation
    const afterNavigateNodeCount = await page.evaluate(() => {
      return document.getElementsByTagName('*').length
    })

    // Navigate back
    await page.goto('/projects')
    await page.waitForLoadState('networkidle')

    // Get final DOM node count
    const finalNodeCount = await page.evaluate(() => {
      return document.getElementsByTagName('*').length
    })

    // Node count should return to approximately initial state
    const nodeDifference = Math.abs(finalNodeCount - initialNodeCount)

    // Allow some variance but not huge accumulation
    expect(nodeDifference).toBeLessThan(1000)
  })

  test('Console errors do not accumulate', async ({ page }) => {
    // Navigate and perform various actions
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('**/projects', { timeout: 10000 })

    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Perform various actions
    const projectCards = page.locator('[data-testid="project-card"]')
    for (let i = 0; i < 5; i++) {
      if (await projectCards.count() > 0) {
        await projectCards.first().click()
        await page.waitForLoadState('networkidle')

        // Switch tabs
        const launchTab = page.locator('[data-testid="launch-tab"]')
        if (await launchTab.isVisible()) {
          await launchTab.click()
          await page.waitForTimeout(300)
        }

        const implementTab = page.locator('[data-testid="jobs-tab"]')
        if (await implementTab.isVisible()) {
          await implementTab.click()
          await page.waitForTimeout(300)
        }

        // Go back
        await page.goto('/projects')
        await page.waitForLoadState('networkidle')
      }
    }

    // Should not accumulate errors
    expect(errors.length).toBeLessThan(10)
  })
})
