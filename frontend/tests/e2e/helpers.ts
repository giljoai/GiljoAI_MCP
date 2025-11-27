/**
 * E2E Test Helpers
 *
 * Shared utilities for Playwright E2E tests including WebSocket event handling,
 * authentication, and test data management.
 */

import { Page, expect } from '@playwright/test'

// ============================================
// CONFIGURATION
// ============================================

const API_BASE_URL = 'http://localhost:7272'

// ============================================
// AUTHENTICATION HELPERS
// ============================================

/**
 * Login as a test user
 *
 * CRITICAL: Verifies httpOnly cookie is set after successful login.
 * The backend sets 'access_token' cookie with httpOnly=true, secure=false, samesite=lax.
 *
 * @param page - Playwright page instance
 * @param email - User email (default: patrik - real user for E2E tests)
 * @param password - User password (default: ***REMOVED***)
 */
export async function loginAsTestUser(
  page: Page,
  email: string = 'patrik',
  password: string = '***REMOVED***'
): Promise<void> {
  console.log('[loginAsTestUser] Starting login process...')

  // Navigate to login page
  await page.goto('http://localhost:7274/login')
  await page.waitForLoadState('networkidle')

  const emailInput = page.locator('[data-testid="email-input"] input')
  const passwordInput = page.locator('[data-testid="password-input"] input')

  await emailInput.fill(email)
  await passwordInput.fill(password)
  await page.click('[data-testid="login-button"]')

  // Wait for post-login redirect (backend redirects to / which Vue Router handles)
  // The URL should change from /login to something else (/, /dashboard, or /projects)
  await page.waitForURL((url) => {
    const urlObj = new URL(url)
    return !urlObj.pathname.includes('/login')
  }, { timeout: 10000 })

  await page.waitForLoadState('networkidle')

  // Wait a bit more to ensure httpOnly cookie is fully set
  await page.waitForTimeout(500)

  // CRITICAL: Verify auth cookie was set by backend
  console.log('[loginAsTestUser] Verifying auth cookie was set...')
  const cookies = await page.context().cookies()
  const authCookie = cookies.find(c => c.name === 'access_token')

  if (!authCookie) {
    console.error('[loginAsTestUser] FAILED: No access_token cookie found after login!')
    console.error('[loginAsTestUser] Available cookies:', cookies.map(c => c.name))
    throw new Error('Login failed: No access_token cookie found')
  }

  console.log('[loginAsTestUser] SUCCESS: Auth cookie verified:', {
    name: authCookie.name,
    domain: authCookie.domain,
    path: authCookie.path,
    httpOnly: authCookie.httpOnly,
    sameSite: authCookie.sameSite,
    secure: authCookie.secure,
    valueLength: authCookie.value.length
  })

  console.log('[loginAsTestUser] Login successful, current URL:', page.url())
}

/**
 * Login as patrik (real user for integration tests)
 */
export async function loginAsDefaultTestUser(page: Page): Promise<void> {
  await loginAsTestUser(page, 'patrik', '***REMOVED***')
}

// ============================================
// WEBSOCKET HELPERS
// ============================================

/**
 * Wait for a specific WebSocket event to fire
 *
 * This helper listens to console messages to detect WebSocket events.
 * The frontend must log WebSocket events to console for this to work.
 *
 * @param page - Playwright page instance
 * @param eventName - WebSocket event name (e.g., 'orchestrator:prompt_generated')
 * @param timeout - Maximum wait time in milliseconds (default: 30000)
 * @returns Promise that resolves when event is detected
 *
 * @example
 * await waitForWebSocketEvent(page, 'orchestrator:prompt_generated')
 */
