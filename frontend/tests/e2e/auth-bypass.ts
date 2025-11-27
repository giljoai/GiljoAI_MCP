/**
 * Auth Bypass Helpers for E2E Tests
 *
 * These helpers provide direct JWT token authentication without going through
 * the login flow. This eliminates redirect issues and speeds up tests.
 */

import { Page } from '@playwright/test'

// Environment-based configuration for flexible deployment
const FRONTEND_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://10.1.0.164:7274'
const BACKEND_URL = process.env.PLAYWRIGHT_API_BASE_URL || 'http://10.1.0.164:7272'
const COOKIE_DOMAIN = process.env.PLAYWRIGHT_COOKIE_DOMAIN || '10.1.0.164'

/**
 * Bypass login by directly setting auth cookie with valid JWT token.
 *
 * This avoids the login flow entirely and prevents redirect issues.
 * The token is fetched via API and set directly in the browser context.
 *
 * CRITICAL: This is the recommended approach for E2E tests as it:
 * - Eliminates login page navigation (faster tests)
 * - Prevents redirect issues during navigation
 * - Allows immediate navigation to protected routes
 * - Supports token caching for better performance
 *
 * @param page - Playwright page object
 * @param token - Optional JWT token (if not provided, will fetch one)
 * @returns The JWT token (useful for caching)
 *
 * @example
 * // Fetch token on first use
 * const token = await setAuthTokenDirectly(page)
 *
 * // Reuse cached token
 * await setAuthTokenDirectly(page, token)
 */
export async function setAuthTokenDirectly(
  page: Page,
  token?: string
): Promise<string> {
  // If no token provided, get one from API
  if (!token) {
    console.log('[setAuthTokenDirectly] Fetching JWT token from API...')
    console.log('[setAuthTokenDirectly] Backend URL:', BACKEND_URL)

    const apiUrl = `${BACKEND_URL}/api/auth/login`
    const response = await page.request.post(apiUrl, {
      data: {
        username: 'patrik',
        password: '***REMOVED***'
      }
    })

    if (!response.ok()) {
      throw new Error(`Failed to get JWT token: ${response.status()}`)
    }

    // Extract token from Set-Cookie header
    const headers = response.headers()
    const setCookieHeader = headers['set-cookie']

    if (!setCookieHeader) {
      throw new Error('No Set-Cookie header found in login response')
    }

    // Parse Set-Cookie header to extract access_token value
    // Format: "access_token=<token>; HttpOnly; Path=/; SameSite=lax"
    const tokenMatch = setCookieHeader.match(/access_token=([^;]+)/)

    if (!tokenMatch) {
      throw new Error('No access_token found in Set-Cookie header')
    }

    token = tokenMatch[1]
    console.log('[setAuthTokenDirectly] JWT token fetched successfully')
  }

  // Set the auth cookie directly in browser context
  // This bypasses the login flow and allows immediate navigation to protected routes
  // CRITICAL: domain must match the hostname you're navigating to (e.g., 10.1.0.164 or localhost)
  console.log('[setAuthTokenDirectly] Setting cookie for domain:', COOKIE_DOMAIN)
  await page.context().addCookies([{
    name: 'access_token',
    value: token,
    domain: COOKIE_DOMAIN,
    path: '/',
    httpOnly: true,
    sameSite: 'Lax',
    secure: false, // Must be false for HTTP
    expires: Math.floor(Date.now() / 1000) + 86400 // 24 hours
  }])

  // Verify cookie was set
  const cookies = await page.context().cookies()
  const authCookie = cookies.find(c => c.name === 'access_token')

  if (!authCookie) {
    throw new Error('Failed to set auth cookie - cookie not found after addCookies()')
  }

  console.log('[setAuthTokenDirectly] Auth cookie set successfully:', {
    domain: authCookie.domain,
    path: authCookie.path,
    httpOnly: authCookie.httpOnly,
    sameSite: authCookie.sameSite,
    valueLength: authCookie.value.length
  })

  return token
}

/**
 * Navigate to project with pre-set authentication.
 *
 * CRITICAL: Call setAuthTokenDirectly() BEFORE using this helper.
 * This helper assumes the auth cookie is already set.
 *
 * Benefits over navigateToProject():
 * - No login redirect issues
 * - Faster navigation (no auth check wait)
 * - Direct route access
 *
 * @param page - Playwright page object
 * @param projectId - Project UUID
 * @param tab - Tab name (launch, jobs, message-center)
 *
 * @example
 * await setAuthTokenDirectly(page)
 * await navigateToProjectAuthenticated(page, projectId, 'launch')
 */
export async function navigateToProjectAuthenticated(
  page: Page,
  projectId: string,
  tab: string = 'launch'
): Promise<void> {
  // Build URL with tab query param
  const url = `${FRONTEND_URL}/projects/${projectId}?tab=${tab}`

  console.log(`[navigateToProjectAuthenticated] Navigating to ${url}`)
  console.log(`[navigateToProjectAuthenticated] URL hostname:`, new URL(url).hostname)
  console.log(`[navigateToProjectAuthenticated] Cookie domain:`, COOKIE_DOMAIN)

  // Small delay to ensure cookie is fully set in context
  await page.waitForTimeout(100)

  // Navigate directly to project page
  await page.goto(url, { waitUntil: 'domcontentloaded' })

  // Wait for navigation to complete
  await page.waitForLoadState('networkidle')

  // Small delay for any JS-based redirects to trigger
  await page.waitForTimeout(500)

  // Verify we didn't get redirected to login
  const finalUrl = page.url()
  if (finalUrl.includes('/login')) {
    // Log cookies for debugging
    const cookies = await page.context().cookies()
    const authCookie = cookies.find(c => c.name === 'access_token')
    console.error('[navigateToProjectAuthenticated] REDIRECT TO LOGIN DETECTED!')
    console.error('[navigateToProjectAuthenticated] Final URL:', finalUrl)
    console.error('[navigateToProjectAuthenticated] Expected URL:', url)
    console.error('[navigateToProjectAuthenticated] Cookie domain:', COOKIE_DOMAIN)
    console.error('[navigateToProjectAuthenticated] Navigation hostname:', new URL(url).hostname)
    console.error('[navigateToProjectAuthenticated] Auth cookie state:', authCookie ? {
      domain: authCookie.domain,
      path: authCookie.path,
      httpOnly: authCookie.httpOnly,
      value: authCookie.value.substring(0, 20) + '...'
    } : 'NOT FOUND')
    throw new Error(`Auth bypass failed - redirected to login. URL: ${finalUrl}`)
  }

  console.log(`[navigateToProjectAuthenticated] Successfully navigated to project ${projectId}, tab: ${tab}`)
}
