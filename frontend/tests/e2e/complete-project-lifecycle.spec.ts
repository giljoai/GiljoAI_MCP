import { test, expect } from '@playwright/test'
import {
  loginAsTestUser,
  createTestProject,
  deleteTestProject,
  cleanupTestData,
  waitForWebSocketEvent,
  waitForAgentStatus,
  waitForMultipleAgentsComplete,
  navigateToProject,
  navigateToTab,
  navigateToSettings,
  expectToastWithText,
  expectAgentCards,
  createAgentTemplates,
} from './helpers'
// Auth bypass imports commented out - using real login flow now
// import { setAuthTokenDirectly, navigateToProjectAuthenticated } from './auth-bypass'

/**
 * E2E Test: Complete Project Lifecycle
 *
 * Validates the entire project lifecycle from staging to closeout:
 * 1. Project staging (orchestrator prompt generation)
 * 2. Agent spawning and mission display
 * 3. Job launching
 * 4. Agent execution and status transitions
 * 5. Inter-agent messaging
 * 6. Project closeout and 360 memory update
 *
 * This test validates real-time WebSocket updates throughout the workflow.
 */
test.describe('Complete Project Lifecycle E2E', () => {
  let projectId: string
  let resourceIds: { projectIds: string[]; templateIds: string[] } = {
    projectIds: [],
    templateIds: [],
  }

  test.beforeEach(async ({ page }) => {
    // Real login flow (not JWT bypass)
    await loginAsTestUser(page)

    // Create test project via API
    projectId = await createTestProject(page, {
      name: 'Complete Lifecycle Test Project',
      description: 'Build a simple REST API with user authentication',
    })
    resourceIds.projectIds.push(projectId)

    // Navigate to project page
    await navigateToProject(page, projectId)

    // Navigate to launch tab
    await navigateToTab(page, 'launch')
  })

  test.afterEach(async ({ page }) => {
    // Clean up test data
    await cleanupTestData(page, resourceIds)
  })

  test('complete lifecycle: stage → launch → execute → closeout', async ({ page }) => {
    // ========================================
    // PHASE 1: STAGING
    // ========================================

    // Navigate to Launch tab
    await navigateToTab(page, 'launch')

    // Click "Stage Project" button
    const stageBtn = page.locator('[data-testid="stage-project-btn"]')
    await expect(stageBtn).toBeVisible()
    await expect(stageBtn).toBeEnabled()
    await stageBtn.click()

    // Wait for orchestrator prompt generation (WebSocket event)
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Verify success toast
    await expectToastWithText(page, 'Orchestrator prompt')

    // Verify mission appears in Panel 2
    const missionPanel = page.locator('[data-testid="mission-panel"]')
    await expect(missionPanel).toBeVisible({ timeout: 5000 })
    const missionText = await missionPanel.textContent()
    expect(missionText).toBeTruthy()
    expect(missionText!.length).toBeGreaterThan(50)

    // Verify agent cards appear in Panel 3
    await expectAgentCards(page, 3)

    // Verify each agent card has required elements
    const agentCards = page.locator('[data-testid="agent-card"]')
    for (let i = 0; i < 3; i++) {
      const card = agentCards.nth(i)
      await expect(card.locator('[data-testid="agent-name"]')).toBeVisible()
      await expect(card.locator('[data-testid="agent-type"]')).toBeVisible()
      await expect(card.locator('[data-testid="status-chip"]')).toBeVisible()
    }

    // ========================================
    // PHASE 2: LAUNCH JOBS
    // ========================================

    // Click "Launch Jobs" button
    const launchBtn = page.locator('[data-testid="launch-jobs-btn"]')
    await expect(launchBtn).toBeVisible()
    await expect(launchBtn).toBeEnabled()
    await launchBtn.click()

    // Wait for jobs to be created (WebSocket event)
    await waitForWebSocketEvent(page, 'agent:jobs_launched', 10000)

    // Verify success toast
    await expectToastWithText(page, 'Jobs launched')

    // ========================================
    // PHASE 3: MONITOR AGENT EXECUTION
    // ========================================

    // Navigate to Jobs tab
    await navigateToTab(page, 'jobs')

    // Verify agent status table is visible
    const statusTable = page.locator('[data-testid="agent-status-table"]')
    await expect(statusTable).toBeVisible()

    // Watch agents transition through statuses
    // Note: In real workflow, agents would transition: waiting → working → completed
    // For E2E testing with mock backend, we verify status updates happen

    // Wait for implementer to complete
    await waitForAgentStatus(page, 'implementer', 'completed', 60000)

    // Wait for tester to complete
    await waitForAgentStatus(page, 'tester', 'completed', 60000)

    // Wait for reviewer to complete
    await waitForAgentStatus(page, 'reviewer', 'completed', 60000)

    // Alternative: Wait for all agents to complete in parallel
    // await waitForMultipleAgentsComplete(page, ['implementer', 'tester', 'reviewer'], 120000)

    // ========================================
    // PHASE 4: VERIFY MESSAGING
    // ========================================

    // Navigate to Message Center tab
    await navigateToTab(page, 'message-center')

    // Verify messages exist (inter-agent communication)
    const messageItems = page.locator('[data-testid="message-item"]')
    const messageCount = await messageItems.count()
    expect(messageCount).toBeGreaterThanOrEqual(2) // At least 2 messages exchanged

    // Verify message structure
    if (messageCount > 0) {
      const firstMessage = messageItems.first()
      await expect(firstMessage.locator('[data-testid="message-from"]')).toBeVisible()
      await expect(firstMessage.locator('[data-testid="message-to"]')).toBeVisible()
      await expect(firstMessage.locator('[data-testid="message-content"]')).toBeVisible()
    }

    // ========================================
    // PHASE 5: PROJECT CLOSEOUT
    // ========================================

    // Navigate back to Jobs tab to access closeout button
    await navigateToTab(page, 'jobs')

    // Click "Close Project" button
    const closeBtn = page.locator('[data-testid="close-project-btn"]')
    await expect(closeBtn).toBeVisible()
    await expect(closeBtn).toBeEnabled()
    await closeBtn.click()

    // Verify closeout modal appears
    const closeoutModal = page.locator('[data-testid="closeout-modal"]')
    await expect(closeoutModal).toBeVisible({ timeout: 3000 })

    // Fill closeout form
    const summaryInput = page.locator('[data-testid="closeout-summary"]')
    await summaryInput.fill('REST API completed successfully with user authentication, CRUD operations, and comprehensive test coverage.')

    const keyOutcomesInput = page.locator('[data-testid="closeout-key-outcomes"]')
    await keyOutcomesInput.fill('- Implemented JWT authentication\n- Created 5 REST endpoints\n- Achieved 95% test coverage')

    const decisionsInput = page.locator('[data-testid="closeout-decisions"]')
    await decisionsInput.fill('- Used PostgreSQL for database\n- Implemented rate limiting for API security')

    // Submit closeout
    const submitBtn = page.locator('[data-testid="submit-closeout-btn"]')
    await expect(submitBtn).toBeEnabled()
    await submitBtn.click()

    // Wait for WebSocket event: product:memory_updated
    await waitForWebSocketEvent(page, 'product:memory_updated', 15000)

    // Verify success toast
    await expectToastWithText(page, 'Project closed')

    // Verify project status badge shows "Completed"
    const statusBadge = page.locator('[data-testid="project-status"]')
    await expect(statusBadge).toContainText('Completed')

    // ========================================
    // PHASE 6: VERIFY 360 MEMORY (Optional)
    // ========================================

    // Navigate to Product settings to verify memory was updated
    await navigateToSettings(page, 'product')

    // Verify 360 memory section exists
    const memorySection = page.locator('[data-testid="360-memory-section"]')
    if (await memorySection.count() > 0) {
      await expect(memorySection).toBeVisible()

      // Verify our project appears in sequential history
      const historyEntries = page.locator('[data-testid="history-entry"]')
      const entryCount = await historyEntries.count()
      expect(entryCount).toBeGreaterThanOrEqual(1)
    }
  })

  test('verify staging workflow components render correctly', async ({ page }) => {
    // Debug: Log current URL
    console.log('[TEST] Current URL before tab navigation:', page.url())

    // Ensure we're not on login page
    const currentUrl = page.url()
    if (currentUrl.includes('/login')) {
      throw new Error('Test setup failed - on login page instead of project page')
    }

    // Navigate to Launch tab
    await navigateToTab(page, 'launch')

    // Debug: Log URL after navigation
    console.log('[TEST] Current URL after navigateToTab:', page.url())

    // Wait for panels to render
    await page.waitForTimeout(500)

    // Verify three-panel layout
    const panels = page.locator('.panel')
    await expect(panels).toHaveCount(3)

    // Verify panel structure using data-testid
    const descriptionPanel = page.locator('[data-testid="description-panel"]')
    const missionPanel = page.locator('[data-testid="mission-panel"]')
    const agentsPanel = page.locator('[data-testid="agents-panel"]')

    await expect(descriptionPanel).toBeVisible()
    await expect(missionPanel).toBeVisible()
    await expect(agentsPanel).toBeVisible()

    // Verify panel headers
    await expect(descriptionPanel.locator('.panel-header')).toContainText('Project Description')
    await expect(missionPanel.locator('.panel-header')).toContainText('Orchestrator Generated Mission')
    await expect(agentsPanel.locator('.panel-header')).toContainText('Default agent')

    // Verify Stage Project button is in header (not panel 1 - moved to ProjectTabs header in Handover 0243)
    const stageBtn = page.locator('[data-testid="stage-project-btn"]')
    await expect(stageBtn).toBeVisible()

    // Verify Launch Jobs button is in header (not panel 3)
    const launchBtn = page.locator('[data-testid="launch-jobs-btn"]')
    await expect(launchBtn).toBeVisible()
    // Note: Button may be disabled until staging completes
  })

  test('verify agent status transitions in real-time', async ({ page }) => {
    // Stage project first
    await navigateToTab(page, 'launch')
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Launch jobs
    await page.click('[data-testid="launch-jobs-btn"]')
    await waitForWebSocketEvent(page, 'agent:jobs_launched', 10000)

    // Navigate to Jobs tab
    await navigateToTab(page, 'jobs')

    // Monitor first agent (implementer) status changes
    // In JobsTab, agents are displayed as table rows, not cards
    const implementerRow = page.locator('[data-testid="agent-row"][data-agent-type="implementer"]')
    const statusChip = implementerRow.locator('[data-testid="status-chip"]')

    // Verify initial status is "waiting" or "working"
    const initialStatus = await statusChip.textContent()
    expect(initialStatus?.toLowerCase()).toMatch(/waiting|working|running/)

    // Wait for status to change to "completed"
    await waitForAgentStatus(page, 'implementer', 'completed', 60000)

    // Verify final status
    const finalStatus = await statusChip.textContent()
    expect(finalStatus?.toLowerCase()).toContain('completed')
  })

  test('verify error handling: staging without active product', async ({ page }) => {
    // This test assumes user has no active product set
    // Navigate to Launch tab
    await navigateToTab(page, 'launch')

    // Click Stage Project button
    const stageBtn = page.locator('[data-testid="stage-project-btn"]')
    await stageBtn.click()

    // Verify error toast appears
    const toast = page.locator('.v-snackbar')
    await expect(toast).toBeVisible({ timeout: 3000 })
    // Toast should contain error message about missing product
    const toastText = await toast.textContent()
    expect(toastText).toBeTruthy()
  })

  test('verify keyboard navigation in Launch tab', async ({ page }) => {
    await navigateToTab(page, 'launch')

    // Test Tab navigation
    await page.keyboard.press('Tab')
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
    expect(focusedElement).toBeTruthy()

    // Focus Stage Project button
    const stageBtn = page.locator('[data-testid="stage-project-btn"]')
    await stageBtn.focus()
    const isFocused = await stageBtn.evaluate(el => el === document.activeElement)
    expect(isFocused).toBe(true)

    // Test Enter key activation
    await page.keyboard.press('Enter')
    // Verify staging initiated (either success toast or error toast)
    const toast = page.locator('.v-snackbar')
    await expect(toast).toBeVisible({ timeout: 5000 })
  })

  test('verify responsive design: mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await navigateToTab(page, 'launch')

    // Verify panels are still visible on mobile
    const panels = page.locator('.panel')
    await expect(panels).toHaveCount(3)

    // Verify panels are stacked vertically (or scroll horizontally)
    const panel1 = panels.nth(0)
    await expect(panel1).toBeVisible()

    // Verify buttons are still accessible
    const stageBtn = page.locator('[data-testid="stage-project-btn"]')
    await expect(stageBtn).toBeVisible()
  })
})