export async function waitForWebSocketEvent(
  page: Page,
  eventName: string,
  timeout: number = 30000
): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Timeout waiting for WebSocket event: ${eventName}`))
    }, timeout)

    // Listen for console messages that indicate WebSocket events
    const handler = (msg: any) => {
      const text = msg.text()
      // Check if the console message contains the event name
      if (text.includes(eventName) || text.includes(`event:${eventName}`)) {
        clearTimeout(timeoutId)
        page.off('console', handler)
        resolve()
      }
    }

    page.on('console', handler)
  })
}

/**
 * Wait for an agent to reach a specific status
 *
 * Works with both LaunchTab (agent cards) and JobsTab (table rows).
 *
 * @param page - Playwright page instance
 * @param agentType - Agent type identifier (e.g., 'implementer', 'tester')
 * @param status - Expected status (e.g., 'completed', 'working', 'waiting')
 * @param timeout - Maximum wait time in milliseconds (default: 60000)
 *
 * @example
 * await waitForAgentStatus(page, 'implementer', 'completed', 60000)
 */
export async function waitForAgentStatus(
  page: Page,
  agentType: string,
  status: string,
  timeout: number = 60000
): Promise<void> {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    // Try agent card first (LaunchTab)
    const agentCard = page.locator(`[data-testid="agent-card"][data-agent-type="${agentType}"]`)

    if (await agentCard.count() > 0) {
      const statusChip = agentCard.locator('[data-testid="status-chip"]')
      const currentStatus = await statusChip.textContent()

      if (currentStatus?.toLowerCase().includes(status.toLowerCase())) {
        return // Status matched!
      }
    }

    // Try agent row (JobsTab)
    const agentRow = page.locator(`[data-testid="agent-row"][data-agent-type="${agentType}"]`)

    if (await agentRow.count() > 0) {
      const statusChip = agentRow.locator('[data-testid="status-chip"]')
      const currentStatus = await statusChip.textContent()

      if (currentStatus?.toLowerCase().includes(status.toLowerCase())) {
        return // Status matched!
      }
    }

    // Wait a bit before checking again
    await page.waitForTimeout(500)
  }

  throw new Error(`Timeout waiting for agent ${agentType} to reach status ${status}`)
}

/**
 * Wait for multiple agents to complete
 *
 * @param page - Playwright page instance
 * @param agentTypes - Array of agent types to wait for
 * @param timeout - Maximum wait time in milliseconds (default: 120000)
 *
 * @example
 * await waitForMultipleAgentsComplete(page, ['implementer', 'tester', 'reviewer'])
 */
export async function waitForMultipleAgentsComplete(
  page: Page,
  agentTypes: string[],
  timeout: number = 120000
): Promise<void> {
  const promises = agentTypes.map(agentType =>
    waitForAgentStatus(page, agentType, 'completed', timeout)
  )

  await Promise.all(promises)
}

/**
 * Wait for WebSocket connection to be established
 *
 * @param page - Playwright page instance
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 */
export async function waitForWebSocketConnection(
  page: Page,
  timeout: number = 5000
): Promise<void> {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    const wsStatus = await page.evaluate(() => {
      // Check if WebSocket is connected via store or global state
      const ws = (window as any).__websocket
      return ws?.readyState === 1 // OPEN
    })

    if (wsStatus) {
      return
    }

    await page.waitForTimeout(100)
  }

  throw new Error('Timeout waiting for WebSocket connection')
}

// ============================================
// TEST DATA HELPERS
// ============================================

/**
 * Create a test project via API
 *
 * @param page - Playwright page instance
 * @param projectData - Project data (name, description)
 * @returns Project ID
 */
export async function createTestProject(
  page: Page,
  projectData: { name?: string; description?: string } = {}
): Promise<string> {
  const token = await getAuthToken(page)

  const response = await page.request.post(`${API_BASE_URL}/api/v1/projects/`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: {
      name: projectData.name || `E2E Test Project ${Date.now()}`,
      description: projectData.description || 'Automated E2E test project',
    },
  })

  if (!response.ok()) {
    throw new Error(`Failed to create test project: ${response.status()}`)
  }

  const data = await response.json()
  return data.id
}

/**
 * Delete a test project via API
 *
 * @param page - Playwright page instance
 * @param projectId - Project ID to delete
 */
export async function deleteTestProject(
  page: Page,
  projectId: string
): Promise<void> {
  const token = await getAuthToken(page)

  await page.request.delete(`${API_BASE_URL}/api/v1/projects/${projectId}/`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Create a test user via API
 *
 * @param page - Playwright page instance
 * @param userData - User data (email, password, full_name)
 * @returns User data
 */
export async function createTestUser(
  page: Page,
  userData: { email?: string; password?: string; full_name?: string } = {}
): Promise<{ email: string; password: string }> {
  const email = userData.email || `test${Date.now()}@example.com`
  const password = userData.password || 'testpassword123'
  const full_name = userData.full_name || 'Test User'

  const response = await page.request.post(`${API_BASE_URL}/api/auth/register`, {
    data: {
      email,
      password,
      full_name,
    },
  })

  if (!response.ok()) {
    throw new Error(`Failed to create test user: ${response.status()}`)
  }

  return { email, password }
}

/**
 * Get authentication token from page context
 *
 * The backend stores the JWT token in an httpOnly cookie named 'access_token'.
 * We retrieve it from the browser's cookie store instead of localStorage.
 *
 * @param page - Playwright page instance
 * @returns JWT token
 */
export async function getAuthToken(page: Page): Promise<string> {
  // Get cookies from the browser context
  const cookies = await page.context().cookies()

  // Find the access_token httpOnly cookie
  const authCookie = cookies.find(cookie => cookie.name === 'access_token')

  if (!authCookie || !authCookie.value) {
    throw new Error('No auth token found in page context (httpOnly cookie "access_token" not found)')
  }

  return authCookie.value
}

/**
 * Create agent templates via API
 *
 * @param page - Playwright page instance
 * @param templates - Array of template data
 * @returns Array of template IDs
 */
export async function createAgentTemplates(
  page: Page,
  templates: Array<{ name: string; agent_type: string; enabled?: boolean }>
): Promise<string[]> {
  const token = await getAuthToken(page)
  const ids: string[] = []

  for (const template of templates) {
    const response = await page.request.post(`${API_BASE_URL}/api/v1/agent-templates/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: {
        name: template.name,
        agent_type: template.agent_type,
        enabled: template.enabled ?? true,
      },
    })

    if (response.ok()) {
      const data = await response.json()
      ids.push(data.id)
    }
  }

  return ids
}

