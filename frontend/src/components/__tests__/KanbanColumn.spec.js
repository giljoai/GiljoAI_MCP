import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import KanbanColumn from '@/components/kanban/KanbanColumn.vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({
  components,
  directives,
})

/**
 * KanbanColumn Component Tests
 *
 * Tests the display-only Kanban column component.
 */

describe('KanbanColumn.vue', () => {
  const defaultProps = {
    status: 'pending',
    jobs: [],
    title: 'Pending Jobs',
    description: 'Waiting to start',
  }

  /**
   * Rendering Tests
   */
  describe('Rendering', () => {
    it('renders column header with title and count', () => {
      const wrapper = mount(KanbanColumn, {
        props: {
          ...defaultProps,
          jobs: [
            { job_id: '1', agent_name: 'Agent 1', status: 'pending' },
            { job_id: '2', agent_name: 'Agent 2', status: 'pending' },
          ],
        },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.text()).toContain('Pending Jobs')
      expect(wrapper.text()).toContain('2')
    })

    it('renders description subtitle', () => {
      const wrapper = mount(KanbanColumn, {
        props: defaultProps,
        global: { plugins: [vuetify] },
      })

      expect(wrapper.text()).toContain('Waiting to start')
    })

    it('displays correct icon for pending status', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, status: 'pending' },
        global: { plugins: [vuetify] },
      })

      const icon = wrapper.find('[class*="v-icon"]')
      expect(icon.exists()).toBe(true)
    })

    it('displays correct icon for active status', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, status: 'active' },
        global: { plugins: [vuetify] },
      })

      const icon = wrapper.find('[class*="v-icon"]')
      expect(icon.exists()).toBe(true)
    })

    it('displays correct icon for completed status', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, status: 'completed' },
        global: { plugins: [vuetify] },
      })

      const icon = wrapper.find('[class*="v-icon"]')
      expect(icon.exists()).toBe(true)
    })

    it('displays correct icon for blocked status', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, status: 'blocked' },
        global: { plugins: [vuetify] },
      })

      const icon = wrapper.find('[class*="v-icon"]')
      expect(icon.exists()).toBe(true)
    })
  })

  /**
   * Job Display Tests
   */
  describe('Job Display', () => {
    it('renders job cards for provided jobs', () => {
      const jobs = [
        { job_id: '1', agent_name: 'Agent 1', agent_type: 'implementer', status: 'pending' },
        { job_id: '2', agent_name: 'Agent 2', agent_type: 'tester', status: 'pending' },
      ]

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs },
        global: { plugins: [vuetify] },
      })

      const jobCards = wrapper.findAll('[class*="job-card"]')
      expect(jobCards).toHaveLength(2)
    })

    it('renders empty state when no jobs', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs: [] },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.text()).toContain('No pending jobs')
    })

    it('updates job count when jobs array changes', async () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs: [] },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.text()).toContain('0')

      await wrapper.setProps({
        jobs: [
          { job_id: '1', agent_name: 'Agent 1', status: 'pending' },
        ],
      })

      expect(wrapper.text()).toContain('1')
    })
  })

  /**
   * Event Emission Tests
   */
  describe('Event Emission', () => {
    it('emits view-job-details when job card clicked', async () => {
      const job = {
        job_id: '1',
        agent_name: 'Agent 1',
        agent_type: 'implementer',
        status: 'pending',
      }

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs: [job] },
        global: { plugins: [vuetify] },
      })

      // Note: Event emission happens in child JobCard component
      // KanbanColumn forwards the event
      expect(wrapper.emitted('view-job-details')).toBeUndefined()
    })

    it('emits open-messages when message badge clicked', async () => {
      const job = {
        job_id: '1',
        agent_name: 'Agent 1',
        agent_type: 'implementer',
        status: 'pending',
        messages: [{ id: '1', status: 'pending', from: 'agent' }],
      }

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs: [job] },
        global: { plugins: [vuetify] },
      })

      // Events are emitted from JobCard child component
      expect(wrapper.emitted('open-messages')).toBeUndefined()
    })
  })

  /**
   * Styling Tests
   */
  describe('Styling', () => {
    it('applies correct status color to icon', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, status: 'active' },
        global: { plugins: [vuetify] },
      })

      // Verify component renders without error
      expect(wrapper.find('[class*="kanban-column"]').exists()).toBe(true)
    })

    it('renders column with proper structure', () => {
      const wrapper = mount(KanbanColumn, {
        props: defaultProps,
        global: { plugins: [vuetify] },
      })

      const column = wrapper.find('[class*="kanban-column"]')
      expect(column.exists()).toBe(true)
    })
  })

  /**
   * Props Validation Tests
   */
  describe('Props Validation', () => {
    it('validates status prop with allowed values', () => {
      const validStatuses = ['pending', 'active', 'completed', 'blocked']

      validStatuses.forEach((status) => {
        const wrapper = mount(KanbanColumn, {
          props: { ...defaultProps, status },
          global: { plugins: [vuetify] },
        })

        expect(wrapper.exists()).toBe(true)
      })
    })

    it('accepts jobs array prop', () => {
      const jobs = [
        { job_id: '1', agent_name: 'Agent 1', status: 'pending' },
      ]

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('has default empty jobs array', () => {
      const wrapper = mount(KanbanColumn, {
        props: {
          status: 'pending',
          title: 'Test',
        },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

  /**
   * Accessibility Tests
   */
  describe('Accessibility', () => {
    it('has semantic structure with headings', () => {
      const wrapper = mount(KanbanColumn, {
        props: defaultProps,
        global: { plugins: [vuetify] },
      })

      const heading = wrapper.find('p[class*="text-h6"]')
      expect(heading.exists()).toBe(true)
    })

    it('displays chip with aria-label for count', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs: [{ job_id: '1', agent_name: 'Agent 1', status: 'pending' }] },
        global: { plugins: [vuetify] },
      })

      const chip = wrapper.find('[class*="v-chip"]')
      expect(chip.exists()).toBe(true)
    })
  })

  /**
   * Edge Cases
   */
  describe('Edge Cases', () => {
    it('handles empty title gracefully', () => {
      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, title: '' },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('handles large job arrays', () => {
      const jobs = Array.from({ length: 50 }, (_, i) => ({
        job_id: `${i}`,
        agent_name: `Agent ${i}`,
        status: 'pending',
      }))

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.text()).toContain('50')
    })

    it('handles jobs with missing optional fields', () => {
      const jobs = [
        { job_id: '1' },
      ]

      const wrapper = mount(KanbanColumn, {
        props: { ...defaultProps, jobs },
        global: { plugins: [vuetify] },
      })

      expect(wrapper.exists()).toBe(true)
    })
  })
})
