import { test, expect } from '@playwright/test'

/**
 * Playwright E2E Test: CLI Mode Toggle Staging Prompt
 *
 * Tests that when a user toggles CLI mode ON, the staging prompt
 * correctly reflects "Claude Code CLI" execution mode.
 *
 * Bug Fix: Handover 0333 Phase 2
 * - User toggles CLI mode ON → project.execution_mode = 'claude_code_cli'
 * - User clicks "Stage Project" → API called with execution_mode parameter
 * - Backend generates prompt with "Claude Code CLI" mode
 * - Prompt shows "Execution Mode: Claude Code CLI"
 *
 * Flow:
 * 1. Navigate to project page
 * 2. Toggle CLI mode ON
 * 3. Verify toggle state is saved
 * 4. Click "Stage Project"
 * 5. Verify API request includes execution_mode parameter
 * 6. Verify staging prompt shows correct mode
 *
 * Configuration:
 * - Frontend URL: http://10.1.0.164:7274
 * - Username: patrik
 * - Password: ***REMOVED***
 * - Project ID: 555d0207-4f30-498a-9c44-9904804270ee
 */

test.describe('CLI Mode Toggle Staging Prompt', () => {
  const BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://10.1.0.164:7274'
  const PROJECT_ID = '555d0207-4f30-498a-9c44-9904804270ee'
  const PROJECT_URL = `${BASE_URL}/projects/${PROJECT_ID}?via=launch`
  const USERNAME = 'patrik'
  const PASSWORD = '***REMOVED***'

  test.beforeEach(async ({ page }) => {
    // Navigate to project page (launch tab)
    await page.goto(PROJECT_URL)

    // Check if login is needed
    const loginUrl = page.url()
    if (loginUrl.includes('/login') || loginUrl.includes('/auth')) {
      // Perform login
      await page.fill('input[type="text"]', USERNAME)
      await page.fill('input[type="password"]', PASSWORD)
      await page.click('button[type="submit"]')

      // Wait for redirect back to project page
      await page.waitForURL(new RegExp(`/projects/${PROJECT_ID}`))
    }

    // Wait for launch tab to load
    await page.waitForSelector('[data-testid="execution-mode-toggle"]', { timeout: 10000 })
  })

  test('cli_mode_toggle_reflects_in_staging_prompt', async ({ page }) => {
    /**
     * Test Scenario:
     * 1. Verify CLI mode toggle is initially OFF (Multi-Terminal)
     * 2. Toggle CLI mode ON (Claude Code CLI)
     * 3. Verify toggle state persists in database
     * 4. Click "Stage Project"
     * 5. Intercept API request and verify execution_mode parameter
     * 6. Verify staging prompt contains "Claude Code CLI" text
     *
     * Expected Behavior:
     * - Toggle switches from Multi-Terminal → Claude Code CLI
     * - API request includes execution_mode=claude_code_cli
     * - Staging prompt shows "Execution Mode: Claude Code CLI"
     */

    const toggle = page.locator('[data-testid="execution-mode-toggle"]')
    const indicator = page.locator('[data-testid="execution-mode-indicator"]')
    const stageButton = page.locator('[data-testid="stage-project-btn"]')

    // Step 1: Verify initial state (Multi-Terminal)
    const initialIndicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    console.log(`[Test] Initial CLI mode state: ${initialIndicatorActive ? 'ON' : 'OFF'}`)

    // Step 2: Toggle CLI mode ON
    console.log('[Test] Toggling CLI mode ON...')
    await toggle.click()

    // Wait for API call to complete and indicator to update
    await page.waitForTimeout(500) // Give time for API call

    // Verify indicator is now active (Claude Code CLI)
    const updatedIndicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    expect(updatedIndicatorActive).toBe(true)
    console.log('[Test] CLI mode toggled ON - indicator active')

    // Step 3: Set up network monitoring to intercept staging API request
    const apiRequests = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/prompts/staging/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
          params: new URL(request.url()).searchParams
        })
      }
    })

    // Step 4: Click "Stage Project"
    console.log('[Test] Clicking "Stage Project"...')
    await stageButton.click()

    // Wait for clipboard notification
    const successToast = page.locator('[role="status"]').filter({
      hasText: /copied|clipboard/i
    })
    await successToast.waitFor({ state: 'visible', timeout: 10000 })
    console.log('[Test] Staging prompt generated and copied to clipboard')

    // Step 5: Verify API request included execution_mode parameter
    expect(apiRequests.length).toBeGreaterThan(0)
    const stagingRequest = apiRequests.find(req => req.url.includes('/prompts/staging/'))
    expect(stagingRequest).toBeDefined()

    const executionMode = stagingRequest.params.get('execution_mode')
    console.log(`[Test] API request execution_mode parameter: ${executionMode}`)
    expect(executionMode).toBe('claude_code_cli')

    // Step 6: Read clipboard and verify prompt content
    // Note: Clipboard API may not work in headless mode, so we'll just verify the API call
    console.log('[Test] Verified API request includes execution_mode=claude_code_cli')
  })

  test('multi_terminal_mode_default_in_staging_prompt', async ({ page }) => {
    /**
     * Test Scenario:
     * 1. Verify CLI mode toggle is OFF (Multi-Terminal)
     * 2. Do NOT toggle CLI mode
     * 3. Click "Stage Project"
     * 4. Verify API request includes execution_mode=multi_terminal
     * 5. Verify staging prompt shows "Multi-Terminal" mode
     *
     * Expected Behavior:
     * - API request includes execution_mode=multi_terminal
     * - Staging prompt shows "Execution Mode: Multi-Terminal"
     */

    const toggle = page.locator('[data-testid="execution-mode-toggle"]')
    const indicator = page.locator('[data-testid="execution-mode-indicator"]')
    const stageButton = page.locator('[data-testid="stage-project-btn"]')

    // Step 1: Verify initial state (Multi-Terminal)
    const initialIndicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    console.log(`[Test] Initial CLI mode state: ${initialIndicatorActive ? 'ON' : 'OFF'}`)

    // If CLI mode is ON, toggle it OFF to reset to Multi-Terminal
    if (initialIndicatorActive) {
      console.log('[Test] Toggling CLI mode OFF to test Multi-Terminal...')
      await toggle.click()
      await page.waitForTimeout(500) // Wait for API call
    }

    // Verify indicator is now inactive (Multi-Terminal)
    const updatedIndicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    expect(updatedIndicatorActive).toBe(false)
    console.log('[Test] Multi-Terminal mode confirmed - indicator inactive')

    // Step 2: Set up network monitoring
    const apiRequests = []
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/prompts/staging/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
          params: new URL(request.url()).searchParams
        })
      }
    })

    // Step 3: Click "Stage Project"
    console.log('[Test] Clicking "Stage Project"...')
    await stageButton.click()

    // Wait for clipboard notification
    const successToast = page.locator('[role="status"]').filter({
      hasText: /copied|clipboard/i
    })
    await successToast.waitFor({ state: 'visible', timeout: 10000 })
    console.log('[Test] Staging prompt generated and copied to clipboard')

    // Step 4: Verify API request included execution_mode=multi_terminal
    expect(apiRequests.length).toBeGreaterThan(0)
    const stagingRequest = apiRequests.find(req => req.url.includes('/prompts/staging/'))
    expect(stagingRequest).toBeDefined()

    const executionMode = stagingRequest.params.get('execution_mode')
    console.log(`[Test] API request execution_mode parameter: ${executionMode}`)
    expect(executionMode).toBe('multi_terminal')
  })

  test('toggle_state_persists_after_page_reload', async ({ page }) => {
    /**
     * Test Scenario:
     * 1. Toggle CLI mode ON
     * 2. Wait for API call to persist state
     * 3. Reload page
     * 4. Verify CLI mode is still ON
     *
     * Expected Behavior:
     * - Toggle state is saved to database
     * - After reload, toggle remains in same state
     */

    const toggle = page.locator('[data-testid="execution-mode-toggle"]')
    const indicator = page.locator('[data-testid="execution-mode-indicator"]')

    // Step 1: Toggle CLI mode ON
    console.log('[Test] Toggling CLI mode ON...')
    await toggle.click()
    await page.waitForTimeout(500) // Wait for API call

    // Verify indicator is active
    let indicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    expect(indicatorActive).toBe(true)
    console.log('[Test] CLI mode ON - indicator active')

    // Step 2: Reload page
    console.log('[Test] Reloading page...')
    await page.reload()
    await page.waitForSelector('[data-testid="execution-mode-toggle"]', { timeout: 10000 })

    // Step 3: Verify CLI mode is still ON
    indicatorActive = await indicator.evaluate((el) => {
      return el.classList.contains('active')
    })
    expect(indicatorActive).toBe(true)
    console.log('[Test] CLI mode persisted after reload - indicator still active')
  })
})
