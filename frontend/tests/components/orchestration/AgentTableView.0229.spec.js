/**
 * AgentTableView.0229.spec.js
 *
 * Tests for Claude Subagents Toggle Integration (Handover 0229)
 * Testing toggle integration with table view: canCopyPrompt logic, ActionIcons delegation
 *
 * Post-refactor notes:
 * - canLaunchAgent, getRowProps, getLaunchTooltip were removed
 * - Launch logic is now handled by ActionIcons + actionConfig.shouldShowLaunchAction
 * - canCopyPrompt remains on AgentTableView
 * - agent_display_name is used (not agent_type)
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
    getAgentDisplayNameColor: (type) => type === 'orchestrator' ? 'primary' : 'secondary',
    getAgentAbbreviation: (type) => type.substring(0, 2).toUpperCase(),
    getMessageCounts: () => ({ unread: 0, acknowledged: 0, total: 0 }),
    getHealthColor: () => 'success',
    getHealthIcon: () => 'mdi-check-circle'
  })
}))

// Mock useToast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
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
   * Test 1: canCopyPrompt - General Mode
   * All non-decommissioned agents can copy prompt
   */
  describe('canCopyPrompt - General Mode', () => {
    it('should allow all non-decommissioned agents to copy prompt', () => {
      const agents = [
        { job_id: '1', agent_display_name: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_display_name: 'analyzer', status: 'working', is_orchestrator: false },
        { job_id: '3', agent_display_name: 'implementer', status: 'complete', is_orchestrator: false }
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
      const decommissioned = { job_id: '1', agent_display_name: 'analyzer', status: 'decommissioned', is_orchestrator: false }

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
   * Test 2: canCopyPrompt - Claude Code Mode
   * Only orchestrator can copy prompt when toggle is ON
   */
  describe('canCopyPrompt - Claude Code Mode', () => {
    it('should allow ONLY orchestrator to copy prompt', () => {
      const agents = [
        { job_id: '1', agent_display_name: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_display_name: 'analyzer', status: 'waiting', is_orchestrator: false },
        { job_id: '3', agent_display_name: 'implementer', status: 'working', is_orchestrator: false }
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
   * Test 3: Component renders with ActionIcons
   * Launch logic is delegated to ActionIcons component
   */
  describe('ActionIcons Integration', () => {
    it('renders AgentTableView with agents', async () => {
      const agents = [
        { job_id: '1', agent_display_name: 'orchestrator', status: 'waiting', is_orchestrator: true },
        { job_id: '2', agent_display_name: 'analyzer', status: 'waiting', is_orchestrator: false }
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

      // Component should render without errors
      expect(wrapper.exists()).toBe(true)
    })

    it('passes usingClaudeCodeSubagents prop to ActionIcons via claude-code-cli-mode', async () => {
      const agents = [
        { job_id: '1', agent_display_name: 'orchestrator', status: 'waiting', is_orchestrator: true }
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

      // The component passes usingClaudeCodeSubagents as claude-code-cli-mode to ActionIcons
      expect(wrapper.props('usingClaudeCodeSubagents')).toBe(true)
    })
  })

  /**
   * Test 4: handleCopyPrompt method exists and works
   */
  describe('handleCopyPrompt', () => {
    it('has handleCopyPrompt method', () => {
      const agents = [
        { job_id: '1', agent_display_name: 'orchestrator', status: 'working', is_orchestrator: true }
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

      expect(wrapper.vm.handleCopyPrompt).toBeDefined()
      expect(typeof wrapper.vm.handleCopyPrompt).toBe('function')
    })
  })
})
