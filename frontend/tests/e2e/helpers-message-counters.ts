/**
 * Message Counter Test Helpers
 *
 * Specialized helpers for testing message counter functionality
 * Used by: message-counters.spec.js
 */

import { Page } from '@playwright/test'
import { getAuthToken } from './helpers'

const API_BASE_URL = 'http://localhost:7272'

/**
 * Get agent card element for message counter tests
 *
 * @param page - Playwright page instance
 * @param agentType - Agent type (e.g., 'orchestrator', 'implementer')
 * @param indexIfMultiple - If multiple agents have same type, which index to use (default: 0)
 * @returns Agent row/card locator
 */
export function getAgentCard(page: Page, agentType: string, indexIfMultiple: number = 0) {
  // Try JobsTab row first
  const rows = page.locator(`[data-testid="agent-row"][data-agent-type="${agentType}"]`)

  if (rows.count() > 0) {
    return rows.nth(indexIfMultiple)
  }

  // Fallback to LaunchTab card
  return page.locator(`[data-testid="agent-card"][data-agent-type="${agentType}"]`).nth(indexIfMultiple)
}

/**
 * Get message counter value for an agent
 *
 * @param page - Playwright page instance
 * @param agentType - Agent type
 * @param counterType - Type of counter: 'sent', 'waiting', or 'read'
 * @returns The counter value as a number
 */
export async function getMessageCounterValue(
  page: Page,
  agentType: string,
  counterType: 'sent' | 'waiting' | 'read'
): Promise<number> {
  const agent = getAgentCard(page, agentType)

  const selectorMap: Record<string, string> = {
    sent: '.messages-sent-cell .message-count',
    waiting: '.messages-waiting-cell .message-count',
    read: '.messages-read-cell .message-count'
  }

  const selector = selectorMap[counterType]
  const element = agent.locator(selector)
  const text = await element.textContent()

  return parseInt(text || '0')
}

/**
 * Create a test project via API
 *
 * @param page - Playwright page instance
 * @param name - Project name
 * @returns Project ID
 */
export async function createTestProject(page: Page, name: string): Promise<string> {
  const token = await getAuthToken(page)

  const response = await page.request.post(`${API_BASE_URL}/api/projects`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    data: {
      name: name || `Test Project ${Date.now()}`,
      description: 'E2E test project',
      tenant_key: 'e2e-test'
    }
  })

  if (!response.ok()) {
    throw new Error(`Failed to create project: ${response.status()}`)
  }

  const data = await response.json()
  return data.id
}

/**
 * Spawn test agents for a project via API
 *
 * @param page - Playwright page instance
 * @param projectId - Project ID
 * @param agentTypes - Array of agent types to spawn (e.g., ['orchestrator', 'implementer'])
 * @returns Array of spawned agent IDs
 */
export async function spawnTestAgents(
  page: Page,
  projectId: string,
  agentTypes: string[] = ['orchestrator', 'implementer', 'tester']
): Promise<string[]> {
  const token = await getAuthToken(page)
  const agentIds = []

  for (const agentType of agentTypes) {
    const response = await page.request.post(`${API_BASE_URL}/api/agent-jobs`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      data: {
        agent_type: agentType,
        project_id: projectId,
        mission: `Test mission for ${agentType}`
      }
    })

    if (response.ok()) {
      const data = await response.json()
      agentIds.push(data.job_id || data.id)
    }
  }

  return agentIds
}

/**
 * Send a message via API for testing
 *
 * @param page - Playwright page instance
 * @param projectId - Project ID
 * @param toAgents - Array of agent types or 'all' for broadcast
 * @param content - Message content
 * @param fromAgent - Sender (default: 'orchestrator')
 * @returns Message ID
 */
export async function sendTestMessage(
  page: Page,
  projectId: string,
  toAgents: string[] | string,
  content: string,
  fromAgent: string = 'orchestrator'
): Promise<string> {
  const token = await getAuthToken(page)

  const recipients = typeof toAgents === 'string' ? [toAgents] : toAgents

  const response = await page.request.post(`${API_BASE_URL}/api/messages`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    data: {
      to_agents: recipients,
      content: content,
      project_id: projectId,
      message_type: recipients.includes('all') ? 'broadcast' : 'direct',
      priority: 'normal',
      from_agent: fromAgent
    }
  })

  if (!response.ok()) {
    throw new Error(`Failed to send message: ${response.status()} ${await response.text()}`)
  }

  const data = await response.json()
  return data.id || data.message_id
}

