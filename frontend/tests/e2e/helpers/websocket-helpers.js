/**
 * WebSocket Test Helpers for Playwright E2E Tests
 *
 * Provides utilities for testing WebSocket real-time updates in Playwright tests,
 * particularly for staging completion and agent spawning workflows.
 */

/**
 * Monitor WebSocket messages during a test action
 *
 * Usage:
 * ```javascript
 * const messages = await captureWebSocketMessages(page, async () => {
 *   await stageButton.click()
 * })
 * expect(messages).toContainEqual(expect.objectContaining({ event: 'project:mission_updated' }))
 * ```
 */
export async function captureWebSocketMessages(page, action, options = {}) {
  const {
    timeout = 30000,
    eventFilter = null,
  } = options

  const messages = []
  const startTime = Date.now()

  // Track WebSocket messages
  page.on('websocket', (ws) => {
    ws.on('framesent', (event) => {
      const payload = tryParseJSON(event.payload)
      if (payload) {
        messages.push({ direction: 'sent', data: payload })
      }
    })

    ws.on('framereceived', (event) => {
      const payload = tryParseJSON(event.payload)
      if (payload) {
        messages.push({ direction: 'received', data: payload })
      }
    })
  })

  // Execute the action
  await action()

  // Wait for expected messages or timeout
  const endTime = Date.now()
  const elapsedTime = endTime - startTime

  console.log(`[WebSocket Helper] Captured ${messages.length} messages in ${elapsedTime}ms`)

  return {
    messages,
    elapsedTime,
    receivedMessages: messages.filter(m => m.direction === 'received').map(m => m.data),
    sentMessages: messages.filter(m => m.direction === 'sent').map(m => m.data),
  }
}

/**
 * Wait for a specific WebSocket event
 *
 * Usage:
 * ```javascript
 * const missionEvent = await waitForWebSocketEvent(page, 'project:mission_updated', {
 *   timeout: 20000,
 *   projectId: projectId
 * })
 * ```
 */
export async function waitForWebSocketEvent(page, eventName, options = {}) {
  const {
    timeout = 30000,
    projectId = null,
    tenantKey = null,
  } = options

  const startTime = Date.now()
  const foundEvent = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      page.off('websocket', wsHandler)
      reject(new Error(`Timeout waiting for WebSocket event: ${eventName}`))
    }, timeout)

    const wsHandler = (ws) => {
      ws.on('framereceived', (event) => {
        const payload = tryParseJSON(event.payload)
        if (!payload) return

        // Check if this matches our event
        const eventType = payload.event || payload.type
        if (eventType === eventName) {
          // Apply optional filters
          let matches = true

          if (projectId && payload.project_id !== projectId) {
            matches = false
          }

          if (tenantKey && payload.tenant_key !== tenantKey) {
            matches = false
          }

          if (matches) {
            clearTimeout(timer)
            page.off('websocket', wsHandler)
            const elapsedTime = Date.now() - startTime
            resolve({
              event: payload,
              elapsedTime,
              message: `Received ${eventName} after ${elapsedTime}ms`
            })
          }
        }
      })
    }

    page.on('websocket', wsHandler)
  })

  return foundEvent
}

/**
 * Verify button state changed in response to WebSocket events
 *
 * Usage:
 * ```javascript
 * await verifyButtonStateChange(page, {
 *   selector: '[data-testid="launch-jobs-btn"]',
 *   expectedStates: { disabled: false },
 *   waitForEvent: 'project:mission_updated',
 *   timeout: 30000
 * })
 * ```
 */
export async function verifyButtonStateChange(page, options = {}) {
  const {
    selector,
    expectedStates = {},
    waitForEvent = null,
    timeout = 30000,
  } = options

  const button = page.locator(selector)

  // Record initial state
  const initialState = {
    disabled: await button.isDisabled(),
    text: await button.textContent(),
    visible: await button.isVisible(),
  }

  console.log(`[Button Helper] Initial state:`, initialState)

  // If waiting for WebSocket event, wait for it
  if (waitForEvent) {
    try {
      const result = await waitForWebSocketEvent(page, waitForEvent, { timeout })
      console.log(`[Button Helper] Event received:`, result.message)
    } catch (err) {
      console.warn(`[Button Helper] Event not received:`, err.message)
    }
  }

  // Wait for expected state
  let finalState = initialState
  const maxAttempts = Math.ceil(timeout / 100)
  let attempts = 0

  while (attempts < maxAttempts) {
    finalState = {
      disabled: await button.isDisabled(),
      text: await button.textContent(),
      visible: await button.isVisible(),
      color: await button.evaluate((el) => {
        const classes = el.className
        if (classes.includes('yellow')) return 'yellow'
        if (classes.includes('grey')) return 'grey'
        return 'unknown'
      }),
    }

    // Check if we've reached expected state
    let stateMatches = true
    for (const [key, expectedValue] of Object.entries(expectedStates)) {
      if (finalState[key] !== expectedValue) {
        stateMatches = false
        break
      }
    }

    if (stateMatches) {
      console.log(`[Button Helper] Expected state reached:`, finalState)
      return {
        success: true,
        initialState,
        finalState,
        message: 'Button state changed as expected',
      }
    }

    attempts++
    await page.waitForTimeout(100)
  }

  console.log(`[Button Helper] Timeout waiting for state:`, {
    expected: expectedStates,
    actual: finalState,
  })

  return {
    success: false,
    initialState,
    finalState,
    message: 'Timeout waiting for button state change',
  }
}

