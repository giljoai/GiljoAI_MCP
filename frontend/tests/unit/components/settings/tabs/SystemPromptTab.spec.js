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

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.exists()).toBe(true)
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

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.props('modelValue')).toBe('You are the Giljo Orchestrator...')
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

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      expect(saveBtn.exists()).toBe(true)
      expect(saveBtn.text()).toContain('Save Override')
    })

    it('renders Restore Default button', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      expect(restoreBtn.exists()).toBe(true)
      expect(restoreBtn.text()).toContain('Restore Default')
    })

    it('Save button is disabled when prompt is not dirty', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      expect(saveBtn.attributes('disabled')).toBeDefined()
    })

    it('Save button is enabled when prompt is modified', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify the prompt
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Modified prompt content')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      expect(saveBtn.attributes('disabled')).toBeUndefined()
    })
  })

  describe('API Integration', () => {
    it('fetches prompt on mount', async () => {
      wrapper = mountComponent()
      await flushPromises()

      expect(apiMock.getOrchestratorPrompt).toHaveBeenCalledTimes(1)
    })

    it('saves prompt when save button clicked', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('New custom prompt')
      await nextTick()

      // Click save
      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
      await flushPromises()

      expect(apiMock.updateOrchestratorPrompt).toHaveBeenCalledWith('New custom prompt')
    })

    it('resets prompt when restore button clicked', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Click restore
      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      await restoreBtn.trigger('click')
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
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Test content')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
      await flushPromises()

      // Should display error
      expect(wrapper.text()).toContain('Save failed')
    })

    it('handles API error on reset gracefully', async () => {
      wrapper = mountComponent()
      await flushPromises()

      apiMock.resetOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Reset failed' } },
      })

      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      await restoreBtn.trigger('click')
      await flushPromises()

      // Should display error
      expect(wrapper.text()).toContain('Reset failed')
    })
  })

  describe('State Management', () => {
    it('tracks dirty state when prompt is modified', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Initially not dirty
      expect(wrapper.vm.promptDirty).toBe(false)

      // Modify prompt
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Modified content')
      await nextTick()

      expect(wrapper.vm.promptDirty).toBe(true)
    })

    it('clears dirty state after successful save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Modified content')
      await nextTick()

      expect(wrapper.vm.promptDirty).toBe(true)

      // Save
      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.promptDirty).toBe(false)
    })

    it('clears dirty state after successful reset', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify prompt
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Modified content')
      await nextTick()

      // Reset
      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      await restoreBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.promptDirty).toBe(false)
    })

    it('updates metadata after successful save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify and save
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('New prompt')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
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
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Test')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      saveBtn.trigger('click')
      await nextTick()

      expect(wrapper.vm.saving).toBe(true)
    })

    it('disables buttons during loading', async () => {
      apiMock.getOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(defaultPromptResponse), 100)
          )
      )

      wrapper = mountComponent()
      await nextTick()

      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      expect(restoreBtn.attributes('disabled')).toBeDefined()
    })

    it('disables buttons during saving', async () => {
      wrapper = mountComponent()
      await flushPromises()

      apiMock.updateOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(overridePromptResponse), 100)
          )
      )

      // Modify and start save
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('Test')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      saveBtn.trigger('click')
      await nextTick()

      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      expect(restoreBtn.attributes('disabled')).toBeDefined()
    })
  })

  describe('Feedback Messages', () => {
    it('displays success message after save', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Modify and save
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('New content')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Override saved successfully')
    })

    it('displays success message after reset', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')
      await restoreBtn.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Reverted to default')
    })

    it('can close error alert', async () => {
      apiMock.getOrchestratorPrompt.mockRejectedValueOnce({
        response: { data: { detail: 'Test error' } },
      })

      wrapper = mountComponent()
      await flushPromises()

      // Error should be displayed
      expect(wrapper.text()).toContain('Test error')

      // Close the alert
      const errorAlert = wrapper.find('[data-test="error-alert"]')
      if (errorAlert.exists()) {
        await errorAlert.trigger('click:close')
        await nextTick()

        expect(wrapper.vm.promptError).toBeNull()
      }
    })

    it('can close success alert', async () => {
      wrapper = mountComponent()
      await flushPromises()

      // Trigger save to show success message
      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      await textarea.setValue('New content')
      await nextTick()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      await saveBtn.trigger('click')
      await flushPromises()

      // Close the success alert
      const successAlert = wrapper.find('[data-test="success-alert"]')
      if (successAlert.exists()) {
        await successAlert.trigger('click:close')
        await nextTick()

        expect(wrapper.vm.promptFeedback).toBeNull()
      }
    })
  })

  describe('Textarea Properties', () => {
    it('textarea is readonly during loading', async () => {
      apiMock.getOrchestratorPrompt.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(defaultPromptResponse), 100)
          )
      )

      wrapper = mountComponent()
      await nextTick()

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.props('readonly')).toBe(true)
    })

    it('textarea has monospace font class', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.classes()).toContain('mono-textarea')
    })

    it('textarea has correct label', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.props('label')).toBe('Orchestrator Prompt')
    })

    it('textarea has spellcheck disabled', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.attributes('spellcheck')).toBe('false')
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
    it('textarea has proper variant', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const textarea = wrapper.findComponent({ name: 'VTextarea' })
      expect(textarea.props('variant')).toBe('outlined')
    })

    it('buttons have icons', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const saveBtn = wrapper.find('[data-test="save-prompt-btn"]')
      const restoreBtn = wrapper.find('[data-test="restore-prompt-btn"]')

      expect(saveBtn.find('.v-icon').exists()).toBe(true)
      expect(restoreBtn.find('.v-icon').exists()).toBe(true)
    })
  })

  describe('Card Structure', () => {
    it('renders within a v-card', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const card = wrapper.findComponent({ name: 'VCard' })
      expect(card.exists()).toBe(true)
    })

    it('has card-title', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const cardTitle = wrapper.findComponent({ name: 'VCardTitle' })
      expect(cardTitle.exists()).toBe(true)
    })

    it('has card-subtitle', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const cardSubtitle = wrapper.findComponent({ name: 'VCardSubtitle' })
      expect(cardSubtitle.exists()).toBe(true)
    })

    it('has card-text', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const cardText = wrapper.findComponent({ name: 'VCardText' })
      expect(cardText.exists()).toBe(true)
    })

    it('has card-actions', async () => {
      wrapper = mountComponent()
      await flushPromises()

      const cardActions = wrapper.findComponent({ name: 'VCardActions' })
      expect(cardActions.exists()).toBe(true)
    })
  })
})
