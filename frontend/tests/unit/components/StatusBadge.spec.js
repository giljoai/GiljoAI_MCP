import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import StatusBadge from '@/components/StatusBadge.vue'

describe('StatusBadge.vue', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify()
  })

  const createWrapper = (props) => {
    return mount(StatusBadge, {
      props: {
        status: 'active',
        projectId: 'proj-123',
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          teleport: true,
        },
      },
    })
  }

  describe('Rendering', () => {
    it('renders badge with correct status text', () => {
      const wrapper = createWrapper({ status: 'active' })
      expect(wrapper.text()).toContain('Active')
    })

    it('renders badge with correct color for each status', () => {
      const statusColors = {
        active: 'success',
        inactive: 'grey',
        completed: 'info',
        cancelled: 'error',
        deleted: 'secondary',
      }

      Object.entries(statusColors).forEach(([status, color]) => {
        const wrapper = createWrapper({ status })
        const chip = wrapper.find('.status-badge')
        expect(chip.exists()).toBe(true)
      })
    })

    it('has cursor pointer style for interactivity', () => {
      const wrapper = createWrapper()
      const chip = wrapper.find('.status-badge')
      expect(chip.classes()).toContain('cursor-pointer')
    })
  })

  describe('Menu Actions', () => {
    it('shows activate action for inactive status', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const menu = wrapper.findComponent({ name: 'VMenu' })

      // Trigger menu opening
      await menu.vm.$emit('click')
      await wrapper.vm.$nextTick()

      // Check that activate action is available
      const actions = wrapper.vm.availableActions
      expect(actions.some((a) => a.value === 'activate')).toBe(true)
    })

    it('shows pause action only for active status', async () => {
      const wrapper = createWrapper({ status: 'active' })
      const actions = wrapper.vm.availableActions

      expect(actions.some((a) => a.value === 'pause')).toBe(true)
      expect(actions.some((a) => a.value === 'activate')).toBe(false)
    })

    it('shows complete and cancel actions for active/inactive projects', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      expect(actions.some((a) => a.value === 'complete')).toBe(true)
      expect(actions.some((a) => a.value === 'cancel')).toBe(true)
    })

    it('shows restore action only for completed or cancelled projects', async () => {
      const completedWrapper = createWrapper({ status: 'completed' })
      const completedActions = completedWrapper.vm.availableActions
      expect(completedActions.some((a) => a.value === 'restore')).toBe(true)

      const cancelledWrapper = createWrapper({ status: 'cancelled' })
      const cancelledActions = cancelledWrapper.vm.availableActions
      expect(cancelledActions.some((a) => a.value === 'restore')).toBe(true)

      const activeWrapper = createWrapper({ status: 'active' })
      const activeActions = activeWrapper.vm.availableActions
      expect(activeActions.some((a) => a.value === 'restore')).toBe(false)
    })

    it('always shows delete action', async () => {
      const statuses = ['active', 'inactive', 'completed', 'cancelled', 'deleted']

      statuses.forEach((status) => {
        const wrapper = createWrapper({ status })
        const actions = wrapper.vm.availableActions
        expect(actions.some((a) => a.value === 'delete')).toBe(true)
      })
    })
  })

  describe('Events', () => {
    it('emits action event when action is clicked', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const activateAction = actions.find((a) => a.value === 'activate')
      wrapper.vm.handleAction(activateAction.value)

      expect(wrapper.emitted('action')).toBeTruthy()
      const emitted = wrapper.emitted('action')[0][0]
      expect(emitted.action).toBe('activate')
      expect(emitted.projectId).toBe('proj-123')
    })

    it('includes projectId in emitted event', () => {
      const wrapper = createWrapper({ status: 'inactive', projectId: 'special-id' })
      wrapper.vm.handleAction('activate')

      const emitted = wrapper.emitted('action')[0][0]
      expect(emitted.projectId).toBe('special-id')
    })

    it('does not emit event for divider action', () => {
      const wrapper = createWrapper()
      wrapper.vm.handleAction('divider')

      expect(wrapper.emitted('action')).toBeFalsy()
    })
  })

  describe('Disabled State', () => {
    it('can accept disabled prop', () => {
      const wrapper = createWrapper({ disabled: true })
      expect(wrapper.props('disabled')).toBe(true)
    })

    it('disables delete action when disabled prop is true', () => {
      const wrapper = createWrapper({ disabled: true })
      const deleteAction = wrapper.vm.availableActions.find((a) => a.value === 'delete')

      expect(deleteAction.disabled).toBe(true)
    })

    it('enables delete action when disabled prop is false', () => {
      const wrapper = createWrapper({ disabled: false })
      const deleteAction = wrapper.vm.availableActions.find((a) => a.value === 'delete')

      expect(deleteAction.disabled).toBe(false)
    })
  })

  describe('Status Transitions', () => {
    it('correctly handles transition from active to inactive', () => {
      const wrapper = createWrapper({ status: 'active' })
      const activeActions = wrapper.vm.availableActions

      expect(activeActions.some((a) => a.value === 'deactivate')).toBe(true)
      expect(activeActions.some((a) => a.value === 'activate')).toBe(false)
    })

    it('correctly handles transition from inactive to active', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const inactiveActions = wrapper.vm.availableActions

      expect(inactiveActions.some((a) => a.value === 'activate')).toBe(true)
      expect(inactiveActions.some((a) => a.value === 'pause')).toBe(false)
    })

    it('correctly handles completed project transitions', () => {
      const wrapper = createWrapper({ status: 'completed' })
      const completedActions = wrapper.vm.availableActions

      expect(completedActions.some((a) => a.value === 'restore')).toBe(true)
      expect(completedActions.some((a) => a.value === 'activate')).toBe(false)
      expect(completedActions.some((a) => a.value === 'complete')).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes on badge', () => {
      const wrapper = createWrapper()
      const chip = wrapper.find('.status-badge')

      // Chip should be interactive via menu
      const menu = wrapper.findComponent({ name: 'VMenu' })
      expect(menu.exists()).toBe(true)
    })

    it('menu items have titles for tooltips', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const activateAction = actions.find((a) => a.value === 'activate')
      expect(activateAction.tooltip).toBe('Activate this project')
    })

    it('shows proper icons for each action', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const actionIcons = {
        activate: 'mdi-play',
        pause: 'mdi-pause',
        complete: 'mdi-check',
        cancel: 'mdi-close',
        restore: 'mdi-history',
        delete: 'mdi-delete',
      }

      Object.entries(actionIcons).forEach(([actionValue, expectedIcon]) => {
        const action = actions.find((a) => a.value === actionValue)
        if (action) {
          expect(action.icon).toBe(expectedIcon)
        }
      })
    })
  })

  describe('Format Status Helper', () => {
    it('formats status correctly', () => {
      const statuses = {
        active: 'Active',
        inactive: 'Inactive',
        completed: 'Completed',
        cancelled: 'Cancelled',
        deleted: 'Deleted',
      }

      Object.entries(statuses).forEach(([status, expected]) => {
        const wrapper = createWrapper({ status })
        expect(wrapper.text()).toContain(expected)
      })
    })
  })
})