/**
 * Monitor store state changes via page.evaluate
 *
 * Usage:
 * ```javascript
 * const storeState = await captureStoreState(page)
 * expect(storeState.readyToLaunch).toBe(true)
 * expect(storeState.agentCount).toBeGreaterThan(0)
 * ```
 */
export async function captureStoreState(page) {
  return await page.evaluate(() => {
    // This assumes Pinia store is available as window.$pinia or similar
    // Adjust based on your app's store setup
    const state = window.__NUXT__?.$store || {}

    return {
      readyToLaunch: state.readyToLaunch || false,
      orchestratorMission: state.orchestratorMission || null,
      agentCount: (state.agents || []).length,
      isStaging: state.isStaging || false,
      agents: (state.agents || []).map(a => ({
        id: a.id || a.job_id,
        type: a.agent_type,
        status: a.status,
      })),
      timestamp: new Date().toISOString(),
    }
  }).catch(() => ({
    error: 'Could not access store - may not be initialized',
    timestamp: new Date().toISOString(),
  }))
}

/**
 * Safe JSON parse with null return on failure
 */
function tryParseJSON(str) {
  try {
    return JSON.parse(str)
  } catch (e) {
    return null
  }
}

/**
 * Retry a test action with exponential backoff
 *
 * Usage:
 * ```javascript
 * await retryAsync(async () => {
 *   await stageButton.click()
 *   await expect(launchButton).toBeEnabled()
 * }, { maxAttempts: 3, backoff: 1000 })
 * ```
 */
export async function retryAsync(action, options = {}) {
  const {
    maxAttempts = 3,
    backoff = 1000, // ms
    backoffMultiplier = 2,
  } = options

  let lastError
  let waitTime = backoff

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      console.log(`[Retry Helper] Attempt ${attempt}/${maxAttempts}`)
      await action()
      console.log(`[Retry Helper] Success on attempt ${attempt}`)
      return { success: true, attempt }
    } catch (error) {
      lastError = error
      console.warn(`[Retry Helper] Attempt ${attempt} failed:`, error.message)

      if (attempt < maxAttempts) {
        console.log(`[Retry Helper] Retrying in ${waitTime}ms...`)
        await new Promise(resolve => setTimeout(resolve, waitTime))
        waitTime *= backoffMultiplier
      }
    }
  }

  throw new Error(`All ${maxAttempts} attempts failed. Last error: ${lastError.message}`)
}

/**
 * Compare initial and final UI states
 *
 * Usage:
 * ```javascript
 * const stateChange = compareStates(
 *   { disabled: true, color: 'grey' },
 *   { disabled: false, color: 'yellow' }
 * )
 * console.log(stateChange.changed) // true
 * console.log(stateChange.changes) // { disabled: [true, false], color: ['grey', 'yellow'] }
 * ```
 */
export function compareStates(initialState, finalState) {
  const changes = {}
  let changed = false

  for (const key in finalState) {
    if (initialState[key] !== finalState[key]) {
      changes[key] = [initialState[key], finalState[key]]
      changed = true
    }
  }

  return {
    changed,
    changes,
    initialState,
    finalState,
  }
}

/**
 * Log test progress with timestamps
 *
 * Usage:
 * ```javascript
 * const testLog = new TestLogger()
 * testLog.info('Starting test')
 * testLog.info('Clicking button')
 * console.log(testLog.getLog())
 * ```
 */
export class TestLogger {
  constructor() {
    this.logs = []
    this.startTime = Date.now()
  }

  info(message) {
    const elapsed = Date.now() - this.startTime
    this.logs.push({ level: 'INFO', message, elapsed })
    console.log(`[+${elapsed}ms] ${message}`)
  }

  warn(message) {
    const elapsed = Date.now() - this.startTime
    this.logs.push({ level: 'WARN', message, elapsed })
    console.warn(`[+${elapsed}ms] ${message}`)
  }

  error(message) {
    const elapsed = Date.now() - this.startTime
    this.logs.push({ level: 'ERROR', message, elapsed })
    console.error(`[+${elapsed}ms] ${message}`)
  }

  getLog() {
    return this.logs
  }

  summary() {
    const totalTime = Date.now() - this.startTime
    return {
      totalTime,
      entries: this.logs.length,
      logs: this.logs
    }
  }
}
