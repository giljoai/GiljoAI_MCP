/**
 * Thin Client UI Tests for LaunchTab Component (Handover 0088)
 *
 * Tests the thin client architecture UI enhancements including:
 * - Thin client badge display
 * - Token savings calculations
 * - Copy button tooltip
 * - Informational alert
 * - Accessibility compliance (WCAG 2.1 AA)
 * - Responsive design
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import LaunchTab from '@/components/projects/LaunchTab.vue'

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives,
})

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn()
    }
  }
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn()
  })
}))

// Mock user store
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      tenant_key: 'test-tenant-key',
      id: 'test-user-id'
    }
  })
}))

describe('LaunchTab - Thin Client UI (Handover 0088)', () => {
  let wrapper
  let pinia

  const mockProject = {
    id: 'test-project-id',
    name: 'Test Project',
    description: 'Test project description',
    status: 'active'
  }

  const mockThinClientResponse = {
    prompt: `I am Orchestrator #1 for GiljoAI Project "Test Project".

IDENTITY:
- Orchestrator ID: test-orch-id
- Project ID: test-project-id
- MCP Server: giljo-mcp (connected via claude-code)

INSTRUCTIONS:
1. Call get_orchestrator_instructions('test-orch-id', 'test-tenant-key')
2. Execute the mission according to instructions
3. Report progress via update_job_progress()

Begin by fetching your mission.`,
    estimated_prompt_tokens: 52,
    orchestrator_id: 'test-orch-id',
    project_name: 'Test Project',
    mcp_tool_name: 'get_orchestrator_instructions',
    instructions_stored: true,
    thin_client: true
  }

  beforeEach(() => {
    pinia = createPinia()
    wrapper = mount(LaunchTab, {
      props: {
        project: mockProject,
        orchestrator: null,
        isStaging: false
      },
      global: {
        plugins: [pinia, vuetify],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })
  })

  /**
   * Test 1: Thin client chip displayed after staging
   */
  it('should display thin client success chip when prompt generated', async () => {
    // Mock API response
    const api = await import('@/services/api')
    api.default.prompts.staging.mockResolvedValue({
      data: mockThinClientResponse
    })

    // Trigger staging
    await wrapper.vm.handleStageProject()
    await wrapper.vm.$nextTick()

    // Open dialog programmatically
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Find thin client chip
    const chip = wrapper.find('.thin-client-chip')
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toContain('Thin Client')
    expect(chip.text()).toContain('70% Token Reduction Active')

    // Verify accessibility
    expect(chip.attributes('aria-label')).toBe('Thin client architecture with 70% token reduction active')
  })

  /**
   * Test 2: Token stats calculated correctly
   */
  it('should calculate and display token statistics correctly', async () => {
    // Set thin client data
    wrapper.vm.generatedPrompt = mockThinClientResponse.prompt
    wrapper.vm.promptTokens = mockThinClientResponse.estimated_prompt_tokens
    wrapper.vm.isThinClient = true
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Verify computed properties
    expect(wrapper.vm.promptLineCount).toBe(12) // Mock prompt has 12 lines
    expect(wrapper.vm.estimatedPromptTokens).toBe(52)
    expect(wrapper.vm.missionTokens).toBe(6000)
    expect(wrapper.vm.tokenSavings).toBe(23948) // 30000 - (52 + 6000)
    expect(wrapper.vm.savingsPercent).toBe(80) // Math.round((23948 / 30000) * 100)

    // Find stats display
    const statsGrid = wrapper.find('.stats-grid')
    expect(statsGrid.exists()).toBe(true)

    const statItems = wrapper.findAll('.stat-item')
    expect(statItems.length).toBe(3) // Prompt size, Mission, Total savings
  })

  /**
   * Test 3: Copy button tooltip shows thin client message
   */
  it('should show correct tooltip on copy button', async () => {
    wrapper.vm.generatedPrompt = mockThinClientResponse.prompt
    wrapper.vm.promptTokens = mockThinClientResponse.estimated_prompt_tokens
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Find copy button
    const copyButton = wrapper.find('[aria-label="Copy thin client prompt to clipboard"]')
    expect(copyButton.exists()).toBe(true)

    // Verify button text includes line count
    expect(copyButton.text()).toContain('Copy Thin Prompt')
    expect(copyButton.text()).toContain('12 lines') // Mock prompt has 12 lines
  })

  /**
   * Test 4: Informational alert present with benefits
   */
  it('should display informational alert with thin client benefits', async () => {
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Find alert
    const alert = wrapper.find('[role="complementary"]')
    expect(alert.exists()).toBe(true)

    // Verify alert content
    const alertText = alert.text()
    expect(alertText).toContain('Thin Client Architecture Benefits')
    expect(alertText).toContain('Mission fetched dynamically via MCP')
    expect(alertText).toContain('70% token reduction ACTIVE')
    expect(alertText).toContain('Lower API costs')
    expect(alertText).toContain('Real-time mission updates possible')
    expect(alertText).toContain('get_orchestrator_instructions()')
  })

  /**
   * Test 5: Prompt line count accurate
   */
  it('should accurately count lines in generated prompt', async () => {
    const testPrompt = 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5'
    wrapper.vm.generatedPrompt = testPrompt
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.promptLineCount).toBe(5)
  })

  /**
   * Test 6: Accessibility compliance (WCAG 2.1 AA)
   */
  it('should meet WCAG 2.1 AA accessibility standards', async () => {
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Check ARIA labels
    const chip = wrapper.find('.thin-client-chip')
    expect(chip.attributes('aria-label')).toBeTruthy()

    const copyButton = wrapper.find('[aria-label="Copy thin client prompt to clipboard"]')
    expect(copyButton.attributes('aria-label')).toBeTruthy()

    const closeButton = wrapper.find('[aria-label="Close dialog"]')
    expect(closeButton.attributes('aria-label')).toBeTruthy()

    // Check role attributes
    const tokenStats = wrapper.find('[role="region"][aria-label="Token statistics"]')
    expect(tokenStats.exists()).toBe(true)

    const promptDisplay = wrapper.find('[role="region"][aria-label="Orchestrator prompt code"]')
    expect(promptDisplay.exists()).toBe(true)

    const alert = wrapper.find('[role="complementary"]')
    expect(alert.exists()).toBe(true)

    // Check keyboard navigation support
    const promptPre = wrapper.find('pre[tabindex="0"]')
    expect(promptPre.exists()).toBe(true)
    expect(promptPre.attributes('aria-label')).toBe('Orchestrator thin client prompt')
  })

  /**
   * Test 7: Responsive layout (mobile, tablet, desktop)
   */
  it('should apply responsive styles for different breakpoints', () => {
    const styles = wrapper.find('style').text()

    // Check mobile styles (<600px)
    expect(styles).toContain('@media (max-width: 600px)')
    expect(styles).toContain('flex-direction: column')
    expect(styles).toContain('font-size: 0.7rem')

    // Check tablet styles (600-960px)
    expect(styles).toContain('@media (max-width: 960px)')
    expect(styles).toContain('grid-template-columns: 1fr')
    expect(styles).toContain('font-size: 0.75rem')

    // Verify stat items have responsive layout
    const statItems = wrapper.findAll('.stat-item')
    statItems.forEach(item => {
      expect(item.classes()).toContain('stat-item')
    })
  })

  /**
   * Test 8: Copy button functionality
   */
  it('should copy prompt to clipboard when copy button clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
    })

    wrapper.vm.generatedPrompt = mockThinClientResponse.prompt
    wrapper.vm.promptTokens = 52
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    // Click copy button
    await wrapper.vm.copyPromptToClipboard()

    // Verify clipboard API called
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockThinClientResponse.prompt)

    // Verify success toast
    expect(wrapper.vm.showToast).toBe(true)
    expect(wrapper.vm.toastMessage).toContain('Thin client prompt copied!')
    expect(wrapper.vm.toastMessage).toContain('80% reduction')
  })

  /**
   * Test 9: Dialog close functionality
   */
  it('should close dialog when close button clicked', async () => {
    wrapper.vm.showPromptDialog = true
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.showPromptDialog).toBe(true)

    // Close dialog
    wrapper.vm.closePromptDialog()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.showPromptDialog).toBe(false)
  })

  /**
   * Test 10: API integration with thin client endpoint
   */
  it('should call staging API endpoint and process thin client response', async () => {
    const api = await import('@/services/api')
    api.default.prompts.staging.mockResolvedValue({
      data: mockThinClientResponse
    })

    await wrapper.vm.handleStageProject()

    // Verify API called correctly
    expect(api.default.prompts.staging).toHaveBeenCalledWith(
      mockProject.id,
      { tool: 'claude-code' }
    )

    // Verify state updated
    expect(wrapper.vm.generatedPrompt).toBe(mockThinClientResponse.prompt)
    expect(wrapper.vm.promptTokens).toBe(52)
    expect(wrapper.vm.orchestratorIdValue).toBe('test-orch-id')
    expect(wrapper.vm.isThinClient).toBe(true)
  })
})
