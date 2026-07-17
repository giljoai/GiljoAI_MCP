import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// ---------- Mocks ----------
let wsHandlers = {}
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: (event, handler) => {
      wsHandlers[event] = handler
      return () => {}
    },
  }),
}))

let mockSelectedTools = ['claude_code', 'codex_cli']
const updateSetupState = vi.fn().mockResolvedValue({})
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { setup_selected_tools: mockSelectedTools },
    updateSetupState,
  }),
}))

// ConnectToolCard's dependencies (rendered real within the directory).
vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      getActive: vi.fn().mockResolvedValue({ data: [] }),
      create: vi.fn().mockResolvedValue({ data: { api_key: 'gk_test' } }),
    },
  },
}))
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockResolvedValue({
      api: { host: 'localhost', port: '7272', protocol: 'http', ssl_enabled: false },
      giljo_mode: 'saas',
    }),
  },
}))
vi.mock('@/composables/useClipboard', () => ({ useClipboard: () => ({ copy: vi.fn().mockResolvedValue(true) }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const globalStubs = {
  'v-text-field': { template: '<input class="v-text-field-stub" />', props: ['modelValue'] },
  'v-icon': { template: '<i class="v-icon-stub"><slot /></i>' },
  'v-btn': { template: '<button class="v-btn-stub" @click="$emit(\'click\', $event)"><slot /></button>', emits: ['click'] },
  'v-progress-circular': { template: '<span />' },
  'v-alert': { template: '<div><slot /></div>' },
  'v-expand-transition': { template: '<div><slot /></div>' },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
}

async function mountDir() {
  const ToolsConnectDirectory = (await import('@/components/tools/ToolsConnectDirectory.vue')).default
  const wrapper = mount(ToolsConnectDirectory, { global: { stubs: globalStubs } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  wsHandlers = {}
  mockSelectedTools = ['claude_code', 'codex_cli']
  updateSetupState.mockClear()
})

describe('ToolsConnectDirectory (C2, FE-9204)', () => {
  it('lists the fleet from setup_selected_tools with a + Add a tool row', async () => {
    const wrapper = await mountDir()
    expect(wrapper.find('[data-testid="dir-tool-claude_code"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="dir-tool-codex_cli"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="dir-add-tool"]').exists()).toBe(true)
  })

  it('selecting a tool shows its shared connect card in the action window', async () => {
    const wrapper = await mountDir()
    await wrapper.find('[data-testid="dir-tool-codex_cli"]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-testid="connect-card-codex_cli"]').exists()).toBe(true)
  })

  it('+ Add a tool opens the six-tool picker in the action window', async () => {
    const wrapper = await mountDir()
    await wrapper.find('[data-testid="dir-add-tool"]').trigger('click')
    await nextTick()
    for (const id of ['claude_code', 'opencode', 'generic']) {
      expect(wrapper.find(`[data-testid="dir-pick-${id}"]`).exists()).toBe(true)
    }
  })

  it('picking a new tool adds it to the fleet and persists the selection', async () => {
    const wrapper = await mountDir()
    await wrapper.find('[data-testid="dir-add-tool"]').trigger('click')
    await nextTick()
    await wrapper.find('[data-testid="dir-pick-opencode"]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-testid="dir-tool-opencode"]').exists()).toBe(true)
    expect(updateSetupState).toHaveBeenCalledWith(
      expect.objectContaining({ setup_selected_tools: expect.arrayContaining(['opencode']) }),
    )
    // The newly added tool becomes the selected card.
    expect(wrapper.find('[data-testid="connect-card-opencode"]').exists()).toBe(true)
  })

  it('the generic connect event flips only the SELECTED tool (active-only, proposal §6)', async () => {
    const wrapper = await mountDir()
    // Default selection is the first fleet tool (claude_code).
    wsHandlers['setup:tool_connected']({ tool_name: 'mcp_connected' })
    await nextTick()
    expect(wrapper.find('[data-testid="dir-tool-claude_code"] .dir-rail-dot--connected').exists()).toBe(true)
    expect(wrapper.find('[data-testid="dir-tool-codex_cli"] .dir-rail-dot--connected').exists()).toBe(false)
  })

  it('removing a tool drops it from the fleet and persists', async () => {
    const wrapper = await mountDir()
    await wrapper.find('[data-testid="dir-remove-tool"]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-testid="dir-tool-claude_code"]').exists()).toBe(false)
    expect(updateSetupState).toHaveBeenCalledWith(
      expect.objectContaining({ setup_selected_tools: expect.not.arrayContaining(['claude_code']) }),
    )
  })
})
