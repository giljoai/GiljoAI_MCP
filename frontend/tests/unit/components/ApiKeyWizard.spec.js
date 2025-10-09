import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ApiKeyWizard from '@/components/ApiKeyWizard.vue'
import { createTestingPinia } from '@pinia/testing'
import axios from 'axios'

vi.mock('axios')

describe('ApiKeyWizard', () => {
  let wrapper
  let mockAxios

  beforeEach(() => {
    mockAxios = {
      post: vi.fn(),
      get: vi.fn()
    }

    axios.create = vi.fn(() => mockAxios)

    wrapper = mount(ApiKeyWizard, {
      props: {
        modelValue: true  // Open the dialog for testing
      },
      global: {
        plugins: [
          createTestingPinia({
            initialState: {
              // Any initial state needed
            }
          })
        ],
        stubs: {
          ToolConfigSnippet: true
        }
      }
    })
  })

  it('renders wizard with initial step', async () => {
    expect(wrapper.vm.currentStep).toBe(1)
    expect(wrapper.find('[data-test="step-1"]').exists()).toBe(true)
  })

  it('validates name input in step 1', async () => {
    // Empty name
    wrapper.vm.keyName = ''
    await wrapper.vm.nextStep()
    expect(wrapper.vm.currentStep).toBe(1)
    expect(wrapper.vm.nameError).toBeTruthy()

    // Valid name
    wrapper.vm.keyName = 'Test API Key'
    await wrapper.vm.nextStep()
    expect(wrapper.vm.currentStep).toBe(2)
    expect(wrapper.vm.nameError).toBeFalsy()
  })

  it('handles tool selection in step 2', async () => {
    // Navigate to step 2
    wrapper.vm.keyName = 'Test Key'
    wrapper.vm.currentStep = 2
    await nextTick()

    // Use selectTool method directly
    wrapper.vm.selectTool('claude-code')
    expect(wrapper.vm.selectedTool).toBe('claude-code')

    wrapper.vm.selectTool('other')  // codex is disabled, use 'other' instead
    expect(wrapper.vm.selectedTool).toBe('other')
  })

  it('generates API key on step 3 with successful backend call', async () => {
    mockAxios.post.mockResolvedValue({
      data: {
        id: 1,
        name: 'Test Key',
        key: 'gk_test_key_123',
        created_at: '2025-10-09T10:00:00Z'
      }
    })

    wrapper.vm.keyName = 'Test Key'
    wrapper.vm.selectedTool = 'claude-code'
    wrapper.vm.currentStep = 3

    await wrapper.vm.generateApiKey()

    expect(mockAxios.post).toHaveBeenCalledWith('/api/auth/api-keys', {
      name: 'Test Key',
      tool: 'claude-code'
    })
    expect(wrapper.vm.generatedKey).toBe('gk_test_key_123')
  })

  it('handles backend errors during key generation', async () => {
    mockAxios.post.mockRejectedValue(new Error('Backend error'))

    wrapper.vm.keyName = 'Test Key'
    wrapper.vm.selectedTool = 'claude-code'
    wrapper.vm.currentStep = 3

    await wrapper.vm.generateApiKey()

    expect(wrapper.vm.errorMessage).toBeTruthy()
    expect(wrapper.vm.generatedKey).toBeNull()
  })

  it('validates key confirmation before finishing', async () => {
    wrapper.vm.currentStep = 3
    wrapper.vm.generatedKey = 'gk_test_key_123'
    await nextTick()

    // Without confirmation
    wrapper.vm.confirmSaved = false
    wrapper.vm.finish()
    expect(wrapper.vm.currentStep).toBe(3)  // Should stay on step 3

    // With confirmation
    wrapper.vm.confirmSaved = true
    wrapper.vm.finish()
    expect(wrapper.vm.currentStep).toBe(1) // Reset
    expect(wrapper.emitted('key-created')).toBeTruthy()
  })
})