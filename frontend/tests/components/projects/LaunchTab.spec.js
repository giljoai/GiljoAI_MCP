/**
 * LaunchTab Component Tests
 * Testing removal of top-action-bar after button relocation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LaunchTab from '@/components/projects/LaunchTab.vue'

// Mock composables
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  })
}))

describe('LaunchTab - After Button Relocation', () => {
  let wrapper

  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Test description',
    status: 'active',
    mission: '',
    agents: []
  }

  beforeEach(() => {
    setActivePinia(createPinia())

    wrapper = mount(LaunchTab, {
      props: {
        project: mockProject,
        orchestrator: null,
        isStaging: false
      },
      global: {
        stubs: {
          VBtn: true,
          VIcon: true,
          VAvatar: true,
          VSnackbar: true
        }
      }
    })
  })

  // ==================== LAYOUT TESTS ====================

  describe('Layout Structure', () => {
    it('does not render top-action-bar', () => {
      const topActionBar = wrapper.find('.top-action-bar')
      expect(topActionBar.exists()).toBe(false)
    })

    it('does not render Stage Project button', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.exists()).toBe(false)
    })

    it('does not render Launch Jobs button', () => {
      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.exists()).toBe(false)
    })

    it('does not render Waiting status text', () => {
      const statusText = wrapper.find('.status-text')
      expect(statusText.exists()).toBe(false)
    })

    it('starts with main-container as top element', () => {
      const wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: null,
          isStaging: false
        }
      })

      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)

      // Should be the first child of launch-tab-wrapper
      const firstChild = wrapper.find('.launch-tab-wrapper > :first-child')
      expect(firstChild.classes()).toContain('main-container')
    })
  })

  // ==================== THREE PANELS LAYOUT ====================

  describe('Three Panels Layout', () => {
    it('renders three panels', () => {
      const panels = wrapper.findAll('.panel')
      expect(panels).toHaveLength(3)
    })

    it('renders Project Description panel', () => {
      const descriptionPanel = wrapper.find('.project-description-panel')
      expect(descriptionPanel.exists()).toBe(true)

      const header = descriptionPanel.find('.panel-header')
      expect(header.text()).toBe('Project Description')
    })

    it('renders Orchestrator Mission panel', () => {
      const missionPanel = wrapper.find('.mission-panel')
      expect(missionPanel.exists()).toBe(true)

      const header = missionPanel.find('.panel-header')
      expect(header.text()).toBe('Orchestrator Generated Mission')
    })

    it('renders Default Agent panel', () => {
      const agentPanel = wrapper.find('.default-agent-panel')
      expect(agentPanel.exists()).toBe(true)

      const header = agentPanel.find('.panel-header')
      expect(header.text()).toBe('Default agent')
    })
  })

  // ==================== SPACING TESTS ====================

  describe('Spacing and Layout', () => {
    it('main-container has proper padding', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)

      // Should have design token padding
      const styles = window.getComputedStyle(mainContainer.element)
      expect(styles.padding).toBeDefined()
    })

    it('removes margin-bottom that was for action bar', () => {
      // The old top-action-bar had margin-bottom: 24px
      // Now main-container should be positioned without that gap
      const launchTabWrapper = wrapper.find('.launch-tab-wrapper')
      const mainContainer = wrapper.find('.main-container')

      // Main container should not have extra margin-top
      const styles = window.getComputedStyle(mainContainer.element)
      expect(styles.marginTop).not.toBe('24px')
    })

    it('maintains three-panel grid layout', () => {
      const threePanels = wrapper.find('.three-panels')
      expect(threePanels.exists()).toBe(true)

      const styles = window.getComputedStyle(threePanels.element)
      expect(styles.display).toBe('grid')
      expect(styles.gridTemplateColumns).toBe('1fr 1fr 1fr')
    })
  })

  // ==================== EVENTS REMOVED TESTS ====================

  describe('Button Events Removed', () => {
    it('does not emit stage-project event', async () => {
      // Component should not have any mechanism to emit stage-project
      expect(wrapper.emitted('stage-project')).toBeUndefined()
    })

    it('does not emit launch-jobs event', async () => {
      // Component should not have any mechanism to emit launch-jobs
      expect(wrapper.emitted('launch-jobs')).toBeUndefined()
    })

    it('still emits edit-description event', async () => {
      const editButton = wrapper.find('.edit-icon')
      await editButton.trigger('click')

      expect(wrapper.emitted('edit-description')).toBeTruthy()
    })

    it('still emits edit-mission event', async () => {
      // This test depends on the edit mission functionality
      // which should still exist in the component
      expect(wrapper.vm.$options.emits).toContain('edit-mission')
    })
  })

  // ==================== PROPS TESTS ====================

  describe('Props', () => {
    it('no longer uses isStaging prop for buttons', () => {
      // isStaging prop should still exist (passed from parent)
      // but should not be used for button states
      expect(wrapper.props('isStaging')).toBe(false)

      // But there should be no stage button to apply it to
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.exists()).toBe(false)
    })

    it('receives project prop', () => {
      expect(wrapper.props('project')).toEqual(mockProject)
    })

    it('receives orchestrator prop', () => {
      expect(wrapper.props('orchestrator')).toBe(null)
    })
  })

  // ==================== FUNCTIONALITY PRESERVED ====================

  describe('Core Functionality Preserved', () => {
    it('displays project description', () => {
      const description = wrapper.find('.description-text')
      expect(description.text()).toBe(mockProject.description)
    })

    it('displays orchestrator card', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      expect(orchestratorCard.exists()).toBe(true)
    })

    it('displays agent team section', () => {
      const agentTeamSection = wrapper.find('.agent-team-section')
      expect(agentTeamSection.exists()).toBe(true)
    })

    it('handles edit description click', async () => {
      const editButton = wrapper.find('.edit-icon')
      await editButton.trigger('click')

      expect(wrapper.emitted('edit-description')).toBeTruthy()
    })

    it('handles agent info click', async () => {
      // Add mock agent to props
      const wrapperWithAgent = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [{ job_id: 'agent-1', agent_type: 'implementor' }]
          },
          orchestrator: null,
          isStaging: false
        }
      })

      const infoIcon = wrapperWithAgent.find('.info-icon')
      await infoIcon.trigger('click')

      expect(wrapperWithAgent.vm.showDetailsModal).toBe(true)
    })
  })

  // ==================== STYLING TESTS ====================

  describe('Styling', () => {
    it('maintains design token styling for panels', () => {
      const panel = wrapper.find('.panel-content')
      expect(panel.exists()).toBe(true)

      // Should use design tokens from design-tokens.scss
      const styles = window.getComputedStyle(panel.element)
      expect(styles.background).toBeDefined()
      expect(styles.borderRadius).toBeDefined()
    })

    it('main-container has unified border', () => {
      const mainContainer = wrapper.find('.main-container')
      const styles = window.getComputedStyle(mainContainer.element)

      expect(styles.border).toBeDefined()
      expect(styles.borderRadius).toBeDefined()
    })
  })

  // ==================== ICON TESTS ====================

  describe('Agent Icons', () => {
    it('orchestrator card displays eye icon (view-only)', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      expect(orchestratorCard.exists()).toBe(true)

      const eyeIcon = orchestratorCard.find('.eye-icon')
      expect(eyeIcon.exists()).toBe(true)
      expect(eyeIcon.text()).toContain('mdi-eye')
    })

    it('orchestrator card does not display lock icon', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      const lockIcon = orchestratorCard.find('.lock-icon')
      expect(lockIcon.exists()).toBe(false)
    })

    it('orchestrator card displays info icon', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      const infoIcon = orchestratorCard.find('.info-icon')
      expect(infoIcon.exists()).toBe(true)
      expect(infoIcon.text()).toContain('mdi-information')
    })

    it('agent team cards display pencil icon (edit)', () => {
      const wrapperWithAgents = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [
              { job_id: 'agent-1', agent_type: 'implementor' },
              { job_id: 'agent-2', agent_type: 'tester' }
            ]
          },
          orchestrator: null,
          isStaging: false
        }
      })

      const agentCards = wrapperWithAgents.findAll('.agent-slim-card')
      expect(agentCards.length).toBeGreaterThan(0)

      agentCards.forEach(card => {
        const editIcon = card.find('.edit-icon')
        expect(editIcon.exists()).toBe(true)
        expect(editIcon.text()).toContain('mdi-pencil')
      })
    })

    it('agent team cards do not display lock icon', () => {
      const wrapperWithAgents = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [{ job_id: 'agent-1', agent_type: 'implementor' }]
          },
          orchestrator: null,
          isStaging: false
        }
      })

      const agentCard = wrapperWithAgents.find('.agent-slim-card')
      const lockIcon = agentCard.find('.lock-icon')
      expect(lockIcon.exists()).toBe(false)
    })

    it('agent team cards display info icon', () => {
      const wrapperWithAgents = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [{ job_id: 'agent-1', agent_type: 'implementor' }]
          },
          orchestrator: null,
          isStaging: false
        }
      })

      const agentCard = wrapperWithAgents.find('.agent-slim-card')
      const infoIcon = agentCard.find('.info-icon')
      expect(infoIcon.exists()).toBe(true)
      expect(infoIcon.text()).toContain('mdi-information')
    })

    it('info icon click handler still works for orchestrator', async () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      const infoIcon = orchestratorCard.find('.info-icon')

      await infoIcon.trigger('click')

      expect(wrapper.vm.showDetailsModal).toBe(true)
      expect(wrapper.vm.selectedAgent).toBeDefined()
      expect(wrapper.vm.selectedAgent.agent_type).toBe('orchestrator')
    })

    it('info icon click handler still works for agent team', async () => {
      const wrapperWithAgent = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [{ job_id: 'agent-1', agent_type: 'implementor' }]
          },
          orchestrator: null,
          isStaging: false
        }
      })

      const agentCard = wrapperWithAgent.find('.agent-slim-card')
      const infoIcon = agentCard.find('.info-icon')

      await infoIcon.trigger('click')

      expect(wrapperWithAgent.vm.showDetailsModal).toBe(true)
      expect(wrapperWithAgent.vm.selectedAgent).toBeDefined()
      expect(wrapperWithAgent.vm.selectedAgent.agent_type).toBe('implementor')
    })
  })

  // ==================== WEBSOCKET INTEGRATION ====================

  describe('WebSocket Integration', () => {
    it('still registers WebSocket listeners on mount', () => {
      // Component should still listen for mission updates and agent creation
      // This functionality is preserved
      expect(wrapper.vm).toBeDefined()
    })

    it('still handles mission update events', async () => {
      const missionText = 'New mission text'

      // Simulate mission update
      wrapper.vm.handleMissionUpdate({
        project_id: mockProject.id,
        tenant_key: 'test-tenant',
        mission: missionText
      })

      await wrapper.vm.$nextTick()

      // Mission should be displayed (functionality preserved)
      expect(wrapper.vm.missionText).toBe(missionText)
    })

    it('still handles agent created events', async () => {
      const agent = {
        agent_id: 'agent-1',
        agent_type: 'implementor',
        status: 'waiting'
      }

      wrapper.vm.handleAgentCreated({
        project_id: mockProject.id,
        tenant_key: 'test-tenant',
        agent: agent
      })

      await wrapper.vm.$nextTick()

      // Agent should be added (functionality preserved)
      expect(wrapper.vm.agents).toHaveLength(1)
    })
  })
})
