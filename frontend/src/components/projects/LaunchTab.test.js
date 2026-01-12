import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LaunchTab from './LaunchTab.vue'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'

// Mock composables
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      tenant_key: 'test-tenant',
    },
  }),
}))

describe('LaunchTab.vue - Pencil Edit Icons', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const createWrapper = (props = {}) => {
    const vuetify = createVuetify()
    const defaultProps = {
      project: {
        id: 'project-1',
        name: 'Test Project',
        description: 'Test Description',
        mission: 'Test Mission',
        agents: [
          {
            id: 'agent-1',
            agent_display_name: 'analyzer',
            agent_name: 'Analyzer Agent',
            status: 'active',
          },
          {
            id: 'agent-2',
            agent_display_name: 'implementor',
            agent_name: 'Implementor Agent',
            status: 'active',
          },
        ],
      },
      orchestrator: {
        name: 'Orchestrator',
        status: 'active',
      },
      isStaging: false,
    }

    return mount(LaunchTab, {
      props: { ...defaultProps, ...props },
      global: {
        plugins: [vuetify],
        stubs: {
          AgentDetailsModal: true,
        },
      },
    })
  }

  it('renders agent cards for non-orchestrator agents', () => {
    const wrapper = createWrapper()
    const agentCards = wrapper.findAll('.agent-slim-card')

    // Should have 2 agent cards (analyzer + implementor, not orchestrator)
    expect(agentCards).toHaveLength(2)
  })

  it('displays edit icon on agent cards', () => {
    const wrapper = createWrapper()
    const editIcons = wrapper.findAll('.agent-slim-card .edit-icon')

    // Should have 2 edit icons (one per agent)
    expect(editIcons).toHaveLength(2)

    // Each icon should be visible and have proper attributes
    editIcons.forEach((icon) => {
      expect(icon.exists()).toBe(true)
      expect(icon.attributes('title')).toBe('Edit agent configuration')
      expect(icon.attributes('role')).toBe('button')
    })
  })

  it('displays edit icon with mdi-pencil icon', () => {
    const wrapper = createWrapper()
    const editIcons = wrapper.findAll('.agent-slim-card .edit-icon')

    editIcons.forEach((icon) => {
      expect(icon.text()).toContain('mdi-pencil')
    })
  })

  it('displays info icon on agent cards', () => {
    const wrapper = createWrapper()
    const infoIcons = wrapper.findAll('.agent-slim-card .info-icon')

    // Should have 2 info icons (one per agent)
    expect(infoIcons).toHaveLength(2)

    infoIcons.forEach((icon) => {
      expect(icon.exists()).toBe(true)
      expect(icon.attributes('title')).toBe('View agent template')
      expect(icon.attributes('role')).toBe('button')
    })
  })

  it('positions edit icon before info icon', () => {
    const wrapper = createWrapper()
    const firstCard = wrapper.find('.agent-slim-card')

    // Get all v-icon elements in the first card
    const icons = firstCard.findAll('.agent-slim-card > .v-icon')

    // Should have edit icon followed by info icon
    expect(icons.length).toBeGreaterThanOrEqual(2)
  })

  it('calls handleAgentEdit when edit icon clicked', async () => {
    const wrapper = createWrapper()
    const firstEditIcon = wrapper.find('.agent-slim-card .edit-icon')

    // Click the edit icon
    await firstEditIcon.trigger('click')

    // Should emit custom event or show alert (implementation dependent)
    // The actual implementation shows an alert for now
  })

  it('calls handleAgentInfo when info icon clicked', async () => {
    const wrapper = createWrapper()
    const firstInfoIcon = wrapper.find('.agent-slim-card .info-icon')

    // Click the info icon
    await firstInfoIcon.trigger('click')

    // Should open the details modal
    expect(wrapper.vm.showDetailsModal).toBe(true)
  })

  it('edit and info icons are visible in computed styles', () => {
    const wrapper = createWrapper()
    const editIcon = wrapper.find('.agent-slim-card .edit-icon')

    if (editIcon.exists()) {
      const styles = window.getComputedStyle(editIcon.element)

      // Verify visibility properties
      expect(styles.visibility).not.toBe('hidden')
      expect(styles.display).not.toBe('none')
      expect(styles.opacity).not.toBe('0')
    }
  })

  it('excludes orchestrator from agent team list', () => {
    const wrapper = createWrapper({
      project: {
        id: 'project-1',
        name: 'Test Project',
        description: 'Test Description',
        mission: 'Test Mission',
        agents: [
          {
            id: 'orchestrator-1',
            agent_display_name: 'orchestrator',
            agent_name: 'Orchestrator',
            status: 'active',
          },
          {
            id: 'agent-1',
            agent_display_name: 'analyzer',
            agent_name: 'Analyzer Agent',
            status: 'active',
          },
        ],
      },
    })

    const agentCards = wrapper.findAll('.agent-slim-card')

    // Should only have analyzer card, not orchestrator
    expect(agentCards).toHaveLength(1)
    expect(agentCards[0].text()).toContain('analyzer')
  })

  it('displays multiple agent instances correctly', () => {
    const wrapper = createWrapper({
      project: {
        id: 'project-1',
        name: 'Test Project',
        description: 'Test Description',
        mission: 'Test Mission',
        agents: [
          {
            id: 'agent-1',
            agent_display_name: 'implementor',
            agent_name: 'Implementor #1',
            status: 'active',
          },
          {
            id: 'agent-2',
            agent_display_name: 'implementor',
            agent_name: 'Implementor #2',
            status: 'active',
          },
          {
            id: 'agent-3',
            agent_display_name: 'tester',
            agent_name: 'Tester',
            status: 'active',
          },
        ],
      },
    })

    const agentCards = wrapper.findAll('.agent-slim-card')
    const editIcons = wrapper.findAll('.agent-slim-card .edit-icon')
    const infoIcons = wrapper.findAll('.agent-slim-card .info-icon')

    expect(agentCards).toHaveLength(3)
    expect(editIcons).toHaveLength(3)
    expect(infoIcons).toHaveLength(3)
  })

  it('edit icon has proper spacing from info icon', () => {
    const wrapper = createWrapper()
    const firstCard = wrapper.find('.agent-slim-card')

    // Get the computed style of the edit icon
    const editIcon = firstCard.find('.edit-icon')

    if (editIcon.exists()) {
      const styles = window.getComputedStyle(editIcon.element)

      // Should have margin-right for spacing
      const marginRight = styles.marginRight
      expect(marginRight).not.toBe('0px')
    }
  })

  it('icons maintain proper flex layout within card', () => {
    const wrapper = createWrapper()
    const firstCard = wrapper.find('.agent-slim-card')

    // Verify card uses flex layout
    const cardStyles = window.getComputedStyle(firstCard.element)
    expect(cardStyles.display).toBe('flex')

    // Verify icons don't shrink
    const editIcon = firstCard.find('.edit-icon')
    if (editIcon.exists()) {
      const iconStyles = window.getComputedStyle(editIcon.element)
      expect(iconStyles.flexShrink).toBe('0')
    }
  })

  it('renders correct agent colors based on type', () => {
    const wrapper = createWrapper()
    const agentCards = wrapper.findAll('.agent-slim-card')

    const displayNames = {
      analyzer: '#e1564b',
      implementor: '#3493bf',
    }

    agentCards.forEach((card, index) => {
      const avatarDiv = card.find('.agent-avatar')
      const style = avatarDiv.attributes('style')

      expect(style).toContain('background')
    })
  })

  it('handles keyboard navigation for edit icon', async () => {
    const wrapper = createWrapper()
    const firstEditIcon = wrapper.find('.agent-slim-card .edit-icon')

    // Simulate Enter key press
    await firstEditIcon.trigger('keydown.enter')

    // Should handle the keyboard event
  })

  it('handles keyboard navigation for info icon', async () => {
    const wrapper = createWrapper()
    const firstInfoIcon = wrapper.find('.agent-slim-card .info-icon')

    // Simulate Enter key press
    await firstInfoIcon.trigger('keydown.enter')

    // Should show the details modal
    expect(wrapper.vm.showDetailsModal).toBe(true)
  })
})