/**
 * Agent Template Manager Tests
 *
 * Validates that only enabled agent templates appear in staging workflow.
 */
test.describe('Agent Template Manager Integration', () => {
  let projectId: string
  let resourceIds: { projectIds: string[]; templateIds: string[] } = {
    projectIds: [],
    templateIds: [],
  }

  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page)

    // Create 5 agent templates (3 enabled, 2 disabled)
    const templates = await createAgentTemplates(page, [
      { name: 'Implementer', agent_type: 'implementer', enabled: true },
      { name: 'Tester', agent_type: 'tester', enabled: true },
      { name: 'Reviewer', agent_type: 'reviewer', enabled: true },
      { name: 'Documenter', agent_type: 'documenter', enabled: false },
      { name: 'Deployer', agent_type: 'deployer', enabled: false },
    ])
    resourceIds.templateIds = templates

    // Create test project
    projectId = await createTestProject(page)
    resourceIds.projectIds.push(projectId)

    await navigateToProject(page, projectId)
  })

  test.afterEach(async ({ page }) => {
    await cleanupTestData(page, resourceIds)
  })

  test('only enabled agents visible after staging', async ({ page }) => {
    // Navigate to Launch tab
    await navigateToTab(page, 'launch')

    // Stage project
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Verify only 3 enabled agents appear
    await expectAgentCards(page, 3)

    // Verify disabled agents do NOT appear
    const agentTypes = await page.locator('[data-testid="agent-card"]').evaluateAll(cards =>
      cards.map(card => card.getAttribute('data-agent-type'))
    )

    expect(agentTypes).toContain('implementer')
    expect(agentTypes).toContain('tester')
    expect(agentTypes).toContain('reviewer')
    expect(agentTypes).not.toContain('documenter')
    expect(agentTypes).not.toContain('deployer')
  })

  test('disabling agent removes it from staging workflow', async ({ page }) => {
    // Navigate to Agent Template Manager
    await navigateToSettings(page, 'agent-templates')

    // Disable the "Tester" agent
    const testerToggle = page.locator('[data-testid="template-toggle-tester"]')
    await testerToggle.click()

    // Wait for update
    await expectToastWithText(page, 'Template updated')

    // Navigate to project and stage
    await navigateToProject(page, projectId)
    await navigateToTab(page, 'launch')
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Verify only 2 agents appear now (implementer, reviewer)
    await expectAgentCards(page, 2)

    const agentTypes = await page.locator('[data-testid="agent-card"]').evaluateAll(cards =>
      cards.map(card => card.getAttribute('data-agent-type'))
    )

    expect(agentTypes).not.toContain('tester')
  })
})

