/**
 * JobsTab Integration Tests
 *
 * Tests for real-time updates, WebSocket integration, and complete user workflows.
 * These tests validate end-to-end functionality of the JobsTab component with
 * actual child components (no mocking except external services).
 *
 * Test Coverage:
 * - Real-time agent status updates
 * - Message stream integration
 * - Complete user workflows (launch agent, send message, closeout)
 * - State synchronization
 * - Multi-agent coordination scenarios
 * - Error recovery and resilience
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import JobsTab from './JobsTab.vue'

// Mock WebSocket service
const mockWebSocket = {
  on: vi.fn((event, handler) => {
    // Store handlers for later invocation
    mockWebSocket.handlers = mockWebSocket.handlers || {}
    mockWebSocket.handlers[event] = handler
    return () => {} // Unsubscribe function
  }),
  emit: vi.fn((event, data) => {
    // Simulate event emission
    if (mockWebSocket.handlers && mockWebSocket.handlers[event]) {
      mockWebSocket.handlers[event](data)
    }
  }),
  handlers: {},
}

vi.mock('@/services/websocket', () => ({
  default: mockWebSocket,
}))

// Test data fixtures
const createMockProject = (overrides = {}) => ({
  project_id: 'proj-integration-test',
  name: 'Integration Test Project',
  description: 'Testing real-time integration',
  ...overrides,
})

const createMockAgent = (type, status, overrides = {}) => ({
  job_id: `job-${type}-${Date.now()}`,
  agent_id: `agent-${type}`,
  agent_display_name: type,
  status: status,
  mission: `Mission for ${type}`,
  progress: status === 'working' ? 0 : 0,
  current_task: null,
  block_reason: null,
  messages: [],
  ...overrides,
})

const createMockMessage = (from, content, overrides = {}) => ({
  id: `msg-${Date.now()}-${Math.random()}`,
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

describe('JobsTab Integration Tests', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    mockWebSocket.handlers = {}
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Complete User Workflows', () => {
    it('completes launch agent workflow', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'waiting'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Find the waiting implementor agent card
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const waitingCard = agentCards.find((card) => card.props('agent').status === 'waiting')

      expect(waitingCard).toBeTruthy()

      // Click launch button
      await waitingCard.vm.$emit('launch-agent', waitingCard.props('agent'))
      await nextTick()

      // Verify event was emitted
      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0][0].agent_display_name).toBe('implementor')
    })

    it('completes send message workflow', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]
      const messages = [createMockMessage('agent', 'Initial message from orchestrator')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages,
          allAgentsComplete: false,
        },
      })

      // Find message input and send a message
      const messageInput = wrapper.findComponent({ name: 'MessageInput' })
      await messageInput.vm.$emit('send', 'Test user message', 'orchestrator')
      await nextTick()

      // Verify event was emitted
      expect(wrapper.emitted('send-message')).toBeTruthy()
      expect(wrapper.emitted('send-message')[0]).toEqual(['Test user message', 'orchestrator'])
    })

    it('completes closeout project workflow', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'complete'),
        createMockAgent('implementor', 'complete'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: true,
        },
      })

      // Verify banner is shown
      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)

      // Find orchestrator card
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const orchestratorCard = agentCards.find(
        (card) => card.props('agent').agent_display_name === 'orchestrator',
      )

      expect(orchestratorCard.props('showCloseoutButton')).toBe(true)

      // Click closeout button
      await orchestratorCard.vm.$emit('closeout-project')
      await nextTick()

      // Verify event was emitted
      expect(wrapper.emitted('closeout-project')).toBeTruthy()
      expect(wrapper.emitted('closeout-project')).toHaveLength(1)
    })

    it('completes view agent details workflow', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('implementor', 'working', {
          progress: 75,
          current_task: 'Implementing feature X',
        }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Find working agent card
      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })

      // Click details button
      await agentCard.vm.$emit('view-details', agentCard.props('agent'))
      await nextTick()

      // Verify event was emitted
      expect(wrapper.emitted('view-details')).toBeTruthy()
      expect(wrapper.emitted('view-details')[0][0].progress).toBe(75)
    })

    it('completes view agent error workflow', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('implementor', 'failed', {
          block_reason: 'Database connection failed',
        }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Find failed agent card
      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })

      // Click view error button
      await agentCard.vm.$emit('view-error', agentCard.props('agent'))
      await nextTick()

      // Verify event was emitted
      expect(wrapper.emitted('view-error')).toBeTruthy()
      expect(wrapper.emitted('view-error')[0][0].block_reason).toBe('Database connection failed')
    })
  })

  describe('Real-time Agent Status Updates', () => {
    it('updates UI when agent transitions from waiting to working', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('implementor', 'waiting')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initially waiting
      let agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('waiting')

      // Update agent status to working
      const updatedAgents = [
        { ...agents[0], status: 'working', progress: 10, current_task: 'Starting work' },
      ]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // Now working
      agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('working')
      expect(agentCard.props('agent').progress).toBe(10)
    })

    it('updates UI when agent transitions from working to complete', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('implementor', 'working', { progress: 90 })]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initially working
      let agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('working')

      // Update agent status to complete
      const updatedAgents = [{ ...agents[0], status: 'complete', progress: 100 }]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // Now complete
      agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('complete')
    })

    it('updates UI when agent encounters error', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('implementor', 'working', { progress: 50 })]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initially working
      let agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('working')

      // Update agent status to failed
      const updatedAgents = [
        {
          ...agents[0],
          status: 'failed',
          block_reason: 'API timeout error',
        },
      ]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // Now failed
      agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('failed')
      expect(agentCard.props('agent').block_reason).toBe('API timeout error')
    })

    it('re-sorts agents when priorities change', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'working'),
        createMockAgent('analyzer', 'complete'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initial order: orchestrator, implementor, analyzer
      let agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      let order = agentCards.map((card) => card.props('agent').agent_display_name)
      expect(order).toEqual(['orchestrator', 'implementor', 'analyzer'])

      // Implementor fails (should move to top)
      const updatedAgents = [
        agents[0], // orchestrator still working
        { ...agents[1], status: 'failed', block_reason: 'Error' }, // implementor failed
        agents[2], // analyzer still complete
      ]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // New order: implementor (failed), orchestrator (working), analyzer (complete)
      agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      order = agentCards.map((card) => card.props('agent').agent_display_name)
      expect(order).toEqual(['implementor', 'orchestrator', 'analyzer'])
    })
  })

  describe('Real-time Message Updates', () => {
    it('displays new messages in real-time', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]
      const initialMessages = [createMockMessage('agent', 'Initial message')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: initialMessages,
          allAgentsComplete: false,
        },
      })

      // Initially 1 message
      let messageStream = wrapper.findComponent({ name: 'MessageStream' })
      expect(messageStream.props('messages')).toHaveLength(1)

      // Add new message
      const updatedMessages = [
        ...initialMessages,
        createMockMessage('agent', 'New message from agent'),
      ]

      await wrapper.setProps({ messages: updatedMessages })
      await nextTick()

      // Now 2 messages
      messageStream = wrapper.findComponent({ name: 'MessageStream' })
      expect(messageStream.props('messages')).toHaveLength(2)
    })

    it('handles rapid message updates', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Add messages rapidly
      for (let i = 0; i < 10; i++) {
        const messages = Array.from({ length: i + 1 }, (_, idx) =>
          createMockMessage('agent', `Message ${idx}`),
        )

        await wrapper.setProps({ messages })
        await nextTick()
      }

      // Should have all 10 messages
      const messageStream = wrapper.findComponent({ name: 'MessageStream' })
      expect(messageStream.props('messages')).toHaveLength(10)
    })

    it('displays user messages correctly', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]
      const messages = [
        createMockMessage('agent', 'Agent message'),
        createMockMessage('developer', 'User message', { from: 'developer' }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages,
          allAgentsComplete: false,
        },
      })

      const messageStream = wrapper.findComponent({ name: 'MessageStream' })
      expect(messageStream.props('messages')).toHaveLength(2)

      // Verify both agent and user messages are present
      const messageList = messageStream.props('messages')
      expect(messageList[0].from).toBe('agent')
      expect(messageList[1].from).toBe('developer')
    })
  })

  describe('Multi-Agent Coordination', () => {
    it('handles multiple agents of same type with correct instance numbers', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('implementor', 'working', { job_id: 'job-impl-1' }),
        createMockAgent('implementor', 'waiting', { job_id: 'job-impl-2' }),
        createMockAgent('implementor', 'complete', { job_id: 'job-impl-3' }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      const implementorCards = agentCards.filter(
        (card) => card.props('agent').agent_display_name === 'implementor',
      )

      expect(implementorCards).toHaveLength(3)

      // Each should have unique instance number
      const instanceNumbers = implementorCards.map((card) => card.props('instanceNumber'))
      expect(instanceNumbers).toEqual([1, 2, 3])
    })

    it('handles agent addition dynamically', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initially 1 agent
      let agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(1)

      // Add new agent
      const updatedAgents = [...agents, createMockAgent('implementor', 'waiting')]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // Now 2 agents
      agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(2)
    })

    it('handles agent removal dynamically', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'complete'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Initially 2 agents
      let agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(2)

      // Remove implementor
      const updatedAgents = [agents[0]]

      await wrapper.setProps({ agents: updatedAgents })
      await nextTick()

      // Now 1 agent
      agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(1)
      expect(agentCards[0].props('agent').agent_display_name).toBe('orchestrator')
    })
  })

  describe('State Synchronization', () => {
    it('maintains consistent state across prop updates', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Update multiple props simultaneously
      const updatedAgents = [
        { ...agents[0], progress: 50 },
        { ...agents[1], status: 'complete' },
      ]
      const newMessages = [createMockMessage('agent', 'Progress update')]

      await wrapper.setProps({
        agents: updatedAgents,
        messages: newMessages,
        allAgentsComplete: false,
      })
      await nextTick()

      // Verify all updates applied
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards[0].props('agent').progress).toBe(50)
      expect(agentCards[1].props('agent').status).toBe('complete')

      const messageStream = wrapper.findComponent({ name: 'MessageStream' })
      expect(messageStream.props('messages')).toHaveLength(1)
    })

    it('shows complete banner when all agents finish', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        createMockAgent('implementor', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Banner not shown initially
      expect(wrapper.find('.jobs-tab__complete-banner').exists()).toBe(false)

      // All agents complete
      const updatedAgents = [
        { ...agents[0], status: 'complete' },
        { ...agents[1], status: 'complete' },
      ]

      await wrapper.setProps({
        agents: updatedAgents,
        allAgentsComplete: true,
      })
      await nextTick()

      // Banner now shown
      expect(wrapper.find('.jobs-tab__complete-banner').exists()).toBe(true)
    })

    it('removes complete banner when agent starts working again', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'complete'),
        createMockAgent('implementor', 'complete'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: true,
        },
      })

      // Banner shown
      expect(wrapper.find('.jobs-tab__complete-banner').exists()).toBe(true)

      // One agent starts working again
      const updatedAgents = [{ ...agents[0], status: 'working' }, agents[1]]

      await wrapper.setProps({
        agents: updatedAgents,
        allAgentsComplete: false,
      })
      await nextTick()

      // Banner removed
      expect(wrapper.find('.jobs-tab__complete-banner').exists()).toBe(false)
    })
  })

  describe('Error Recovery and Resilience', () => {
    it('recovers from malformed agent data', async () => {
      const project = createMockProject()
      const agents = [
        createMockAgent('orchestrator', 'working'),
        { status: 'working' }, // Missing agent_display_name and job_id
      ]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Should still render without crashing
      expect(wrapper.exists()).toBe(true)
    })

    it('handles rapid prop changes without errors', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('orchestrator', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Rapidly change props
      for (let i = 0; i < 20; i++) {
        await wrapper.setProps({
          agents: [{ ...agents[0], progress: i * 5 }],
        })
      }

      // Should still be functional
      expect(wrapper.exists()).toBe(true)
      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').progress).toBe(95)
    })

    it('maintains functionality after error state', async () => {
      const project = createMockProject()
      const agents = [createMockAgent('implementor', 'working')]

      wrapper = mount(JobsTab, {
        props: {
          project,
          agents,
          messages: [],
          allAgentsComplete: false,
        },
      })

      // Agent encounters error
      await wrapper.setProps({
        agents: [{ ...agents[0], status: 'failed', block_reason: 'Error' }],
      })
      await nextTick()

      // User views error
      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      await agentCard.vm.$emit('view-error', agentCard.props('agent'))
      await nextTick()

      // Should still emit events correctly
      expect(wrapper.emitted('view-error')).toBeTruthy()

      // Agent recovers (hypothetically)
      await wrapper.setProps({
        agents: [{ ...agents[0], status: 'working', block_reason: null }],
      })
      await nextTick()

      // Should still be functional
      expect(wrapper.exists()).toBe(true)
    })
  })
})
