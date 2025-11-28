import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import JobsTab from '@/components/projects/JobsTab.vue'

/**
 * JobsTab Component Tests
 * Focus: Copy button visibility control based on Claude Code CLI toggle
 *
 * Test Scenario:
 * - When toggle is OFF (manual mode): all agents show copy buttons
 * - When toggle is ON (Claude Code CLI mode): only orchestrator shows copy button
 */

// Mock setup
const mockProject = {
  project_id: 'test-project-1',
  name: 'Test Project',
  description: 'Test Description',
}

const mockAgents = [
  {
    agent_id: 'orch-1',
    job_id: 'job-orch-1',
    agent_type: 'orchestrator',
    status: 'waiting',
    messages: [],
  },
  {
    agent_id: 'impl-1',
    job_id: 'job-impl-1',
    agent_type: 'implementer',
    status: 'waiting',
    messages: [],
  },
  {
    agent_id: 'test-1',
    job_id: 'job-test-1',
    agent_type: 'tester',
    status: 'waiting',
    messages: [],
  },
  {
    agent_id: 'ana-1',
    job_id: 'job-ana-1',
    agent_type: 'analyzer',
    status: 'waiting',
    messages: [],
  },
]

function createWrapper(agents = mockAgents) {
  return mount(JobsTab, {
    props: {
      project: mockProject,
      agents: agents,
      messages: [],
      allAgentsComplete: false,
    },
    global: {
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
        'LaunchSuccessorDialog': true,
        'AgentDetailsModal': true,
        'CloseoutModal': true,
      },
      mocks: {
        showToast: vi.fn(),
      },
    },
  })
}

