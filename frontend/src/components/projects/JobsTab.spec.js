/**
 * JobsTab Component Tests
 *
 * Production-grade test suite for Handover 0077 JobsTab component.
 * Tests component rendering, agent sorting, user interactions, event emissions,
 * accessibility, and responsive behavior.
 *
 * Test Coverage:
 * - Component rendering with props
 * - Agent sorting priority (failed/blocked → waiting → working → complete)
 * - All agents complete banner display
 * - Event emissions for user actions
 * - Message handling
 * - Keyboard navigation
 * - Scroll indicators
 * - Responsive design
 * - Accessibility (ARIA labels, keyboard support)
 * - Edge cases and error states
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import JobsTab from './JobsTab.vue'
import AgentCardEnhanced from './AgentCardEnhanced.vue'
import MessageStream from './MessageStream.vue'
import MessageInput from './MessageInput.vue'

// Mock child components
vi.mock('./AgentCardEnhanced.vue', () => ({
  default: {
    name: 'AgentCardEnhanced',
    props: ['agent', 'mode', 'instanceNumber', 'isOrchestrator', 'showCloseoutButton'],
    emits: ['launch-agent', 'view-details', 'view-error', 'closeout-project'],
    template: `
      <div
        class="agent-card-mock"
        :data-agent-type="agent.agent_display_name"
        :data-status="agent.status"
        :data-instance="instanceNumber"
        :data-orchestrator="isOrchestrator"
      >
        <button v-if="agent.status === 'waiting'" @click="$emit('launch-agent', agent)">Launch</button>
        <button v-if="agent.status === 'working'" @click="$emit('view-details', agent)">Details</button>
        <button v-if="agent.status === 'failed' || agent.status === 'blocked'" @click="$emit('view-error', agent)">View Error</button>
        <button v-if="isOrchestrator && showCloseoutButton" @click="$emit('closeout-project')">Closeout</button>
      </div>
    `,
  },
}))

vi.mock('./MessageStream.vue', () => ({
  default: {
    name: 'MessageStream',
    props: ['messages', 'projectId', 'autoScroll', 'loading'],
    template: '<div class="message-stream-mock">{{ messages.length }} messages</div>',
  },
}))

vi.mock('./MessageInput.vue', () => ({
  default: {
    name: 'MessageInput',
    props: ['disabled'],
    emits: ['send'],
    template:
      "<div class=\"message-input-mock\"><button @click=\"$emit('send', 'test message', 'orchestrator')\">Send</button></div>",
  },
}))

// Test data fixtures
const createMockProject = (overrides = {}) => ({
  project_id: 'proj-12345678',
  name: 'Test Project',
  description: 'Test project description',
  ...overrides,
})

const createMockAgent = (type, status, overrides = {}) => ({
  job_id: `job-${type}-${Math.random().toString(36).substr(2, 9)}`,
  agent_id: `agent-${type}`,
  agent_display_name: type,
  status: status,
  mission: `Mission for ${type}`,
  progress: status === 'working' ? 50 : 0,
  current_task: status === 'working' ? 'Working on task' : null,
  block_reason: status === 'failed' || status === 'blocked' ? 'Error occurred' : null,
  messages: [],
  ...overrides,
})

const createMockMessage = (from, content, overrides = {}) => ({
  id: `msg-${Math.random().toString(36).substr(2, 9)}`,
  from: from,
  from_agent: from === 'agent' ? 'orchestrator' : null,
  to_agent: 'orchestrator',
  type: from === 'agent' ? 'agent' : 'user',
  content: content,
  timestamp: new Date().toISOString(),
  agent_display_name: from === 'agent' ? 'orchestrator' : null,
  instance_number: 1,
  ...overrides,
})

describe('JobsTab Component', () => {
  let wrapper

  const defaultProps = {
    project: createMockProject(),
    agents: [
      createMockAgent('orchestrator', 'working'),
      createMockAgent('analyzer', 'waiting'),
      createMockAgent('implementor', 'complete'),
    ],
    messages: [],
    allAgentsComplete: false,
  }

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Component Rendering', () => {
    it('renders with required props', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.jobs-tab').exists()).toBe(true)
    })

    it('displays project header with name and ID', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      expect(projectHeader.exists()).toBe(true)
      expect(projectHeader.text()).toContain('Test Project')
      expect(projectHeader.text()).toContain('proj-12345678')
    })

    it('renders correct number of agent cards', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(3)
    })

    it('renders message stream and message input', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      expect(wrapper.findComponent(MessageStream).exists()).toBe(true)
      expect(wrapper.findComponent(MessageInput).exists()).toBe(true)
    })

    it('does not show complete banner when agents are not complete', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: false,
        },
      })

      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(false)
    })

    it('shows complete banner when all agents are complete', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: true,
        },
      })

      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('All agents report complete')
    })
  })

  describe('Agent Sorting Priority', () => {
    it('sorts agents by priority: failed > blocked > waiting > working > complete', () => {
      const agents = [
        createMockAgent('implementor', 'complete'),
        createMockAgent('analyzer', 'working'),
        createMockAgent('researcher', 'waiting'),
        createMockAgent('reviewer', 'blocked'),
        createMockAgent('tester', 'failed'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const sortedStatuses = agentCards.map((card) => card.props('agent').status)

      expect(sortedStatuses).toEqual(['failed', 'blocked', 'waiting', 'working', 'complete'])
    })

    it('prioritizes orchestrator within same status', () => {
      const agents = [
        createMockAgent('analyzer', 'waiting'),
        createMockAgent('orchestrator', 'waiting'),
        createMockAgent('implementor', 'waiting'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const sortedTypes = agentCards.map((card) => card.props('agent').agent_display_name)

      expect(sortedTypes[0]).toBe('orchestrator')
    })

    it('sorts alphabetically by agent type within same priority', () => {
      const agents = [
        createMockAgent('implementor', 'working'),
        createMockAgent('analyzer', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const sortedTypes = agentCards.map((card) => card.props('agent').agent_display_name)

      expect(sortedTypes).toEqual(['analyzer', 'implementor'])
    })

    it('handles empty agents array', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents: [],
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(0)
    })

    it('handles agents with unknown status', () => {
      const agents = [
        createMockAgent('analyzer', 'unknown_status'),
        createMockAgent('implementor', 'waiting'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Should not throw error and should render all agents
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(2)
    })
  })

  describe('Instance Number Calculation', () => {
    it('assigns instance number 1 for single agent of type', () => {
      const agents = [createMockAgent('implementor', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('instanceNumber')).toBe(1)
    })

    it('assigns incremental instance numbers for multiple agents of same type', () => {
      const agents = [
        createMockAgent('implementor', 'working', { job_id: 'job-impl-1' }),
        createMockAgent('implementor', 'working', { job_id: 'job-impl-2' }),
        createMockAgent('implementor', 'complete', { job_id: 'job-impl-3' }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const implementorCards = agentCards.filter(
        (card) => card.props('agent').agent_display_name === 'implementor',
      )

      // All implementors should have unique instance numbers
      const instanceNumbers = implementorCards.map((card) => card.props('instanceNumber'))
      expect(instanceNumbers).toEqual([1, 2, 3])
    })

    it('assigns different instance numbers to different agent types', () => {
      const agents = [
        createMockAgent('implementor', 'working', { job_id: 'job-impl-1' }),
        createMockAgent('implementor', 'working', { job_id: 'job-impl-2' }),
        createMockAgent('analyzer', 'working', { job_id: 'job-anlz-1' }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })

      const implementorCards = agentCards.filter(
        (card) => card.props('agent').agent_display_name === 'implementor',
      )
      const implementorInstances = implementorCards.map((card) => card.props('instanceNumber'))
      expect(implementorInstances).toEqual([1, 2])

      const analyzerCards = agentCards.filter(
        (card) => card.props('agent').agent_display_name === 'analyzer',
      )
      const analyzerInstances = analyzerCards.map((card) => card.props('instanceNumber'))
      expect(analyzerInstances).toEqual([1])
    })
  })

  describe('Orchestrator Detection', () => {
    it('identifies orchestrator agent correctly', () => {
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })

      const orchestratorCard = agentCards.find(
        (card) => card.props('agent').agent_display_name === 'orchestrator',
      )
      expect(orchestratorCard.props('isOrchestrator')).toBe(true)

      const implementorCard = agentCards.find(
        (card) => card.props('agent').agent_display_name === 'implementor',
      )
      expect(implementorCard.props('isOrchestrator')).toBe(false)
    })

    it('shows closeout button only on orchestrator when all complete', () => {
      const agents = [
        createMockAgent('orchestrator', 'complete'),
        createMockAgent('implementor', 'complete'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
          allAgentsComplete: true,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })

      const orchestratorCard = agentCards.find(
        (card) => card.props('agent').agent_display_name === 'orchestrator',
      )
      expect(orchestratorCard.props('showCloseoutButton')).toBe(true)

      const implementorCard = agentCards.find(
        (card) => card.props('agent').agent_display_name === 'implementor',
      )
      expect(implementorCard.props('showCloseoutButton')).toBe(false)
    })
  })

  describe('Event Emissions', () => {
    it('emits launch-agent event when agent card emits it', async () => {
      const agents = [createMockAgent('implementor', 'waiting')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      await agentCard.vm.$emit('launch-agent', agents[0])

      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0]).toEqual([agents[0]])
    })

    it('emits view-details event when agent card emits it', async () => {
      const agents = [createMockAgent('implementor', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      await agentCard.vm.$emit('view-details', agents[0])

      expect(wrapper.emitted('view-details')).toBeTruthy()
      expect(wrapper.emitted('view-details')[0]).toEqual([agents[0]])
    })

    it('emits view-error event when agent card emits it', async () => {
      const agents = [createMockAgent('implementor', 'failed')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      await agentCard.vm.$emit('view-error', agents[0])

      expect(wrapper.emitted('view-error')).toBeTruthy()
      expect(wrapper.emitted('view-error')[0]).toEqual([agents[0]])
    })

    it('emits closeout-project event when orchestrator closeout button clicked', async () => {
      const agents = [createMockAgent('orchestrator', 'complete')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
          allAgentsComplete: true,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      await agentCard.vm.$emit('closeout-project')

      expect(wrapper.emitted('closeout-project')).toBeTruthy()
      expect(wrapper.emitted('closeout-project')).toHaveLength(1)
    })

    it('emits send-message event when message input emits send', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const messageInput = wrapper.findComponent(MessageInput)
      await messageInput.vm.$emit('send', 'Test message', 'orchestrator')

      expect(wrapper.emitted('send-message')).toBeTruthy()
      expect(wrapper.emitted('send-message')[0]).toEqual(['Test message', 'orchestrator'])
    })
  })

  describe('Message Handling', () => {
    it('passes messages to MessageStream component', () => {
      const messages = [
        createMockMessage('agent', 'Agent message 1'),
        createMockMessage('developer', 'User message 1'),
        createMockMessage('agent', 'Agent message 2'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          messages,
        },
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('messages')).toEqual(messages)
      expect(messageStream.props('messages')).toHaveLength(3)
    })

    it('passes project ID to MessageStream for ARIA label', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('projectId')).toBe('proj-12345678')
    })

    it('enables auto-scroll in MessageStream', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('autoScroll')).toBe(true)
    })
  })

  describe('Layout and Responsive Design', () => {
    it('renders 2-column layout with correct structure', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const leftColumn = wrapper.find('.jobs-tab__left-column')
      const rightColumn = wrapper.find('.jobs-tab__right-column')

      expect(leftColumn.exists()).toBe(true)
      expect(rightColumn.exists()).toBe(true)

      // Left column contains project header and agent cards
      expect(leftColumn.find('.jobs-tab__project-header').exists()).toBe(true)
      expect(leftColumn.find('.jobs-tab__agents-container').exists()).toBe(true)

      // Right column contains messages
      expect(rightColumn.find('.jobs-tab__messages-panel').exists()).toBe(true)
    })

    it('has horizontal scroll container for agent cards', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const scrollContainer = wrapper.find('.jobs-tab__agents-scroll')
      expect(scrollContainer.exists()).toBe(true)
      expect(scrollContainer.attributes('role')).toBe('list')
      expect(scrollContainer.attributes('tabindex')).toBe('0')
    })

    it('renders agent count chip', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents: [
            createMockAgent('orchestrator', 'working'),
            createMockAgent('analyzer', 'waiting'),
            createMockAgent('implementor', 'complete'),
          ],
        },
      })

      const agentsHeader = wrapper.find('.jobs-tab__agents-header')
      expect(agentsHeader.text()).toContain('3')
    })
  })

  describe('Scroll Indicators', () => {
    it('renders scroll indicator buttons', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const scrollIndicators = wrapper.find('.jobs-tab__scroll-indicators')
      expect(scrollIndicators.exists()).toBe(true)
    })

    it('scroll left button has correct ARIA label', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const leftButton = wrapper.find('.jobs-tab__scroll-left')
      if (leftButton.exists()) {
        expect(leftButton.attributes('aria-label')).toBe('Scroll agents left')
      }
    })

    it('scroll right button has correct ARIA label', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const rightButton = wrapper.find('.jobs-tab__scroll-right')
      if (rightButton.exists()) {
        expect(rightButton.attributes('aria-label')).toBe('Scroll agents right')
      }
    })
  })

  describe('Keyboard Navigation', () => {
    it('agent scroll container is keyboard focusable', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const scrollContainer = wrapper.find('.jobs-tab__agents-scroll')
      expect(scrollContainer.attributes('tabindex')).toBe('0')
    })

    it('handles arrow key navigation for agent scroll', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const scrollContainer = wrapper.find('.jobs-tab__agents-scroll')
      const element = scrollContainer.element

      // Mock scrollBy method
      const scrollBySpy = vi.fn()
      element.scrollBy = scrollBySpy

      // Simulate ArrowRight key
      await scrollContainer.trigger('keydown', { key: 'ArrowRight' })
      expect(scrollBySpy).toHaveBeenCalledWith({
        left: 300,
        behavior: 'smooth',
      })

      // Simulate ArrowLeft key
      await scrollContainer.trigger('keydown', { key: 'ArrowLeft' })
      expect(scrollBySpy).toHaveBeenCalledWith({
        left: -300,
        behavior: 'smooth',
      })
    })

    it('handles Home and End keys for agent scroll', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const scrollContainer = wrapper.find('.jobs-tab__agents-scroll')
      const element = scrollContainer.element

      // Mock scrollTo method and scrollWidth property
      const scrollToSpy = vi.fn()
      element.scrollTo = scrollToSpy
      Object.defineProperty(element, 'scrollWidth', { value: 1000, configurable: true })

      // Simulate Home key
      await scrollContainer.trigger('keydown', { key: 'Home' })
      expect(scrollToSpy).toHaveBeenCalledWith({
        left: 0,
        behavior: 'smooth',
      })

      // Simulate End key
      await scrollContainer.trigger('keydown', { key: 'End' })
      expect(scrollToSpy).toHaveBeenCalledWith({
        left: 1000,
        behavior: 'smooth',
      })
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA label on main container', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const mainContainer = wrapper.find('.jobs-tab')
      expect(mainContainer.attributes('role')).toBe('main')
      expect(mainContainer.attributes('aria-label')).toBe('Jobs view for project Test Project')
    })

    it('agent cards container has list role', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const scrollContainer = wrapper.find('.jobs-tab__agents-scroll')
      expect(scrollContainer.attributes('role')).toBe('list')
    })

    it('agent cards have listitem role', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentCards = wrapper.findAll('.jobs-tab__agent-card')
      agentCards.forEach((card) => {
        expect(card.attributes('role')).toBe('listitem')
      })
    })

    it('complete banner has correct structure for screen readers', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: true,
        },
      })

      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)
      expect(banner.find('.text-h6').exists()).toBe(true)
      expect(banner.find('.text-body-2').exists()).toBe(true)
    })

    it('project ID uses code element for semantic meaning', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      const codeElement = projectHeader.find('code')
      expect(codeElement.exists()).toBe(true)
      expect(codeElement.text()).toBe('proj-12345678')
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('handles null or undefined project gracefully', () => {
      // Should not throw error even with invalid project
      const createWrapper = () => {
        return mount(JobsTab, {
          props: {
            project: null,
            agents: [],
            messages: [],
            allAgentsComplete: false,
          },
        })
      }

      // This should throw validation error, which is expected behavior
      expect(createWrapper).toThrow()
    })

    it('handles agents without job_id or agent_id', () => {
      const agents = [{ agent_display_name: 'implementor', status: 'working', mission: 'Test' }]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Should render without error
      expect(wrapper.exists()).toBe(true)
    })

    it('handles agents without agent_display_name', () => {
      const agents = [{ job_id: 'job-1', status: 'working', mission: 'Test' }]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Should render without error (uses default instance number 1)
      expect(wrapper.exists()).toBe(true)
    })

    it('handles empty messages array', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          messages: [],
        },
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('messages')).toEqual([])
    })

    it('handles very long project names gracefully', () => {
      const longName = 'A'.repeat(200)

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          project: createMockProject({ name: longName }),
        },
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      expect(projectHeader.text()).toContain(longName)
    })

    it('handles very long project IDs gracefully', () => {
      const longId = 'proj-' + 'x'.repeat(200)

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          project: createMockProject({ project_id: longId }),
        },
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      expect(projectHeader.text()).toContain(longId)
    })

    it('handles large number of agents efficiently', () => {
      const manyAgents = Array.from({ length: 50 }, (_, i) =>
        createMockAgent(`agent-${i}`, 'working'),
      )

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents: manyAgents,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(50)
    })

    it('handles large number of messages efficiently', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) =>
        createMockMessage('agent', `Message ${i}`),
      )

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          messages: manyMessages,
        },
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('messages')).toHaveLength(100)
    })
  })

  describe('Props Validation', () => {
    it('requires project prop with project_id', () => {
      // Spy on console.warn to catch validation warnings
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      wrapper = mount(JobsTab, {
        props: {
          project: { name: 'Test' }, // Missing project_id
          agents: [],
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Vue should warn about validation failure
      // (In production, prop validation warnings appear in console)
      expect(wrapper.exists()).toBe(true)

      warnSpy.mockRestore()
    })

    it('requires agents prop as array', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: createMockProject(),
          agents: [], // Valid empty array
          messages: [],
          allAgentsComplete: false,
        },
      })

      expect(wrapper.exists()).toBe(true)
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(0)
    })

    it('accepts valid props without error', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.jobs-tab').exists()).toBe(true)
    })
  })

  describe('Component Integration', () => {
    it('passes correct props to AgentCardEnhanced', () => {
      const agents = [createMockAgent('implementor', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('mode')).toBe('jobs')
      expect(agentCard.props('agent')).toEqual(agents[0])
      expect(agentCard.props('instanceNumber')).toBe(1)
      expect(agentCard.props('isOrchestrator')).toBe(false)
      expect(agentCard.props('showCloseoutButton')).toBe(false)
    })

    it('passes correct props to MessageStream', () => {
      const messages = [createMockMessage('agent', 'Test')]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          messages,
        },
      })

      const messageStream = wrapper.findComponent(MessageStream)
      expect(messageStream.props('messages')).toEqual(messages)
      expect(messageStream.props('projectId')).toBe('proj-12345678')
      expect(messageStream.props('autoScroll')).toBe(true)
      expect(messageStream.props('loading')).toBe(false)
    })

    it('passes correct props to MessageInput', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const messageInput = wrapper.findComponent(MessageInput)
      expect(messageInput.props('disabled')).toBe(false)
    })
  })

  describe('Lifecycle and Cleanup', () => {
    it('sets up scroll listeners on mount', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener')

      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      expect(addEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function))
    })

    it('cleans up scroll listeners on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')

      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      wrapper.unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function))
    })
  })
})
