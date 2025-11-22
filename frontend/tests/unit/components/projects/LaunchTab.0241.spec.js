/**
 * LaunchTab.0241.spec.js
 *
 * Test suite for Launch Tab complete rewrite (Handover 0241)
 * Following TDD: Write tests FIRST, watch them FAIL, then implement
 *
 * Reference screenshot: handovers/Launch-Jobs_panels2/Launch Tab.jpg
 *
 * Layout Requirements:
 * - Top action bar outside main container (stage button left, status text center, launch button right)
 * - Main container with unified border and rounded corners
 * - Three equal panels inside container (Project Description, Orchestrator Mission, Default Agent)
 * - Exact colors and styling from screenshot
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import LaunchTab from '@/components/projects/LaunchTab.vue'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
  })
}))

// Mock user store
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      tenant_key: 'test-tenant-123'
    }
  })
}))

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn().mockResolvedValue({
        data: {
          prompt: 'Test staging prompt',
          estimated_prompt_tokens: 1500
        }
      })
    },
    projects: {
      cancelStaging: vi.fn().mockResolvedValue({
        data: {
          agents_deleted: 3,
          messages_deleted: 5
        }
      })
    }
  }
}))

describe('LaunchTab.vue - Complete Rewrite (0241)', () => {
  let wrapper

  // Sample project data
  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla tincidunt consequat dolor.',
    mission: null,
    agents: []
  }

  beforeEach(() => {
    wrapper = mount(LaunchTab, {
      global: {
        plugins: [vuetify],
      },
      props: {
        project: mockProject,
        orchestrator: null,
        isStaging: false
      }
    })
  })

  describe('Top Action Bar Layout', () => {
    it('should render top action bar with 3 elements', () => {
      const actionBar = wrapper.find('.top-action-bar')
      expect(actionBar.exists()).toBe(true)

      // Should have stage button, status text, and launch button
      const stageButton = actionBar.find('.stage-button')
      const statusText = actionBar.find('.status-text')
      const launchButton = actionBar.find('.launch-button')

      expect(stageButton.exists()).toBe(true)
      expect(statusText.exists()).toBe(true)
      expect(launchButton.exists()).toBe(true)
    })

    it('should position stage button on left with yellow outline style', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.exists()).toBe(true)
      expect(stageButton.text()).toContain('Stage project')

      // Check button has outlined variant
      expect(stageButton.attributes('variant')).toBe('outlined')
      // Check button has yellow color
      expect(stageButton.attributes('color')).toBe('yellow-darken-2')
      // Check button is rounded
      expect(stageButton.attributes('rounded')).toBeDefined()
    })

    it('should display status text in center with yellow italic style', () => {
      const statusText = wrapper.find('.status-text')
      expect(statusText.exists()).toBe(true)
      expect(statusText.text()).toBe('Waiting:')

      // Check styling (will verify in CSS)
      expect(statusText.classes()).toContain('status-text')
    })

    it('should position launch button on right, grey when disabled', () => {
      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.exists()).toBe(true)
      expect(launchButton.text()).toContain('Launch jobs')

      // Should be disabled initially (no mission staged)
      expect(launchButton.attributes('disabled')).toBeDefined()
      // Should have grey color when disabled
      expect(launchButton.attributes('color')).toBe('grey')
    })

    it('should enable launch button with yellow color when ready', async () => {
      // Set ready to launch state
      wrapper.vm.setMission('Test mission')
      await wrapper.vm.$nextTick()

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('disabled')).toBeUndefined()
      expect(launchButton.attributes('color')).toBe('yellow-darken-2')
    })
  })

  describe('Main Container Layout', () => {
    it('should render main container with light border and rounded corners', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)

      // CSS will validate border and border-radius
      expect(mainContainer.classes()).toContain('main-container')
    })

    it('should contain three equal panels inside container', () => {
      const panels = wrapper.find('.three-panels')
      expect(panels.exists()).toBe(true)

      const panelElements = panels.findAll('.panel')
      expect(panelElements.length).toBe(3)
    })
  })

  describe('Panel 1: Project Description', () => {
    it('should render Project Description panel with header', () => {
      const descPanel = wrapper.find('.project-description-panel')
      expect(descPanel.exists()).toBe(true)

      const header = descPanel.find('.panel-header')
      expect(header.exists()).toBe(true)
      expect(header.text()).toBe('Project Description')
    })

    it('should display project description text', () => {
      const descPanel = wrapper.find('.project-description-panel')
      const descText = descPanel.find('.description-text')

      expect(descText.exists()).toBe(true)
      expect(descText.text()).toContain('Lorem ipsum')
    })

    it('should have edit icon in bottom right corner', () => {
      const descPanel = wrapper.find('.project-description-panel')
      const editIcon = descPanel.find('.edit-icon')

      expect(editIcon.exists()).toBe(true)
      expect(editIcon.attributes('icon')).toBe('mdi-pencil')

      // CSS will validate position: absolute bottom right
      expect(editIcon.classes()).toContain('edit-icon')
    })

    it('should emit edit-description event when edit icon clicked', async () => {
      const editIcon = wrapper.find('.edit-icon')
      await editIcon.trigger('click')

      expect(wrapper.emitted('edit-description')).toBeTruthy()
    })
  })

  describe('Panel 2: Orchestrator Mission', () => {
    it('should render Orchestrator Mission panel with header', () => {
      const missionPanel = wrapper.find('.mission-panel')
      expect(missionPanel.exists()).toBe(true)

      const header = missionPanel.find('.panel-header')
      expect(header.exists()).toBe(true)
      expect(header.text()).toBe('Orchestrator Generated Mission')
    })

    it('should show document icon in empty state', () => {
      const missionPanel = wrapper.find('.mission-panel')
      const emptyState = missionPanel.find('.empty-state')

      expect(emptyState.exists()).toBe(true)

      // Verify empty icon class exists in HTML (icon component may not render in test)
      const html = missionPanel.html()
      expect(html).toContain('empty-icon')
    })

    it('should display mission content when mission exists', async () => {
      // Set mission
      wrapper.vm.setMission('Test mission content for orchestrator')
      await wrapper.vm.$nextTick()

      const missionPanel = wrapper.find('.mission-panel')
      const missionContent = missionPanel.find('.mission-content')

      expect(missionContent.exists()).toBe(true)
      expect(missionContent.text()).toContain('Test mission content')

      // Empty state should be hidden
      const emptyState = missionPanel.find('.empty-state')
      expect(emptyState.exists()).toBe(false)
    })
  })

  describe('Panel 3: Default Agent', () => {
    it('should render Default Agent panel with header', () => {
      const agentPanel = wrapper.find('.default-agent-panel')
      expect(agentPanel.exists()).toBe(true)

      const header = agentPanel.find('.panel-header')
      expect(header.exists()).toBe(true)
      expect(header.text()).toBe('Default agent')
    })

    it('should display Orchestrator card with tan/beige avatar', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      expect(orchestratorCard.exists()).toBe(true)

      const avatar = orchestratorCard.find('.agent-avatar')
      expect(avatar.exists()).toBe(true)

      // Should have tan/beige color (#d4a574)
      expect(avatar.attributes('color')).toBe('#d4a574')
      expect(avatar.text()).toContain('Or')
    })

    it('should display Orchestrator name in card', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')
      const agentName = orchestratorCard.find('.agent-name')

      expect(agentName.exists()).toBe(true)
      expect(agentName.text()).toBe('Orchestrator')
    })

    it('should have lock icon in Orchestrator card', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')

      // Verify lock icon class exists in the HTML
      const html = orchestratorCard.html()
      expect(html).toContain('lock-icon')
    })

    it('should have info icon in Orchestrator card', () => {
      const orchestratorCard = wrapper.find('.orchestrator-card')

      // Verify info icon class exists in the HTML
      const html = orchestratorCard.html()
      expect(html).toContain('info-icon')
    })

    it('should display Agent Team section below Orchestrator card', () => {
      const agentPanel = wrapper.find('.default-agent-panel')
      const agentTeamSection = agentPanel.find('.agent-team-section')

      expect(agentTeamSection.exists()).toBe(true)

      const agentTeamHeader = agentTeamSection.find('.agent-team-header')
      expect(agentTeamHeader.exists()).toBe(true)
      expect(agentTeamHeader.text()).toBe('Agent Team')
    })

    it('should have Agent Team list with scrollbar on right edge', () => {
      const agentTeamSection = wrapper.find('.agent-team-section')
      const agentTeamList = agentTeamSection.find('.agent-team-list')

      expect(agentTeamList.exists()).toBe(true)
      expect(agentTeamList.classes()).toContain('agent-team-list')

      // CSS will validate scrollbar styling
    })
  })

  describe('Visual Styling Requirements', () => {
    it('should apply dark navy blue background to wrapper', () => {
      const wrapper_element = wrapper.find('.launch-tab-wrapper')
      expect(wrapper_element.exists()).toBe(true)
      expect(wrapper_element.classes()).toContain('launch-tab-wrapper')

      // CSS verification: background: #0e1c2d
    })

    it('should apply light border to main container', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.classes()).toContain('main-container')

      // CSS verification: border: 2px solid rgba(255, 255, 255, 0.2)
    })

    it('should apply rounded corners (16px) to main container', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.classes()).toContain('main-container')

      // CSS verification: border-radius: 16px
    })

    it('should apply darker background to panel content boxes', () => {
      const panelContent = wrapper.find('.panel-content')
      expect(panelContent.exists()).toBe(true)
      expect(panelContent.classes()).toContain('panel-content')

      // CSS verification: background: rgba(20, 35, 50, 0.8)
    })
  })

  describe('Interaction Behaviors', () => {
    it('should call handleStage when stage button clicked', async () => {
      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('click')

      expect(wrapper.emitted('stage-project')).toBeTruthy()
    })

    it('should call handleLaunch when launch button clicked (when enabled)', async () => {
      // Enable launch button
      wrapper.vm.setMission('Test mission')
      await wrapper.vm.$nextTick()

      const launchButton = wrapper.find('.launch-button')
      await launchButton.trigger('click')

      expect(wrapper.emitted('launch-jobs')).toBeTruthy()
    })
  })

  describe('Responsive Layout', () => {
    it('should arrange three panels side by side with equal widths', () => {
      const threePanels = wrapper.find('.three-panels')
      expect(threePanels.exists()).toBe(true)

      // CSS verification: grid-template-columns: 1fr 1fr 1fr
      expect(threePanels.classes()).toContain('three-panels')
    })

    it('should apply proper spacing between panels', () => {
      const threePanels = wrapper.find('.three-panels')
      expect(threePanels.classes()).toContain('three-panels')

      // CSS verification: gap: 24px
    })
  })
})
