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
      // Gradient Rail redesign (FE-6259b) renamed the heading to cover both
      // skills and agent templates in one line.
      expect(wrapper.text()).toContain('Install skills & agents')
    })

    it('renders giljo_setup command', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('giljo_setup')
    })

    it('renders instruction text with tool name', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('Ask your Claude Code CLI to run:')
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
    it('starts with checklist unchecked', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      const items = wrapper.findAll('.checklist-item')
      expect(items).toHaveLength(2)
      expect(wrapper.findAll('.checklist-text--done')).toHaveLength(0)
    })

    it('flips checkmark on setup:bootstrap_complete WebSocket event', async () => {
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
  })

  // -------------------------------------------------------------------
  // Post-install agent refresh hint (shown after agents are installed)
  // -------------------------------------------------------------------
  describe('Post-install agent refresh hint', () => {
    it('points to giljo_setup "Agents only" after setup completes', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      const onCall = mockWsOn.mock.calls.find((c) => c[0] === 'setup:bootstrap_complete')
      onCall[1]({})
      await flushPromises()

      expect(wrapper.text()).toContain('giljo_setup')
      expect(wrapper.text()).toContain('Agents only')
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
    it('pre-fills checkmark when previouslyCompleted is true', async () => {
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
  // Skip control — moved to the shared wizard footer (FE-6259b: the
  // Gradient Rail redesign centralizes the step-1/step-2 skip control in
  // SetupWizardOverlay's footer instead of each step owning its own
  // skip link — see SetupWizardOverlay.vue footerSkipLabel/handleFooterSkip
  // and the passing coverage in
  // src/components/setup/__tests__/SetupWizardOverlay.spec.js). This
  // component no longer renders a skip link or emits 'skip' on its own;
  // verify that delegation held and that the remaining escape hatch at
  // this level (the manual-setup pointer) still renders.
  // -------------------------------------------------------------------
  describe('Skip control (delegated to wizard footer, FE-6259b)', () => {
    it('does not render its own skip link (control now lives in the wizard footer)', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.find('.skip-link').exists()).toBe(false)
    })

    it('does not emit a "skip" event on its own — SetupWizardOverlay owns skip now', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.emitted('skip')).toBeUndefined()
    })

    it('still points users to manual setup as a fallback', async () => {
      const wrapper = mountStep3()
      await flushPromises()
      expect(wrapper.text()).toContain('For manual setup, go to')
      expect(wrapper.text()).toContain('Tools')
      expect(wrapper.text()).toContain('Connect')
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
    it('subscribes to WebSocket events on mount', async () => {
      mountStep3()
      await flushPromises()

      const eventTypes = mockWsOn.mock.calls.map((c) => c[0])
      expect(eventTypes).toContain('setup:commands_installed')
      expect(eventTypes).toContain('setup:agents_downloaded')
      expect(eventTypes).toContain('setup:bootstrap_complete')
    })

    it('unsubscribes from WebSocket events on unmount', async () => {
      const wrapper = mountStep3()
      await flushPromises()

      wrapper.unmount()
      expect(mockUnsub).toHaveBeenCalledTimes(3)
    })
  })
})