// ============================================
// NAVIGATION HELPERS
// ============================================

/**
 * Navigate to project detail page
 *
 * CRITICAL FIX: Preserve authentication cookies across navigation
 * httpOnly cookies can be lost during page.goto() in Playwright tests.
 * We save and restore cookies before/after navigation to ensure auth persists.
 *
 * @param page - Playwright page instance
 * @param projectId - Project ID
 */
export async function navigateToProject(
  page: Page,
  projectId: string
): Promise<void> {
  // CRITICAL: Save auth cookie before navigation
  console.log('[navigateToProject] Checking cookies before navigation...')
  const beforeCookies = await page.context().cookies()
  const authCookie = beforeCookies.find(c => c.name === 'access_token')

  if (!authCookie) {
    console.warn('[navigateToProject] WARNING: No access_token cookie found before navigation!')
    console.warn('[navigateToProject] Available cookies:', beforeCookies.map(c => c.name))
    throw new Error('No auth cookie found - user may not be logged in')
  }

  console.log('[navigateToProject] Auth cookie found:', {
    name: authCookie.name,
    domain: authCookie.domain,
    path: authCookie.path,
    httpOnly: authCookie.httpOnly,
    sameSite: authCookie.sameSite,
    secure: authCookie.secure,
    valueLength: authCookie.value.length
  })

  // CRITICAL FIX: Intercept ALL /api requests and manually add Cookie header
  // httpOnly cookies don't always propagate correctly to fetch/XHR in Playwright
  let requestCount = 0
  await page.route('**/api/**', async (route) => {
    const url = route.request().url()
    requestCount++
    const headers = route.request().headers()
    headers['Cookie'] = `access_token=${authCookie.value}`
    console.log(`[navigateToProject] Intercepted request #${requestCount}: ${url}`)

    await route.continue({ headers })
  })

  // Navigate to project
  const fullUrl = `http://localhost:7274/projects/${projectId}`
  console.log('[navigateToProject] Navigating to:', fullUrl)

  await page.goto(fullUrl, {
    waitUntil: 'domcontentloaded'
  })

  // Wait for DefaultLayout to mount and make /api/auth/me request
  console.log('[navigateToProject] Waiting for DefaultLayout auth check...')

  try {
    // Wait for /api/auth/me to complete successfully
    const authResponse = await page.waitForResponse(
      response => response.url().includes('/api/auth/me'),
      { timeout: 5000 }
    )

    console.log('[navigateToProject] /api/auth/me response:', {
      status: authResponse.status(),
      statusText: authResponse.statusText()
    })

    if (authResponse.status() !== 200) {
      throw new Error(`Auth check failed with status ${authResponse.status()}`)
    }
  } catch (error) {
    console.error('[navigateToProject] ERROR: Auth check failed:', error.message)
    throw error
  }

  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(1000)

  // Verify final URL (should not be login page)
  const finalUrl = page.url()
  console.log('[navigateToProject] Final URL after navigation:', finalUrl)

  if (finalUrl.includes('/login')) {
    throw new Error(`Navigation failed: Redirected to login page. URL: ${finalUrl}`)
  }

  // Unroute to avoid affecting subsequent requests
  await page.unroute('**/api/**')
}

/**
 * Navigate to a specific tab in project view
 *
 * Uses URL query params for navigation (e.g., ?tab=launch, ?tab=jobs)
 * because Vue Router manages tab state via query params, not just data-testid clicks.
 *
 * CRITICAL FIX: Preserve authentication cookies across navigation
 * httpOnly cookies can be lost during page.goto() in Playwright tests.
 * We save and restore cookies before/after navigation to ensure auth persists.
 *
 * @param page - Playwright page instance
 * @param tabName - Tab name (launch, jobs, message-center)
 */