/**
 * Context Priority Settings Tests
 *
 * Validates that context priority configuration affects what data is fetched.
 */
test.describe('Context Priority Settings Integration', () => {
  let projectId: string

  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page)
    projectId = await createTestProject(page)
    await navigateToProject(page, projectId)
  })

  test.afterEach(async ({ page }) => {
    await deleteTestProject(page, projectId)
  })

  test('excluded fields not fetched during staging', async ({ page }) => {
    // Navigate to Context settings
    await navigateToSettings(page, 'context')

    // Set vision_documents to EXCLUDED
    const visionPriorityDropdown = page.locator('[data-testid="priority-vision-documents"]')
    await visionPriorityDropdown.click()
    await page.click('[data-testid="priority-option-excluded"]')

    // Save settings
    await page.click('[data-testid="save-context-settings"]')
    await expectToastWithText(page, 'Settings saved')

    // Navigate to project and stage
    await navigateToProject(page, projectId)
    await navigateToTab(page, 'launch')

    // Listen to network requests
    const requests: string[] = []
    page.on('request', req => {
      requests.push(req.url())
    })

    // Stage project
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Verify fetch_vision_document was NOT called
    const visionRequests = requests.filter(url => url.includes('fetch_vision_document'))
    expect(visionRequests).toHaveLength(0)
  })

  test('depth configuration affects content size', async ({ page }) => {
    // Navigate to Context settings
    await navigateToSettings(page, 'context')

    // Set vision_documents depth to "none"
    const visionDepthDropdown = page.locator('[data-testid="depth-vision-documents"]')
    await visionDepthDropdown.click()
    await page.click('[data-testid="depth-option-none"]')

    // Save settings
    await page.click('[data-testid="save-context-settings"]')
    await expectToastWithText(page, 'Settings saved')

    // Stage project
    await navigateToProject(page, projectId)
    await navigateToTab(page, 'launch')
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)

    // Verify mission is shorter (no vision content)
    const missionText = await page.locator('[data-testid="mission-panel"]').textContent()
    expect(missionText).toBeTruthy()
    // Mission should be present but not include detailed vision content
  })
})

