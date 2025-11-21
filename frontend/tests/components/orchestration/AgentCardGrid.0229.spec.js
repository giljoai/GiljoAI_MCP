/**
 * AgentCardGrid.0229.spec.js
 *
 * Tests for Claude Subagents Toggle Integration with AgentCardGrid (Handover 0229)
 * Testing behavior: canLaunchAgent(), canCopyPrompt(), visual feedback, button states
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import AgentCardGrid from '@/components/orchestration/AgentCardGrid.vue'

// Mock components
vi.mock('@/components/AgentCard.vue', () => ({
  default: {
    name: 'AgentCard',
    template: '<div class="mock-agent-card"></div>',
    props: ['agent', 'unreadCount', 'isExpanded']
  }
}))

vi.mock('@/components/orchestration/OrchestratorCard.vue', () => ({
  default: {
    name: 'OrchestratorCard',
    template: '<div class="mock-orchestrator-card"></div>',
    props: ['orchestrator', 'project']
  }
}))

vi.mock('@/components/orchestration/AgentTableView.vue', () => ({
  default: {
    name: 'AgentTableView',
    template: '<div class="mock-agent-table-view"></div>',
    props: ['agents', 'mode', 'usingClaudeCodeSubagents']
  }
}))

// Mock composables
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn()
  })
}))

// Mock stores
vi.mock('@/stores/orchestration', () => ({
  useOrchestrationStore: () => ({
    orchestrator: null,
    regularAgents: []
  })
}))

describe('AgentCardGrid - Claude Subagents Toggle Integration (Handover 0229)', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    setActivePinia(createPinia())
  })

  /**
   * Test 1: Prop Acceptance
   * Verify that AgentCardGrid accepts usingClaudeCodeSubagents prop
   */
  describe('Prop Acceptance', () => {
    it('should accept usingClaudeCodeSubagents prop with default false', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid'
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Component should have usingClaudeCodeSubagents prop (default false)
      expect(wrapper.props('usingClaudeCodeSubagents')).toBeDefined()
    })

    it('should accept usingClaudeCodeSubagents=true from parent', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.props('usingClaudeCodeSubagents')).toBe(true)
    })

    it('should accept usingClaudeCodeSubagents=false from parent', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.props('usingClaudeCodeSubagents')).toBe(false)
    })
  })

  /**
   * Test 2: canLaunchAgent() Method - General Mode
   * Verify that all agents can be launched when toggle is OFF
   */
  describe('canLaunchAgent() - General CLI Mode', () => {
    it('should return true for orchestrator in General mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const orchestrator = {
        agent_type: 'orchestrator',
        status: 'waiting',
        is_orchestrator: true
      }

      expect(wrapper.vm.canLaunchAgent(orchestrator)).toBe(true)
    })

    it('should return true for non-orchestrator agents in General mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const analyzer = {
        agent_type: 'analyzer',
        status: 'waiting',
        is_orchestrator: false
      }

      const implementer = {
        agent_type: 'implementer',
        status: 'waiting',
        is_orchestrator: false
      }

      expect(wrapper.vm.canLaunchAgent(analyzer)).toBe(true)
      expect(wrapper.vm.canLaunchAgent(implementer)).toBe(true)
    })

    it('should return false for terminal states in General mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned']

      terminalStates.forEach(status => {
        const agent = {
          agent_type: 'analyzer',
          status,
          is_orchestrator: false
        }
        expect(wrapper.vm.canLaunchAgent(agent)).toBe(false)
      })
    })
  })

  /**
   * Test 3: canLaunchAgent() Method - Claude Code Mode
   * Verify that only orchestrators can be launched when toggle is ON
   */
  describe('canLaunchAgent() - Claude Code Mode', () => {
    it('should return true for orchestrator in Claude Code mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const orchestrator = {
        agent_type: 'orchestrator',
        status: 'waiting',
        is_orchestrator: true
      }

      expect(wrapper.vm.canLaunchAgent(orchestrator)).toBe(true)
    })

    it('should return false for non-orchestrators in Claude Code mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const analyzer = {
        agent_type: 'analyzer',
        status: 'waiting',
        is_orchestrator: false
      }

      const implementer = {
        agent_type: 'implementer',
        status: 'waiting',
        is_orchestrator: false
      }

      expect(wrapper.vm.canLaunchAgent(analyzer)).toBe(false)
      expect(wrapper.vm.canLaunchAgent(implementer)).toBe(false)
    })

    it('should return false for blocked agents in Claude Code mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const blockedAgent = {
        agent_type: 'analyzer',
        status: 'blocked',
        is_orchestrator: false
      }

      expect(wrapper.vm.canLaunchAgent(blockedAgent)).toBe(false)
    })
  })

  /**
   * Test 4: canCopyPrompt() Method
   * Verify that prompt copying respects toggle state
   */
  describe('canCopyPrompt() Method', () => {
    it('should return true for all agents in General mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const orchestrator = {
        agent_type: 'orchestrator',
        status: 'waiting',
        is_orchestrator: true
      }

      const analyzer = {
        agent_type: 'analyzer',
        status: 'waiting',
        is_orchestrator: false
      }

      expect(wrapper.vm.canCopyPrompt(orchestrator)).toBe(true)
      expect(wrapper.vm.canCopyPrompt(analyzer)).toBe(true)
    })

    it('should return false for decommissioned agents', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      const decommissioned = {
        agent_type: 'analyzer',
        status: 'decommissioned',
        is_orchestrator: false
      }

      expect(wrapper.vm.canCopyPrompt(decommissioned)).toBe(false)
    })

    it('should return true for orchestrator in Claude Code mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const orchestrator = {
        agent_type: 'orchestrator',
        status: 'waiting',
        is_orchestrator: true
      }

      expect(wrapper.vm.canCopyPrompt(orchestrator)).toBe(true)
    })

    it('should return false for non-orchestrators in Claude Code mode', () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const analyzer = {
        agent_type: 'analyzer',
        status: 'waiting',
        is_orchestrator: false
      }

      expect(wrapper.vm.canCopyPrompt(analyzer)).toBe(false)
    })
  })

  /**
   * Test 5: Prop Passing to AgentTableView
   * Verify that toggle state is passed to table view
   */
  describe('Prop Passing to AgentTableView', () => {
    it('should pass usingClaudeCodeSubagents to AgentTableView', async () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      expect(tableView.exists()).toBe(true)
      expect(tableView.props('usingClaudeCodeSubagents')).toBe(true)
    })

    it('should update AgentTableView prop when toggle changes', async () => {
      wrapper = mount(AgentCardGrid, {
        props: {
          projectId: 'test-uuid',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      expect(tableView.props('usingClaudeCodeSubagents')).toBe(false)

      // Update prop
      await wrapper.setProps({ usingClaudeCodeSubagents: true })

      expect(tableView.props('usingClaudeCodeSubagents')).toBe(true)
    })
  })
})
