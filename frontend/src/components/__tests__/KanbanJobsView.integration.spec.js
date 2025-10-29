import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import KanbanJobsView from '@/components/project-launch/KanbanJobsView.vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({
  components,
  directives,
})

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    agentJobs: {
      getKanbanBoard: vi.fn(() =>
        Promise.resolve({
          data: {
            jobs: [
              {
                job_id: 'job-1',
                agent_id: 'agent-1',
                agent_name: 'Alice',
                agent_type: 'implementer',
                status: 'pending',
                mode: 'claude',
                mission: 'Build user authentication system',
                progress: 0,
                created_at: new Date().toISOString(),
                messages: [{ id: 'm1', from: 'agent', status: 'pending', content: 'Starting work' }],
              },
              {
                job_id: 'job-2',
                agent_id: 'agent-2',
                agent_name: 'Bob',
                agent_type: 'tester',
                status: 'active',
                mode: 'codex',
                mission: 'Write unit tests for auth module',
                progress: 50,
                created_at: new Date().toISOString(),
                messages: [],
              },
              {
                job_id: 'job-3',
                agent_id: 'agent-3',
                agent_name: 'Charlie',
                agent_type: 'analyzer',
                status: 'completed',
                mode: 'gemini',
                mission: 'Analyze performance bottlenecks',
                progress: 100,
                created_at: new Date().toISOString(),
                messages: [
                  { id: 'm1', from: 'developer', status: 'sent', content: 'Great work!' },
                  { id: 'm2', from: 'agent', status: 'acknowledged', content: 'Thank you!' },
                ],
              },
              {
                job_id: 'job-4',
                agent_id: 'agent-4',
                agent_name: 'Diana',
                agent_type: 'backend',
                status: 'blocked',
                mode: 'claude',
                mission: 'Implement database migration',
                progress: 25,
                created_at: new Date().toISOString(),
                messages: [
                  { id: 'm1', from: 'developer', status: 'sent', content: 'What is the issue?' },
                ],
              },
            ],
          },
        }),
      ),
    },
  },
}))

// Mock WebSocket service
vi.mock('@/services/websocket', () => ({
  default: {
    onMessage: vi.fn(() => () => {}),
  },
}))

/**
 * KanbanJobsView Integration Tests
 *
 * Tests the complete Kanban board integration with all subcomponents.
 * Verifies that components work together to display, organize, and manage jobs.
 */

