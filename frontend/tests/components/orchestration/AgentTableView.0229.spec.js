/**
 * AgentTableView.0229.spec.js
 *
 * Tests for Claude Subagents Toggle Integration (Handover 0229)
 * Testing toggle integration with table view: canLaunchAgent, canCopyPrompt, visual feedback
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'

// Mock useAgentData composable
vi.mock('@/composables/useAgentData', () => ({
  useAgentData: () => ({
    getStatusColor: (status) => status === 'complete' ? 'success' : 'primary',
    getAgentTypeColor: (type) => type === 'orchestrator' ? 'primary' : 'secondary',
    getAgentAbbreviation: (type) => type.substring(0, 2).toUpperCase(),
    getMessageCounts: () => ({ unread: 0, acknowledged: 0, total: 0 }),
    getHealthColor: () => 'success',
    getHealthIcon: () => 'mdi-check-circle'
  })
}))

describe('AgentTableView - Claude Subagents Toggle (Handover 0229)', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives
    })
  })

  /**
   * Test 1: canLaunchAgent - General Mode
   * All agents can be launched when toggle is OFF
   */
  describe('canLaunchAgent - General Mode', () => {
    it('should allow all non-terminal agents to be launched', () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false },
        { job_id: '3', agent_type: 'implementer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canLaunchAgent(agents[0])).toBe(true)
      expect(wrapper.vm.canLaunchAgent(agents[1])).toBe(true)
      expect(wrapper.vm.canLaunchAgent(agents[2])).toBe(true)
    })

    it('should NOT allow terminal state agents to be launched', () => {
      const terminalAgents = [
        { job_id: '1', agent_type: 'analyzer', status: 'complete', is_orchestrator: false },
        { job_id: '2', agent_type: 'analyzer', status: 'failed', is_orchestrator: false },
        { job_id: '3', agent_type: 'analyzer', status: 'cancelled', is_orchestrator: false },
        { job_id: '4', agent_type: 'analyzer', status: 'decommissioned', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents: terminalAgents,
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      terminalAgents.forEach(agent => {
        expect(wrapper.vm.canLaunchAgent(agent)).toBe(false)
      })
    })

    it('should NOT allow blocked agents to be launched', () => {
      const blockedAgent = { job_id: '1', agent_type: 'analyzer', status: 'blocked', is_orchestrator: false }

      wrapper = mount(AgentTableView, {
        props: {
          agents: [blockedAgent],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canLaunchAgent(blockedAgent)).toBe(false)
    })
  })

  /**
   * Test 2: canLaunchAgent - Claude Code Mode
   * Only orchestrator can be launched when toggle is ON
   */
  describe('canLaunchAgent - Claude Code Mode', () => {
    it('should allow ONLY orchestrator to be launched', () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false },
        { job_id: '3', agent_type: 'implementer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canLaunchAgent(agents[0])).toBe(true)   // Orchestrator
      expect(wrapper.vm.canLaunchAgent(agents[1])).toBe(false)  // Analyzer
      expect(wrapper.vm.canLaunchAgent(agents[2])).toBe(false)  // Implementer
    })

    it('should NOT allow terminal orchestrators to be launched', () => {
      const orchestrator = { job_id: '1', agent_type: 'orchestrator', status: 'complete', is_orchestrator: true }

      wrapper = mount(AgentTableView, {
        props: {
          agents: [orchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canLaunchAgent(orchestrator)).toBe(false)
    })
  })

  /**
   * Test 3: canCopyPrompt - General Mode
   * All non-decommissioned agents can copy prompt
   */
  describe('canCopyPrompt - General Mode', () => {
    it('should allow all non-decommissioned agents to copy prompt', () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'working', is_orchestrator: false },
        { job_id: '3', agent_type: 'implementer', status: 'complete', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canCopyPrompt(agents[0])).toBe(true)
      expect(wrapper.vm.canCopyPrompt(agents[1])).toBe(true)
      expect(wrapper.vm.canCopyPrompt(agents[2])).toBe(true)
    })

    it('should NOT allow decommissioned agents to copy prompt', () => {
      const decommissioned = { job_id: '1', agent_type: 'analyzer', status: 'decommissioned', is_orchestrator: false }

      wrapper = mount(AgentTableView, {
        props: {
          agents: [decommissioned],
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canCopyPrompt(decommissioned)).toBe(false)
    })
  })

  /**
   * Test 4: canCopyPrompt - Claude Code Mode
   * Only orchestrator can copy prompt when toggle is ON
   */
  describe('canCopyPrompt - Claude Code Mode', () => {
    it('should allow ONLY orchestrator to copy prompt', () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false },
        { job_id: '3', agent_type: 'implementer', status: 'working', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.canCopyPrompt(agents[0])).toBe(true)   // Orchestrator
      expect(wrapper.vm.canCopyPrompt(agents[1])).toBe(false)  // Analyzer
      expect(wrapper.vm.canCopyPrompt(agents[2])).toBe(false)  // Implementer
    })
  })

  /**
   * Test 5: Button Disabling
   * Launch buttons should be disabled based on canLaunchAgent result
   */
  describe('Button Disabling', () => {
    it('should disable launch button for non-orchestrators in Claude mode', async () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      // Find all launch buttons (there should be 2 for waiting agents)
      const launchButtons = wrapper.findAll('[icon="mdi-rocket-launch"]')
      expect(launchButtons).toHaveLength(2)

      // First button (orchestrator) should NOT be disabled
      expect(launchButtons[0].attributes('disabled')).toBeUndefined()

      // Second button (analyzer) should be disabled
      expect(launchButtons[1].attributes('disabled')).toBeDefined()
    })

    it('should enable all launch buttons in General mode', async () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const launchButtons = wrapper.findAll('[icon="mdi-rocket-launch"]')

      launchButtons.forEach(button => {
        expect(button.attributes('disabled')).toBeUndefined()
      })
    })
  })

  /**
   * Test 6: Row Visual Feedback
   * Disabled agent rows should have visual styling
   */
  describe('Row Visual Feedback', () => {
    it('should apply disabled-agent-row class to non-orchestrators in Claude mode', async () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      // Get row props for each agent
      const orchestratorRow = wrapper.vm.getRowProps({ item: agents[0] })
      const analyzerRow = wrapper.vm.getRowProps({ item: agents[1] })

      expect(orchestratorRow.class).not.toContain('disabled-agent-row')
      expect(analyzerRow.class).toContain('disabled-agent-row')
    })

    it('should NOT apply disabled-agent-row class in General mode', async () => {
      const agents = [
        { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs',
          usingClaudeCodeSubagents: false
        },
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const orchestratorRow = wrapper.vm.getRowProps({ item: agents[0] })
      const analyzerRow = wrapper.vm.getRowProps({ item: agents[1] })

      expect(orchestratorRow.class).not.toContain('disabled-agent-row')
      expect(analyzerRow.class).not.toContain('disabled-agent-row')
    })
  })

  /**
   * Test 7: Tooltip Text
   * Tooltips should explain why buttons are disabled
   */
  describe('Tooltip Text', () => {
    it('should show disabled message for non-orchestrators in Claude mode', () => {
      const analyzer = { job_id: '1', agent_type: 'analyzer', status: 'waiting', is_orchestrator: false }

      wrapper = mount(AgentTableView, {
        props: {
          agents: [analyzer],
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const disabledMessage = wrapper.vm.getLaunchTooltip(analyzer)
      expect(disabledMessage).toContain('Disabled in Claude Code mode')
    })

    it('should show launch message for orchestrator in Claude mode', () => {
      const orchestrator = { job_id: '1', agent_type: 'orchestrator', status: 'waiting', is_orchestrator: true }

      wrapper = mount(AgentTableView, {
        props: {
          agents: [orchestrator],
          mode: 'jobs',
          usingClaudeCodeSubagents: true
        },
        global: {
          plugins: [vuetify]
        }
      })

      const launchMessage = wrapper.vm.getLaunchTooltip(orchestrator)
      expect(launchMessage).toContain('Launch')
      expect(launchMessage).not.toContain('Disabled')
    })
  })
})
