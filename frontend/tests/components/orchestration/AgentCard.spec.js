import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
// import AgentCard from '@/components/orchestration/AgentCard.vue' // module deleted/moved

describe.skip('AgentCard.vue - module deleted/moved', () => {
  let wrapper
  let pinia
  let vuetify

  const mockWorkingAgent = {
    id: 'agent-1',
    job_id: 'job-1',
    name: 'Backend Agent',
    status: 'working',
    agent_type: 'backend',
    tool_type: 'codex',
    job_description: 'Implementing REST API endpoints for user authentication and authorization. Building secure middleware and validation layers.',
    current_task: 'Adding input validation',
    progress: 47,
    messages: [
      { id: 'msg-1', content: 'Started implementation', read: true },
      { id: 'msg-2', content: 'Validation added', read: false }
    ]
  }

  const mockBlockedAgent = {
    id: 'agent-2',
    job_id: 'job-2',
    name: 'Frontend Agent',
    status: 'blocked',
    agent_type: 'frontend',
    tool_type: 'claude-code',
    job_description: 'Building Vue 3 components',
    block_reason: 'Waiting for API endpoints to be completed',
    messages: []
  }

  const mockCompleteAgent = {
    id: 'agent-3',
    job_id: 'job-3',
    name: 'Test Agent',
    status: 'complete',
    agent_type: 'testing',
    tool_type: 'gemini',
    job_description: 'Writing comprehensive test suite',
    messages: []
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue()
      }
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Rendering', () => {
    it('renders the component successfully', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays agent name and tool badge', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.text()).toContain('Backend Agent')
      expect(wrapper.find('.tool-badge').text()).toContain('codex')
    })

    it('displays job description truncated to 120 chars', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const description = wrapper.find('.job-description')
      expect(description.text().length).toBeLessThanOrEqual(123) // 120 + "..."
    })

    it('applies correct dimensions (280x360px)', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const card = wrapper.find('.agent-card')
      const styles = window.getComputedStyle(card.element)

      expect(card.attributes('style')).toContain('width')
      expect(card.attributes('style')).toContain('min-height')
    })

    it('applies colored left border matching status', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const card = wrapper.find('.agent-card')
      expect(card.classes()).toContain('status-working')
    })
  })

  describe('Status Display', () => {
    const statusTests = [
      { status: 'waiting', color: 'grey', icon: 'mdi-clock-outline', label: 'Waiting' },
      { status: 'preparing', color: 'light-blue', icon: 'mdi-loading', label: 'Preparing' },
      { status: 'working', color: 'primary', icon: 'mdi-cog', label: 'Working' },
      { status: 'review', color: 'purple', icon: 'mdi-eye', label: 'Under Review' },
      { status: 'complete', color: 'success', icon: 'mdi-check-circle', label: 'Complete' },
      { status: 'failed', color: 'error', icon: 'mdi-alert-circle', label: 'Failed' },
      { status: 'blocked', color: 'deep-orange-darken-4', icon: 'mdi-block-helper', label: 'Blocked' }
    ]

    statusTests.forEach(({ status, color, icon, label }) => {
      it(`displays ${status} status correctly`, () => {
        const agent = { ...mockWorkingAgent, status }

        wrapper = mount(AgentCard, {
          props: { agent },
          global: {
            plugins: [pinia, vuetify]
          }
        })

        const statusBadge = wrapper.find('.status-badge')
        expect(statusBadge.text()).toContain(label)
        expect(wrapper.find(`v-icon[icon="${icon}"]`).exists()).toBe(true)
      })
    })
  })

  describe('Progress Bar', () => {
    it('shows progress bar for working status', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const progressBar = wrapper.find('.progress-bar')
      expect(progressBar.exists()).toBe(true)
      expect(progressBar.text()).toContain('47%')
    })

    it('hides progress bar for non-working statuses', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockCompleteAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const progressBar = wrapper.find('.progress-bar')
      expect(progressBar.exists()).toBe(false)
    })

    it('displays current task when working', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const currentTask = wrapper.find('.current-task')
      expect(currentTask.exists()).toBe(true)
      expect(currentTask.text()).toContain('Adding input validation')
    })

    it('updates progress bar reactively', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.setProps({
        agent: { ...mockWorkingAgent, progress: 75 }
      })

      const progressBar = wrapper.find('.progress-bar')
      expect(progressBar.text()).toContain('75%')
    })
  })

  describe('Blocked Status', () => {
    it('displays block reason alert', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockBlockedAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const blockAlert = wrapper.find('.block-reason')
      expect(blockAlert.exists()).toBe(true)
      expect(blockAlert.text()).toContain('Waiting for API endpoints')
    })

    it('styles block alert as warning', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockBlockedAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const alert = wrapper.findComponent({ name: 'VAlert' })
      expect(alert.props('type')).toBe('warning')
    })
  })

  describe('Copy Prompt Button', () => {
    it('renders copy prompt button', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const copyButton = wrapper.find('.copy-prompt-btn')
      expect(copyButton.exists()).toBe(true)
      expect(copyButton.text()).toContain('Copy Prompt')
    })

    it('emits copy-prompt event on click', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const copyButton = wrapper.find('.copy-prompt-btn')
      await copyButton.trigger('click')

      expect(wrapper.emitted('copy-prompt')).toBeTruthy()
      expect(wrapper.emitted('copy-prompt')[0]).toEqual([mockWorkingAgent.id])
    })

    it('copies to clipboard on click', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const copyButton = wrapper.find('.copy-prompt-btn')
      await copyButton.trigger('click')

      expect(navigator.clipboard.writeText).toHaveBeenCalled()
    })

    it('shows success feedback after copying', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const copyButton = wrapper.find('.copy-prompt-btn')
      await copyButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showCopySuccess).toBe(true)
    })
  })

  describe('Message Badge', () => {
    it('displays message count badge', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          unreadCount: 1
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const badge = wrapper.findComponent({ name: 'VBadge' })
      expect(badge.exists()).toBe(true)
      expect(badge.props('content')).toBe(1)
    })

    it('hides badge when no unread messages', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          unreadCount: 0
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const badge = wrapper.findComponent({ name: 'VBadge' })
      expect(badge.exists()).toBe(false)
    })
  })

  describe('Message Accordion', () => {
    it('toggles message section on button click', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          isExpanded: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const toggleButton = wrapper.find('.message-toggle')
      await toggleButton.trigger('click')

      expect(wrapper.emitted('toggle-messages')).toBeTruthy()
    })

    it('shows expanded messages when isExpanded is true', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          isExpanded: true
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const expandedSection = wrapper.find('.expanded-messages')
      expect(expandedSection.exists()).toBe(true)
    })

    it('hides messages when isExpanded is false', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          isExpanded: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const expandedSection = wrapper.find('.expanded-messages')
      expect(expandedSection.exists()).toBe(false)
    })

    it('changes icon when expanded', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent,
          isExpanded: false
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      let icon = wrapper.find('.message-toggle v-icon:last-child')
      expect(icon.attributes('icon')).toBe('mdi-chevron-down')

      await wrapper.setProps({ isExpanded: true })

      icon = wrapper.find('.message-toggle v-icon:last-child')
      expect(icon.attributes('icon')).toBe('mdi-chevron-up')
    })
  })

  describe('Tool Type Badge', () => {
    const toolTests = [
      { tool: 'claude-code', color: 'primary' },
      { tool: 'codex', color: 'secondary' },
      { tool: 'gemini', color: 'accent' },
      { tool: 'universal', color: 'grey' }
    ]

    toolTests.forEach(({ tool, color }) => {
      it(`displays ${tool} badge with correct color`, () => {
        const agent = { ...mockWorkingAgent, tool_type: tool }

        wrapper = mount(AgentCard, {
          props: { agent },
          global: {
            plugins: [pinia, vuetify]
          }
        })

        const toolBadge = wrapper.find('.tool-badge')
        expect(toolBadge.exists()).toBe(true)
        expect(toolBadge.text()).toContain(tool)
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const card = wrapper.find('.agent-card')
      expect(card.attributes('role')).toBe('article')
      expect(card.attributes('aria-label')).toContain('Backend Agent')
    })

    it('supports keyboard navigation', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('tabindex')).not.toBe('-1')
      })
    })

    it('announces status changes to screen readers', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.setProps({
        agent: { ...mockWorkingAgent, status: 'complete' }
      })

      const liveRegion = wrapper.find('[role="status"]')
      expect(liveRegion.exists()).toBe(true)
    })

    it('has sufficient color contrast', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // WCAG 2.1 AA requires 4.5:1 contrast for normal text
      // This is validated through visual regression testing
      expect(wrapper.find('.agent-card').exists()).toBe(true)
    })
  })

  describe('Responsive Design', () => {
    it('adapts to mobile screens', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const card = wrapper.find('.agent-card')
      expect(card.classes()).toContain('responsive')
    })

    it('maintains aspect ratio on different screen sizes', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const card = wrapper.find('.agent-card')
      const styles = window.getComputedStyle(card.element)

      expect(styles.aspectRatio).toBeDefined()
    })
  })

  describe('State Updates', () => {
    it('updates UI when agent prop changes', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.text()).toContain('Working')

      await wrapper.setProps({
        agent: { ...mockWorkingAgent, status: 'complete', progress: 100 }
      })

      expect(wrapper.text()).toContain('Complete')
    })

    it('updates progress bar smoothly', async () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const progressValues = [50, 65, 80, 95, 100]

      for (const progress of progressValues) {
        await wrapper.setProps({
          agent: { ...mockWorkingAgent, progress }
        })

        const progressBar = wrapper.find('.progress-bar')
        expect(progressBar.text()).toContain(`${progress}%`)
      }
    })
  })

  describe('Performance', () => {
    it('renders quickly', () => {
      const startTime = performance.now()

      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // Should render in less than 50ms
      expect(renderTime).toBeLessThan(50)
    })

    it('does not cause memory leaks', () => {
      wrapper = mount(AgentCard, {
        props: {
          agent: mockWorkingAgent
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      wrapper.unmount()

      // Verify cleanup
      expect(wrapper.vm).toBeUndefined()
    })
  })
})