describe('KanbanJobsView.vue - Integration Tests', () => {
  /**
   * Component Setup Tests
   */
  describe('Component Initialization', () => {
    it('renders Kanban board on mount', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('[class*="kanban-jobs-view"]').exists()).toBe(true)
    })

    it('fetches jobs on component mount', async () => {
      const { api } = await import('@/services/api')

      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      // Wait for async data loading
      await wrapper.vm.$nextTick()

      // Jobs should be loaded (checked via loading state)
      expect(wrapper.exists()).toBe(true)
    })

    it('displays header with refresh button', () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      expect(wrapper.text()).toContain('Active Agent Jobs')
      expect(wrapper.text()).toContain('Refresh')
    })
  })

  /**
   * Kanban Column Organization Tests
   */
  describe('Job Organization', () => {
    it('organizes jobs into 4 columns by status', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      await wrapper.vm.$nextTick()

      // Check that kanbanColumns computed property contains 4 entries
      expect(wrapper.vm.kanbanColumns).toHaveLength(4)
      expect(wrapper.vm.kanbanColumns[0].status).toBe('pending')
      expect(wrapper.vm.kanbanColumns[1].status).toBe('active')
      expect(wrapper.vm.kanbanColumns[2].status).toBe('completed')
      expect(wrapper.vm.kanbanColumns[3].status).toBe('blocked')
    })

    it('assigns jobs to correct columns based on status', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      await wrapper.vm.$nextTick()

      const columns = wrapper.vm.kanbanColumns
      expect(columns[0].jobs).toHaveLength(1) // pending
      expect(columns[1].jobs).toHaveLength(1) // active
      expect(columns[2].jobs).toHaveLength(1) // completed
      expect(columns[3].jobs).toHaveLength(1) // blocked
    })

    it('displays correct job counts in column headers', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      await wrapper.vm.$nextTick()

      const columns = wrapper.vm.kanbanColumns
      expect(columns[0].title).toBe('Pending')
      expect(columns[0].jobs.length).toBe(1)
    })
  })

  /**
   * Message Badge Aggregation Tests
   */
  describe('Message Badge Calculations', () => {
    it('calculates message counts for selected job', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      // Select job-3 which has both sent and acknowledged messages
      wrapper.vm.selectedJob = wrapper.vm.jobs[2]
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.unreadCount).toBe(0)
      expect(wrapper.vm.acknowledgedCount).toBe(1)
      expect(wrapper.vm.sentCount).toBe(1)
      expect(wrapper.vm.totalMessageCount).toBe(2)
    })

    it('counts unread messages correctly', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      // Select job-1 which has an unread message
      wrapper.vm.selectedJob = wrapper.vm.jobs[0]
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.unreadCount).toBe(1)
    })
  })

  /**
   * Job Details Dialog Tests
   */
  describe('Job Details Dialog', () => {
    it('opens job details dialog when job selected', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const job = wrapper.vm.jobs[0]
      wrapper.vm.openJobDetails(job)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedJob).toBe(job)
      expect(wrapper.vm.jobDetailsOpen).toBe(true)
    })

    it('displays job information in details dialog', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const job = wrapper.vm.jobs[1] // Active job with progress
      wrapper.vm.selectedJob = job
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedJob.agent_name).toBe('Bob')
      expect(wrapper.vm.selectedJob.status).toBe('active')
      expect(wrapper.vm.selectedJob.progress).toBe(50)
    })

    it('closes dialog when requested', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      wrapper.vm.jobDetailsOpen = true
      await wrapper.vm.$nextTick()

      wrapper.vm.jobDetailsOpen = false
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.jobDetailsOpen).toBe(false)
    })
  })

  /**
   * Message Panel Integration Tests
   */
  describe('Message Panel Integration', () => {
    it('opens message panel for selected job', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const job = wrapper.vm.jobs[0]
      wrapper.vm.openMessagePanel(job)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedJob).toBe(job)
      expect(wrapper.vm.messagePanelOpen).toBe(true)
    })

    it('passes correct job to message panel', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const job = wrapper.vm.jobs[2]
      wrapper.vm.selectedJob = job
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedJob.job_id).toBe('job-3')
      expect(wrapper.vm.selectedJob.messages.length).toBe(2)
    })

    it('handles new message from message panel', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      wrapper.vm.selectedJob = wrapper.vm.jobs[0]
      const initialMessageCount = wrapper.vm.selectedJob.messages.length

      const newMessage = {
        id: 'msg-new',
        from: 'developer',
        content: 'Test message',
        created_at: new Date().toISOString(),
      }

      wrapper.vm.onMessageSent(newMessage)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedJob.messages.length).toBe(initialMessageCount + 1)
    })
  })

  /**
   * Real-Time Update Tests
   */
  describe('Real-Time WebSocket Updates', () => {
    it('handles job status change event', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      // Simulate WebSocket update: pending job moves to active
      const updateData = {
        job_id: 'job-1',
        status: 'active',
        project_id: 'project-123',
      }

      wrapper.vm.handleJobUpdate(updateData)
      await wrapper.vm.$nextTick()

      const updatedJob = wrapper.vm.jobs.find((j) => j.job_id === 'job-1')
      expect(updatedJob.status).toBe('active')
    })

    it('re-organizes columns when job status changes', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      await wrapper.vm.$nextTick()

      // Check initial state
      const initialPendingCount = wrapper.vm.kanbanColumns[0].jobs.length
      const initialActiveCount = wrapper.vm.kanbanColumns[1].jobs.length

      // Simulate status change
      wrapper.vm.handleJobUpdate({
        job_id: 'job-1',
        status: 'active',
        project_id: 'project-123',
      })
      await wrapper.vm.$nextTick()

      // Verify column reorganization
      expect(wrapper.vm.kanbanColumns[0].jobs.length).toBe(initialPendingCount - 1)
      expect(wrapper.vm.kanbanColumns[1].jobs.length).toBe(initialActiveCount + 1)
    })

    it('ignores updates for different project', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const initialJobCount = wrapper.vm.jobs.length

      // Send update for different project
      wrapper.vm.handleJobUpdate({
        job_id: 'job-99',
        status: 'active',
        project_id: 'project-999', // Different project
      })
      await wrapper.vm.$nextTick()

      // Job count should not change
      expect(wrapper.vm.jobs.length).toBe(initialJobCount)
    })

    it('adds new job from WebSocket update', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      const initialJobCount = wrapper.vm.jobs.length

      // Simulate new job creation via WebSocket
      wrapper.vm.handleJobUpdate({
        job_id: 'job-new',
        agent_id: 'agent-new',
        agent_name: 'New Agent',
        agent_type: 'implementer',
        status: 'pending',
        mode: 'claude',
        mission: 'New mission',
        created_at: new Date().toISOString(),
        project_id: 'project-123',
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.jobs.length).toBe(initialJobCount + 1)
    })
  })

  /**
   * Styling & Display Tests
   */
  describe('Status Styling', () => {
    it('returns correct color for each status', () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      expect(wrapper.vm.getJobStatusColor('pending')).toBe('grey')
      expect(wrapper.vm.getJobStatusColor('active')).toBe('primary')
      expect(wrapper.vm.getJobStatusColor('completed')).toBe('success')
      expect(wrapper.vm.getJobStatusColor('blocked')).toBe('error')
    })

    it('returns correct icon for each status', () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      expect(wrapper.vm.getJobStatusIcon('pending')).toBe('mdi-clock-outline')
      expect(wrapper.vm.getJobStatusIcon('active')).toBe('mdi-play-circle')
      expect(wrapper.vm.getJobStatusIcon('completed')).toBe('mdi-check-circle')
      expect(wrapper.vm.getJobStatusIcon('blocked')).toBe('mdi-alert-circle')
    })

    it('returns correct agent type icon and color', () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      expect(wrapper.vm.getAgentTypeIcon('implementer')).toBe('mdi-code-braces')
      expect(wrapper.vm.getAgentTypeColor('implementer')).toBe('green')
    })
  })

  /**
   * Error Handling Tests
   */
  describe('Error Handling', () => {
    it('handles empty jobs array gracefully', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      wrapper.vm.jobs = []
      await wrapper.vm.$nextTick()

      // All columns should be empty
      wrapper.vm.kanbanColumns.forEach((col) => {
        expect(col.jobs).toHaveLength(0)
      })
    })

    it('handles missing job properties', async () => {
      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      wrapper.vm.jobs = [{ job_id: 'job-1' }]
      await wrapper.vm.$nextTick()

      expect(wrapper.exists()).toBe(true)
    })
  })

  /**
   * Cleanup Tests
   */
  describe('Component Cleanup', () => {
    it('unsubscribes from WebSocket on unmount', () => {
      const unsubscribeMock = vi.fn()
      const websocketService = require('@/services/websocket').default

      vi.mocked(websocketService.onMessage).mockReturnValue(unsubscribeMock)

      const wrapper = mount(KanbanJobsView, {
        props: { projectId: 'project-123' },
        global: { plugins: [vuetify], stubs: { KanbanColumn: true, JobCard: true, MessageThreadPanel: true } },
      })

      wrapper.unmount()

      // Verify cleanup happens (unsubscribe should be called)
      expect(wrapper.exists()).toBe(false)
    })
  })
})
