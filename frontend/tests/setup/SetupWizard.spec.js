import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, VueWrapper } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { useRouter } from 'vue-router'
import { vi } from 'vitest'
import { nextTick } from 'vue'
import SetupWizard from '@/views/SetupWizard.vue'
import AttachToolsStep from '@/components/setup/AttachToolsStep.vue'
import NetworkConfigStep from '@/components/setup/NetworkConfigStep.vue'
import SetupCompleteStep from '@/components/setup/SetupCompleteStep.vue'

// Mock services and stores
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    currentRoute: {
      value: {
        path: '/setup'
      }
    }
  })),
  RouterView: { template: '<div />' }
}))

// Mock Vuetify components
const VuetifyMock = {
  VContainer: {
    template: '<div><slot /></div>'
  },
  VRow: {
    template: '<div><slot /></div>'
  },
  VCol: {
    template: '<div><slot /></div>'
  },
  VStepper: {
    template: '<div><slot /></div>'
  },
  VStepperHeader: {
    template: '<div><slot /></div>'
  },
  VStepperItem: {
    template: '<div><slot /></div>'
  },
  VStepperContent: {
    template: '<div><slot /></div>'
  },
  VCard: {
    template: '<div><slot /></div>'
  },
  VCardTitle: {
    template: '<div><slot /></div>'
  },
  VCardText: {
    template: '<div><slot /></div>'
  },
  VCardActions: {
    template: '<div><slot /></div>'
  },
  VBtn: {
    template: '<button><slot /></button>'
  }
}

vi.mock('vuetify/components', () => VuetifyMock)

// Ignore Vuetify CSS
vi.mock('vuetify/lib/components/VCode/VCode.css', () => ({
  __esModule: true,
  default: ''
}))

// Helper function to create a mock store
const createMockSetupStore = () => ({
  currentStep: 1,
  completedSteps: [],
  setupData: {},
  nextStep: vi.fn(),
  prevStep: vi.fn(),
  completeSetup: vi.fn()
})

describe('SetupWizard', () => {
  let wrapper
  let mockRouter

  beforeEach(() => {
    mockRouter = {
      push: vi.fn(),
      currentRoute: { value: { path: '/setup' } }
    }
    vi.mocked(useRouter).mockReturnValue(mockRouter)

    wrapper = mount(SetupWizard, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {
              setup: {
                currentStep: 1,
                completedSteps: [],
                setupData: {}
              }
            }
          })
        ],
        stubs: {
          'attach-tools-step': true,
          'network-config-step': true,
          'setup-complete-step': true
        }
      }
    })
  })

  // Test 1: First Launch Detection
  it('renders setup wizard with correct initial state', async () => {
    expect(wrapper.findComponent(AttachToolsStep).exists()).toBe(true)
    expect(wrapper.text()).toContain('Step 1 of 3: Attach Tools')

    // Verify progress indicator
    const progressIndicator = wrapper.find('[data-testid="progress-indicator"]')
    expect(progressIndicator.text()).toMatch(/●━━○━━○/)
  })

  // Test 2: Step Navigation
  it('allows navigation between steps', async () => {
    const nextButton = wrapper.find('[data-testid="next-button"]')

    // Simulate step 1 completion
    await wrapper.vm.nextStep()

    // Should be on step 2
    expect(wrapper.findComponent(NetworkConfigStep).exists()).toBe(true)
    expect(wrapper.text()).toContain('Step 2 of 3: Network Configuration')
  })

  // Test 3: Error Handling
  it('handles navigation errors gracefully', async () => {
    // Simulate an error preventing step progression
    vi.spyOn(wrapper.vm, 'validateStep').mockImplementationOnce(() => {
      throw new Error('Validation failed')
    })

    const nextButton = wrapper.find('[data-testid="next-button"]')
    await nextButton.trigger('click')

    // Verify error handling
    expect(wrapper.text()).toContain('Could not proceed')
  })

  // Test 4: Responsive Behavior
  it('adjusts layout for different screen sizes', async () => {
    // Simulate mobile viewport
    window.innerWidth = 375
    window.dispatchEvent(new Event('resize'))
    await flushPromises()

    expect(wrapper.classes()).toContain('mobile-layout')

    // Simulate desktop viewport
    window.innerWidth = 1920
    window.dispatchEvent(new Event('resize'))
    await flushPromises()

    expect(wrapper.classes()).toContain('desktop-layout')
  })

  // Test 5: Accessibility
  it('supports keyboard navigation', async () => {
    const nextButton = wrapper.find('[data-testid="next-button"]')

    // Simulate keyboard navigation
    await nextButton.trigger('keydown.enter')
    await nextButton.trigger('keydown.space')

    expect(wrapper.vm.currentStep).toBe(2)
  })

  // Test 6: Final Completion
  it('completes setup and redirects to dashboard', async () => {
    // Simulate completing all steps
    await wrapper.vm.completeSetup()

    expect(mockRouter.push).toHaveBeenCalledWith('/')
    // Verify API call was made to mark setup complete
  })
})

// Detailed step-specific tests
describe('AttachToolsStep', () => {
  it('shows Claude Code attachment options', () => {
    const wrapper = mount(AttachToolsStep)

    const claudeCodeCard = wrapper.find('[data-testid="claude-code-card"]')
    expect(claudeCodeCard.exists()).toBe(true)
    expect(claudeCodeCard.text()).toContain('Attach')

    const futureCards = wrapper.findAll('[data-testid$="-future-card"]')
    expect(futureCards.length).toBe(2)
  })
})

describe('NetworkConfigStep', () => {
  it('supports localhost and LAN configurations', async () => {
    const wrapper = mount(NetworkConfigStep)

    // Select LAN option
    const lanRadio = wrapper.find('[data-testid="lan-option"]')
    await lanRadio.trigger('change')

    // Verify LAN configuration fields appear
    expect(wrapper.find('[data-testid="lan-config-panel"]').exists()).toBe(true)
  })
})

describe('SetupCompleteStep', () => {
  it('shows configuration summary', () => {
    const wrapper = mount(SetupCompleteStep, {
      props: {
        setupData: {
          mode: 'localhost',
          toolsAttached: ['Claude Code'],
          databaseReady: true
        }
      }
    })

    expect(wrapper.text()).toContain('Setup Complete')
    expect(wrapper.text()).toContain('Localhost Mode')
    expect(wrapper.text()).toContain('Claude Code Attached')
  })
})