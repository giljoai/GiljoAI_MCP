import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick } from 'vue'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'
import * as api from '@/services/api'

/**
 * Test suite for AgentTableView - Copy Prompt Functionality
 *
 * Handover 0230: Prompt Generation & Clipboard Copy
 *
 * Post-refactor notes:
 * - snackbar ref replaced by useToast composable (showToast)
 * - Success/error feedback now uses toast, not snackbar state
 * - agent_display_name used instead of agent_type for orchestrator check
 */

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      agentPrompt: vi.fn()
    }
  }
}))

// Mock useClipboard composable
const mockCopy = vi.fn()
vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: mockCopy,
    isSupported: { value: true },
    copied: { value: false },
    error: { value: null }
  })
}))

// Mock useToast composable
const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast,
  })
}))

describe('AgentTableView - Copy Prompt (Handover 0230)', () => {
  let wrapper
  let pinia
  let vuetify

  const mockOrchestrator = {
    id: 'orch-1',
    job_id: 'job-orch-1',
    agent_name: 'Orchestrator',
    agent_display_name: 'orchestrator',
    is_orchestrator: true,
    status: 'working',
    progress: 50,
    messages: [],
    health_status: 'healthy'
  }

  const mockImplementer = {
    id: 'impl-1',
    job_id: 'job-impl-1',
    agent_name: 'Backend Agent',
    agent_display_name: 'implementer',
    is_orchestrator: false,
    status: 'working',
    progress: 30,
    messages: [],
    health_status: 'healthy'
  }

  const mockDecommissioned = {
    id: 'decomm-1',
    job_id: 'job-decomm-1',
    agent_name: 'Old Agent',
    agent_display_name: 'tester',
    is_orchestrator: false,
    status: 'decommissioned',
    progress: 0,
    messages: [],
    health_status: 'unknown'
  }

  const mockPromptResponse = {
    data: {
      prompt: '# Agent Prompt\n\nMission: Test mission\n\nEnvironment:\n- TEST_VAR=value\n\nCommands:\n```bash\npython test.py\n```'
    }
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })

    // Reset all mocks
    vi.clearAllMocks()

    // Setup default mock responses
    api.default.prompts.agentPrompt.mockResolvedValue(mockPromptResponse)
    mockCopy.mockResolvedValue(true)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.resetAllMocks()
  })

  describe('Copy Button Visibility and State', () => {
    it('component has handleCopyPrompt method', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.vm.handleCopyPrompt).toBeDefined()
      expect(typeof wrapper.vm.handleCopyPrompt).toBe('function')
    })

    it('component has copyingJobId ref', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.vm.copyingJobId).toBeDefined()
      expect(wrapper.vm.copyingJobId).toBe(null)
    })
  })

  describe('Copy Prompt Functionality', () => {
    it('calls API and copies prompt to clipboard', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Directly call handleCopyPrompt
      await wrapper.vm.handleCopyPrompt(mockOrchestrator)
      await nextTick()

      // Verify API was called with correct job_id
      expect(api.default.prompts.agentPrompt).toHaveBeenCalledWith('job-orch-1')

      // Verify clipboard copy was called with correct prompt
      expect(mockCopy).toHaveBeenCalledWith(mockPromptResponse.data.prompt)
    })

    it('shows success toast after successful copy', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.handleCopyPrompt(mockOrchestrator)
      await nextTick()

      // Check toast was called with success
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('copied'),
          type: 'success'
        })
      )
    })

    it('shows error toast when API call fails', async () => {
      // Mock API failure
      api.default.prompts.agentPrompt.mockRejectedValue(new Error('API Error'))

      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.handleCopyPrompt(mockOrchestrator)
      await nextTick()

      // Check error toast was called
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('Failed to copy prompt'),
          type: 'error'
        })
      )
    })

    it('shows error toast when clipboard copy fails', async () => {
      // Mock clipboard failure
      mockCopy.mockResolvedValue(false)

      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.handleCopyPrompt(mockOrchestrator)
      await nextTick()

      // Check error toast was called
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error'
        })
      )
    })

    it('sets loading state during API call', async () => {
      // Mock slow API response
      api.default.prompts.agentPrompt.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve(mockPromptResponse), 50))
      )

      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Start the copy operation
      const copyPromise = wrapper.vm.handleCopyPrompt(mockOrchestrator)
      await nextTick()

      // Check loading state is set
      expect(wrapper.vm.copyingJobId).toBe('job-orch-1')

      // Wait for completion
      await copyPromise
      await nextTick()

      // Check loading state is cleared
      expect(wrapper.vm.copyingJobId).toBe(null)
    })

    it('does not copy if canCopyPrompt returns false', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockDecommissioned],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.handleCopyPrompt(mockDecommissioned)
      await nextTick()

      // API should not be called for decommissioned agent
      expect(api.default.prompts.agentPrompt).not.toHaveBeenCalled()
      expect(mockCopy).not.toHaveBeenCalled()
    })
  })

  describe('canCopyPrompt Logic', () => {
    it('returns false for decommissioned agents', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockDecommissioned],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // canCopyPrompt should return false for decommissioned
      const result = wrapper.vm.canCopyPrompt(mockDecommissioned)
      expect(result).toBe(false)
    })

    it('returns false for non-orchestrator in Claude Code mode', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockImplementer],
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const result = wrapper.vm.canCopyPrompt(mockImplementer)
      expect(result).toBe(false)
    })

    it('returns true for orchestrator in Claude Code mode', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const result = wrapper.vm.canCopyPrompt(mockOrchestrator)
      expect(result).toBe(true)
    })

    it('returns true for all non-decommissioned agents in CLI mode', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockOrchestrator, mockImplementer],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.vm.canCopyPrompt(mockOrchestrator)).toBe(true)
      expect(wrapper.vm.canCopyPrompt(mockImplementer)).toBe(true)
    })
  })

})