describe('JobsTab - Copy Button Visibility (Claude Code CLI Toggle)', () => {
  describe('shouldShowCopyButton function behavior', () => {
    it('should call the helper function when rendering copy button v-if', async () => {
      const wrapper = createWrapper()

      // Verify the component has the shouldShowCopyButton method
      expect(typeof wrapper.vm.shouldShowCopyButton).toBe('function')
    })

    it('should return true for waiting agents when toggle is OFF', () => {
      const wrapper = createWrapper()

      const waitingAgent = {
        agent_type: 'implementer',
        status: 'waiting',
      }

      // Toggle is OFF (default)
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
      expect(wrapper.vm.shouldShowCopyButton(waitingAgent)).toBe(true)
    })

    it('should return false for non-waiting agents when toggle is OFF', () => {
      const wrapper = createWrapper()

      const workingAgent = {
        agent_type: 'implementer',
        status: 'working',
      }

      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
      expect(wrapper.vm.shouldShowCopyButton(workingAgent)).toBe(false)
    })

    it('should return true for waiting orchestrator when toggle is ON', async () => {
      const wrapper = createWrapper()

      const waitingOrchestrator = {
        agent_type: 'orchestrator',
        status: 'waiting',
      }

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.shouldShowCopyButton(waitingOrchestrator)).toBe(true)
    })

    it('should return false for waiting specialist when toggle is ON', async () => {
      const wrapper = createWrapper()

      const waitingSpecialist = {
        agent_type: 'implementer',
        status: 'waiting',
      }

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.shouldShowCopyButton(waitingSpecialist)).toBe(false)
    })

    it('should return false for non-waiting orchestrator when toggle is ON', async () => {
      const wrapper = createWrapper()

      const workingOrchestrator = {
        agent_type: 'orchestrator',
        status: 'working',
      }

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.shouldShowCopyButton(workingOrchestrator)).toBe(false)
    })
  })

  describe('Toggle OFF (Manual Mode) - Copy Button Visibility', () => {
    it('should show copy buttons for all waiting agents when toggle is OFF', async () => {
      const wrapper = createWrapper()

      // Toggle is OFF (default)
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // All waiting agents should show copy button
      mockAgents.forEach((agent) => {
        if (agent.status === 'waiting') {
          expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(true)
        }
      })
    })

    it('should show copy button for orchestrator when toggle is OFF and status is waiting', () => {
      const wrapper = createWrapper()

      const orchestrator = mockAgents.find((a) => a.agent_type === 'orchestrator')
      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
    })

    it('should show copy button for implementer when toggle is OFF and status is waiting', () => {
      const wrapper = createWrapper()

      const implementer = mockAgents.find((a) => a.agent_type === 'implementer')
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(true)
    })

    it('should show copy button for tester when toggle is OFF and status is waiting', () => {
      const wrapper = createWrapper()

      const tester = mockAgents.find((a) => a.agent_type === 'tester')
      expect(wrapper.vm.shouldShowCopyButton(tester)).toBe(true)
    })

    it('should show copy button for analyzer when toggle is OFF and status is waiting', () => {
      const wrapper = createWrapper()

      const analyzer = mockAgents.find((a) => a.agent_type === 'analyzer')
      expect(wrapper.vm.shouldShowCopyButton(analyzer)).toBe(true)
    })

    it('should not show copy button for non-waiting agents when toggle is OFF', () => {
      const wrapper = createWrapper([
        { agent_type: 'orchestrator', status: 'working', agent_id: '1' },
        { agent_type: 'implementer', status: 'complete', agent_id: '2' },
        { agent_type: 'tester', status: 'failed', agent_id: '3' },
      ])

      const agentsWithDifferentStatuses = wrapper.props('agents')
      agentsWithDifferentStatuses.forEach((agent) => {
        expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(false)
      })
    })
  })

  describe('Toggle ON (Claude Code CLI Mode) - Copy Button Visibility', () => {
    it('should show copy button only for waiting orchestrator when toggle is ON', async () => {
      const wrapper = createWrapper()

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true
      await nextTick()

      // Only orchestrator should show copy button
      mockAgents.forEach((agent) => {
        if (agent.agent_type === 'orchestrator' && agent.status === 'waiting') {
          expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(true)
        } else {
          expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(false)
        }
      })
    })

    it('should hide copy button for implementer when toggle is ON', async () => {
      const wrapper = createWrapper()

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const implementer = mockAgents.find((a) => a.agent_type === 'implementer')
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(false)
    })

    it('should hide copy button for tester when toggle is ON', async () => {
      const wrapper = createWrapper()

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const tester = mockAgents.find((a) => a.agent_type === 'tester')
      expect(wrapper.vm.shouldShowCopyButton(tester)).toBe(false)
    })

    it('should hide copy button for analyzer when toggle is ON', async () => {
      const wrapper = createWrapper()

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const analyzer = mockAgents.find((a) => a.agent_type === 'analyzer')
      expect(wrapper.vm.shouldShowCopyButton(analyzer)).toBe(false)
    })

    it('should show copy button for waiting orchestrator when toggle is ON', async () => {
      const wrapper = createWrapper()

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const orchestrator = mockAgents.find((a) => a.agent_type === 'orchestrator')
      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
    })

    it('should not show copy button for non-waiting orchestrator when toggle is ON', async () => {
      const wrapper = createWrapper([
        { agent_type: 'orchestrator', status: 'working', agent_id: '1' },
      ])

      // Toggle to ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const workingOrchestrator = wrapper.props('agents')[0]
      expect(wrapper.vm.shouldShowCopyButton(workingOrchestrator)).toBe(false)
    })
  })

  describe('Toggle State Transitions', () => {
    it('should toggle between ON and OFF states correctly', async () => {
      const wrapper = createWrapper()

      // Start OFF
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // Toggle ON
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)

      // Toggle OFF
      wrapper.vm.usingClaudeCodeSubagents = false
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
    })

    it('should transition copy button visibility from all to orchestrator only', async () => {
      const wrapper = createWrapper()

      const orchestrator = mockAgents.find((a) => a.agent_type === 'orchestrator')
      const implementer = mockAgents.find((a) => a.agent_type === 'implementer')

      // Start OFF - both show copy buttons
      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(true)

      // Toggle ON - only orchestrator shows
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(false)
    })

    it('should transition copy button visibility from orchestrator only back to all', async () => {
      const wrapper = createWrapper()

      const orchestrator = mockAgents.find((a) => a.agent_type === 'orchestrator')
      const implementer = mockAgents.find((a) => a.agent_type === 'implementer')

      // Start with toggle ON
      wrapper.vm.usingClaudeCodeSubagents = true
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(false)

      // Toggle OFF - all show again
      wrapper.vm.usingClaudeCodeSubagents = false
      expect(wrapper.vm.shouldShowCopyButton(orchestrator)).toBe(true)
      expect(wrapper.vm.shouldShowCopyButton(implementer)).toBe(true)
    })
  })

  describe('Copy Button Status Conditions', () => {
    it('should only show copy button when agent status is waiting (toggle OFF)', () => {
      const wrapper = createWrapper([
        { agent_type: 'orchestrator', status: 'waiting', agent_id: '1' },
        { agent_type: 'implementer', status: 'working', agent_id: '2' },
        { agent_type: 'tester', status: 'complete', agent_id: '3' },
        { agent_type: 'analyzer', status: 'failed', agent_id: '4' },
      ])

      const agents = wrapper.props('agents')

      // Only waiting agent should have copy button
      const waitingAgent = agents.find((a) => a.status === 'waiting')
      const nonWaitingAgents = agents.filter((a) => a.status !== 'waiting')

      expect(wrapper.vm.shouldShowCopyButton(waitingAgent)).toBe(true)
      nonWaitingAgents.forEach((agent) => {
        expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(false)
      })
    })

    it('should only show copy button for waiting orchestrator when toggle ON', async () => {
      const wrapper = createWrapper([
        { agent_type: 'orchestrator', status: 'waiting', agent_id: '1' },
        { agent_type: 'orchestrator', status: 'working', agent_id: '2' },
        { agent_type: 'implementer', status: 'waiting', agent_id: '3' },
      ])

      // Toggle ON
      wrapper.vm.usingClaudeCodeSubagents = true

      const agents = wrapper.props('agents')
      const waitingOrchestrator = agents.find(
        (a) => a.agent_type === 'orchestrator' && a.status === 'waiting'
      )
      const workingOrchestrator = agents.find(
        (a) => a.agent_type === 'orchestrator' && a.status === 'working'
      )
      const waitingImplementer = agents.find(
        (a) => a.agent_type === 'implementer' && a.status === 'waiting'
      )

      // Only waiting orchestrator should have copy button
      expect(wrapper.vm.shouldShowCopyButton(waitingOrchestrator)).toBe(true)
      expect(wrapper.vm.shouldShowCopyButton(workingOrchestrator)).toBe(false)
      expect(wrapper.vm.shouldShowCopyButton(waitingImplementer)).toBe(false)
    })

    it('should prioritize waiting status over agent type when toggle OFF', () => {
      const wrapper = createWrapper([
        { agent_type: 'orchestrator', status: 'waiting', agent_id: '1' },
        { agent_type: 'orchestrator', status: 'working', agent_id: '2' },
        { agent_type: 'implementer', status: 'waiting', agent_id: '3' },
        { agent_type: 'implementer', status: 'working', agent_id: '4' },
      ])

      const agents = wrapper.props('agents')

      // All waiting agents should show copy button regardless of type
      agents.forEach((agent) => {
        if (agent.status === 'waiting') {
          expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(true)
        } else {
          expect(wrapper.vm.shouldShowCopyButton(agent)).toBe(false)
        }
      })
    })
  })

  describe('Toggle function', () => {
    it('should toggle the execution mode state', async () => {
      const wrapper = createWrapper()

      // Start OFF
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // Call toggleExecutionMode
      await wrapper.vm.toggleExecutionMode()
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)

      // Call again to toggle OFF
      await wrapper.vm.toggleExecutionMode()
      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
    })
  })
})
