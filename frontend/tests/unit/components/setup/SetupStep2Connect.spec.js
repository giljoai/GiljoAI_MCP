/**
 * Unit tests for SetupStep2Connect component (Handover 0855d)
 * Covers: rendering, tabs, API key flow, config generation, WS connection status, can-proceed logic.
 *
 * Updated for FE-6159: OAuth is now the default/primary path for OAuth-capable tools
 * (claude_code, codex_cli, gemini_cli). The API-key/bearer flow is hidden behind a
 * "Use an API key instead" reveal toggle. Tests that assert key-flow UI must first
 * trigger that reveal for OAuth-capable tools. Connection status dots for OAuth tools
 * live in the OAuth section (.conn-dot--*), not the key-flow child (.status-dot--*).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import SetupStep2Connect from '@/components/setup/SetupStep2Connect.vue'
import api from '@/services/api'
import configService from '@/services/configService'

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

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(),
  },
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

/**
 * Reveal the bearer/API-key flow for an OAuth-capable tool by clicking the
 * "Use an API key instead" toggle. No-op for key-only tools (Antigravity)
 * which show the key flow immediately.
 */
async function revealBearer(wrapper) {
  const toggle = wrapper.find('.bearer-toggle-link')
  if (toggle.exists()) {
    await toggle.trigger('click')
    await flushPromises()
  }
}

// ─── Tests ────────────────────────────────────────────────────────

describe('SetupStep2Connect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: return an active API key
    api.apiKeys.getActive = vi.fn().mockResolvedValue({ data: [{ key_prefix: 'giljo_abc' }] })
    api.apiKeys.create = vi.fn().mockResolvedValue({ data: { api_key: 'giljo_full_key_123' } })
    // Default: no backend config override (keep window.location.* fallback)
    configService.fetchConfig.mockResolvedValue(null)
  })

  // 1. Renders heading text
  it('renders heading text', async () => {
    const wrapper = mountStep2()
    await flushPromises()
    // Gradient Rail redesign (FE-6259b) shortened the heading; the wizard rail
    // title now carries the "GiljoAI MCP" branding instead.
    expect(wrapper.text()).toContain('Connect your tools')
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
  // Bearer flow must be revealed first for OAuth-capable tools (FE-6159).
  it('displays existing key prefix after loading', async () => {
    api.apiKeys.getActive.mockResolvedValue({
      data: [{ key_prefix: 'giljo_abc' }],
    })

    const wrapper = mountStep2()
    await flushPromises()

    // OAuth is the primary path — reveal the bearer/API-key fallback first.
    await revealBearer(wrapper)

    expect(wrapper.text()).toContain('giljo_abc')
    expect(wrapper.text()).toContain('Key exists')
  })

  // 6. API key check: shows generate button when no active keys
  // Bearer flow must be revealed first for OAuth-capable tools (FE-6159).
  it('shows generate button when no active keys exist', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })

    const wrapper = mountStep2()
    await flushPromises()

    // Reveal the API-key fallback — for OAuth tools it is hidden by default.
    await revealBearer(wrapper)

    expect(wrapper.text()).toContain('Generate API Key')
  })

  // 7. Generate key button calls API
  // Bearer flow must be revealed first for OAuth-capable tools (FE-6159).
  it('calls api.apiKeys.create when generate key button is clicked', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })

    const wrapper = mountStep2()
    await flushPromises()

    // Reveal the API-key fallback section.
    await revealBearer(wrapper)

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
  // Bearer flow must be revealed first for OAuth-capable tools (FE-6159).
  it('renders config command for claude_code when key is generated', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    // Reveal the bearer/API-key fallback section.
    await revealBearer(wrapper)

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

    // codex_cli supports OAuth — reveal the bearer fallback first.
    await revealBearer(wrapper)

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

    // gemini_cli supports OAuth — reveal the bearer fallback first.
    await revealBearer(wrapper)

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('gemini mcp add')
  })

  // 9. Connection status: waiting dot visible before connection
  // For OAuth-capable tools the connection dot lives in the OAuth section
  // (.conn-dot--waiting), not in the key-flow child (.status-dot--waiting).
  it('shows waiting status dot after key is generated', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2()
    await flushPromises()

    // The OAuth section's connection dot is always rendered for OAuth tools,
    // even before a key is generated — it starts in the waiting state.
    expect(wrapper.find('.conn-dot--waiting').exists()).toBe(true)
  })

  // 10. Connection status updates on WebSocket event after key is generated
  // The OAuth section's .conn-dot--connected is the visible indicator for OAuth tools.
  it('updates connection status dot to connected when WebSocket event fires', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    // Find the handler registered for setup:tool_connected
    const onCall = mockWsOn.mock.calls.find(
      (call) => call[0] === 'setup:tool_connected',
    )
    expect(onCall).toBeTruthy()

    const handler = onCall[1]
    handler({ tool_name: 'claude_code' })
    await flushPromises()

    // OAuth section switches from .conn-dot--waiting to .conn-dot--connected.
    expect(wrapper.find('.conn-dot--connected').exists()).toBe(true)
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

  // 14. INF-5012b: component mirrors null backend port as empty string
  // (reverse-proxy case where std 443/80 is implicit). Regression guard
  // against showing a stale 7272 on Cloudflare/nginx deployments.
  // Bearer flow must be revealed first so the bearer config command renders.
  it('mirrors null backend port from configService as empty string (INF-5012b)', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    configService.fetchConfig.mockResolvedValue({
      api: { host: 'mcp.example.com', port: null, protocol: 'https' },
    })

    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    // Reveal the bearer/API-key fallback section so the config command renders.
    await revealBearer(wrapper)

    // Click generate so the bearer config panel (with server URL) is rendered.
    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    // The generated bearer command must reflect the public host with no :7272 port.
    const text = wrapper.text()
    expect(text).toContain('mcp.example.com')
    expect(text).not.toContain('mcp.example.com:7272')
  })

  // 15. INF-5012b: component mirrors numeric backend port when host differs
  // from browser host (proxy-fronted LAN case where backend identity is
  // reported by configService and composed out-of-band).
  // Bearer flow must be revealed first so the bearer config command renders.
  it('mirrors numeric backend port from configService when host differs (INF-5012b)', async () => {
    api.apiKeys.getActive.mockResolvedValue({ data: [] })
    configService.fetchConfig.mockResolvedValue({
      api: { host: '192.0.2.50', port: 7272, protocol: 'http' },
    })

    const wrapper = mountStep2({ selectedTools: ['claude_code'] })
    await flushPromises()

    // Reveal the bearer/API-key fallback section so the config command renders.
    await revealBearer(wrapper)

    const buttons = wrapper.findAll('button')
    const generateBtn = buttons.find((b) => b.text().includes('Generate API Key'))
    await generateBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('192.0.2.50:7272')
  })
})
