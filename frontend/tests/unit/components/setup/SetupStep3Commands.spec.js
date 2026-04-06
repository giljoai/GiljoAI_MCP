/**
 * Unit tests for SetupStep3Commands component (Handover 0855e)
 * Covers: rendering, giljo_setup command display, mini-checklist, WebSocket events,
 * post-install agent command, can-proceed logic, skip behavior, tab switching.
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
        Transition: { template: '<div><slot /></div>' },
      },
    },
  })
}

// --- Tests ---

describe('SetupStep3Commands', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------
  describe('Rendering', () => {
    it('renders heading text', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Install Skills and Agents')
    })

    it('renders giljo_setup command', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('giljo_setup')
    })

    it('renders instruction text with tool name', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Ask your Claude Code to run:')
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
  // Mini-checklist
  // -------------------------------------------------------------------
  describe('Mini-checklist', () => {
    it('starts with both checkmarks unchecked', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      const items = wrapper.findAll('.checklist-item')
      expect(items).toHaveLength(2)
      expect(wrapper.text()).toContain('Skills downloaded')
      expect(wrapper.text()).toContain('Agents downloaded')
      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(0)
    })

    it('flips skills checkmark on setup:commands_installed WebSocket event', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const onCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      expect(onCall).toBeTruthy()

      onCall[1]({ tool_name: 'claude_code' })
      await flushPromises()

      const doneItems = wrapper.findAll('.checklist-text--done')
      expect(doneItems).toHaveLength(1)
      expect(doneItems[0].text()).toBe('Skills downloaded')
    })

    it('flips agents checkmark on setup:agents_downloaded WebSocket event', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const onCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )
      expect(onCall).toBeTruthy()

      onCall[1]({ agent_count: 3 })
      await flushPromises()

      const doneItems = wrapper.findAll('.checklist-text--done')
      expect(doneItems).toHaveLength(1)
      expect(doneItems[0].text()).toBe('Agents downloaded')
    })

    it('marks both checkmarks when setup:bootstrap_complete fires', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const onCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:bootstrap_complete',
      )
      expect(onCall).toBeTruthy()

      onCall[1]({})
      await flushPromises()

      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(2)
    })

    it('marks both checkmarks when both individual events fire', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )

      cmdCall[1]({ tool_name: 'claude_code' })
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(2)
    })
  })

  // -------------------------------------------------------------------
  // Post-install agent command display
  // -------------------------------------------------------------------
  describe('Post-install agent command', () => {
    it('does not show agent command before agents are downloaded', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).not.toContain('/gil_get_agents')
    })

    it('shows /gil_get_agents for claude_code after agents are downloaded', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      expect(wrapper.text()).toContain('/gil_get_agents')
    })

    it('shows $gil-get-agents for codex_cli after agents are downloaded', async () => {
      const wrapper = mountStep3({
        selectedTools: ['codex_cli'],
        connectedTools: ['codex_cli'],
      })
      await flushPromises()

      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )
      agentCall[1]({ agent_count: 3 })
      await flushPromises()

      expect(wrapper.text()).toContain('$gil-get-agents')
    })

    it('shows /gil_get_agents for gemini_cli after agents are downloaded', async () => {
      const wrapper = mountStep3({
        selectedTools: ['gemini_cli'],
        connectedTools: ['gemini_cli'],
      })
      await flushPromises()

      const agentCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:agents_downloaded',
      )
      agentCall[1]({ agent_count: 3 })
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

    it('emits can-proceed true when commands are installed for at least 1 tool', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )
      cmdCall[1]({ tool_name: 'claude_code' })
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([true])
    })

    it('does not emit can-proceed true with no commands installed', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([false])
    })

    it('emits can-proceed true via bootstrap_complete event', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const bootstrapCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:bootstrap_complete',
      )
      bootstrapCall[1]({})
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([true])
    })
  })

  // -------------------------------------------------------------------
  // step-data emit
  // -------------------------------------------------------------------
  describe('step-data', () => {
    it('emits step-data with installed tools after commands installed', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )

      cmdCall[1]({ tool_name: 'claude_code' })
      await flushPromises()

      const events = wrapper.emitted('step-data')
      expect(events).toBeTruthy()
      const lastEmit = events[events.length - 1][0]
      expect(lastEmit.installedTools).toContain('claude_code')
    })
  })

  // -------------------------------------------------------------------
  // previouslyCompleted prop
  // -------------------------------------------------------------------
  describe('previouslyCompleted prop', () => {
    it('pre-fills both checkmarks when previouslyCompleted is true', async () => {
      const wrapper = mountStep3({ previouslyCompleted: true })
      await flushPromises()

      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(2)
    })

    it('emits can-proceed true immediately when previouslyCompleted is true', async () => {
      const wrapper = mountStep3({ previouslyCompleted: true })
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      expect(events).toBeTruthy()
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([true])
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

    it('emits can-proceed when one tool has commands installed in multi-tool setup', async () => {
      const wrapper = mountStep3({
        selectedTools: ['claude_code', 'codex_cli'],
        connectedTools: ['claude_code', 'codex_cli'],
      })
      await flushPromises()

      const cmdCall = mockWsOn.mock.calls.find(
        (call) => call[0] === 'setup:commands_installed',
      )

      cmdCall[1]({ tool_name: 'claude_code' })
      await flushPromises()

      const events = wrapper.emitted('can-proceed')
      const lastEmit = events[events.length - 1]
      expect(lastEmit).toEqual([true])
    })
  })

  // -------------------------------------------------------------------
  // WebSocket cleanup
  // -------------------------------------------------------------------
  describe('Cleanup', () => {
    it('subscribes to all three WebSocket events on mount', async () => {
      mountStep3()
      await flushPromises()

      const eventTypes = mockWsOn.mock.calls.map((c) => c[0])
      expect(eventTypes).toContain('setup:commands_installed')
      expect(eventTypes).toContain('setup:agents_downloaded')
      expect(eventTypes).toContain('setup:bootstrap_complete')
    })

    it('unsubscribes from all WebSocket events on unmount', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      wrapper.unmount()
      expect(mockUnsub).toHaveBeenCalledTimes(3)
    })
  })
})
