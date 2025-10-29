import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'

describe('CloseoutModal.vue', () => {
  let wrapper
  let pinia
  let vuetify

  const mockCloseoutData = {
    project_id: 'project-1',
    project_name: 'E-commerce Platform',
    checklist: [
      'Review all agent work',
      'Run final tests',
      'Commit all changes',
      'Push to remote repository',
      'Update documentation',
      'Close agent terminals'
    ],
    closeout_prompt: `#!/bin/bash
# Project closeout commands
cd /path/to/project
git add .
git commit -m "Project complete: E-commerce Platform"
git push origin main
orchestrator document-project
orchestrator close-agents`
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
    it('renders when show prop is true', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(true)
    })

    it('does not render when show prop is false', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: false,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(false)
    })

    it('displays project name in title', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const title = wrapper.find('.modal-title')
      expect(title.text()).toContain('E-commerce Platform')
    })

    it('displays all checklist items', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Wait for checklist to load
      await wrapper.vm.$nextTick()

      const checklistItems = wrapper.findAll('.checklist-item')
      expect(checklistItems.length).toBe(mockCloseoutData.checklist.length)
    })

    it('displays closeout prompt in code block', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const codeBlock = wrapper.find('.closeout-prompt')
      expect(codeBlock.exists()).toBe(true)
      expect(codeBlock.text()).toContain('git add .')
      expect(codeBlock.text()).toContain('git commit')
      expect(codeBlock.text()).toContain('git push')
    })
  })

  describe('Closeout Data Loading', () => {
    it('fetches closeout data on mount', async () => {
      const fetchCloseoutMock = vi.fn().mockResolvedValue(mockCloseoutData)

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            fetchCloseoutData: fetchCloseoutMock
          }
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.loading).toBe(false)
      expect(wrapper.vm.closeoutData).toBeDefined()
    })

    it('shows loading state while fetching', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const loader = wrapper.findComponent({ name: 'VProgressCircular' })
      expect(loader.exists()).toBe(true)
    })

    it('handles fetch error gracefully', async () => {
      const fetchCloseoutMock = vi.fn().mockRejectedValue(new Error('API Error'))

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            fetchCloseoutData: fetchCloseoutMock
          }
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.error).toBeTruthy()
      const errorAlert = wrapper.findComponent({ name: 'VAlert' })
      expect(errorAlert.exists()).toBe(true)
    })
  })

  describe('Checklist Interaction', () => {
    it('allows checking checklist items', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const firstCheckbox = wrapper.findAll('.checklist-checkbox')[0]
      await firstCheckbox.trigger('click')

      expect(wrapper.vm.checkedItems).toContain(0)
    })

    it('tracks all checked items', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const checkboxes = wrapper.findAll('.checklist-checkbox')

      for (let i = 0; i < checkboxes.length; i++) {
        await checkboxes[i].trigger('click')
      }

      expect(wrapper.vm.checkedItems.length).toBe(mockCloseoutData.checklist.length)
    })

    it('shows visual feedback for checked items', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const firstCheckbox = wrapper.findAll('.checklist-checkbox')[0]
      await firstCheckbox.trigger('click')

      const firstItem = wrapper.findAll('.checklist-item')[0]
      expect(firstItem.classes()).toContain('checked')
    })
  })

  describe('Copy Prompt Functionality', () => {
    it('copies closeout prompt to clipboard', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const copyButton = wrapper.find('.copy-closeout-btn')
      await copyButton.trigger('click')

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('git add .'))
    })

    it('shows success feedback after copying', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const copyButton = wrapper.find('.copy-closeout-btn')
      await copyButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.copySuccess).toBe(true)
      expect(wrapper.find('.copy-success-msg').exists()).toBe(true)
    })

    it('handles clipboard API failure with fallback', async () => {
      navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('Permission denied'))

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const copyButton = wrapper.find('.copy-closeout-btn')
      await copyButton.trigger('click')

      await wrapper.vm.$nextTick()

      // Should use fallback method (textarea copy)
      expect(wrapper.vm.copySuccess).toBe(true)
    })
  })

  describe('Confirmation Checkbox', () => {
    it('renders confirmation checkbox', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const confirmCheckbox = wrapper.find('.confirm-checkbox')
      expect(confirmCheckbox.exists()).toBe(true)
      expect(confirmCheckbox.text()).toContain('I have executed the closeout')
    })

    it('disables complete button until confirmed', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const completeButton = wrapper.find('.complete-project-btn')
      expect(completeButton.attributes('disabled')).toBeDefined()
    })

    it('enables complete button when confirmed', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const confirmCheckbox = wrapper.find('.confirm-checkbox')
      await confirmCheckbox.trigger('click')

      const completeButton = wrapper.find('.complete-project-btn')
      expect(completeButton.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Modal Actions', () => {
    it('emits close event on cancel', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const cancelButton = wrapper.find('.cancel-btn')
      await cancelButton.trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('calls API and emits complete event on confirm', async () => {
      const completeProjectMock = vi.fn().mockResolvedValue({ success: true })

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            completeProject: completeProjectMock
          }
        }
      })

      await wrapper.vm.$nextTick()

      // Confirm closeout
      const confirmCheckbox = wrapper.find('.confirm-checkbox')
      await confirmCheckbox.trigger('click')

      // Click complete
      const completeButton = wrapper.find('.complete-project-btn')
      await completeButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(completeProjectMock).toHaveBeenCalledWith(mockCloseoutData.project_id)
      expect(wrapper.emitted('complete')).toBeTruthy()
    })

    it('shows loading state during completion', async () => {
      const completeProjectMock = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            completeProject: completeProjectMock
          }
        }
      })

      await wrapper.vm.$nextTick()

      const confirmCheckbox = wrapper.find('.confirm-checkbox')
      await confirmCheckbox.trigger('click')

      const completeButton = wrapper.find('.complete-project-btn')
      await completeButton.trigger('click')

      expect(wrapper.vm.completing).toBe(true)
      expect(completeButton.attributes('loading')).toBe('true')
    })

    it('handles completion error', async () => {
      const completeProjectMock = vi.fn().mockRejectedValue(new Error('API Error'))

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            completeProject: completeProjectMock
          }
        }
      })

      await wrapper.vm.$nextTick()

      const confirmCheckbox = wrapper.find('.confirm-checkbox')
      await confirmCheckbox.trigger('click')

      const completeButton = wrapper.find('.complete-project-btn')
      await completeButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.error).toBeTruthy()
      const errorAlert = wrapper.findComponent({ name: 'VAlert' })
      expect(errorAlert.exists()).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper modal role and labels', () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      expect(dialog.attributes('role')).toBe('dialog')
      expect(dialog.attributes('aria-labelledby')).toBeDefined()
    })

    it('traps focus within modal', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        },
        attachTo: document.body
      })

      await wrapper.vm.$nextTick()

      const focusableElements = wrapper.findAll('button, input, [tabindex]:not([tabindex="-1"])')
      expect(focusableElements.length).toBeGreaterThan(0)
    })

    it('closes on Escape key', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        },
        attachTo: document.body
      })

      await wrapper.trigger('keydown', { key: 'Escape' })

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('has proper ARIA labels on all interactive elements', async () => {
      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      const buttons = wrapper.findAll('button')
      buttons.forEach(button => {
        expect(button.attributes('aria-label')).toBeDefined()
      })
    })
  })

  describe('Responsive Design', () => {
    it('renders fullscreen on mobile', () => {
      global.innerWidth = 400

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      expect(dialog.props('fullscreen')).toBe(true)
    })

    it('renders as dialog on desktop', () => {
      global.innerWidth = 1200

      wrapper = mount(CloseoutModal, {
        props: {
          show: true,
          projectId: mockCloseoutData.project_id,
          projectName: mockCloseoutData.project_name
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      expect(dialog.props('fullscreen')).toBe(false)
      expect(dialog.props('maxWidth')).toBeDefined()
    })
  })
})