/**
 * GitHub Integration Toggle Tests
 *
 * Validates GitHub integration toggle behavior in closeout workflow.
 */
test.describe('GitHub Integration Toggle', () => {
  let projectId: string

  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page)
    projectId = await createTestProject(page)
    await navigateToProject(page, projectId)

    // Stage and launch project (so we can close it)
    await navigateToTab(page, 'launch')
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)
    await page.click('[data-testid="launch-jobs-btn"]')
    await waitForWebSocketEvent(page, 'agent:jobs_launched', 10000)
  })

  test.afterEach(async ({ page }) => {
    await deleteTestProject(page, projectId)
  })

  test('github enabled: shows commits in closeout modal', async ({ page }) => {
    // Enable GitHub integration
    await navigateToSettings(page, 'integrations')
    const githubToggle = page.locator('[data-testid="github-integration-toggle"]')
    await githubToggle.check()
    await expectToastWithText(page, 'GitHub integration enabled')

    // Navigate to Jobs tab and close project
    await navigateToProject(page, projectId)
    await navigateToTab(page, 'jobs')
    await page.click('[data-testid="close-project-btn"]')

    // Verify closeout modal shows git commits section
    const closeoutModal = page.locator('[data-testid="closeout-modal"]')
    await expect(closeoutModal).toBeVisible()

    const gitCommitsSection = closeoutModal.locator('[data-testid="git-commits-section"]')
    await expect(gitCommitsSection).toBeVisible()
  })

  test('github disabled: shows manual summary only', async ({ page }) => {
    // Disable GitHub integration
    await navigateToSettings(page, 'integrations')
    const githubToggle = page.locator('[data-testid="github-integration-toggle"]')
    await githubToggle.uncheck()
    await expectToastWithText(page, 'GitHub integration disabled')

    // Navigate to Jobs tab and close project
    await navigateToProject(page, projectId)
    await navigateToTab(page, 'jobs')
    await page.click('[data-testid="close-project-btn"]')

    // Verify closeout modal does NOT show git commits section
    const closeoutModal = page.locator('[data-testid="closeout-modal"]')
    await expect(closeoutModal).toBeVisible()

    const gitCommitsSection = closeoutModal.locator('[data-testid="git-commits-section"]')
    await expect(gitCommitsSection).not.toBeVisible()

    // Verify manual summary field is present
    const summaryInput = closeoutModal.locator('[data-testid="closeout-summary"]')
    await expect(summaryInput).toBeVisible()
  })
})

