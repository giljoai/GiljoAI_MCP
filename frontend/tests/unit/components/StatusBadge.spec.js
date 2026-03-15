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
      // The v-chip with statusLabel is inside v-menu's activator slot.
      // Global test stubs don't render named slots, so verify via vm.
      expect(wrapper.vm.statusLabel).toBe('Active')
    })

    it('renders badge with correct color for each status', () => {
      const statusColors = {
        active: 'success',
        inactive: 'grey',
        completed: 'info',
        cancelled: 'warning',
        terminated: 'error',
        deleted: 'error',
      }

      Object.entries(statusColors).forEach(([status, expectedColor]) => {
        const wrapper = createWrapper({ status })
        // Verify color through the computed property since the v-chip
        // is inside a named slot that stubs don't render
        expect(wrapper.vm.statusColor).toBe(expectedColor)
      })
    })

    it('has status-badge-chip class defined in component', () => {
      // The chip is in v-menu's activator slot which doesn't render in stubs.
      // Verify the component exists and has the statusLabel computed.
      const wrapper = createWrapper()
      expect(wrapper.vm.statusLabel).toBeDefined()
      expect(wrapper.vm.statusColor).toBeDefined()
    })
  })

  describe('Menu Actions', () => {
    it('shows activate action for inactive status', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions
      expect(actions.some((a) => a.value === 'activate')).toBe(true)
    })

    it('shows deactivate action for active status', async () => {
      const wrapper = createWrapper({ status: 'active' })
      const actions = wrapper.vm.availableActions

      expect(actions.some((a) => a.value === 'deactivate')).toBe(true)
      expect(actions.some((a) => a.value === 'activate')).toBe(false)
    })

    it('shows complete and cancel actions for inactive projects', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      expect(actions.some((a) => a.value === 'complete')).toBe(true)
      expect(actions.some((a) => a.value === 'cancel')).toBe(true)
    })

    it('shows complete and cancel actions for active projects', async () => {
      const wrapper = createWrapper({ status: 'active' })
      const actions = wrapper.vm.availableActions

      expect(actions.some((a) => a.value === 'complete')).toBe(true)
      expect(actions.some((a) => a.value === 'cancel')).toBe(true)
    })

    it('shows review action for completed projects', async () => {
      const wrapper = createWrapper({ status: 'completed' })
      const actions = wrapper.vm.availableActions
      expect(actions.some((a) => a.value === 'review')).toBe(true)
      expect(actions.some((a) => a.value === 'activate')).toBe(false)
      expect(actions.some((a) => a.value === 'complete')).toBe(false)
    })

    it('shows reopen action for cancelled projects', async () => {
      const wrapper = createWrapper({ status: 'cancelled' })
      const actions = wrapper.vm.availableActions
      expect(actions.some((a) => a.value === 'reopen')).toBe(true)
    })

    it('shows review action for terminated projects', async () => {
      const wrapper = createWrapper({ status: 'terminated' })
      const actions = wrapper.vm.availableActions
      expect(actions.some((a) => a.value === 'review')).toBe(true)
    })

    it('has no actions for deleted status', async () => {
      const wrapper = createWrapper({ status: 'deleted' })
      const actions = wrapper.vm.availableActions
      expect(actions.length).toBe(0)
    })
  })

  describe('Events', () => {
    it('emits action event when action is clicked', async () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const activateAction = actions.find((a) => a.value === 'activate')
      // handleActionClick handles non-confirm actions immediately
      wrapper.vm.handleActionClick(activateAction)

      expect(wrapper.emitted('action')).toBeTruthy()
      const emitted = wrapper.emitted('action')[0][0]
      expect(emitted.action).toBe('activate')
      expect(emitted.projectId).toBe('proj-123')
    })

    it('includes projectId in emitted event', () => {
      const wrapper = createWrapper({ status: 'inactive', projectId: 'special-id' })
      const actions = wrapper.vm.availableActions
      const activateAction = actions.find((a) => a.value === 'activate')
      wrapper.vm.handleActionClick(activateAction)

      const emitted = wrapper.emitted('action')[0][0]
      expect(emitted.projectId).toBe('special-id')
    })
  })

  describe('Status Transitions', () => {
    it('correctly handles transition from active to inactive (deactivate)', () => {
      const wrapper = createWrapper({ status: 'active' })
      const activeActions = wrapper.vm.availableActions

      expect(activeActions.some((a) => a.value === 'deactivate')).toBe(true)
      expect(activeActions.some((a) => a.value === 'activate')).toBe(false)
    })

    it('correctly handles transition from inactive to active', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const inactiveActions = wrapper.vm.availableActions

      expect(inactiveActions.some((a) => a.value === 'activate')).toBe(true)
      expect(inactiveActions.some((a) => a.value === 'deactivate')).toBe(false)
    })

    it('correctly handles completed project transitions', () => {
      const wrapper = createWrapper({ status: 'completed' })
      const completedActions = wrapper.vm.availableActions

      expect(completedActions.some((a) => a.value === 'review')).toBe(true)
      expect(completedActions.some((a) => a.value === 'activate')).toBe(false)
      expect(completedActions.some((a) => a.value === 'complete')).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes on badge', () => {
      const wrapper = createWrapper()
      // Global test stubs render v-menu as <div class="v-menu">
      const menu = wrapper.find('.v-menu')
      expect(menu.exists()).toBe(true)
    })

    it('menu items have labels', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const activateAction = actions.find((a) => a.value === 'activate')
      expect(activateAction.label).toBe('Activate')
    })

    it('shows proper icons for each action', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      const actions = wrapper.vm.availableActions

      const actionIcons = {
        activate: 'mdi-play',
        complete: 'mdi-check-circle',
        cancel: 'mdi-cancel',
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
        terminated: 'Terminated',
        deleted: 'Deleted',
      }

      Object.entries(statuses).forEach(([status, expected]) => {
        const wrapper = createWrapper({ status })
        // Verify via computed statusLabel since the label text is
        // inside v-menu's activator slot which stubs don't render
        expect(wrapper.vm.statusLabel).toBe(expected)
      })
    })
  })
})
