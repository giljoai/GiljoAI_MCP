/**
 * Unit tests for SetupStep3Commands component (Handover 0855e)
 * Covers: rendering, bootstrap prompt fetch, copy, mini-checklist, WebSocket events,
 * post-install command display, Next/Skip behavior, Codex two-step flow.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import SetupStep3Commands from '@/components/setup/SetupStep3Commands.vue'

// --- Mock stores ---

const mockUnsub = vi.fn()
const mockWsOn = vi.fn(() => mockUnsub)

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: mockWsOn,
    off: vi.fn(),
    isConnected: true,
  }),
}))

const mockClipboardCopy = vi.fn(() => Promise.resolve(true))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: mockClipboardCopy,
  }),
}))

// --- Fetch mock ---

const MOCK_PROMPT_TEXT = 'Install the GiljoAI CLI integration. This is a one-time setup.'

function mockFetchSuccess(prompt = MOCK_PROMPT_TEXT) {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ prompt }),
    }),
  )
}

function mockFetchFailure(status = 500) {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({}),
    }),
  )
}

// --- Mount helper ---

function mountStep3(props = {}) {
  return mount(SetupStep3Commands, {
    props: {
      selectedTools: ['claude_code'],
      connectedTools: ['claude_code'],
      ...props,
    },
    global: {
      plugins: [createPinia()],
      stubs: {
        'v-btn-toggle': { template: '<div class="v-btn-toggle"><slot /></div>' },
        'v-expand-transition': { template: '<div><slot /></div>' },
        Transition: { template: '<div><slot /></div>' },
      },
    },
  })
}

// --- Tests ---

describe('SetupStep3Commands', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchSuccess()
  })

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------
  describe('Rendering', () => {
    it('renders heading text', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Install commands and agents')
    })

    it('renders bootstrap prompt for connected tool', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain(MOCK_PROMPT_TEXT)
    })

    it('renders instruction label with tool name', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Paste this into your Claude Code terminal')
    })

    it('does not show tab bar with single connected tool', async () => {
      const wrapper = mountStep3({ connectedTools: ['claude_code'] })
      await flushPromises()
      expect(wrapper.find('.tool-tabs').exists()).toBe(false)
    })

    it('shows tab bar with multiple connected tools', async () => {
      const wrapper = mountStep3({
        selectedTools: ['claude_code', 'codex_cli'],
        connectedTools: ['claude_code', 'codex_cli'],
      })
      await flushPromises()
      expect(wrapper.find('.tool-tabs').exists()).toBe(true)
      expect(wrapper.findAll('.tool-tab')).toHaveLength(2)
    })
  })

  // -------------------------------------------------------------------
  // Bootstrap prompt fetch
  // -------------------------------------------------------------------
  describe('Bootstrap prompt fetch', () => {
    it('fetches prompt on mount for each connected tool', async () => {
      mountStep3({ connectedTools: ['claude_code', 'gemini_cli'] })
      await flushPromises()
      expect(global.fetch).toHaveBeenCalledTimes(2)
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/download/bootstrap-prompt?platform=claude_code',
        expect.objectContaining({ method: 'GET' }),
      )
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/download/bootstrap-prompt?platform=gemini_cli',
        expect.objectContaining({ method: 'GET' }),
      )
    })

    it('shows loading state while fetching', () => {
      // Use a never-resolving fetch to keep loading state
      global.fetch = vi.fn(() => new Promise(() => {}))
      const wrapper = mountStep3()
      expect(wrapper.find('.prompt-loading').exists()).toBe(true)
      expect(wrapper.text()).toContain('Fetching bootstrap prompt')
    })

    it('shows error state when fetch fails', async () => {
      mockFetchFailure(500)
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.find('.prompt-error').exists()).toBe(true)
      expect(wrapper.text()).toContain('Failed')
    })

    it('retries fetch when retry button is clicked', async () => {
      mockFetchFailure(500)
      const wrapper = mountStep3()
      await flushPromises()

      // Now make fetch succeed
      mockFetchSuccess()
      const retryBtn = wrapper.find('.retry-btn')
      expect(retryBtn.exists()).toBe(true)
      await retryBtn.trigger('click')
      await flushPromises()

      expect(wrapper.find('.prompt-error').exists()).toBe(false)
      expect(wrapper.text()).toContain(MOCK_PROMPT_TEXT)
    })
  })

  // -------------------------------------------------------------------
  // Copy functionality
  // -------------------------------------------------------------------
  describe('Copy functionality', () => {
    it('renders copy button', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Copy to Clipboard')
    })

    it('copies prompt text when copy button is clicked', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const copyBtn = wrapper.find('.copy-btn')
      expect(copyBtn.exists()).toBe(true)
      await copyBtn.trigger('click')
      await flushPromises()

      expect(mockClipboardCopy).toHaveBeenCalledWith(MOCK_PROMPT_TEXT)
    })
  })

  // -------------------------------------------------------------------
  // Mini-checklist
  // -------------------------------------------------------------------
  describe('Mini-checklist', () => {
    it('starts with both checkmarks unchecked', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      const items = wrapper.findAll('.checklist-item')
      expect(items).toHaveLength(2)
      expect(wrapper.text()).toContain('Slash commands installed')
      expect(wrapper.text()).toContain('Agents downloaded')
      // Neither should have the --done class
      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(0)
    })

    it('flips slash command checkmark on WebSocket event', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      // Find the handler registered for setup:commands_installed
      const onCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      expect(onCall).toBeTruthy()

      const handler = onCall[1]
      handler({ tool_name: 'claude_code', command_count: 5 })
      await flushPromises()

      const doneItems = wrapper.findAll('.checklist-text--done')
      expect(doneItems).toHaveLength(1)
      expect(doneItems[0].text()).toBe('Slash commands installed')
    })

    it('flips agent download checkmark on WebSocket event', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const onCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )
      expect(onCall).toBeTruthy()

      const handler = onCall[1]
      handler({ agent_count: 3 })
      await flushPromises()

      const doneItems = wrapper.findAll('.checklist-text--done')
      expect(doneItems).toHaveLength(1)
      expect(doneItems[0].text()).toBe('Agents downloaded')
    })

    it('marks both checkmarks when both events fire', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )

      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(2)
    })
  })

  // -------------------------------------------------------------------
  // Post-install command display
  // -------------------------------------------------------------------
  describe('Post-install command', () => {
    it('does not show agent command before commands installed', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).not.toContain('/gil_get_agents')
    })

    it('shows /gil_get_agents after slash commands installed for claude_code', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      await flushPromises()

      expect(wrapper.text()).toContain('/gil_get_agents')
      expect(wrapper.text()).toContain('Now run this command')
      expect(wrapper.text()).toContain('Use default model for all')
    })

    it('shows $gil-get-agents for codex_cli', async () => {
      const wrapper = mountStep3({
        selectedTools: ['codex_cli'],
        connectedTools: ['codex_cli'],
      })
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      cmdCall[1]({ tool_name: 'codex_cli', command_count: 5 })
      await flushPromises()

      expect(wrapper.text()).toContain('$gil-get-agents')
    })

    it('shows /gil_get_agents for gemini_cli', async () => {
      const wrapper = mountStep3({
        selectedTools: ['gemini_cli'],
        connectedTools: ['gemini_cli'],
      })
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      cmdCall[1]({ tool_name: 'gemini_cli', command_count: 5 })
      await flushPromises()

      expect(wrapper.text()).toContain('/gil_get_agents')
    })
  })

  // -------------------------------------------------------------------
  // can-proceed logic
  // -------------------------------------------------------------------
  describe('can-proceed', () => {
    it('emits can-proceed false initially', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      expect(events).toBeTruthy()
      expect(events[0]).toEqual([false])
    })

    it('emits can-proceed true when both checkmarks are green for at least 1 tool', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )

      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([true])
    })

    it('does not emit can-proceed true with only commands installed', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([false])
    })
  })

  // -------------------------------------------------------------------
  // step-data emit
  // -------------------------------------------------------------------
  describe('step-data', () => {
    it('emits step-data with installed tools after both events fire', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )

      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      const events = wrapper.emitted('step-data')
      expect(events).toBeTruthy()
      const lastEmit = events[events.length - 1][0]
      expect(lastEmit.installedTools).toContain('claude_code')
    })
  })

  // -------------------------------------------------------------------
  // Skip link
  // -------------------------------------------------------------------
  describe('Skip link', () => {
    it('renders skip link', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.find('.skip-link').exists()).toBe(true)
      expect(wrapper.text()).toContain("Skip")
      expect(wrapper.text()).toContain("I'll do this later")
    })

    it('emits skip event when clicked', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      await wrapper.find('.skip-link').trigger('click')
      expect(wrapper.emitted('skip')).toBeTruthy()
    })

    it('emits skip event on Enter keypress', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      await wrapper.find('.skip-link').trigger('keydown.enter')
      expect(wrapper.emitted('skip')).toBeTruthy()
    })
  })

  // -------------------------------------------------------------------
  // Tab switching (multi-tool)
  // -------------------------------------------------------------------
  describe('Tab switching', () => {
    it('switches active tool on tab click', async () => {
      const wrapper = mountStep3({
        selectedTools: ['claude_code', 'codex_cli'],
        connectedTools: ['claude_code', 'codex_cli'],
      })
      await flushPromises()

      const tabs = wrapper.findAll('.tool-tab')
      expect(tabs).toHaveLength(2)

      await tabs[1].trigger('click')
      await flushPromises()

      expect(tabs[1].classes()).toContain('tool-tab--active')
    })

    it('shows tab status dot as complete when both checkmarks are green', async () => {
      const wrapper = mountStep3({
        selectedTools: ['claude_code', 'codex_cli'],
        connectedTools: ['claude_code', 'codex_cli'],
      })
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )

      cmdCall[1]({ tool_name: 'claude_code', command_count: 5 })
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      const dots = wrapper.findAll('.tab-status-dot')
      // claude_code should be complete (both events), codex_cli should be complete (agents is user-level)
      // Actually agents_downloaded marks ALL tools, so codex has agents=true but commands=false
      // Only claude_code has both
      expect(dots[0].classes()).toContain('tab-status-dot--complete')
      expect(dots[1].classes()).not.toContain('tab-status-dot--complete')
    })
  })

  // -------------------------------------------------------------------
  // WebSocket cleanup
  // -------------------------------------------------------------------
  describe('Cleanup', () => {
    it('subscribes to both WebSocket events on mount', async () => {
      mountStep3()
      await flushPromises()

      const eventTypes = mockWsOn.mock.calls.map((c) => c[0])
      expect(eventTypes).toContain('setup:commands_installed')
      expect(eventTypes).toContain('setup:agents_downloaded')
    })

    it('unsubscribes from WebSocket events on unmount', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      wrapper.unmount()
      // mockUnsub is called for each subscription
      expect(mockUnsub).toHaveBeenCalledTimes(2)
    })
  })
})
