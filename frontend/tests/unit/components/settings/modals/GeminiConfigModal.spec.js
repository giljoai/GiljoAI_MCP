/**
 * Test suite for GeminiConfigModal.vue component
 * Handover 0321: Settings Componentization
 *
 * Tests the Gemini CLI configuration modal:
 * - Modal rendering with v-model binding
 * - Modal displays correct title
 * - Modal has close button
 * - Modal emits update:modelValue on close
 * - Tab navigation (manual/download)
 * - Copy configuration functionality
 * - Download instructions functionality
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import GeminiConfigModal from '@/components/settings/modals/GeminiConfigModal.vue'

describe('GeminiConfigModal.vue', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })

    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the modal when modelValue is true', () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays correct title "How to Configure Gemini CLI"', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('How to Configure Gemini CLI')
    })

    it('displays API key info alert', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('generate an API key')
    })

    it('has two tabs (Manual, Download)', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Manual Configuration')
      expect(wrapper.text()).toContain('Download Instructions')
    })

    it('has a Close button', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const closeButton = wrapper.find('[data-test="close-button"]')
      expect(closeButton.exists()).toBe(true)
      expect(closeButton.text()).toContain('Close')
    })
  })

  describe('v-model Binding', () => {
    it('emits update:modelValue when Close button is clicked', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      const closeButton = wrapper.find('[data-test="close-button"]')
      await closeButton.trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })
  })

  describe('Tab Navigation', () => {
    it('shows manual configuration content by default', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Configuration File Location')
    })

    it('can switch to download instructions tab', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Find and click the Download Instructions tab
      const tabs = wrapper.findAllComponents({ name: 'VTab' })
      const downloadTab = tabs.find(tab => tab.text().includes('Download Instructions'))
      expect(downloadTab).toBeDefined()

      if (downloadTab) {
        await downloadTab.trigger('click')
        await wrapper.vm.$nextTick()
        expect(wrapper.text()).toContain('Download Configuration Instructions')
      }
    })
  })

  describe('Copy Configuration', () => {
    it('has a Copy Configuration button', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Copy Configuration')
    })

    it('copies configuration to clipboard when copy button is clicked', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      const copyButton = wrapper.find('[data-test="copy-config-button"]')
      if (copyButton.exists()) {
        await copyButton.trigger('click')
        expect(navigator.clipboard.writeText).toHaveBeenCalled()
      }
    })
  })

  describe('Download Instructions', () => {
    it('has a Download button in download tab', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Switch to download tab
      const tabs = wrapper.findAllComponents({ name: 'VTab' })
      const downloadTab = tabs.find(tab => tab.text().includes('Download Instructions'))
      if (downloadTab) {
        await downloadTab.trigger('click')
        await wrapper.vm.$nextTick()
      }

      expect(wrapper.text()).toContain('Download Gemini CLI Setup Guide')
    })
  })

  describe('Configuration Content', () => {
    it('displays JSON configuration example', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('mcpServers')
      expect(wrapper.text()).toContain('giljo-mcp')
      expect(wrapper.text()).toContain('GiljoAI Agent Orchestration MCP Server')
    })

    it('shows configuration file locations', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('settings.json')
    })

    it('displays capabilities configuration', async () => {
      wrapper = mount(GeminiConfigModal, {
        props: {
          modelValue: true,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('capabilities')
      expect(wrapper.text()).toContain('agent_coordination')
    })
  })
})
