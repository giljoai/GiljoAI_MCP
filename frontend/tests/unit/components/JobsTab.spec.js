import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import JobsTab from '@/components/projects/JobsTab.vue'

/**
 * JobsTab Component Tests
 * Focus: Copy button visibility control based on execution mode (project.execution_mode)
 *
 * Current behavior (post Handover 0333 Phase 3):
 * - shouldShowCopyButton reads execution_mode from props.project.execution_mode
 * - Multi-terminal mode (default): always show launch button (prompt re-copying)
 * - Claude Code CLI mode: only orchestrator shows launch button
 * - No longer checks for waiting status (always visible for prompt re-copying)
 */

// Mock composables BEFORE component mount
const mockShowToast = vi.fn()

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast
  })
}))

// Mock API for prompt fetching
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      agentPrompt: vi.fn(),
      implementation: vi.fn(),
    },
    projects: {
      launchImplementation: vi.fn(),
    },
  }
}))

// Mock useAgentJobs composable
vi.mock('@/composables/useAgentJobs', () => ({
  useAgentJobs: () => ({
    sortedJobs: { value: [] },
    loadJobs: vi.fn(),
    store: {
      getJob: vi.fn(),
    },
  })
}))

// Mock WebSocket store
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: vi.fn(() => vi.fn()),
    off: vi.fn(),
    isConnected: { value: false },
  }),
}))

// Mock navigator.clipboard for clipboard operations
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})

// Mock window.isSecureContext
Object.defineProperty(window, 'isSecureContext', {
  writable: true,
  value: true
})

// Mock setup
const mockProject = {
  project_id: 'test-project-1',
  name: 'Test Project',
  description: 'Test Description',
  execution_mode: 'multi_terminal',
}

function createWrapper(projectOverrides = {}) {
  return mount(JobsTab, {
    props: {
      project: { ...mockProject, ...projectOverrides },
    },
    global: {
      plugins: [createPinia()],
      stubs: {
        'v-btn': true,
        'v-icon': true,
        'v-tooltip': true,
        'v-avatar': true,
        'v-dialog': true,
        'v-card': true,
        'v-card-title': true,
        'v-card-text': true,
        'v-card-actions': true,
        'v-text-field': true,
        'v-spacer': true,
        'v-snackbar': true,
        'LaunchSuccessorDialog': true,
        'AgentDetailsModal': true,
        'AgentJobModal': true,
        'MessageAuditModal': true,
        'CloseoutModal': true,
        'HandoverModal': true,
      },
    },
  })
}

describe('JobsTab - Copy Button Visibility (Execution Mode)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('shouldShowCopyButton function behavior', () => {
    it('should have the shouldShowCopyButton method', async () => {
      const wrapper = createWrapper()

      // Verify the component has the shouldShowCopyButton method
      expect(typeof wrapper.vm.shouldShowCopyButton).toBe('function')
    })

    it('should return true for any agent when execution_mode is multi_terminal', () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      const implementerAgent = {
        agent_display_name: 'implementer',
        status: 'working',
      }

      expect(wrapper.vm.shouldShowCopyButton(implementerAgent)).toBe(true)
    })

    it('should return true for orchestrator when execution_mode is claude_code_cli', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      const orchestrator = {
        agent_display_name: 'orchestrator',
        status: 'working',
      }

      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
    })

    it('should return false for specialist when execution_mode is claude_code_cli', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      const specialist = {
        agent_display_name: 'implementer',
        status: 'working',
      }

      expect(wrapper.vm.shouldShowCopyButton(specialist)).toBe(false)
    })
  })

  describe('Multi-Terminal Mode - Copy Button Visibility', () => {
    it('should show copy buttons for all agents when in multi_terminal mode', () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      const agentTypes = ['orchestrator', 'implementer', 'tester', 'analyzer']
      agentTypes.forEach((agentType) => {
        expect(wrapper.vm.shouldShowCopyButton({
          agent_display_name: agentType,
          status: 'working',
        })).toBe(true)
      })
    })

    it('should show copy button for orchestrator in multi_terminal mode', () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'orchestrator',
        status: 'waiting',
      })).toBe(true)
    })

    it('should show copy button for implementer in multi_terminal mode', () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'waiting',
      })).toBe(true)
    })

    it('should show copy button for tester in multi_terminal mode', () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'tester',
        status: 'complete',
      })).toBe(true)
    })
  })

  describe('Claude Code CLI Mode - Copy Button Visibility', () => {
    it('should show copy button only for orchestrator when in claude_code_cli mode', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'orchestrator',
        status: 'working',
      })).toBe(true)

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'working',
      })).toBe(false)

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'tester',
        status: 'working',
      })).toBe(false)

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'analyzer',
        status: 'working',
      })).toBe(false)
    })

    it('should hide copy button for implementer when in claude_code_cli mode', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'waiting',
      })).toBe(false)
    })

    it('should hide copy button for tester when in claude_code_cli mode', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'tester',
        status: 'waiting',
      })).toBe(false)
    })

    it('should hide copy button for analyzer when in claude_code_cli mode', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'analyzer',
        status: 'waiting',
      })).toBe(false)
    })
  })

  describe('Execution Mode from Project Prop', () => {
    it('should read execution_mode from project prop', () => {
      const wrapper = createWrapper({ execution_mode: 'claude_code_cli' })

      // In CLI mode, only orchestrator shows
      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'orchestrator',
        status: 'working',
      })).toBe(true)

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'working',
      })).toBe(false)
    })

    it('should default to multi_terminal behavior when execution_mode is undefined', () => {
      const wrapper = createWrapper({ execution_mode: undefined })

      // All agents should show copy button in multi_terminal mode
      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'working',
      })).toBe(true)
    })

    it('should update behavior when project prop changes', async () => {
      const wrapper = createWrapper({ execution_mode: 'multi_terminal' })

      // Initially multi_terminal - all agents show
      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'working',
      })).toBe(true)

      // Change to CLI mode
      await wrapper.setProps({
        project: { ...mockProject, execution_mode: 'claude_code_cli' },
      })

      // Now only orchestrator shows
      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'implementer',
        status: 'working',
      })).toBe(false)

      expect(wrapper.vm.shouldShowCopyButton({
        agent_display_name: 'orchestrator',
        status: 'working',
      })).toBe(true)
    })
  })

  describe('Messages Waiting Counter', () => {
    it('should have getMessagesWaiting method', () => {
      const wrapper = createWrapper()
      expect(typeof wrapper.vm.getMessagesWaiting).toBe('function')
    })

    it('should return messages_waiting_count from agent', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.getMessagesWaiting({ messages_waiting_count: 5 })).toBe(5)
    })

    it('should return 0 when messages_waiting_count is undefined', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.getMessagesWaiting({})).toBe(0)
    })

    it('should return 0 when agent is null', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.getMessagesWaiting(null)).toBe(0)
    })
  })
})
