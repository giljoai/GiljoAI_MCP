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
        ...props,
      },
      global: {
        plugins: [vuetify],
      },
    })
  }

  describe('Rendering', () => {
    it('renders badge with correct status text', () => {
      const wrapper = createWrapper({ status: 'active' })
      expect(wrapper.vm.statusLabel).toBe('Active')
    })

    it('renders with tinted background style for each status', () => {
      const statuses = ['active', 'inactive', 'completed', 'cancelled', 'terminated', 'deleted']
      statuses.forEach((status) => {
        const wrapper = createWrapper({ status })
        const badge = wrapper.find('.status-badge')
        const style = badge.attributes('style')
        expect(style).toContain('rgba(')
        expect(style).toContain('0.15)')
      })
    })

    it('has status-badge class on the element', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.status-badge').exists()).toBe(true)
    })

    it('renders as a span with tinted styling', () => {
      const wrapper = createWrapper()
      const badge = wrapper.find('.status-badge')
      expect(badge.exists()).toBe(true)
      expect(badge.element.tagName).toBe('SPAN')
    })

    it('renders status label text inside the badge', () => {
      const wrapper = createWrapper({ status: 'completed' })
      expect(wrapper.text()).toContain('Completed')
    })
  })

  describe('Computed Properties', () => {
    it('returns correct config for active status', () => {
      const wrapper = createWrapper({ status: 'active' })
      expect(wrapper.vm.config.color).toBe('#6DB3E4')
    })

    it('returns correct config for inactive status', () => {
      const wrapper = createWrapper({ status: 'inactive' })
      expect(wrapper.vm.config.color).toBe('#9e9e9e')
    })

    it('returns correct config for terminated status', () => {
      const wrapper = createWrapper({ status: 'terminated' })
      expect(wrapper.vm.config.color).toBe('#E07872')
    })

    it('returns fallback config for unknown status via computed', () => {
      const wrapper = mount(StatusBadge, {
        props: { status: 'active' },
        global: { plugins: [vuetify] },
      })
      expect(wrapper.vm.config.color).toBe('#6DB3E4')
    })
  })

  describe('Accessibility', () => {
    it('has proper aria-label on the badge', () => {
      const wrapper = createWrapper({ status: 'active' })
      const badge = wrapper.find('.status-badge')
      expect(badge.attributes('aria-label')).toBe('Project status: Active')
    })

    it('sets aria-label correctly for each status', () => {
      const statuses = ['inactive', 'completed', 'cancelled', 'terminated', 'deleted']
      statuses.forEach((status) => {
        const wrapper = createWrapper({ status })
        const badge = wrapper.find('.status-badge')
        const label = wrapper.vm.statusLabel
        expect(badge.attributes('aria-label')).toBe(`Project status: ${label}`)
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
        expect(wrapper.vm.statusLabel).toBe(expected)
      })
    })
  })
})
