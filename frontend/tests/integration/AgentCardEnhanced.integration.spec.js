/**
 * AgentCardEnhanced Integration Tests
 *
 * Tests the AgentCardEnhanced component in realistic usage scenarios
 * including interaction with Vuetify components and child components.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentCardEnhanced from '@/components/projects/AgentCardEnhanced.vue'

const vuetify = createVuetify({
  components,
  directives
})

describe('AgentCardEnhanced Integration Tests', () => {
  let wrapper

  beforeEach(() => {
    // Clean up any existing wrapper
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Complete User Flow - Launch Tab', () => {
    it('allows user to edit mission from launch tab', async () => {
      const agent = {
        job_id: 'test-001',
        agent_type: 'implementor',
        status: 'waiting',
        mission: 'Test mission'
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'launch'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Find and click edit button
      const buttons = wrapper.findAll('button')
      const editButton = buttons.find(btn => btn.text().includes('Edit Mission'))

      expect(editButton).toBeDefined()
      await editButton.trigger('click')
      await flushPromises()

      // Verify event emitted
      expect(wrapper.emitted('edit-mission')).toBeTruthy()
      expect(wrapper.emitted('edit-mission')[0][0]).toEqual(agent)
    })
  })

  describe('Complete User Flow - Jobs Tab Waiting to Working', () => {
    it('launches agent from waiting state', async () => {
      const agent = {
        job_id: 'test-002',
        agent_type: 'implementor',
        status: 'waiting',
        mission: 'Implement feature',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify initial state
      expect(wrapper.find('.status-badge').text()).toBe('Waiting')

      // Find and click launch button
      const buttons = wrapper.findAll('button')
      const launchButton = buttons.find(btn => btn.text().includes('Launch Agent'))

      expect(launchButton).toBeDefined()
      await launchButton.trigger('click')
      await flushPromises()

      // Verify event emitted
      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0][0]).toEqual(agent)
    })

    it('updates to working state and displays progress', async () => {
      const agent = {
        job_id: 'test-003',
        agent_type: 'implementor',
        status: 'working',
        mission: 'Implement feature',
        progress: 45,
        current_task: 'Writing unit tests',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify working state display
      expect(wrapper.find('.status-badge').text()).toBe('Working')
      expect(wrapper.find('.progress-section').exists()).toBe(true)
      expect(wrapper.text()).toContain('45%')
      expect(wrapper.text()).toContain('Writing unit tests')

      // Find and click details button
      const buttons = wrapper.findAll('button')
      const detailsButton = buttons.find(btn => btn.text().includes('Details'))

      expect(detailsButton).toBeDefined()
      await detailsButton.trigger('click')
      await flushPromises()

      // Verify event emitted
      expect(wrapper.emitted('view-details')).toBeTruthy()
    })
  })

  describe('Message Badge Integration', () => {
    it('displays and counts all message types correctly', async () => {
      const agent = {
        job_id: 'test-004',
        agent_type: 'implementor',
        status: 'working',
        mission: 'Test mission',
        progress: 50,
        messages: [
          { id: 1, status: 'pending', from: 'agent', content: 'Question 1' },
          { id: 2, status: 'pending', from: 'agent', content: 'Question 2' },
          { id: 3, status: 'pending', from: 'agent', content: 'Question 3' },
          { id: 4, status: 'acknowledged', from: 'agent', content: 'Update 1' },
          { id: 5, status: 'acknowledged', from: 'agent', content: 'Update 2' },
          { id: 6, from: 'developer', content: 'Response 1' },
          { id: 7, from: 'developer', content: 'Response 2' },
          { id: 8, from: 'developer', content: 'Response 3' },
          { id: 9, from: 'developer', content: 'Response 4' }
        ]
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify all three badge types exist
      const badges = wrapper.findAll('.message-badges .v-chip')
      expect(badges.length).toBeGreaterThanOrEqual(3)

      // Verify counts
      const unreadBadge = badges.find(badge => badge.text().includes('Unread'))
      expect(unreadBadge).toBeDefined()
      expect(unreadBadge.text()).toContain('3')

      const readBadge = badges.find(badge => badge.text().includes('Read'))
      expect(readBadge).toBeDefined()
      expect(readBadge.text()).toContain('2')

      const sentBadge = badges.find(badge => badge.text().includes('Sent'))
      expect(sentBadge).toBeDefined()
      expect(sentBadge.text()).toContain('4')
    })

    it('hides badges when counts are zero', async () => {
      const agent = {
        job_id: 'test-005',
        agent_type: 'implementor',
        status: 'working',
        mission: 'Test mission',
        progress: 50,
        messages: [
          { id: 1, status: 'acknowledged', from: 'agent', content: 'Only acknowledged' }
        ]
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      const badges = wrapper.findAll('.message-badges .v-chip')

      // Should only show acknowledged badge
      const unreadBadge = badges.find(badge => badge.text().includes('Unread'))
      expect(unreadBadge).toBeUndefined()

      const sentBadge = badges.find(badge => badge.text().includes('Sent'))
      expect(sentBadge).toBeUndefined()

      const readBadge = badges.find(badge => badge.text().includes('Read'))
      expect(readBadge).toBeDefined()
    })
  })

  describe('Error Handling Flow', () => {
    it('handles failed state and allows viewing error', async () => {
      const agent = {
        job_id: 'test-006',
        agent_type: 'implementor',
        status: 'failed',
        mission: 'Test mission',
        block_reason: 'Database connection failed',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify failed state display
      expect(wrapper.find('.status-badge').text()).toBe('Failure')
      expect(wrapper.find('.priority-card').exists()).toBe(true)
      expect(wrapper.text()).toContain('Database connection failed')

      // Find and click view error button
      const buttons = wrapper.findAll('button')
      const errorButton = buttons.find(btn => btn.text().includes('View Error'))

      expect(errorButton).toBeDefined()
      await errorButton.trigger('click')
      await flushPromises()

      // Verify event emitted
      expect(wrapper.emitted('view-error')).toBeTruthy()
      expect(wrapper.emitted('view-error')[0][0]).toEqual(agent)
    })

    it('handles blocked state with warning alert', async () => {
      const agent = {
        job_id: 'test-007',
        agent_type: 'implementor',
        status: 'blocked',
        mission: 'Test mission',
        block_reason: 'Waiting for API approval',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs'
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify blocked state display
      expect(wrapper.find('.status-badge').text()).toBe('Blocked')
      expect(wrapper.find('.priority-card').exists()).toBe(true)
      expect(wrapper.text()).toContain('Waiting for API approval')
    })
  })

  describe('Multi-Instance Agent Display', () => {
    it('displays instance badge for second instance', async () => {
      const agent = {
        job_id: 'test-008',
        agent_type: 'implementor',
        status: 'complete',
        mission: 'Test mission',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs',
          instanceNumber: 2
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify instance badge
      expect(wrapper.find('.instance-badge').exists()).toBe(true)
      expect(wrapper.text()).toContain('Instance 2')
    })

    it('does not display instance badge for first instance', async () => {
      const agent = {
        job_id: 'test-009',
        agent_type: 'implementor',
        status: 'complete',
        mission: 'Test mission',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs',
          instanceNumber: 1
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify no instance badge for first instance
      expect(wrapper.find('.instance-badge').exists()).toBe(false)
    })
  })

  describe('Orchestrator Features Integration', () => {
    it('displays launch prompt icons for orchestrator', async () => {
      const agent = {
        job_id: 'test-010',
        agent_type: 'orchestrator',
        status: 'working',
        mission: 'Coordinate agents',
        progress: 50,
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs',
          isOrchestrator: true
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify LaunchPromptIcons component exists
      const launchPromptIcons = wrapper.findComponent({ name: 'LaunchPromptIcons' })
      expect(launchPromptIcons.exists()).toBe(true)
    })

    it('displays closeout button when all agents complete', async () => {
      const agent = {
        job_id: 'test-011',
        agent_type: 'orchestrator',
        status: 'complete',
        mission: 'Coordinate agents',
        progress: 100,
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: {
          agent,
          mode: 'jobs',
          isOrchestrator: true,
          showCloseoutButton: true
        },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Find closeout button
      const buttons = wrapper.findAll('button')
      const closeoutButton = buttons.find(btn => btn.text().includes('Closeout Project'))

      expect(closeoutButton).toBeDefined()

      // Click button and verify event
      await closeoutButton.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('closeout-project')).toBeTruthy()
    })
  })

  describe('Responsive Behavior', () => {
    it('maintains fixed width of 280px', async () => {
      const agent = {
        job_id: 'test-012',
        agent_type: 'implementor',
        status: 'waiting',
        mission: 'Test mission',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: { agent, mode: 'jobs' },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      const card = wrapper.find('.agent-card-enhanced')
      const style = card.attributes('style')

      expect(style).toContain('280px')
    })
  })

  describe('Accessibility Integration', () => {
    it('provides complete keyboard navigation', async () => {
      const agent = {
        job_id: 'test-013',
        agent_type: 'implementor',
        status: 'waiting',
        mission: 'Test mission',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: { agent, mode: 'jobs' },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()

      // Verify card has proper ARIA attributes
      const card = wrapper.find('[role="article"]')
      expect(card.exists()).toBe(true)
      expect(card.attributes('aria-label')).toBeTruthy()

      // Verify all interactive elements are keyboard accessible
      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('tabindex')).not.toBe('-1')
      })
    })
  })

  describe('Real-world Scenario: Complete Project Lifecycle', () => {
    it('handles agent progressing through all states', async () => {
      // Start with waiting state
      let agent = {
        job_id: 'lifecycle-001',
        agent_type: 'implementor',
        status: 'waiting',
        mission: 'Build authentication system',
        messages: []
      }

      wrapper = mount(AgentCardEnhanced, {
        props: { agent, mode: 'jobs' },
        global: {
          plugins: [vuetify],
          stubs: {
            ChatHeadBadge: true,
            LaunchPromptIcons: true
          }
        }
      })

      await flushPromises()
      expect(wrapper.find('.status-badge').text()).toBe('Waiting')

      // Update to working state
      await wrapper.setProps({
        agent: {
          ...agent,
          status: 'working',
          progress: 25,
          current_task: 'Setting up database schema'
        }
      })
      await flushPromises()
      expect(wrapper.find('.status-badge').text()).toBe('Working')
      expect(wrapper.text()).toContain('25%')

      // Progress update
      await wrapper.setProps({
        agent: {
          ...agent,
          status: 'working',
          progress: 75,
          current_task: 'Implementing login endpoints'
        }
      })
      await flushPromises()
      expect(wrapper.text()).toContain('75%')
      expect(wrapper.text()).toContain('Implementing login endpoints')

      // Complete state
      await wrapper.setProps({
        agent: {
          ...agent,
          status: 'complete',
          progress: 100
        }
      })
      await flushPromises()
      expect(wrapper.find('.status-badge').text()).toBe('Complete')
      expect(wrapper.find('.complete-text').exists()).toBe(true)
    })
  })
})
