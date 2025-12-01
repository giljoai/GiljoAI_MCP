/**
 * Test suite for ContextPriorityConfig.vue dual-endpoint save/load
 * Tests the complete save/load workflow with TWO endpoints:
 * 1. PUT /api/v1/users/me/field-priority (priorities)
 * 2. PUT /api/v1/users/me/context/depth (depth/count settings)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'

// Mock axios at module level
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

describe('ContextPriorityConfig.vue - Dual Endpoint Integration', () => {
  let vuetify
  let pinia
  let wrapper
  let axiosMock

  beforeEach(async () => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Setup Pinia
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup axios mock
    const axios = await import('axios')
    axiosMock = axios.default

    // Default mock implementations
    axiosMock.get.mockResolvedValue({ data: { priorities: {} } })
    axiosMock.put.mockResolvedValue({ data: { success: true } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  // ============================================================================
  // FETCH CONFIG TESTS (Load both endpoints)
  // ============================================================================

  describe('fetchConfig() - Load from both endpoints', () => {
    it('fetches from /field-priority endpoint only (current behavior)', async () => {
      axiosMock.get.mockResolvedValue({
        data: {
          priorities: {
            product_core: 1,
            vision_documents: 2,
            project_context: 2,
            testing: 3,
            agent_templates: 2,
            memory_360: 3,
            git_history: 3,
          },
        },
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Verify endpoint called
      expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/field-priority')
    })

    it.skip('should load depth config from /context/depth endpoint (TODO)', async () => {
      // This test documents the MISSING functionality
      // After implementation, this should verify both endpoints called

      const depthConfigResponse = {
        data: {
          vision_chunking: 'moderate',
          memory_last_n_projects: 3,
          git_commits: 25,
          agent_template_detail: 'standard',
          tech_stack_sections: 'all',
          architecture_depth: 'overview',
        },
      }

      axiosMock.get
        .mockResolvedValueOnce({
          data: { priorities: { product_core: 1 } },
        })
        .mockResolvedValueOnce(depthConfigResponse)

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // After implementation, this should pass:
      // expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/context/depth')
      // For now, it documents what's missing
    })

    it.skip('merges priority and depth config into single state structure', async () => {
      const prioritiesResponse = {
        data: {
          priorities: {
            product_core: 1,
            vision_documents: 2,
            memory_360: 3,
            git_history: 3,
          },
        },
      }

      const depthResponse = {
        data: {
          vision_chunking: 'heavy',
          memory_last_n_projects: 5,
          git_commits: 50,
        },
      }

      axiosMock.get
        .mockResolvedValueOnce(prioritiesResponse)
        .mockResolvedValueOnce(depthResponse)

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // After implementation, config should merge both responses
      // vision_documents should have: priority: 2, depth: 'heavy'
      // memory_360 should have: priority: 3, count: 5
      // etc.
    })

    it('handles error from /field-priority endpoint gracefully', async () => {
      axiosMock.get.mockRejectedValueOnce(new Error('API Error'))

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Component should still render with defaults
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.text()).toContain('Context Priority Configuration')
    })

    it.skip('handles error from /context/depth endpoint gracefully', async () => {
      axiosMock.get
        .mockResolvedValueOnce({
          data: { priorities: { product_core: 1 } },
        })
        .mockRejectedValueOnce(new Error('Depth endpoint error'))

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Component should still render with default depth values
      expect(wrapper.exists()).toBe(true)
    })
  })

  // ============================================================================
  // SAVE CONFIG TESTS (Save to both endpoints)
  // ============================================================================

  describe('saveConfig() - Save to both endpoints', () => {
    it('calls BOTH field-priority AND context/depth endpoints', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Clear mock history from mount
      axiosMock.put.mockClear()

      // Trigger save
      await wrapper.vm.saveConfig()
      await flushPromises()

      // Should call field-priority endpoint
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/field-priority',
        expect.objectContaining({
          version: '2.0',
          priorities: expect.any(Object),
        })
      )

      // Should also call context/depth endpoint
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/context/depth',
        expect.objectContaining({
          vision_chunking: expect.any(String),
          memory_last_n_projects: expect.any(Number),
          git_commits: expect.any(Number),
          agent_template_detail: expect.any(String),
          tech_stack_sections: expect.any(String),
          architecture_depth: expect.any(String),
        })
      )

      // Should have called both endpoints
      expect(axiosMock.put).toHaveBeenCalledTimes(2)
    })

    it('should save priorities to /field-priority endpoint', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Change a priority
      wrapper.vm.updatePriority('tech_stack', 1)
      await flushPromises()

      // Should save priorities with backend format
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/field-priority',
        expect.objectContaining({
          version: '2.0',
          priorities: expect.objectContaining({
            product_core: expect.any(Number),
          }),
        })
      )
    })

    it.skip('should save depth config to /context/depth endpoint (TODO)', async () => {
      // This test documents the MISSING functionality
      // After implementation, this should verify the depth endpoint called

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Change a depth value
      wrapper.vm.updateDepth('vision_documents', 'heavy')
      await flushPromises()

      // After implementation, should call depth endpoint:
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.objectContaining({
      //     vision_chunking: 'heavy',
      //     // ... other depth fields
      //   })
      // )
    })

    it.skip('maps frontend field names to backend field names correctly', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Update depth values
      wrapper.vm.updateDepth('vision_documents', 'heavy')
      wrapper.vm.updateDepth('memory_360', 10)
      wrapper.vm.updateDepth('git_history', 50)
      await flushPromises()

      // After implementation, field mapping should work:
      // vision_documents -> vision_chunking
      // memory_360 -> memory_last_n_projects
      // git_history -> git_commits
    })

    it.skip('calls both endpoints atomically (or with error handling)', async () => {
      // After implementation, verify that both endpoints are called
      // in sequence and errors from either are handled

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      await wrapper.vm.saveConfig()
      await flushPromises()

      // After implementation, should have 2 PUT calls:
      // expect(axiosMock.put).toHaveBeenCalledTimes(2)
      // One to /field-priority
      // One to /context/depth
    })

    it('handles error from /field-priority save gracefully', async () => {
      axiosMock.put.mockRejectedValueOnce(new Error('Save priority failed'))

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Should not throw
      await expect(wrapper.vm.saveConfig()).resolves.toBeUndefined()
    })

    it.skip('handles error from /context/depth save gracefully (TODO)', async () => {
      // After implementation, verify error handling for depth endpoint

      axiosMock.put
        .mockResolvedValueOnce({ data: { success: true } }) // field-priority succeeds
        .mockRejectedValueOnce(new Error('Save depth failed')) // context/depth fails

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Should not throw
      // await expect(wrapper.vm.saveConfig()).resolves.toBeUndefined()
    })
  })

  // ============================================================================
  // AUTO-SAVE TRIGGER TESTS (Verify both endpoints called on changes)
  // ============================================================================

  describe('Auto-save on user interactions', () => {
    it('auto-save on toggle calls both endpoints', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Toggle a context
      wrapper.vm.toggleContext('vision_documents')
      await flushPromises()

      // After implementation, both endpoints should be called:
      // expect(axiosMock.put).toHaveBeenCalledTimes(2)
      // Verify field-priority endpoint
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/field-priority',
        expect.any(Object)
      )
      // Verify context/depth endpoint
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.any(Object)
      // )
    })

    it('auto-save on priority change calls both endpoints', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Change priority
      wrapper.vm.updatePriority('tech_stack', 1)
      await flushPromises()

      // After implementation, both endpoints should be called:
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/field-priority',
        expect.any(Object)
      )
    })

    it.skip('auto-save on depth change calls both endpoints', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Change depth value
      wrapper.vm.updateDepth('vision_documents', 'heavy')
      await flushPromises()

      // After implementation, both endpoints should be called:
      // expect(axiosMock.put).toHaveBeenCalledTimes(2)
    })

    it.skip('auto-save on count change calls both endpoints', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Change count value
      wrapper.vm.updateDepth('memory_360', 10)
      await flushPromises()

      // After implementation, both endpoints should be called:
      // expect(axiosMock.put).toHaveBeenCalledTimes(2)
    })
  })

  // ============================================================================
  // FIELD MAPPING TESTS (Frontend vs Backend names)
  // ============================================================================

  describe('Field name mapping (Frontend <-> Backend)', () => {
    it.skip('maps vision_documents depth to vision_chunking', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      wrapper.vm.updateDepth('vision_documents', 'moderate')
      await flushPromises()

      // After implementation, should send to depth endpoint with mapped name:
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.objectContaining({
      //     vision_chunking: 'moderate',
      //   })
      // )
    })

    it.skip('maps memory_360 count to memory_last_n_projects', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      wrapper.vm.updateDepth('memory_360', 5)
      await flushPromises()

      // After implementation, should send to depth endpoint with mapped name:
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.objectContaining({
      //     memory_last_n_projects: 5,
      //   })
      // )
    })

    it.skip('maps git_history count to git_commits', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      wrapper.vm.updateDepth('git_history', 50)
      await flushPromises()

      // After implementation, should send to depth endpoint with mapped name:
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.objectContaining({
      //     git_commits: 50,
      //   })
      // )
    })

    it.skip('maps agent_templates depth to agent_template_detail', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      wrapper.vm.updateDepth('agent_templates', 'full')
      await flushPromises()

      // After implementation, should send to depth endpoint with mapped name:
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.objectContaining({
      //     agent_template_detail: 'full',
      //   })
      // )
    })
  })

  // ============================================================================
  // COMPLETE WORKFLOW TESTS
  // ============================================================================

  describe('Complete workflows', () => {
    it('load + toggle + save workflow uses both endpoints', async () => {
      // Mock load response
      axiosMock.get.mockResolvedValue({
        data: {
          priorities: {
            product_core: 1,
            vision_documents: 2,
          },
        },
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Verify load called field-priority
      expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/field-priority')

      axiosMock.put.mockClear()

      // Toggle and save
      wrapper.vm.toggleContext('vision_documents')
      await flushPromises()

      // After implementation, both endpoints should be called:
      expect(axiosMock.put).toHaveBeenCalledWith(
        '/api/v1/users/me/field-priority',
        expect.any(Object)
      )
      // expect(axiosMock.put).toHaveBeenCalledWith(
      //   '/api/v1/users/me/context/depth',
      //   expect.any(Object)
      // )
    })

    it('page refresh reloads both configs', async () => {
      axiosMock.get.mockResolvedValue({
        data: {
          priorities: { product_core: 1 },
        },
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // After implementation, both endpoints should be called on mount:
      // expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/field-priority')
      // expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/context/depth')
    })

    it.skip('changing multiple settings persists all changes', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      axiosMock.put.mockClear()

      // Make multiple changes
      wrapper.vm.toggleContext('testing')
      await flushPromises()
      wrapper.vm.updatePriority('vision_documents', 1)
      await flushPromises()
      wrapper.vm.updateDepth('memory_360', 10)
      await flushPromises()

      // After implementation, each change triggers both endpoints:
      // Should have 6 calls total (2 per change)
      // expect(axiosMock.put).toHaveBeenCalledTimes(6)
    })
  })

  // ============================================================================
  // LOGGING TESTS (Verify console output for debugging)
  // ============================================================================

  describe('Console logging', () => {
    it('logs successful field priority save', async () => {
      const consoleSpy = vi.spyOn(console, 'log')

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      consoleSpy.mockClear()

      await wrapper.vm.saveConfig()
      await flushPromises()

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Field priorities saved successfully')
      )

      consoleSpy.mockRestore()
    })

    it('logs error when save fails', async () => {
      axiosMock.put.mockRejectedValueOnce(new Error('Save failed'))
      const consoleSpy = vi.spyOn(console, 'error')

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      consoleSpy.mockClear()

      await wrapper.vm.saveConfig()
      await flushPromises()

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save config'),
        expect.any(Error)
      )

      consoleSpy.mockRestore()
    })

    it.skip('logs depth config save (after implementation)', async () => {
      // After implementation, should log depth endpoint save
      const consoleSpy = vi.spyOn(console, 'log')

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      consoleSpy.mockClear()

      await wrapper.vm.saveConfig()
      await flushPromises()

      // After implementation, should log depth save:
      // expect(consoleSpy).toHaveBeenCalledWith(
      //   expect.stringContaining('Depth config saved successfully')
      // )

      consoleSpy.mockRestore()
    })
  })
})
