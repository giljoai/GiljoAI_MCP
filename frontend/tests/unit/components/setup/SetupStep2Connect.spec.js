/**
 * Unit tests for SetupStep2Connect component (Handover 0855d)
 * Covers: rendering, tabs, API key flow, config generation, WS connection status, can-proceed logic.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import SetupStep2Connect from '@/components/setup/SetupStep2Connect.vue'
import api from '@/services/api'

// ─── Mock stores ──────────────────────────────────────────────────

const mockUnsub = vi.fn()
const mockWsOn = vi.fn(() => mockUnsub)

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: mockWsOn,
    off: vi.fn(),
    isConnected: true,
  }),
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn(() => Promise.resolve(true)),
  }),
}))

// ─── Mount helper (uses global stubs from setup.js) ──────────────

function mountStep2(props = {}) {
  return mount(SetupStep2Connect, {
    props: {
      selectedTools: ['claude_code'],
      ...props,
    },
    global: {
      plugins: [createPinia()],
      stubs: {
        'v-btn-toggle': { template: '<div class="v-btn-toggle"><slot /></div>' },
        'v-expand-transition': { template: '<div><slot /></div>' },
      },
    },
  })
}

// ─── Tests ────────────────────────────────────────────────────────

describe('SetupStep2Connect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: return an active API key
    api.apiKeys.getActive = vi.fn().mockResolvedValue({ data: [{ key_prefix: 'giljo_abc' }] })
    api.apiKeys.create = vi.fn().mockResolvedValue({ data: { api_key: 'giljo_full_key_123' } })
  })

  // 1. Renders heading text
  it('renders heading text', async () => {
    const wrapper = mountStep2()
    await flushPromises()
    expect(wrapper.text()).toContain('Connect your tools to GiljoAI MCP')
  })

  // 2. Single tool: no tab bar
  it('does not render tab bar when only one tool is selected', async () => {
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()
    expect(wrapper.find('.tool-tabs').exists()).toBe(false)
  })

  // 3. Multiple tools: renders tab bar
  it('renders tab bar with correct count when multiple tools selected', async () => {
    const wrapper = mountStep2({ selectedTools: ['claude_code', 'codex_cli'] })
    await flushPromises()
    expect(wrapper.find('.tool-tabs').exists()).toBe(true)
    const tabs = wrapper.findAll('.tool-tab')
    expect(tabs).toHaveLength(2)
  })

  // 4. Tab click switches active tool
  it('switches active tool when tab is clicked', async () => {
    const wrapper = mountStep2({
      selectedTools: ['claude_code', 'gemini_cli'],
    })
    await flushPromises()

    const tabs = wrapper.findAll('.tool-tab')
    expect(tabs.length).toBe(2)

    // Click the second tab (gemini)
    await tabs[1].trigger('click')
    await flushPromises()

    // The second tab should now be active
    expect(tabs[1].classes()).toContain('tool-tab--active')
  })

  // 5. API key check: shows key prefix when active key exists
  it('displays existing key prefix after loading', async () => {
    api.apiKeys.getActive.mockResolvedValue({
      data: [{ key_prefix: 'giljo_abc' }],
    })

    const wrapper = mountStep2()
    await flushPromises()
    expect(wrapper.text()).toContain('giljo_abc')
    expect(wrapper.text()).toContain('Key exists')
  })

  // 6. API key check: shows generate button when no active keys
  it('shows generate button when no active keys exist', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })

    const wrapper = mountStep2()
    await flushPromises()

    expect(wrapper.text()).toContain('Generate API Key')
  })

  // 7. Generate key button calls API
  it('calls api.apiKeys.create when generate key button is clicked', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })

    const wrapper = mountStep2()
    await flushPromises()

    // Find and click the generate key button
    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find(
      (b) => b.text().includes('Generate API Key'),
    )
    expect(generateBtn).toBeTruthy()

    await generateBtn.trigger('click')
    await flushPromises()

    expect(api.apiKeys.create).toHaveBeenCalled()
  })

  // 8. Config renders after key is generated (config section only shows when generatedKey is set)
  it('renders config command for claude_code when key is generated', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    // Click generate key button
    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('claude mcp add')
  })

  it('renders config command for codex_cli', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['codex_cli'] })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('codex mcp add')
  })

  it('renders config command for gemini_cli', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['gemini_cli'] })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('gemini mcp add')
  })

  // 9. Connection status: waiting dot visible after key is generated
  it('shows waiting status dot after key is generated', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.status-dot--waiting').exists()).toBe(true)
  })

  // 10. Connection status updates on WebSocket event after key is generated
  it('updates connection status dot to connected when WebSocket event fires', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    // Find the handler registered for setup:tool_connected
    const onCall = mockWsOn.mock.calls.find(
      (call) => call[0] === 'setup:tool_connected',
    )
    expect(onCall).toBeTruthy()

    const handler = onCall[1]
    handler({ tool_name: 'claude_code' })
    await flushPromises()

    expect(wrapper.find('.status-dot--connected').exists()).toBe(true)
  })

  // 11. "Next" disabled until >= 1 tool connected
  it('emits can-proceed false initially and true after connection', async () => {
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    const canProceedEvents = wrapper.emitted('can-proceed')
    expect(canProceedEvents).toBeTruthy()
    expect(canProceedEvents[0]).toEqual([false])

    // Simulate connection
    const onCall = mockWsOn.mock.calls.find(
      (call) => call[0] === 'setup:tool_connected',
    )
    const handler = onCall[1]
    handler({ tool_name: 'claude_code' })
    await flushPromises()

    const allCanProceed = wrapper.emitted('can-proceed')
    const lastEmit = allCanProceed[allCanProceed.length - 1]
    expect(lastEmit).toEqual([true])
  })

  // 12. Emits step-data with connected tools
  it('emits step-data with connected tools after connection event', async () => {
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    const onCall = mockWsOn.mock.calls.find(
      (call) => call[0] === 'setup:tool_connected',
    )
    const handler = onCall[1]
    handler({ tool_name: 'claude_code' })
    await flushPromises()

    const stepDataEvents = wrapper.emitted('step-data')
    expect(stepDataEvents).toBeTruthy()
    const lastEmit = stepDataEvents[stepDataEvents.length - 1][0]
    expect(lastEmit).toHaveProperty('connectedTools')
    expect(lastEmit.connectedTools).toContain('claude_code')
  })

  // 13. Cleanup: WebSocket unsubscribe on unmount
  it('calls WebSocket unsubscribe function on unmount', async () => {
    const wrapper = mountStep2()
    await flushPromises()

    expect(mockWsOn).toHaveBeenCalled()
    wrapper.unmount()
    expect(mockUnsub).toHaveBeenCalled()
  })
})