/**
 * Wait for message counter to reach specific value
 *
 * @param page - Playwright page instance
 * @param agentType - Agent type
 * @param counterType - Type of counter: 'sent', 'waiting', or 'read'
 * @param expectedValue - Expected counter value
 * @param timeout - Max wait time in milliseconds (default: 15000)
 */
export async function waitForMessageCounter(
  page: Page,
  agentType: string,
  counterType: 'sent' | 'waiting' | 'read',
  expectedValue: number,
  timeout: number = 15000
): Promise<void> {
  const agent = getAgentCard(page, agentType)

  const selectorMap: Record<string, string> = {
    sent: '.messages-sent-cell .message-count',
    waiting: '.messages-waiting-cell .message-count',
    read: '.messages-read-cell .message-count'
  }

  const selector = selectorMap[counterType]
  const element = agent.locator(selector)

  await page.waitForFunction(
    async () => {
      const text = await element.textContent()
      const value = parseInt(text || '0')
      return value === expectedValue
    },
    { timeout }
  )
}

/**
 * Wait for message counter to reach at least a specific value
 *
 * @param page - Playwright page instance
 * @param agentType - Agent type
 * @param counterType - Type of counter: 'sent', 'waiting', or 'read'
 * @param minValue - Minimum expected counter value
 * @param timeout - Max wait time in milliseconds (default: 15000)
 */
export async function waitForMessageCounterAtLeast(
  page: Page,
  agentType: string,
  counterType: 'sent' | 'waiting' | 'read',
  minValue: number,
  timeout: number = 15000
): Promise<void> {
  const agent = getAgentCard(page, agentType)

  const selectorMap: Record<string, string> = {
    sent: '.messages-sent-cell .message-count',
    waiting: '.messages-waiting-cell .message-count',
    read: '.messages-read-cell .message-count'
  }

  const selector = selectorMap[counterType]
  const element = agent.locator(selector)

  await page.waitForFunction(
    async () => {
      const text = await element.textContent()
      const value = parseInt(text || '0')
      return value >= minValue
    },
    { timeout }
  )
}

/**
 * Get all agent counters as a snapshot
 *
 * @param page - Playwright page instance
 * @returns Object with agent types as keys and counter objects as values
 */
export async function getCounterSnapshot(
  page: Page
): Promise<Record<string, { sent: number; waiting: number; read: number }>> {
  const snapshot: Record<string, { sent: number; waiting: number; read: number }> = {}

  const allRows = page.locator('[data-testid="agent-row"]')
  const count = await allRows.count()

  for (let i = 0; i < count; i++) {
    const row = allRows.nth(i)
    const agentType = await row.getAttribute('data-agent-type')

    if (agentType) {
      const sent = parseInt((await row.locator('.messages-sent-cell .message-count').textContent()) || '0')
      const waiting = parseInt((await row.locator('.messages-waiting-cell .message-count').textContent()) || '0')
      const read = parseInt((await row.locator('.messages-read-cell .message-count').textContent()) || '0')

      snapshot[agentType] = { sent, waiting, read }
    }
  }

  return snapshot
}

/**
 * Verify counter change between two snapshots
 *
 * @param beforeSnapshot - Snapshot before action
 * @param afterSnapshot - Snapshot after action
 * @param expectedChanges - Object describing expected changes
 * @returns true if changes match expected
 */
export function verifyCounterChanges(
  beforeSnapshot: Record<string, { sent: number; waiting: number; read: number }>,
  afterSnapshot: Record<string, { sent: number; waiting: number; read: number }>,
  expectedChanges: Record<string, { sentDelta?: number; waitingDelta?: number; readDelta?: number }>
): boolean {
  for (const agentType in expectedChanges) {
    const expected = expectedChanges[agentType]
    const before = beforeSnapshot[agentType] || { sent: 0, waiting: 0, read: 0 }
    const after = afterSnapshot[agentType] || { sent: 0, waiting: 0, read: 0 }

    if (expected.sentDelta !== undefined && after.sent - before.sent !== expected.sentDelta) {
      console.error(`[verifyCounterChanges] ${agentType} sent delta mismatch: expected ${expected.sentDelta}, got ${after.sent - before.sent}`)
      return false
    }

    if (expected.waitingDelta !== undefined && after.waiting - before.waiting !== expected.waitingDelta) {
      console.error(`[verifyCounterChanges] ${agentType} waiting delta mismatch: expected ${expected.waitingDelta}, got ${after.waiting - before.waiting}`)
      return false
    }

    if (expected.readDelta !== undefined && after.read - before.read !== expected.readDelta) {
      console.error(`[verifyCounterChanges] ${agentType} read delta mismatch: expected ${expected.readDelta}, got ${after.read - before.read}`)
      return false
    }
  }

  return true
}
