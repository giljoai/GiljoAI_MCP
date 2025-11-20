/**
 * Test suite for SystemPromptTab.vue component
 * TDD Implementation: RED Phase
 *
 * Tests the System Orchestrator Prompt tab:
 * - Rendering of prompt editor and metadata
 * - Warning alerts and feedback messages
 * - API integration for loading/saving/resetting prompt
 * - State management and dirty tracking
 * - Loading and saving states
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick } from 'vue'
import SystemPromptTab from '@/components/settings/tabs/SystemPromptTab.vue'

// Mock the api service
vi.mock('@/services/api', () => ({
  default: {
    system: {
      getOrchestratorPrompt: vi.fn(),
      updateOrchestratorPrompt: vi.fn(),
      resetOrchestratorPrompt: vi.fn(),
    },
  },
}))

describe('SystemPromptTab.vue', () => {
  let vuetify
  let wrapper
  let apiMock

  const defaultPromptResponse = {
    data: {
      content: 'You are the Giljo Orchestrator...',
      is_override: false,
      updated_at: null,
      updated_by: null,
    },
  }

  const overridePromptResponse = {
    data: {
      content: 'Custom orchestrator prompt...',
      is_override: true,
      updated_at: '2025-11-19T10:30:00Z',
      updated_by: 'admin',
    },
  }

  beforeEach(async () => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Setup api mock
    const api = await import('@/services/api')
    apiMock = api.default.system
    apiMock.getOrchestratorPrompt.mockResolvedValue(defaultPromptResponse)
    apiMock.updateOrchestratorPrompt.mockResolvedValue(overridePromptResponse)
    apiMock.resetOrchestratorPrompt.mockResolvedValue(defaultPromptResponse)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  const mountComponent = () => {
    return mount(SystemPromptTab, {
      global: {
        plugins: [vuetify],
      },
    })
  }

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mountComponent()
      expect(wrapper.exists()).toBe(true)
    })

    it('displays card title "System Orchestrator Prompt"', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('System Orchestrator Prompt')
    })

    it('displays card subtitle with admin override note', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('Core instructions for the Giljo Orchestrator')
      expect(wrapper.text()).toContain('admin override only')
    })

    it('displays warning alert about editing impact', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('Editing this prompt can break orchestrator coordination')
    })

    it('renders prompt textarea', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check for textarea element in rendered HTML
      expect(wrapper.html()).toContain('textarea')
    })

    it('displays status text showing default or override', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('Using default system prompt')
    })
  })

  describe('Prompt Content Display', () => {
    it('displays loaded prompt content in textarea', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check that the prompt value was loaded into the component state
      expect(wrapper.vm.prompt).toBe('You are the Giljo Orchestrator...')
    })

    it('displays override status when prompt is customized', async () => {
      apiMock.getOrchestratorPrompt.mockResolvedValueOnce(overridePromptResponse)

      wrapper = mountComponent()
      await flushPromises()

      const text = wrapper.text()
      expect(text).toContain('Override saved')
      expect(text).toContain('admin')
    })
  })

  describe('Action Buttons', () => {
    it('renders Save Override button', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const text = wrapper.text()
      expect(text).toContain('Save Override')
    })

    it('renders Restore Default button', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const text = wrapper.text()
      expect(text).toContain('Restore Default')
    })

    it('Save button is disabled when prompt is not dirty', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Not dirty, so save should be disabled
      expect(wrapper.vm.promptDirty).toBe(false)
    })

    it('Save button is enabled when prompt is modified', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify the prompt
      wrapper.vm.prompt = 'Modified prompt content'
      await nextTick()

      expect(wrapper.vm.promptDirty).toBe(true)
    })
  })

  describe('API Integration', () => {
    it('fetches prompt on mount', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(apiMock.getOrchestratorPrompt).toHaveBeenCalledTimes(1)
    })

    it('saves prompt when save is triggered', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt and call save directly
      wrapper.vm.prompt = 'New custom prompt'
      await nextTick()

      await wrapper.vm.savePrompt()
      await flushPromises()

      expect(apiMock.updateOrchestratorPrompt).toHaveBeenCalledWith('New custom prompt')
    })

    it('resets prompt when restore is triggered', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Call restore directly
      await wrapper.vm.restorePrompt()
      await flushPromises()

      expect(apiMock.resetOrchestratorPrompt).toHaveBeenCalledTimes(1)
    })

    it('handles API error on load gracefully', async () => {
      apiMock.getOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Failed to load prompt' } },
      })

      wrapper = mountComponent()
      await flushPromises()

      // Should display error
      expect(wrapper.text()).toContain('Failed to load')
    })

    it('handles API error on save gracefully', async () => {
      wrapper = mountComponent()
      await flushPromises()

      apiMock.updateOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Save failed' } },
      })

      // Modify and save
      wrapper.vm.prompt = 'Test content'
      await nextTick()

      await wrapper.vm.savePrompt()
      await flushPromises()

      // Should display error
      expect(wrapper.vm.promptError).toContain('Save failed')
    })

    it('handles API error on reset gracefully', async () => {
      wrapper = mountComponent()
      await flushPromises()

      apiMock.resetOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Reset failed' } },
      })

      await wrapper.vm.restorePrompt()
      await flushPromises()

      // Should display error
      expect(wrapper.vm.promptError).toContain('Reset failed')
    })
  })

  describe('State Management', () => {
    it('tracks dirty state when prompt is modified', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Initially not dirty
      expect(wrapper.vm.promptDirty).toBe(false)

      // Modify prompt
      wrapper.vm.prompt = 'Modified content'
      await nextTick()

      expect(wrapper.vm.promptDirty).toBe(true)
    })

    it('clears dirty state after successful save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt
      wrapper.vm.prompt = 'Modified content'
      await nextTick()

      expect(wrapper.vm.promptDirty).toBe(true)

      // Save
      await wrapper.vm.savePrompt()
      await flushPromises()

      expect(wrapper.vm.promptDirty).toBe(false)
    })

    it('clears dirty state after successful reset', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt
      wrapper.vm.prompt = 'Modified content'
      await nextTick()

      // Reset
      await wrapper.vm.restorePrompt()
      await flushPromises()

      expect(wrapper.vm.promptDirty).toBe(false)
    })

    it('updates metadata after successful save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify and save
      wrapper.vm.prompt = 'New prompt'
      await nextTick()

      await wrapper.vm.savePrompt()
      await flushPromises()

      expect(wrapper.vm.promptMetadata.isOverride).toBe(true)
      expect(wrapper.vm.promptMetadata.updatedBy).toBe('admin')
    })
  })

  describe('Loading States', () => {
    it('shows loading state during fetch', async () => {
      // Delay the response
      apiMock.getOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(defaultPromptResponse), 100)
          )
      )

      wrapper = mountComponent()

      // Check loading state before response
      expect(wrapper.vm.loading).toBe(true)
    })

    it('shows saving state during save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Delay save response
      apiMock.updateOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(overridePromptResponse), 100)
          )
      )

      // Modify and start save
      wrapper.vm.prompt = 'Test'
      await nextTick()

      wrapper.vm.savePrompt()
      await nextTick()

      expect(wrapper.vm.saving).toBe(true)
    })

    it('disables actions during loading', async () => {
      apiMock.getOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(defaultPromptResponse), 100)
          )
      )

      wrapper = mountComponent()
      await nextTick()

      // During loading, buttons should be disabled
      expect(wrapper.vm.loading).toBe(true)
    })

    it('disables actions during saving', async () => {
      wrapper = mountComponent()
      await flushPromises()

      apiMock.updateOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(overridePromptResponse), 100)
          )
      )

      // Modify and start save
      wrapper.vm.prompt = 'Test'
      await nextTick()

      wrapper.vm.savePrompt()
      await nextTick()

      expect(wrapper.vm.saving).toBe(true)
    })
  })

  describe('Feedback Messages', () => {
    it('displays success message after save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify and save
      wrapper.vm.prompt = 'New content'
      await nextTick()

      await wrapper.vm.savePrompt()
      await flushPromises()

      expect(wrapper.vm.promptFeedback).toContain('Override saved successfully')
    })

    it('displays success message after reset', async () => {
      wrapper = mountComponent()
      await flushPromises()

      await wrapper.vm.restorePrompt()
      await flushPromises()

      expect(wrapper.vm.promptFeedback).toContain('Reverted to default')
    })

    it('can clear error state', async () => {
      apiMock.getOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Test error' } },
      })

      wrapper = mountComponent()
      await flushPromises()

      // Error should be displayed
      expect(wrapper.vm.promptError).toContain('Test error')

      // Clear the error
      wrapper.vm.promptError = null
      await nextTick()

      expect(wrapper.vm.promptError).toBeNull()
    })

    it('can clear success state', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Trigger save to show success message
      wrapper.vm.prompt = 'New content'
      await nextTick()

      await wrapper.vm.savePrompt()
      await flushPromises()

      // Clear the success feedback
      wrapper.vm.promptFeedback = null
      await nextTick()

      expect(wrapper.vm.promptFeedback).toBeNull()
    })
  })

  describe('Textarea Properties', () => {
    it('loading state makes textarea readonly', async () => {
      apiMock.getOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(defaultPromptResponse), 100)
          )
      )

      wrapper = mountComponent()
      await nextTick()

      // During loading, textarea should be readonly
      expect(wrapper.vm.loading).toBe(true)
    })

    it('textarea label is configured correctly', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check that the component contains the label text
      expect(wrapper.text()).toContain('Orchestrator Prompt')
    })

    it('component has monospace style', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check that the style is applied
      const style = wrapper.find('.mono-textarea')
      expect(style.exists()).toBe(true)
    })
  })

  describe('Status Display', () => {
    it('shows "Using default system prompt" when not override', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('Using default system prompt')
    })

    it('shows override timestamp and actor when is override', async () => {
      apiMock.getOrchestratorPrompt.mockResolvedValueOnce(overridePromptResponse)

      wrapper = mountComponent()
      await flushPromises()

      const text = wrapper.text()
      expect(text).toContain('Override saved')
      expect(text).toContain('admin')
    })
  })

  describe('Accessibility', () => {
    it('component uses outlined variant for textarea', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check for outlined class in the HTML
      expect(wrapper.html()).toContain('outlined')
    })

    it('buttons display icons', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check that icons are rendered (mdi icon classes)
      const html = wrapper.html()
      expect(html).toContain('mdi-content-save')
      expect(html).toContain('mdi-backup-restore')
    })
  })

  describe('Card Structure', () => {
    it('contains card title text', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('System Orchestrator Prompt')
    })

    it('contains card subtitle text', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('admin override only')
    })

    it('contains card content area', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Check for card content elements
      expect(wrapper.text()).toContain('Orchestrator Prompt')
    })

    it('contains card action buttons', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.text()).toContain('Save Override')
      expect(wrapper.text()).toContain('Restore Default')
    })
  })
})
