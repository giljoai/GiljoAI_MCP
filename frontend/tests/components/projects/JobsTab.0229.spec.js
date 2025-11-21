/**
 * JobsTab.0229.spec.js
 *
 * Tests for Claude Subagents Toggle (Handover 0229)
 * Testing behavior: toggle changes button availability, visual feedback, state persistence
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import JobsTab from '@/components/projects/JobsTab.vue'

// Mock AgentCard component
vi.mock('@/components/AgentCard.vue', () => ({
  default: {
    name: 'AgentCard',
    template: '<div class="mock-agent-card"></div>',
    props: ['agent', 'mode', 'instanceNumber', 'isOrchestrator', 'showCloseoutButton', 'promptButtonDisabled']
  }
}))

// Mock MessageStream and MessageInput
vi.mock('@/components/MessageStream.vue', () => ({
  default: {
    name: 'MessageStream',
    template: '<div class="mock-message-stream"></div>',
    props: ['messages', 'projectId', 'autoScroll', 'loading']
  }
}))

vi.mock('@/components/MessageInput.vue', () => ({
  default: {
    name: 'MessageInput',
    template: '<div class="mock-message-input"></div>',
    props: ['disabled']
  }
}))

// Mock useWebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    sendMessage: vi.fn()
  })
}))

describe('JobsTab - Claude Subagents Toggle (Handover 0229)', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    // Create fresh Vuetify instance
    vuetify = createVuetify({
      components,
      directives
    })

    // Create fresh Pinia store
    setActivePinia(createPinia())

    // Clear localStorage
    localStorage.clear()
  })

  /**
   * Test 1: Toggle Rendering
   * Verify that toggle component exists and renders correctly
   */
  describe('Toggle Rendering', () => {
    it('should render toggle card with Launch Mode header', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Check that toggle card exists with Launch Mode header
      const toggleCard = wrapper.find('.claude-code-toggle')
      expect(toggleCard.exists()).toBe(true)
      expect(toggleCard.text()).toContain('Launch Mode')
    })

    it('should display hint text explaining current mode', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      const hintText = wrapper.find('.text-caption')
      expect(hintText.exists()).toBe(true)
      expect(hintText.text()).toBeTruthy()
      expect(hintText.text()).toContain('mode')
    })
  })

  /**
   * Test 2: Toggle State Changes
   * Verify that switching updates usingClaudeCodeSubagents
   */
  describe('Toggle State Changes', () => {
    it('should default to false (General CLI mode)', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
    })

    it('should toggle state when switch is clicked', async () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)

      // Toggle switch
      wrapper.vm.usingClaudeCodeSubagents = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(true)

      // Toggle back
      wrapper.vm.usingClaudeCodeSubagents = false
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.usingClaudeCodeSubagents).toBe(false)
    })
  })

  /**
   * Test 3: Hint Text Updates
   * Verify that computed toggleHintText changes based on state
   */
  describe('Hint Text Updates', () => {
    it('should show General CLI hint when toggle is OFF', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = false
      expect(wrapper.vm.toggleHintText).toContain('Normal mode')
      expect(wrapper.vm.toggleHintText).toContain('independent')
    })

    it('should show Claude Code hint when toggle is ON', async () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toggleHintText).toContain('Claude Code')
      expect(wrapper.vm.toggleHintText).toContain('subagent')
    })
  })

  /**
   * Test 4: shouldDisablePromptButton Logic
   * Verify that shouldDisablePromptButton returns correct values
   */
  describe('shouldDisablePromptButton Logic', () => {
    it('should NOT disable any agents in General CLI mode', () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = false

      const orchestrator = { agent_type: 'orchestrator', status: 'waiting' }
      const analyzer = { agent_type: 'analyzer', status: 'waiting' }
      const implementer = { agent_type: 'implementer', status: 'waiting' }

      expect(wrapper.vm.shouldDisablePromptButton(orchestrator)).toBe(false)
      expect(wrapper.vm.shouldDisablePromptButton(analyzer)).toBe(false)
      expect(wrapper.vm.shouldDisablePromptButton(implementer)).toBe(false)
    })

    it('should disable non-orchestrators in Claude Code mode', async () => {
      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents: []
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = true
      await wrapper.vm.$nextTick()

      const orchestrator = { agent_type: 'orchestrator', status: 'waiting' }
      const analyzer = { agent_type: 'analyzer', status: 'waiting' }
      const implementer = { agent_type: 'implementer', status: 'waiting' }

      expect(wrapper.vm.shouldDisablePromptButton(orchestrator)).toBe(false)
      expect(wrapper.vm.shouldDisablePromptButton(analyzer)).toBe(true)
      expect(wrapper.vm.shouldDisablePromptButton(implementer)).toBe(true)
    })
  })

  /**
   * Test 5: AgentCard Prop Passing
   * Verify that promptButtonDisabled is passed to AgentCard components
   */
  describe('AgentCard Prop Passing', () => {
    it('should pass promptButtonDisabled=false to all cards in General mode', () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting' },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting' }
      ]

      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = false

      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })
      expect(agentCards).toHaveLength(2)

      agentCards.forEach(card => {
        expect(card.props('promptButtonDisabled')).toBe(false)
      })
    })

    it('should pass promptButtonDisabled=true to non-orchestrators in Claude mode', async () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting' },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting' }
      ]

      wrapper = mount(JobsTab, {
        props: {
          project: { project_id: 'test-uuid', name: 'Test Project' },
          agents
        },
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.usingClaudeCodeSubagents = true
      await wrapper.vm.$nextTick()

      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })

      // First card (orchestrator) should NOT be disabled
      expect(agentCards[0].props('promptButtonDisabled')).toBe(false)

      // Second card (analyzer) should be disabled
      expect(agentCards[1].props('promptButtonDisabled')).toBe(true)
    })
  })
})
