import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import JobReadAckIndicators from '@/components/StatusBoard/JobReadAckIndicators.vue'

/**
 * Test suite for JobReadAckIndicators component
 *
 * This component displays job read and acknowledged status indicators
 * using Vuetify icons with title tooltips.
 *
 * Handover 0233: Frontend job read/acknowledged indicators
 */
describe('JobReadAckIndicators.vue', () => {
  let wrapper
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.resetAllMocks()
  })

  describe('Rendering', () => {
    it('renders the component successfully', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.job-read-ack-indicators').exists()).toBe(true)
    })

    it('renders two icon indicators', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const icons = wrapper.findAll('[class*=indicator]')
      // Should have at least 2 indicators
      expect(icons.length).toBeGreaterThanOrEqual(2)
    })

    it('renders read indicator with correct class', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.exists()).toBe(true)
    })

    it('renders acknowledged indicator with correct class', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.exists()).toBe(true)
    })
  })

  describe('Mission Read Indicator - Icon Display', () => {
    it('uses check-circle icon when mission is read', () => {
      const readTime = '2025-11-21T10:30:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: readTime,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.text()).toContain('mdi-check-circle')
    })

    it('uses minus-circle-outline icon when mission is not read', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.text()).toContain('mdi-minus-circle-outline')
    })
  })

  describe('Mission Acknowledged Indicator - Icon Display', () => {
    it('uses check-circle icon when mission is acknowledged', () => {
      const ackTime = '2025-11-21T10:35:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: ackTime,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.text()).toContain('mdi-check-circle')
    })

    it('uses minus-circle-outline icon when mission is not acknowledged', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.text()).toContain('mdi-minus-circle-outline')
    })
  })

  describe('Title Tooltips', () => {
    it('displays "Not yet read" title when mission is not read', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('title')).toBe('Not yet read')
    })

    it('displays "Read at [timestamp]" title when mission is read', () => {
      const readTime = '2025-11-21T10:30:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: readTime,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const title = readIndicator.attributes('title')
      expect(title).toContain('Read at')
    })

    it('displays "Not yet acknowledged" title when mission is not acknowledged', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.attributes('title')).toBe('Not yet acknowledged')
    })

    it('displays "Acknowledged at [timestamp]" title when mission is acknowledged', () => {
      const ackTime = '2025-11-21T10:35:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: ackTime,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      const title = ackIndicator.attributes('title')
      expect(title).toContain('Acknowledged at')
    })
  })

  describe('Reactive Updates', () => {
    it('updates icon when missionReadAt prop changes', async () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      let readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.text()).toContain('mdi-minus-circle-outline')

      await wrapper.setProps({ missionReadAt: '2025-11-21T10:30:00Z' })
      await wrapper.vm.$nextTick()

      readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.text()).toContain('mdi-check-circle')
    })

    it('updates icon when missionAcknowledgedAt prop changes', async () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      let ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.text()).toContain('mdi-minus-circle-outline')

      await wrapper.setProps({ missionAcknowledgedAt: '2025-11-21T10:35:00Z' })
      await wrapper.vm.$nextTick()

      ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.text()).toContain('mdi-check-circle')
    })

    it('updates title when props change', async () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      let readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('title')).toBe('Not yet read')

      await wrapper.setProps({ missionReadAt: '2025-11-21T10:30:00Z' })
      await wrapper.vm.$nextTick()

      readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('title')).toContain('Read at')
    })
  })

  describe('Edge Cases', () => {
    it('handles both timestamps being null', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const ackIndicator = wrapper.find('.ack-indicator')

      expect(readIndicator.text()).toContain('mdi-minus-circle-outline')
      expect(ackIndicator.text()).toContain('mdi-minus-circle-outline')
    })

    it('handles both timestamps being set', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T10:30:00Z',
          missionAcknowledgedAt: '2025-11-21T10:35:00Z',
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const ackIndicator = wrapper.find('.ack-indicator')

      expect(readIndicator.text()).toContain('mdi-check-circle')
      expect(ackIndicator.text()).toContain('mdi-check-circle')
    })

    it('handles invalid date strings gracefully', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: 'invalid-date',
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Component should still render without crashing
      expect(wrapper.exists()).toBe(true)
      const indicators = wrapper.findAll('[class*=indicator]')
      expect(indicators.length).toBeGreaterThanOrEqual(2)

      // Should fall back to "Not yet read" when date is invalid
      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('title')).toBe('Not yet read')
    })

    it('maintains visual layout with flexbox container', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const container = wrapper.find('.job-read-ack-indicators')
      expect(container.classes()).toContain('d-flex')
      expect(container.classes()).toContain('gap-2')
    })
  })

  describe('Accessibility', () => {
    it('icons have title attributes for accessibility', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T10:30:00Z',
          missionAcknowledgedAt: '2025-11-21T10:35:00Z',
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const ackIndicator = wrapper.find('.ack-indicator')

      expect(readIndicator.attributes('title')).toBeTruthy()
      expect(ackIndicator.attributes('title')).toBeTruthy()
    })

    it('uses semantic icon names that convey meaning', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T10:30:00Z',
          missionAcknowledgedAt: '2025-11-21T10:35:00Z',
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const ackIndicator = wrapper.find('.ack-indicator')

      // Should use check-circle for success
      expect(readIndicator.text()).toContain('mdi-check-circle')
      expect(ackIndicator.text()).toContain('mdi-check-circle')
    })

    it('uses dash icons to indicate pending status', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const ackIndicator = wrapper.find('.ack-indicator')

      // Should use minus-circle for pending
      expect(readIndicator.text()).toContain('mdi-minus-circle-outline')
      expect(ackIndicator.text()).toContain('mdi-minus-circle-outline')
    })
  })

  describe('Component Props', () => {
    it('accepts missionReadAt as null (default)', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props().missionReadAt).toBeNull()
    })

    it('accepts missionReadAt as ISO string', () => {
      const timestamp = '2025-11-21T10:30:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: timestamp,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props().missionReadAt).toBe(timestamp)
    })

    it('accepts missionAcknowledgedAt as null (default)', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props().missionAcknowledgedAt).toBeNull()
    })

    it('accepts missionAcknowledgedAt as ISO string', () => {
      const timestamp = '2025-11-21T10:35:00Z'
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: timestamp,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.props().missionAcknowledgedAt).toBe(timestamp)
    })
  })

  describe('Timestamp Formatting', () => {
    it('formats ISO timestamp to localized string', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T10:30:00Z',
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const title = readIndicator.attributes('title')

      // Should contain "Read at" and some date information
      expect(title).toContain('Read at')
      expect(title.length).toBeGreaterThan('Read at'.length)
    })

    it('handles UTC timezone correctly', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T14:30:00.000Z',
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      const title = readIndicator.attributes('title')

      expect(title).toContain('Read at')
      // Should have parsed the timestamp without error
      expect(title).not.toContain('undefined')
    })
  })

  describe('Color Props', () => {
    it('applies success color when mission is read', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: '2025-11-21T10:30:00Z',
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('color')).toBe('success')
    })

    it('applies grey color when mission is not read', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const readIndicator = wrapper.find('.read-indicator')
      expect(readIndicator.attributes('color')).toBe('grey')
    })

    it('applies success color when mission is acknowledged', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: '2025-11-21T10:35:00Z',
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.attributes('color')).toBe('success')
    })

    it('applies grey color when mission is not acknowledged', () => {
      wrapper = mount(JobReadAckIndicators, {
        props: {
          missionReadAt: null,
          missionAcknowledgedAt: null,
        },
        global: {
          plugins: [vuetify],
        },
      })

      const ackIndicator = wrapper.find('.ack-indicator')
      expect(ackIndicator.attributes('color')).toBe('grey')
    })
  })
})
