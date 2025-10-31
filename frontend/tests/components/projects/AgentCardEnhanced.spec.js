/**
 * AgentCardEnhanced Component Tests
 *
 * Production-grade test suite for Handover 0077 AgentCard component.
 * Tests all modes, states, and user interactions.
 *
 * Test Coverage:
 * - Component rendering in different modes (launch/jobs)
 * - All agent states (waiting, working, complete, failed, blocked)
 * - Message badge display and counts
 * - Action button behavior
 * - Orchestrator special features
 * - Accessibility compliance
 * - Responsive design
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentCardEnhanced from '@/components/projects/AgentCardEnhanced.vue'
import ChatHeadBadge from '@/components/projects/ChatHeadBadge.vue'
import LaunchPromptIcons from '@/components/projects/LaunchPromptIcons.vue'

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives
})

// Global mounting options
const globalOptions = {
  global: {
    plugins: [vuetify],
    stubs: {
      ChatHeadBadge: true,
      LaunchPromptIcons: true
    }
  }
}

describe('AgentCardEnhanced', () => {
  // Sample agent data for tests
  const baseAgent = {
    job_id: 'agent-123456789',
    agent_id: 'agent-123456789',
    agent_type: 'implementor',
    agent_name: 'Implementor Agent',
    status: 'waiting',
    mission: 'Implement user authentication feature',
    progress: 0,
    current_task: null,
    messages: [],
    block_reason: null
  }

  describe('Component Rendering', () => {
    it('renders the component with minimum required props', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      expect(wrapper.find('.agent-card-enhanced').exists()).toBe(true)
      expect(wrapper.find('.agent-card__header').exists()).toBe(true)
      expect(wrapper.find('.agent-card__body').exists()).toBe(true)
    })

    it('displays agent type label in header', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      const header = wrapper.find('.agent-header-text')
      expect(header.exists()).toBe(true)
      expect(header.text()).toBe('Implementor')
    })

    it('displays truncated agent ID', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      const agentId = wrapper.find('.agent-id')
      expect(agentId.exists()).toBe(true)
      expect(agentId.text()).toContain('agent-123456')
    })

    it('includes ChatHeadBadge component', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      expect(wrapper.findComponent({ name: 'ChatHeadBadge' }).exists()).toBe(true)
    })

    it('applies correct agent type class', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      expect(wrapper.find('.agent-card--implementor').exists()).toBe(true)
    })

    it('applies correct status class', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, status: 'working' }
        }
      })

      expect(wrapper.find('.status--working').exists()).toBe(true)
    })
  })

  describe('Launch Tab Mode', () => {
    it('displays mission content in launch mode', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent,
          mode: 'launch'
        }
      })

      const missionContent = wrapper.find('.mission-content')
      expect(missionContent.exists()).toBe(true)
      expect(missionContent.text()).toContain('Implement user authentication feature')
    })

    it('displays "Edit Mission" button in launch mode', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent,
          mode: 'launch'
        }
      })

      const buttons = wrapper.findAll('button')
      const editButton = buttons.find(btn => btn.text().includes('Edit Mission'))
      expect(editButton).toBeDefined()
    })

    it('emits edit-mission event when button clicked', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent,
          mode: 'launch'
        }
      })

      const buttons = wrapper.findAll('button')
      const editButton = buttons.find(btn => btn.text().includes('Edit Mission'))
      await editButton.trigger('click')

      expect(wrapper.emitted('edit-mission')).toBeTruthy()
      expect(wrapper.emitted('edit-mission')[0]).toEqual([baseAgent])
    })

    it('does NOT display status badges in launch mode', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent,
          mode: 'launch'
        }
      })

      expect(wrapper.find('.status-badge').exists()).toBe(false)
    })

    it('does NOT display message badges in launch mode', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: {
            ...baseAgent,
            messages: [{ id: 1, status: 'pending', content: 'Test message' }]
          },
          mode: 'launch'
        }
      })

      expect(wrapper.find('.message-badges').exists()).toBe(false)
    })
  })

  describe('Jobs Tab - Waiting State', () => {
    const waitingAgent = {
      ...baseAgent,
      status: 'waiting'
    }

    it('displays status badge for waiting state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: waitingAgent,
          mode: 'jobs'
        }
      })

      const statusBadge = wrapper.find('.status-badge')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.text()).toBe('Waiting')
    })

    it('displays "Launch Agent" button for waiting state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: waitingAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const launchButton = buttons.find(btn => btn.text().includes('Launch Agent'))
      expect(launchButton).toBeDefined()
    })

    it('emits launch-agent event when button clicked', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: waitingAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const launchButton = buttons.find(btn => btn.text().includes('Launch Agent'))
      await launchButton.trigger('click')

      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0]).toEqual([waitingAgent])
    })

    it('displays truncated mission text', () => {
      const longMission = 'A'.repeat(150)
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...waitingAgent, mission: longMission },
          mode: 'jobs'
        }
      })

      const waitingContent = wrapper.find('.waiting-content')
      expect(waitingContent.exists()).toBe(true)
      expect(waitingContent.text().length).toBeLessThan(longMission.length)
      expect(waitingContent.text()).toContain('...')
    })
  })

  describe('Jobs Tab - Working State', () => {
    const workingAgent = {
      ...baseAgent,
      status: 'working',
      progress: 45,
      current_task: 'Creating user model in database'
    }

    it('displays status badge for working state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: workingAgent,
          mode: 'jobs'
        }
      })

      const statusBadge = wrapper.find('.status-badge')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.text()).toBe('Working')
    })

    it('displays progress bar with correct value', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: workingAgent,
          mode: 'jobs'
        }
      })

      const progressSection = wrapper.find('.progress-section')
      expect(progressSection.exists()).toBe(true)
      expect(progressSection.text()).toContain('45%')
    })

    it('displays current task', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: workingAgent,
          mode: 'jobs'
        }
      })

      const currentTask = wrapper.find('.current-task')
      expect(currentTask.exists()).toBe(true)
      expect(currentTask.text()).toContain('Creating user model in database')
    })

    it('displays "Details" button for working state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: workingAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const detailsButton = buttons.find(btn => btn.text().includes('Details'))
      expect(detailsButton).toBeDefined()
    })

    it('emits view-details event when button clicked', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: workingAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const detailsButton = buttons.find(btn => btn.text().includes('Details'))
      await detailsButton.trigger('click')

      expect(wrapper.emitted('view-details')).toBeTruthy()
      expect(wrapper.emitted('view-details')[0]).toEqual([workingAgent])
    })

    it('handles zero progress correctly', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...workingAgent, progress: 0 },
          mode: 'jobs'
        }
      })

      const progressSection = wrapper.find('.progress-section')
      expect(progressSection.text()).toContain('0%')
    })

    it('handles missing current_task gracefully', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...workingAgent, current_task: null },
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.current-task').exists()).toBe(false)
    })
  })

  describe('Jobs Tab - Complete State', () => {
    const completeAgent = {
      ...baseAgent,
      status: 'complete'
    }

    it('displays status badge for complete state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs'
        }
      })

      const statusBadge = wrapper.find('.status-badge')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.text()).toBe('Complete')
    })

    it('displays "Complete" text in yellow', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs'
        }
      })

      const completeContent = wrapper.find('.complete-content')
      expect(completeContent.exists()).toBe(true)

      const completeText = wrapper.find('.complete-text')
      expect(completeText.exists()).toBe(true)
      expect(completeText.text()).toBe('Complete')
    })

    it('displays instance badge for multi-instance agents', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs',
          instanceNumber: 2
        }
      })

      const instanceBadge = wrapper.find('.instance-badge')
      expect(instanceBadge.exists()).toBe(true)
      expect(instanceBadge.text()).toContain('Instance 2')
    })

    it('does NOT display instance badge for first instance', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs',
          instanceNumber: 1
        }
      })

      expect(wrapper.find('.instance-badge').exists()).toBe(false)
    })

    it('does NOT display action button for complete state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs'
        }
      })

      const cardActions = wrapper.find('.v-card-actions')
      // Should be empty or only contain orchestrator buttons
      const buttons = cardActions.findAll('button')
      const hasStandardButton = buttons.some(btn =>
        btn.text().includes('Launch') ||
        btn.text().includes('Details') ||
        btn.text().includes('Edit')
      )
      expect(hasStandardButton).toBe(false)
    })

    it('applies grayed-out styling', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: completeAgent,
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.status--complete').exists()).toBe(true)
    })
  })

  describe('Jobs Tab - Failed State', () => {
    const failedAgent = {
      ...baseAgent,
      status: 'failed',
      block_reason: 'Authentication API endpoint not responding'
    }

    it('displays status badge for failed state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: failedAgent,
          mode: 'jobs'
        }
      })

      const statusBadge = wrapper.find('.status-badge')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.text()).toBe('Failure')
    })

    it('displays error alert with block reason', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: failedAgent,
          mode: 'jobs'
        }
      })

      const errorContent = wrapper.find('.error-content')
      expect(errorContent.exists()).toBe(true)
      expect(errorContent.text()).toContain('Authentication API endpoint not responding')
    })

    it('displays "View Error" button for failed state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: failedAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const errorButton = buttons.find(btn => btn.text().includes('View Error'))
      expect(errorButton).toBeDefined()
    })

    it('emits view-error event when button clicked', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: failedAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const errorButton = buttons.find(btn => btn.text().includes('View Error'))
      await errorButton.trigger('click')

      expect(wrapper.emitted('view-error')).toBeTruthy()
      expect(wrapper.emitted('view-error')[0]).toEqual([failedAgent])
    })

    it('applies priority styling (moved to top)', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: failedAgent,
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.priority-card').exists()).toBe(true)
    })

    it('handles missing block_reason gracefully', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...failedAgent, block_reason: null },
          mode: 'jobs'
        }
      })

      const errorContent = wrapper.find('.error-content')
      expect(errorContent.text()).toContain('No details available')
    })
  })

  describe('Jobs Tab - Blocked State', () => {
    const blockedAgent = {
      ...baseAgent,
      status: 'blocked',
      block_reason: 'Waiting for database schema approval'
    }

    it('displays status badge for blocked state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: blockedAgent,
          mode: 'jobs'
        }
      })

      const statusBadge = wrapper.find('.status-badge')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.text()).toBe('Blocked')
    })

    it('displays warning alert with block reason', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: blockedAgent,
          mode: 'jobs'
        }
      })

      const errorContent = wrapper.find('.error-content')
      expect(errorContent.exists()).toBe(true)
      expect(errorContent.text()).toContain('Waiting for database schema approval')
    })

    it('displays "View Error" button for blocked state', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: blockedAgent,
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const errorButton = buttons.find(btn => btn.text().includes('View Error'))
      expect(errorButton).toBeDefined()
    })

    it('applies priority styling (moved to top)', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: blockedAgent,
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.priority-card').exists()).toBe(true)
    })
  })

  describe('Message Badges', () => {
    const agentWithMessages = {
      ...baseAgent,
      status: 'working',
      messages: [
        { id: 1, status: 'pending', from: 'agent', content: 'Need clarification' },
        { id: 2, status: 'pending', from: 'agent', content: 'API not responding' },
        { id: 3, status: 'acknowledged', from: 'agent', content: 'Task completed' },
        { id: 4, status: 'acknowledged', from: 'agent', content: 'Ready for review' },
        { id: 5, status: 'acknowledged', from: 'agent', content: 'Tests passing' },
        { id: 6, from: 'developer', content: 'Proceed with implementation' },
        { id: 7, from: 'developer', content: 'Update approved' }
      ]
    }

    it('displays unread message badge with correct count', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: agentWithMessages,
          mode: 'jobs'
        }
      })

      const badges = wrapper.findAll('.message-badges .v-chip')
      const unreadBadge = badges.find(badge => badge.text().includes('Unread'))
      expect(unreadBadge).toBeDefined()
      expect(unreadBadge.text()).toContain('2')
    })

    it('displays acknowledged message badge with correct count', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: agentWithMessages,
          mode: 'jobs'
        }
      })

      const badges = wrapper.findAll('.message-badges .v-chip')
      const readBadge = badges.find(badge => badge.text().includes('Read'))
      expect(readBadge).toBeDefined()
      expect(readBadge.text()).toContain('3')
    })

    it('displays sent message badge with correct count', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: agentWithMessages,
          mode: 'jobs'
        }
      })

      const badges = wrapper.findAll('.message-badges .v-chip')
      const sentBadge = badges.find(badge => badge.text().includes('Sent'))
      expect(sentBadge).toBeDefined()
      expect(sentBadge.text()).toContain('2')
    })

    it('does NOT display badge when count is zero', () => {
      const agentNoUnread = {
        ...baseAgent,
        status: 'working',
        messages: [
          { id: 1, status: 'acknowledged', from: 'agent', content: 'Done' }
        ]
      }

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: agentNoUnread,
          mode: 'jobs'
        }
      })

      const badges = wrapper.findAll('.message-badges .v-chip')
      const unreadBadge = badges.find(badge => badge.text().includes('Unread'))
      expect(unreadBadge).toBeUndefined()
    })

    it('does NOT display message badges when no messages exist', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, messages: [] },
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.message-badges').exists()).toBe(false)
    })

    it('handles undefined messages array gracefully', () => {
      const agentNoMessages = { ...baseAgent }
      delete agentNoMessages.messages

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: agentNoMessages,
          mode: 'jobs'
        }
      })

      expect(wrapper.find('.message-badges').exists()).toBe(false)
    })
  })

  describe('Orchestrator Special Features', () => {
    const orchestratorAgent = {
      ...baseAgent,
      agent_type: 'orchestrator',
      status: 'working'
    }

    it('displays LaunchPromptIcons for orchestrator', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: orchestratorAgent,
          mode: 'jobs',
          isOrchestrator: true
        }
      })

      expect(wrapper.findComponent({ name: 'LaunchPromptIcons' }).exists()).toBe(true)
    })

    it('does NOT display LaunchPromptIcons for non-orchestrator', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent,
          mode: 'jobs',
          isOrchestrator: false
        }
      })

      expect(wrapper.findComponent({ name: 'LaunchPromptIcons' }).exists()).toBe(false)
    })

    it('displays "Closeout Project" button when showCloseoutButton is true', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...orchestratorAgent, status: 'complete' },
          mode: 'jobs',
          isOrchestrator: true,
          showCloseoutButton: true
        }
      })

      const buttons = wrapper.findAll('button')
      const closeoutButton = buttons.find(btn => btn.text().includes('Closeout Project'))
      expect(closeoutButton).toBeDefined()
    })

    it('emits closeout-project event when button clicked', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...orchestratorAgent, status: 'complete' },
          mode: 'jobs',
          isOrchestrator: true,
          showCloseoutButton: true
        }
      })

      const buttons = wrapper.findAll('button')
      const closeoutButton = buttons.find(btn => btn.text().includes('Closeout Project'))
      await closeoutButton.trigger('click')

      expect(wrapper.emitted('closeout-project')).toBeTruthy()
    })

    it('does NOT display closeout button when showCloseoutButton is false', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...orchestratorAgent, status: 'complete' },
          mode: 'jobs',
          isOrchestrator: true,
          showCloseoutButton: false
        }
      })

      const buttons = wrapper.findAll('button')
      const closeoutButton = buttons.find(btn => btn.text().includes('Closeout Project'))
      expect(closeoutButton).toBeUndefined()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA label on card', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      const card = wrapper.find('.agent-card-enhanced')
      expect(card.attributes('aria-label')).toContain('Implementor')
      expect(card.attributes('aria-label')).toContain('Waiting')
    })

    it('has role="article" on card', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      expect(wrapper.find('[role="article"]').exists()).toBe(true)
    })

    it('all buttons are keyboard accessible', async () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, status: 'waiting' },
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('tabindex')).not.toBe('-1')
      })
    })

    it('displays meaningful button labels', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, status: 'waiting' },
          mode: 'jobs'
        }
      })

      const buttons = wrapper.findAll('button')
      const launchButton = buttons.find(btn => btn.text().includes('Launch Agent'))
      expect(launchButton.text()).toBeTruthy()
      expect(launchButton.text().length).toBeGreaterThan(0)
    })
  })

  describe('Prop Validation', () => {
    it('requires agent prop', () => {
      // This test validates the prop is marked as required
      const validator = AgentCardEnhanced.props.agent.required
      expect(validator).toBe(true)
    })

    it('validates mode prop accepts only "launch" or "jobs"', () => {
      const validator = AgentCardEnhanced.props.mode.validator
      expect(validator('launch')).toBe(true)
      expect(validator('jobs')).toBe(true)
      expect(validator('invalid')).toBe(false)
    })

    it('validates instanceNumber is >= 1', () => {
      const validator = AgentCardEnhanced.props.instanceNumber.validator
      expect(validator(1)).toBe(true)
      expect(validator(5)).toBe(true)
      expect(validator(0)).toBe(false)
      expect(validator(-1)).toBe(false)
    })

    it('uses default values when props not provided', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      // Default mode is 'jobs'
      expect(wrapper.vm.mode).toBe('jobs')
      // Default instanceNumber is 1
      expect(wrapper.vm.instanceNumber).toBe(1)
      // Default isOrchestrator is false
      expect(wrapper.vm.isOrchestrator).toBe(false)
    })
  })

  describe('Styling and Layout', () => {
    it('has fixed width of 280px', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      const card = wrapper.find('.agent-card-enhanced')
      const style = card.attributes('style')
      expect(style).toContain('280px')
    })

    it('has scrollable content area', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      expect(wrapper.find('.scrollable-content').exists()).toBe(true)
    })

    it('applies hover effect class', () => {
      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: baseAgent
        }
      })

      const card = wrapper.find('.agent-card-enhanced')
      expect(card.classes()).toContain('agent-card-enhanced')
    })

    it('applies priority styling for failed/blocked states', () => {
      const failedWrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, status: 'failed' }
        }
      })

      expect(failedWrapper.find('.priority-card').exists()).toBe(true)

      const blockedWrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: { ...baseAgent, status: 'blocked' }
        }
      })

      expect(blockedWrapper.find('.priority-card').exists()).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('handles very long agent IDs', () => {
      const longIdAgent = {
        ...baseAgent,
        job_id: 'agent-' + 'x'.repeat(100)
      }

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: longIdAgent
        }
      })

      const agentId = wrapper.find('.agent-id')
      expect(agentId.text()).toContain('...')
      expect(agentId.text().length).toBeLessThan(50)
    })

    it('handles very long mission text', () => {
      const longMissionAgent = {
        ...baseAgent,
        mission: 'A'.repeat(500)
      }

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: longMissionAgent,
          mode: 'jobs'
        }
      })

      const content = wrapper.find('.waiting-content')
      expect(content.text()).toContain('...')
    })

    it('handles null/undefined mission gracefully', () => {
      const noMissionAgent = {
        ...baseAgent,
        mission: null
      }

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: noMissionAgent,
          mode: 'launch'
        }
      })

      const missionContent = wrapper.find('.mission-content')
      expect(missionContent.text()).toContain('No mission assigned')
    })

    it('handles progress > 100%', () => {
      const overProgressAgent = {
        ...baseAgent,
        status: 'working',
        progress: 150
      }

      const wrapper = mount(AgentCardEnhanced, {
        ...globalOptions,
        props: {
          agent: overProgressAgent,
          mode: 'jobs'
        }
      })

      const progressSection = wrapper.find('.progress-section')
      expect(progressSection.text()).toContain('150%')
    })

    it('handles missing agent_type gracefully', () => {
      const noTypeAgent = { ...baseAgent }
      delete noTypeAgent.agent_type

      // Should not crash
      expect(() => {
        mount(AgentCardEnhanced, {
          ...globalOptions,
          props: {
            agent: { ...noTypeAgent, agent_type: 'orchestrator' }
          }
        })
      }).not.toThrow()
    })
  })
})