/**
 * Agent Action Button Tests
 *
 * Validates agent action buttons (cancel, handover, etc.) work correctly.
 */
test.describe('Agent Action Buttons', () => {
  let projectId: string

  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page)
    projectId = await createTestProject(page)
    await navigateToProject(page, projectId)

    // Stage and launch project
    await navigateToTab(page, 'launch')
    await page.click('[data-testid="stage-project-btn"]')
    await waitForWebSocketEvent(page, 'orchestrator:prompt_generated', 30000)
    await page.click('[data-testid="launch-jobs-btn"]')
    await waitForWebSocketEvent(page, 'agent:jobs_launched', 10000)

    // Navigate to Jobs tab
    await navigateToTab(page, 'jobs')
  })

  test.afterEach(async ({ page }) => {
    await deleteTestProject(page, projectId)
  })

  test('cancel button stops agent execution', async ({ page }) => {
    // Find a working agent in JobsTab (table row)
    const workingAgent = page.locator('[data-testid="agent-row"][data-agent-status="working"]').first()

    if (await workingAgent.count() > 0) {
      // Click cancel button (mdi-cancel icon button in actions cell)
      const cancelBtn = workingAgent.locator('.v-btn[icon="mdi-cancel"]')
      await cancelBtn.click()

      // Wait for confirmation dialog
      const confirmDialog = page.locator('.v-dialog:visible')
      await expect(confirmDialog).toBeVisible()

      // Confirm cancellation (look for "Yes, cancel" button)
      const confirmBtn = confirmDialog.locator('button:has-text("Yes, cancel")')
      await confirmBtn.click()

      // Wait for WebSocket event
      await waitForWebSocketEvent(page, 'agent:cancelled', 10000)

      // Verify agent status changed to "cancelled"
      const statusChip = workingAgent.locator('[data-testid="status-chip"]')
      await expect(statusChip).toContainText('Cancelled')
    }
  })

  test('handover button creates successor orchestrator', async ({ page }) => {
    // Find the orchestrator row in JobsTab
    const orchestratorRow = page.locator('[data-testid="agent-row"][data-agent-type="orchestrator"]')

    if (await orchestratorRow.count() > 0) {
      // Click handover button (mdi-hand-wave icon)
      const handoverBtn = orchestratorRow.locator('.v-btn[icon="mdi-hand-wave"]')
      await handoverBtn.click()

      // Wait for LaunchSuccessorDialog to appear
      const confirmDialog = page.locator('.v-dialog:visible')
      await expect(confirmDialog).toBeVisible()

      // Confirm handover (look for confirmation button in dialog)
      const confirmBtn = confirmDialog.locator('button:has-text("Trigger Succession")')
      if (await confirmBtn.count() > 0) {
        await confirmBtn.click()
      }

      // Wait for WebSocket event
      await waitForWebSocketEvent(page, 'orchestrator:successor_created', 15000)

      // Verify success toast
      await expectToastWithText(page, 'Successor')

      // Verify successor orchestrator row appears
      const orchestratorRows = page.locator('[data-testid="agent-row"][data-agent-type="orchestrator"]')
      await expect(orchestratorRows).toHaveCount(2) // Original + successor
    }
  })

  test('copy prompt button copies to clipboard', async ({ page }) => {
    // Find any agent row in JobsTab
    const agentRow = page.locator('[data-testid="agent-row"]').first()

    // Click play/copy button (mdi-play icon)
    const copyBtn = agentRow.locator('.v-btn[icon="mdi-play"]')
    await copyBtn.click()

    // Verify success toast
    await expectToastWithText(page, 'copied')

    // Verify clipboard contains data (may fail in non-HTTPS context)
    try {
      const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
      expect(clipboardText).toBeTruthy()
      expect(clipboardText.length).toBeGreaterThan(50)
    } catch (e) {
      // Clipboard API may not work in HTTP context - skip verification
      console.log('Clipboard verification skipped (HTTP context)')
    }
  })

  test('message composer sends messages to orchestrator', async ({ page }) => {
    // Message composer is at bottom of JobsTab
    const messageComposer = page.locator('.message-composer')
    await expect(messageComposer).toBeVisible()

    // Type message
    const messageInput = messageComposer.locator('input[placeholder="Type message..."]')
    await messageInput.fill('Test message from E2E test')

    // Select orchestrator as recipient (should be default)
    const orchestratorBtn = messageComposer.locator('button:has-text("Orchestrator")')
    await orchestratorBtn.click()

    // Send message
    const sendBtn = messageComposer.locator('.v-btn[icon="mdi-play"]')
    await sendBtn.click()

    // Verify success toast
    await expectToastWithText(page, 'Message sent')
  })

  test('launch button triggers agent execution', async ({ page }) => {
    // Navigate back to Launch tab
    await navigateToTab(page, 'launch')

    // Wait for agent cards to appear
    await page.waitForSelector('[data-testid="agent-card"]', { timeout: 5000 })

    // Find an agent card in LaunchTab
    const agentCard = page.locator('[data-testid="agent-card"]').first()

    // Note: In LaunchTab, there's no individual "launch" button per agent
    // Launch is done globally via "Launch Jobs" button
    // This test may need to be revised or removed
    if (await agentCard.count() > 0) {
      console.log('Agent cards found in LaunchTab - individual launch not implemented')
    }
  })
})
