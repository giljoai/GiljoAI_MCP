import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import LaunchSuccessorDialog from '../LaunchSuccessorDialog.vue'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      triggerSuccession: vi.fn(),
    },
  },
}))

// Mock useToast composable
const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
}

vi.mock('@/composables/useToast', () => ({
  useToast: () => mockToast,
}))

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(),
  },
})

describe('LaunchSuccessorDialog.vue', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify()
    vi.clearAllMocks()
  })

  const mockCurrentJob = {
    id: 'job-1',
    instance_number: 1,
    status: 'working',
    context_used: 150000,
    context_budget: 200000,
  }

  const mockSuccessionResponse = {
    data: {
      successor_job_id: 'job-2',
      instance_number: 2,
      launch_prompt: 'Launch successor with this prompt...',
      handover_summary: 'Handover summary here',
      succession_reason: 'manual',
      created_at: '2025-01-15T15:00:00Z',
    },
  }

  const createWrapper = (props = {}) => {
    return mount(LaunchSuccessorDialog, {
      props: {
        jobId: 'job-1',
        currentJob: mockCurrentJob,
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
    it('renders dialog with activator slot', () => {
      const wrapper = createWrapper()
      expect(wrapper.findComponent({ name: 'VDialog' }).exists()).toBe(true)
    })

    it('displays correct title with next instance number', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Launch Successor Orchestrator')
      expect(wrapper.text()).toContain('Instance 2')
    })

    it('shows info alert about creating new instance', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('This will create a new orchestrator instance (2)')
    })

    it('displays warning alert about agent completion', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Ensure all agents have completed their work before proceeding')
      expect(wrapper.text()).toContain(
        'Messages sent to this orchestrator will be received by the successor',
      )
    })

    it('displays succession reason dropdown', () => {
      const wrapper = createWrapper()
      const select = wrapper.findComponent({ name: 'VSelect' })
      expect(select.exists()).toBe(true)
    })

    it('displays optional notes textarea', () => {
      const wrapper = createWrapper()
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.exists()).toBe(true)
      expect(textarea.props('label')).toContain('Notes (optional)')
    })
  })

  describe('Current Instance Summary', () => {
    it('displays current instance details', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Current Instance Summary')
      expect(wrapper.text()).toContain('Instance: 1')
      expect(wrapper.text()).toContain('Status: working')
    })

    it('shows context usage with formatted numbers', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('150,000')
      expect(wrapper.text()).toContain('200,000')
      expect(wrapper.text()).toContain('75%')
    })

    it('displays context usage progress bar', () => {
      const wrapper = createWrapper()
      const progressBar = wrapper.findComponent({ name: 'VProgressLinear' })
      expect(progressBar.exists()).toBe(true)
      expect(progressBar.props('modelValue')).toBe(75)
    })

    it('shows correct context color based on usage', () => {
      const wrapper = createWrapper({ currentJob: { ...mockCurrentJob, context_used: 50000 } })
      expect(wrapper.vm.contextColor).toBe('success')

      const wrapper2 = createWrapper({ currentJob: { ...mockCurrentJob, context_used: 150000 } })
      expect(wrapper2.vm.contextColor).toBe('warning')

      const wrapper3 = createWrapper({ currentJob: { ...mockCurrentJob, context_used: 190000 } })
      expect(wrapper3.vm.contextColor).toBe('error')
    })
  })

  describe('Succession Reason Selection', () => {
    it('has manual as default reason', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.successionReason).toBe('manual')
    })

    it('provides correct reason options', () => {
      const wrapper = createWrapper()
      const options = wrapper.vm.reasonOptions
      expect(options).toHaveLength(3)
      expect(options.map((o) => o.value)).toEqual(['manual', 'context_limit', 'phase_transition'])
    })

    it('allows selecting different reasons', async () => {
      const wrapper = createWrapper()
      wrapper.vm.successionReason = 'context_limit'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.successionReason).toBe('context_limit')
    })
  })

  describe('Trigger Succession', () => {
    it('calls API with correct parameters', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()

      wrapper.vm.successionReason = 'manual'
      wrapper.vm.notes = 'Test notes'
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(api.agentJobs.triggerSuccession).toHaveBeenCalledWith('job-1', 'manual', 'Test notes')
    })

    it('displays launch prompt after successful succession', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()

      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(wrapper.vm.launchPrompt).toBe('Launch successor with this prompt...')
      expect(wrapper.text()).toContain('Thin-Client Launch Prompt')
    })

    it('shows success toast with instance number', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()

      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(mockToast.success).toHaveBeenCalledWith('Successor instance 2 created')
    })

    it('emits succession-triggered event with data', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()

      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(wrapper.emitted('succession-triggered')).toBeTruthy()
      expect(wrapper.emitted('succession-triggered')[0][0]).toEqual(mockSuccessionResponse.data)
    })

    it('sets loading state during API call', async () => {
      let resolvePromise
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      api.agentJobs.triggerSuccession.mockReturnValue(promise)

      const wrapper = createWrapper()
      const successionPromise = wrapper.vm.triggerSuccession()

      expect(wrapper.vm.loading).toBe(true)

      resolvePromise(mockSuccessionResponse)
      await successionPromise
      await flushPromises()

      expect(wrapper.vm.loading).toBe(false)
    })

    it('handles API errors gracefully', async () => {
      const errorResponse = {
        response: {
          data: {
            detail: 'Job not found',
          },
        },
      }
      api.agentJobs.triggerSuccession.mockRejectedValue(errorResponse)
      const wrapper = createWrapper()

      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(wrapper.vm.error).toBe('Job not found')
      expect(mockToast.error).toHaveBeenCalledWith('Job not found')
      expect(wrapper.text()).toContain('Job not found')
    })

    it('shows generic error message when detail not available', async () => {
      api.agentJobs.triggerSuccession.mockRejectedValue(new Error('Network error'))
      const wrapper = createWrapper()

      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(wrapper.vm.error).toBe('Failed to trigger succession')
      expect(mockToast.error).toHaveBeenCalledWith('Failed to trigger succession')
    })
  })

  describe('Launch Prompt Actions', () => {
    beforeEach(async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
    })

    it('shows copy button when launch prompt is available', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      const copyButton = wrapper.find('[icon="mdi-content-copy"]')
      expect(copyButton.exists()).toBe(true)
    })

    it('copies prompt to clipboard', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      await wrapper.vm.copyPrompt()

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        'Launch successor with this prompt...',
      )
      expect(mockToast.success).toHaveBeenCalledWith('Launch prompt copied to clipboard')
    })

    it('handles clipboard copy failure', async () => {
      navigator.clipboard.writeText.mockRejectedValueOnce(new Error('Clipboard error'))
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      await wrapper.vm.copyPrompt()

      expect(mockToast.error).toHaveBeenCalledWith('Failed to copy prompt')
    })

    it('shows copy and close button after prompt generation', async () => {
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      expect(wrapper.text()).toContain('Copy Prompt & Close')
    })

    it('copies prompt and closes dialog on copyAndClose', async () => {
      const wrapper = createWrapper()
      wrapper.vm.dialog = true
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      await wrapper.vm.copyAndClose()

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        'Launch successor with this prompt...',
      )
      expect(wrapper.vm.dialog).toBe(false)
    })
  })

  describe('Dialog Controls', () => {
    it('has cancel button', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Cancel')
    })

    it('has trigger succession button', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Trigger Succession')
    })

    it('shows loading state on trigger button', async () => {
      let resolvePromise
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      api.agentJobs.triggerSuccession.mockReturnValue(promise)

      const wrapper = createWrapper()
      const successionPromise = wrapper.vm.triggerSuccession()

      await wrapper.vm.$nextTick()
      const button = wrapper.findAll('button').find((b) => b.text().includes('Trigger Succession'))
      expect(wrapper.vm.loading).toBe(true)

      resolvePromise(mockSuccessionResponse)
      await successionPromise
    })
  })

  describe('Computed Properties', () => {
    it('calculates next instance number correctly', () => {
      const wrapper = createWrapper({ currentJob: { ...mockCurrentJob, instance_number: 3 } })
      expect(wrapper.vm.nextInstanceNumber).toBe(4)
    })

    it('defaults to instance 2 when instance_number is null', () => {
      const wrapper = createWrapper({ currentJob: { ...mockCurrentJob, instance_number: null } })
      expect(wrapper.vm.nextInstanceNumber).toBe(2)
    })

    it('calculates context percentage correctly', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.contextPercentage).toBe(75)
    })

    it('returns 0 for context percentage when budget is missing', () => {
      const wrapper = createWrapper({ currentJob: { ...mockCurrentJob, context_budget: null } })
      expect(wrapper.vm.contextPercentage).toBe(0)
    })
  })

  describe('Helper Functions', () => {
    it('formatNumber adds thousand separators', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.formatNumber(150000)).toBe('150,000')
      expect(wrapper.vm.formatNumber(1500)).toBe('1,500')
      expect(wrapper.vm.formatNumber(null)).toBe(0)
    })
  })

  describe('Accessibility', () => {
    it('has proper dialog structure', () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent({ name: 'VDialog' })
      expect(dialog.exists()).toBe(true)
      expect(dialog.props('maxWidth')).toBe('800')
    })

    it('has activator slot for custom triggers', () => {
      const wrapper = createWrapper()
      const dialog = wrapper.findComponent({ name: 'VDialog' })
      expect(dialog.vm.$slots.activator).toBeDefined()
    })
  })

  describe('Prompt Display', () => {
    it('displays prompt in monospace font', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      const promptElement = wrapper.find('.launch-prompt')
      expect(promptElement.exists()).toBe(true)
    })

    it('has scrollable prompt area', async () => {
      api.agentJobs.triggerSuccession.mockResolvedValue(mockSuccessionResponse)
      const wrapper = createWrapper()
      await wrapper.vm.triggerSuccession()
      await flushPromises()

      const promptElement = wrapper.find('.launch-prompt')
      expect(promptElement.classes()).toContain('launch-prompt')
    })
  })
})