export async function navigateToTab(
  page: Page,
  tabName: string
): Promise<void> {
  // CRITICAL: Save auth cookie before navigation
  console.log('[navigateToTab] Checking cookies before navigation...')
  const beforeCookies = await page.context().cookies()
  const authCookie = beforeCookies.find(c => c.name === 'access_token')

  if (!authCookie) {
    console.warn('[navigateToTab] WARNING: No access_token cookie found before navigation!')
    console.warn('[navigateToTab] Available cookies:', beforeCookies.map(c => c.name))
    throw new Error('No auth cookie found - user may not be logged in')
  }

  // CRITICAL FIX: Intercept ALL /api requests and manually add Cookie header
  // httpOnly cookies don't always propagate correctly to fetch/XHR in Playwright
  await page.route('**/api/**', async (route) => {
    const headers = route.request().headers()
    headers['Cookie'] = `access_token=${authCookie.value}`
    await route.continue({ headers })
  })

  // Get current URL
  const currentUrl = new URL(page.url())

  // Update tab query param
  currentUrl.searchParams.set('tab', tabName)

  console.log('[navigateToTab] Navigating to:', currentUrl.toString())

  // Navigate to URL with new tab param
  await page.goto(currentUrl.toString())

  // Verify final URL (should not be login page)
  const finalUrl = page.url()
  console.log('[navigateToTab] Final URL:', finalUrl)

  if (finalUrl.includes('/login')) {
    throw new Error(`Navigation to tab '${tabName}' failed: Redirected to login page. URL: ${finalUrl}`)
  }

  await page.waitForLoadState('networkidle')

  // Wait for tab content to render
  await page.waitForTimeout(500)

  // Unroute to avoid affecting subsequent requests
  await page.unroute('**/api/**')
}

/**
 * Navigate to settings page
 *
 * @param page - Playwright page instance
 * @param section - Settings section (context, integrations, etc.)
 */
export async function navigateToSettings(
  page: Page,
  section?: string
): Promise<void> {
  await page.goto('/settings')
  await page.waitForLoadState('networkidle')

  if (section) {
    await page.click(`[data-testid="${section}-settings-tab"]`)
    await page.waitForLoadState('networkidle')
  }
}

// ============================================
// ASSERTION HELPERS
// ============================================

/**
 * Assert that a toast/notification is shown with specific text
 *
 * @param page - Playwright page instance
 * @param text - Expected toast text
 * @param timeout - Maximum wait time in milliseconds (default: 3000)
 */
export async function expectToastWithText(
  page: Page,
  text: string,
  timeout: number = 3000
): Promise<void> {
  const toast = page.locator('.v-snackbar')
  await expect(toast).toBeVisible({ timeout })
  await expect(toast).toContainText(text)
}

/**
 * Assert that a status chip shows specific status
 *
 * @param page - Playwright page instance
 * @param status - Expected status text
 */
export async function expectStatusChip(
  page: Page,
  status: string
): Promise<void> {
  const statusChip = page.locator('[data-testid="status-chip"]')
  await expect(statusChip).toContainText(status)
}

/**
 * Assert that agent cards are visible
 *
 * @param page - Playwright page instance
 * @param expectedCount - Expected number of agent cards (optional)
 */
export async function expectAgentCards(
  page: Page,
  expectedCount?: number
): Promise<void> {
  const agentCards = page.locator('[data-testid="agent-card"]')

  if (expectedCount !== undefined) {
    await expect(agentCards).toHaveCount(expectedCount)
  } else {
    await expect(agentCards.first()).toBeVisible()
  }
}

// ============================================
// CLEANUP HELPERS
// ============================================

/**
 * Clean up test data (projects, users, etc.)
 *
 * @param page - Playwright page instance
 * @param resourceIds - Object containing IDs of resources to clean up
 */
export async function cleanupTestData(
  page: Page,
  resourceIds: {
    projectIds?: string[]
    userIds?: string[]
    templateIds?: string[]
  }
): Promise<void> {
  const token = await getAuthToken(page)

  // Delete projects
  if (resourceIds.projectIds) {
    for (const projectId of resourceIds.projectIds) {
      await page.request.delete(`${API_BASE_URL}/api/v1/projects/${projectId}/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {
        // Ignore errors during cleanup
      })
    }
  }

  // Delete templates
  if (resourceIds.templateIds) {
    for (const templateId of resourceIds.templateIds) {
      await page.request.delete(`${API_BASE_URL}/api/v1/agent-templates/${templateId}/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {
        // Ignore errors during cleanup
      })
    }
  }

  // Note: User deletion may require special admin permissions
}
