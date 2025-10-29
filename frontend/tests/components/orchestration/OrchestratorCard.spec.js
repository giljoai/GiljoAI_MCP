import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import OrchestratorCard from '@/components/orchestration/OrchestratorCard.vue'

describe('OrchestratorCard.vue', () => {
  let wrapper
  let pinia
  let vuetify

  const mockOrchestrator = {
    id: 'orch-1',
    job_id: 'job-orch-1',
    is_orchestrator: true,
    name: 'Orchestrator',
    status: 'working',
    mission_summary: 'Building e-commerce platform with microservices architecture. Coordinating 6 specialized agents for backend, frontend, database, testing, documentation, and deployment tasks.',
    messages: [
      { id: 'msg-1', content: 'Agent coordination active', read: true },
      { id: 'msg-2', content: 'Backend agent blocked', read: false }
    ],
    tool_type: 'orchestrator'
  }

  const mockProject = {
    id: 'project-1',
    name: 'E-commerce Platform',
    status: 'active',
    can_close: false
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
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays orchestrator title with icon', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const title = wrapper.find('.orchestrator-title')
      expect(title.text()).toContain('ORCHESTRATOR')
      expect(wrapper.find('v-icon[icon="mdi-brain"]').exists()).toBe(true)
    })

    it('applies purple gradient header', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const header = wrapper.find('.orchestrator-header')
      expect(header.classes()).toContain('purple-gradient')
    })

    it('displays status message', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const status = wrapper.find('.orchestrator-status')
      expect(status.text()).toContain('Context Management & Project Coordination')
    })

    it('truncates mission summary to 150 characters', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const summary = wrapper.find('.mission-summary')
      expect(summary.text().length).toBeLessThanOrEqual(153) // 150 + "..."
    })
  })

  describe('Copy Prompt Buttons', () => {
    it('renders both copy prompt buttons', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const buttons = wrapper.findAll('.copy-prompt-btn')
      expect(buttons).toHaveLength(2)

      expect(buttons[0].text()).toContain('Copy Prompt (Claude Code)')
      expect(buttons[1].text()).toContain('Copy Prompt (Codex/Gemini)')
    })

    it('emits copy-prompt event for Claude Code', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const claudeButton = wrapper.findAll('.copy-prompt-btn')[0]
      await claudeButton.trigger('click')

      expect(wrapper.emitted('copy-prompt')).toBeTruthy()
      expect(wrapper.emitted('copy-prompt')[0]).toEqual(['claude-code'])
    })

    it('emits copy-prompt event for Codex/Gemini', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const codexButton = wrapper.findAll('.copy-prompt-btn')[1]
      await codexButton.trigger('click')

      expect(wrapper.emitted('copy-prompt')).toBeTruthy()
      expect(wrapper.emitted('copy-prompt')[0]).toEqual(['codex-gemini'])
    })

    it('copies to clipboard on button click', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const claudeButton = wrapper.findAll('.copy-prompt-btn')[0]
      await claudeButton.trigger('click')

      expect(navigator.clipboard.writeText).toHaveBeenCalled()
    })

    it('shows success notification after copying', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const claudeButton = wrapper.findAll('.copy-prompt-btn')[0]
      await claudeButton.trigger('click')

      await wrapper.vm.$nextTick()

      // Verify snackbar or toast notification
      expect(wrapper.vm.showCopySuccess).toBe(true)
    })

    it('handles clipboard API failure gracefully', async () => {
      // Mock clipboard failure
      navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('Clipboard denied'))

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const claudeButton = wrapper.findAll('.copy-prompt-btn')[0]
      await claudeButton.trigger('click')

      await wrapper.vm.$nextTick()

      // Should fall back to textarea copy method
      expect(wrapper.vm.copyError).toBeFalsy()
    })
  })

  describe('Message Count Badge', () => {
    it('displays message count badge', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const badge = wrapper.find('.message-badge')
      expect(badge.exists()).toBe(true)
    })

    it('shows unread message count', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const badge = wrapper.find('.message-badge')
      expect(badge.text()).toContain('1') // 1 unread message
    })

    it('hides badge when no unread messages', () => {
      const orchestratorAllRead = {
        ...mockOrchestrator,
        messages: [
          { id: 'msg-1', content: 'Message 1', read: true },
          { id: 'msg-2', content: 'Message 2', read: true }
        ]
      }

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: orchestratorAllRead,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const badge = wrapper.find('.message-badge')
      expect(badge.exists()).toBe(false)
    })
  })

  describe('Close Project Button', () => {
    it('hides close button when agents not finished', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const closeButton = wrapper.find('.close-project-btn')
      expect(closeButton.exists()).toBe(false)
    })

    it('shows close button when all agents finished', () => {
      const finishedProject = {
        ...mockProject,
        can_close: true
      }

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: finishedProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const closeButton = wrapper.find('.close-project-btn')
      expect(closeButton.exists()).toBe(true)
    })

    it('emits close-project event when button clicked', async () => {
      const finishedProject = {
        ...mockProject,
        can_close: true
      }

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: finishedProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const closeButton = wrapper.find('.close-project-btn')
      await closeButton.trigger('click')

      expect(wrapper.emitted('close-project')).toBeTruthy()
    })

    it('shows confirmation dialog before closing', async () => {
      const finishedProject = {
        ...mockProject,
        can_close: true
      }

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: finishedProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const closeButton = wrapper.find('.close-project-btn')
      await closeButton.trigger('click')

      // Verify confirmation dialog appears
      expect(wrapper.vm.showCloseConfirmation).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels on buttons', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('aria-label')).toBeDefined()
      })
    })

    it('supports keyboard navigation', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const buttons = wrapper.findAll('.copy-prompt-btn')

      // Test Tab key navigation
      buttons.forEach(button => {
        expect(button.attributes('tabindex')).not.toBe('-1')
      })
    })

    it('announces copy success to screen readers', async () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const claudeButton = wrapper.findAll('.copy-prompt-btn')[0]
      await claudeButton.trigger('click')

      await wrapper.vm.$nextTick()

      // Verify ARIA live region updated
      const liveRegion = wrapper.find('[role="status"]')
      expect(liveRegion.text()).toContain('Copied')
    })
  })

  describe('Responsive Design', () => {
    it('applies full width on mobile', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        },
        attachTo: document.body
      })

      const card = wrapper.find('.orchestrator-card')
      expect(card.classes()).toContain('full-width-mobile')
    })

    it('stacks buttons vertically on small screens', () => {
      // Mock small screen
      global.innerWidth = 400

      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const buttonContainer = wrapper.find('.button-container')
      expect(buttonContainer.classes()).toContain('flex-column')
    })
  })

  describe('Visual Styling', () => {
    it('uses purple color theme', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const header = wrapper.find('.orchestrator-header')
      const styles = window.getComputedStyle(header.element)

      // Verify purple gradient
      expect(styles.background).toContain('purple')
    })

    it('distinguishes from regular agent cards', () => {
      wrapper = mount(OrchestratorCard, {
        props: {
          orchestrator: mockOrchestrator,
          project: mockProject
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.classes()).toContain('orchestrator-card')
      expect(wrapper.classes()).not.toContain('agent-card')
    })
  })
})
